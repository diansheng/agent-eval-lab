def judge(case, normalized_output, reference, config):
    _ = case
    _ = reference
    trace = normalized_output.get("trace")
    if not trace:
        return {
            "judge_name": "tool_usage",
            "judge_type": "script",
            "status": "skipped",
            "score": None,
            "pass": False,
            "rationale": "Skipped because trace output is unavailable.",
            "evidence": [normalized_output.get("trace_error")],
            "error": None,
        }

    tool_calls = trace.get("tool_calls", [])
    min_tool_calls = int(config.get("min_tool_calls", 1))
    tool_names = [
        call.get("name")
        for call in tool_calls
        if isinstance(call, dict) and isinstance(call.get("name"), str)
    ]
    passed = len(tool_names) >= min_tool_calls

    return {
        "judge_name": "tool_usage",
        "judge_type": "script",
        "status": "ok",
        "score": 1.0 if passed else 0.0,
        "pass": passed,
        "rationale": (
            f"The run used tools at least {min_tool_calls} time(s)."
            if passed
            else f"The run used tools fewer than {min_tool_calls} time(s)."
        ),
        "evidence": {
            "tool_names": tool_names,
            "tool_call_count": len(tool_names),
            "min_tool_calls": min_tool_calls,
        },
        "error": None,
    }
