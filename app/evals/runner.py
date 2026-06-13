from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import time
from typing import Any, Optional, Union

import yaml

from app.review_schema import ReviewFormatError, validate_review_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
SENSITIVE_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")
TEMPLATE_PATTERN = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def _utc_timestamp() -> str:
    """Return a UTC timestamp string for run metadata."""

    return datetime.now(timezone.utc).isoformat()


def _load_yaml(file_path: Path) -> dict[str, Any]:
    """Load a YAML file into a Python dictionary."""

    with file_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML object in {file_path}")
    return payload


def _load_json(file_path: Path) -> dict[str, Any]:
    """Load a JSON file into a Python dictionary."""

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {file_path}")
    return payload


def _lookup_context_value(context: dict[str, Any], dotted_key: str) -> Any:
    """Resolve a dotted template path like `inputs.diff_file`."""

    current: Any = context
    for part in dotted_key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        raise KeyError(f"Unknown template variable: {dotted_key}")
    return current


def _render_template(template: str, context: dict[str, Any]) -> str:
    """Render `{{ dotted.path }}` placeholders using a context dictionary."""

    def replacer(match: re.Match[str]) -> str:
        value = _lookup_context_value(context, match.group(1).strip())
        return str(value)

    return TEMPLATE_PATTERN.sub(replacer, template)


def _scrub_env_snapshot(env: dict[str, str]) -> dict[str, str]:
    """Keep a debug-friendly environment snapshot without leaking secrets."""

    safe_env: dict[str, str] = {}
    for key, value in sorted(env.items()):
        if any(marker in key.upper() for marker in SENSITIVE_ENV_MARKERS):
            safe_env[key] = "[redacted]"
        else:
            safe_env[key] = value
    return safe_env


def _parse_changed_files(diff_file: Path) -> list[str]:
    """Extract changed file paths from a unified diff file."""

    changed_files: list[str] = []
    for line in diff_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("+++ b/"):
            changed_files.append(line.removeprefix("+++ b/"))
    return changed_files


def _parse_changed_files_from_trace(trace: dict[str, Any]) -> list[str]:
    """Extract changed files from any tool result that returns file entries."""

    changed_files: list[str] = []
    for event in trace.get("events", []):
        if event.get("type") != "tool_result":
            continue
        if event.get("tool_name") != "fetch_files":
            continue

        result = event.get("result", [])
        if not isinstance(result, list):
            continue

        for item in result:
            if not isinstance(item, dict):
                continue
            filename = item.get("filename")
            if isinstance(filename, str) and filename and filename not in changed_files:
                changed_files.append(filename)

    return changed_files


def _load_script_module(script_path: Path) -> Any:
    """Load a script judge module from disk."""

    module_name = f"eval_judge_{script_path.stem}_{abs(hash(script_path))}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Failed to load judge script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_run_id(label: str) -> str:
    """Create a filesystem-friendly run identifier."""

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", label).strip("_") or "run"
    return f"{timestamp}_{slug}"


def _build_case_context(
    case_data: dict[str, Any], case_path: Path, case_dir: Path, run_id: str
) -> dict[str, Any]:
    """Build a templating context for one case execution."""

    case_root = case_path.parent
    raw_inputs = case_data.get("inputs", {})
    resolved_inputs: dict[str, Any] = {}
    for key, value in raw_inputs.items():
        if isinstance(value, str):
            candidate = (case_root / value).resolve()
            resolved_inputs[key] = str(candidate) if candidate.exists() else value
        else:
            resolved_inputs[key] = value

    return {
        "repo_root": str(REPO_ROOT),
        "python_executable": sys.executable,
        "case_dir": str(case_root),
        "run_id": run_id,
        "case": {
            "id": case_data["id"],
            "task_type": case_data.get("task_type", "unknown"),
        },
        "inputs": resolved_inputs,
        "artifacts": {
            "case_dir": str(case_dir),
            "input_snapshot_dir": str(case_dir / "input_snapshot"),
            "command_txt": str(case_dir / "command.txt"),
            "stdout_txt": str(case_dir / "stdout.txt"),
            "stderr_txt": str(case_dir / "stderr.txt"),
            "execution_json": str(case_dir / "execution.json"),
            "output_json": str(case_dir / "output.json"),
            "trace_json": str(case_dir / "trace.json"),
            "normalized_json": str(case_dir / "normalized.json"),
            "judge_results_json": str(case_dir / "judge_results.json"),
            "investigation_md": str(case_dir / "investigation.md"),
        },
    }


