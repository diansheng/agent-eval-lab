def judge(case, normalized_output, reference, config):
    parsed_output = normalized_output.get("parsed_output")
    parse_error = normalized_output.get("parse_error")
    execution = normalized_output.get("execution", {})
    passed = execution.get("status") == "completed" and parsed_output is not None and parse_error is None
    return {
        "judge_name": "schema_valid",
        "judge_type": "script",
        "status": "ok",
        "score": 1.0 if passed else 0.0,
        "pass": passed,
        "rationale": "Parsed output matches the expected review schema." if passed else f"Schema validation failed: {parse_error or execution.get('status')}",
        "evidence": [parse_error] if parse_error else [],
        "error": None,
    }
