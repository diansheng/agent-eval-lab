def judge(case, normalized_output, reference, config):
    parsed_output = normalized_output.get("parsed_output")
    if not parsed_output:
        return {
            "judge_name": "hallucination_check",
            "judge_type": "script",
            "status": "skipped",
            "score": None,
            "pass": False,
            "rationale": "Skipped because parsed output is unavailable.",
            "evidence": [normalized_output.get("parse_error")],
            "error": None,
        }

    changed_files = set(normalized_output.get("input_analysis", {}).get("changed_files", []))
    findings = parsed_output.get("findings", [])
    bad_findings = [finding for finding in findings if finding.get("file") not in changed_files]
    passed = not bad_findings
    return {
        "judge_name": "hallucination_check",
        "judge_type": "script",
        "status": "ok",
        "score": 1.0 if passed else 0.0,
        "pass": passed,
        "rationale": "All findings referenced changed files." if passed else "Some findings referenced files not present in the diff.",
        "evidence": bad_findings,
        "error": None,
    }