def _snapshot_inputs(case_path: Path, case_data: dict[str, Any], case_dir: Path) -> None:
    """Copy declared input files into the run artifact directory."""

    snapshot_dir = case_dir / "input_snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    for value in case_data.get("inputs", {}).values():
        if not isinstance(value, str):
            continue
        source = (case_path.parent / value).resolve()
        if source.exists() and source.is_file():
            shutil.copy2(source, snapshot_dir / source.name)


def _normalize_case_output(
    case_data: dict[str, Any],
    run_id: str,
    output_path: Path,
    trace_path: Optional[Path],
    execution: dict[str, Any],
    diff_file: Optional[Path],
) -> dict[str, Any]:
    """Normalize raw execution outputs into a stable structure for judges."""

    normalized: dict[str, Any] = {
        "case_id": case_data["id"],
        "run_id": run_id,
        "execution": execution,
        "raw_output": {
            "path": str(output_path),
            "exists": output_path.exists(),
        },
        "raw_trace": {
            "path": str(trace_path) if trace_path else None,
            "exists": trace_path.exists() if trace_path else False,
        },
        "parsed_output": None,
        "parse_error": None,
        "trace": None,
        "trace_error": None,
        "input_analysis": {
            "changed_files": _parse_changed_files(diff_file) if diff_file else [],
        },
    }

    if not output_path.exists():
        normalized["parse_error"] = f"Expected output file was not created: {output_path}"
        return normalized

    raw_text = output_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        normalized["parse_error"] = "Output file is empty."
        return normalized

    try:
        payload = json.loads(raw_text)
        normalized["parsed_output"] = validate_review_payload(payload)
    except (json.JSONDecodeError, ReviewFormatError) as error:
        normalized["parse_error"] = str(error)

    if trace_path:
        if trace_path.exists():
            try:
                trace_payload = _load_json(trace_path)
                normalized["trace"] = trace_payload
                if not normalized["input_analysis"]["changed_files"]:
                    normalized["input_analysis"]["changed_files"] = _parse_changed_files_from_trace(
                        trace_payload
                    )
            except (ValueError, json.JSONDecodeError) as error:
                normalized["trace_error"] = str(error)
        else:
            normalized["trace_error"] = f"Expected trace file was not created: {trace_path}"

    return normalized


def _run_judge(
    judge_config: dict[str, Any],
    case_data: dict[str, Any],
    normalized_output: dict[str, Any],
    reference: dict[str, Any],
) -> dict[str, Any]:
    """Execute one script judge and normalize its result shape."""

    script_relative_path = judge_config.get("config", {}).get("script")
    if not script_relative_path:
        raise ValueError(f"Judge '{judge_config.get('name', 'unknown')}' is missing config.script")

    script_path = (REPO_ROOT / script_relative_path).resolve()
    module = _load_script_module(script_path)
    raw_result = module.judge(
        case=case_data,
        normalized_output=normalized_output,
        reference=reference,
        config=judge_config.get("config", {}),
    )

    return {
        "judge_name": raw_result.get("judge_name", judge_config.get("name", "unknown")),
        "judge_type": raw_result.get("judge_type", judge_config.get("type", "script")),
        "status": raw_result.get("status", "ok"),
        "score": raw_result.get("score"),
        "pass": bool(raw_result.get("pass", False)),
        "rationale": raw_result.get("rationale", ""),
        "evidence": raw_result.get("evidence", []),
        "error": raw_result.get("error"),
    }


