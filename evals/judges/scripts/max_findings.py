def judge(case, normalized_output, reference, config):
    parsed_output = normalized_output.get("parsed_output")
    if not parsed_output:
        return {
            "judge_name": "max_findings",
            "judge_type": "script",
            "status": "skipped",
            "score": None,
            "pass": False,
            "rationale": "Skipped because parsed output is unavailable.",
            "evidence": [normalized_output.get("parse_error")],
            "error": None,
        }

    findings = parsed_output.get("findings", [])
    max_findings = int(config.get("max_findings", reference.get("max_findings", 0)))
    passed = len(findings) <= max_findings
    return {
        "judge_name": "max_findings",
        "judge_type": "script",
        "status": "ok",
        "score": 1.0 if passed else 0.0,
        "pass": passed,
        "rationale": f"Expected at most {max_findings} findings and saw {len(findings)}.",
        "evidence": [finding.get("title", "") for finding in findings],
        "error": None,
    }