def _write_investigation_note(case_dir: Path, case_result: dict[str, Any]) -> None:
    """Create a small investigation note for failed eval cases."""

    if case_result["pass"]:
        return

    failed_judges = [judge for judge in case_result["judge_results"] if not judge["pass"]]
    lines = [
        f"# Investigation: {case_result['case_id']}",
        "",
        f"- Run ID: `{case_result['run_id']}`",
        f"- Execution status: `{case_result['execution']['status']}`",
        f"- Case pass: `{case_result['pass']}`",
        "",
        "## Failed Judges",
    ]
    for judge in failed_judges:
        lines.extend(
            [
                f"- `{judge['judge_name']}`: {judge['rationale']}",
                f"  Evidence: {json.dumps(judge.get('evidence', []))}",
            ]
        )

    lines.extend(
        [
            "",
            "## Suspected Root Cause",
            "- Fill this in after reviewing stdout, stderr, normalized output, and judge results.",
            "",
            "## Proposed Fix",
            "- Fill this in after triage.",
        ]
    )

    (case_dir / "investigation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_case(case_path: Union[str, Path], run_root: Path, run_id: str) -> dict[str, Any]:
    """Run one case, save artifacts, and return a structured result summary."""

    case_file = Path(case_path).resolve()
    case_data = _load_yaml(case_file)
    case_name = f"{case_data.get('task_type', 'task')}__{case_data['id']}"
    case_dir = run_root / "cases" / case_name
    case_dir.mkdir(parents=True, exist_ok=True)

    context = _build_case_context(case_data, case_file, case_dir, run_id)
    _snapshot_inputs(case_file, case_data, case_dir)

    run_config = case_data.get("run", {})
    command = _render_template(run_config["command"], context)
    cwd_value = run_config.get("cwd", "{{repo_root}}")
    cwd = Path(_render_template(cwd_value, context))
    timeout_seconds = int(run_config.get("timeout_seconds", 60))
    env_overrides = {
        key: _render_template(str(value), context)
        for key, value in run_config.get("env", {}).items()
    }

    env = os.environ.copy()
    env.update(env_overrides)

    resolved_output_path = Path(
        _render_template(
            case_data.get("expected", {}).get("output_path", "{{artifacts.output_json}}"),
            context,
        )
    )
    trace_path_value = case_data.get("expected", {}).get("trace_path")
    resolved_trace_path = (
        Path(_render_template(trace_path_value, context))
        if isinstance(trace_path_value, str)
        else None
    )
    diff_file_value = case_data.get("inputs", {}).get("diff_file")
    diff_file = (case_file.parent / diff_file_value).resolve() if diff_file_value else None

    (case_dir / "command.txt").write_text(command + "\n", encoding="utf-8")
    (case_dir / "env_snapshot.json").write_text(
        json.dumps(_scrub_env_snapshot(env_overrides), indent=2) + "\n",
        encoding="utf-8",
    )

    started_at = time()
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
        timed_out = False
    except subprocess.TimeoutExpired as error:
        completed = error
        timed_out = True

    stdout_text = completed.stdout or ""
    stderr_text = completed.stderr or ""
    exit_code = None if timed_out else completed.returncode
    duration_ms = int((time() - started_at) * 1000)

    (case_dir / "stdout.txt").write_text(stdout_text, encoding="utf-8")
    (case_dir / "stderr.txt").write_text(stderr_text, encoding="utf-8")

    execution = {
        "status": "timeout"
        if timed_out
        else ("completed" if exit_code == 0 else "failed"),
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "command": command,
        "cwd": str(cwd),
        "timeout_seconds": timeout_seconds,
    }
    (case_dir / "execution.json").write_text(json.dumps(execution, indent=2) + "\n", encoding="utf-8")

    normalized = _normalize_case_output(
        case_data=case_data,
        run_id=run_id,
        output_path=resolved_output_path,
        trace_path=resolved_trace_path,
        execution=execution,
        diff_file=diff_file,
    )
    (case_dir / "normalized.json").write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")

    reference = {}
    reference_file_name = case_data.get("expected", {}).get("reference_file")
    if reference_file_name:
        reference = _load_json((case_file.parent / reference_file_name).resolve())

    judge_results = [
        _run_judge(judge, case_data, normalized, reference)
        for judge in case_data.get("judges", [])
    ]
    (case_dir / "judge_results.json").write_text(
        json.dumps(judge_results, indent=2) + "\n",
        encoding="utf-8",
    )

    case_pass = (
        execution["status"] == "completed"
        and normalized["parse_error"] is None
        and all(judge["pass"] for judge in judge_results)
    )
    case_result = {
        "case_id": case_data["id"],
        "description": case_data.get("description", ""),
        "task_type": case_data.get("task_type", "unknown"),
        "tags": case_data.get("tags", []),
        "priority": case_data.get("priority", "medium"),
        "run_id": run_id,
        "pass": case_pass,
        "execution": execution,
        "normalized_path": str(case_dir / "normalized.json"),
        "judge_results": judge_results,
    }

    _write_investigation_note(case_dir, case_result)
    return case_result


def _load_suite_cases(suite_path: Path) -> tuple[str, list[Path]]:
    """Load a suite manifest and resolve its case paths."""

    suite_data = _load_yaml(suite_path)
    case_paths = [(REPO_ROOT / case_path).resolve() for case_path in suite_data.get("cases", [])]
    return suite_data.get("name", suite_path.stem), case_paths


def _build_summary(run_id: str, suite_name: str, case_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate case-level results into a suite-level summary."""

    total_cases = len(case_results)
    passed_cases = sum(1 for result in case_results if result["pass"])
    failed_cases = total_cases - passed_cases
    parse_successes = sum(
        1
        for result in case_results
        if result["execution"]["status"] == "completed"
        and all(judge["judge_name"] != "schema_valid" or judge["pass"] for judge in result["judge_results"])
    )
    average_duration_ms = (
        round(sum(result["execution"]["duration_ms"] for result in case_results) / total_cases, 2)
        if total_cases
        else 0
    )

    return {
        "run_id": run_id,
        "suite_name": suite_name,
        "timestamp": _utc_timestamp(),
        "metrics": {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "pass_rate": round(passed_cases / total_cases, 4) if total_cases else 0.0,
            "parse_success_rate": round(parse_successes / total_cases, 4) if total_cases else 0.0,
            "average_duration_ms": average_duration_ms,
        },
        "failed_cases": [
            {
                "case_id": result["case_id"],
                "execution_status": result["execution"]["status"],
                "failed_judges": [
                    judge["judge_name"] for judge in result["judge_results"] if not judge["pass"]
                ],
            }
            for result in case_results
            if not result["pass"]
        ],
        "case_results": case_results,
    }


def _write_summary_markdown(summary: dict[str, Any], destination: Path) -> None:
    """Write a short human-readable summary for the latest run."""

    metrics = summary["metrics"]
    lines = [
        f"# Eval Summary: {summary['suite_name']}",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Timestamp: `{summary['timestamp']}`",
        f"- Total cases: `{metrics['total_cases']}`",
        f"- Passed: `{metrics['passed_cases']}`",
        f"- Failed: `{metrics['failed_cases']}`",
        f"- Pass rate: `{metrics['pass_rate']}`",
        f"- Parse success rate: `{metrics['parse_success_rate']}`",
        f"- Average duration (ms): `{metrics['average_duration_ms']}`",
        "",
        "## Failed Cases",
    ]

    if not summary["failed_cases"]:
        lines.append("- None")
    else:
        for failed_case in summary["failed_cases"]:
            lines.append(
                f"- `{failed_case['case_id']}`: status `{failed_case['execution_status']}`, "
                f"failed judges `{', '.join(failed_case['failed_judges']) or 'none'}`"
            )

    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_cases(case_paths: list[Union[str, Path]], suite_name: str) -> dict[str, Any]:
    """Run a list of cases and persist all suite-level artifacts."""

    run_id = _build_run_id(suite_name)
    run_root = REPO_ROOT / "evals" / "runs" / run_id
    run_root.mkdir(parents=True, exist_ok=True)

    case_results = [run_case(case_path, run_root, run_id) for case_path in case_paths]
    summary = _build_summary(run_id, suite_name, case_results)

    manifest = {
        "run_id": run_id,
        "suite_name": suite_name,
        "started_at": summary["timestamp"],
        "repo_root": str(REPO_ROOT),
        "case_paths": [str(Path(case_path).resolve()) for case_path in case_paths],
    }
    (run_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (run_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    summary_md_path = run_root / "summary.md"
    _write_summary_markdown(summary, summary_md_path)
    latest_report_path = REPO_ROOT / "evals" / "reports" / "latest_summary.md"
    shutil.copy2(summary_md_path, latest_report_path)

    return summary


def run_suite(suite_path: Union[str, Path]) -> dict[str, Any]:
    """Run all cases listed in a suite manifest."""

    suite_file = Path(suite_path).resolve()
    suite_name, case_paths = _load_suite_cases(suite_file)
    return run_cases(case_paths, suite_name)
