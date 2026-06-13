def judge(case, normalized_output, reference, config):
    _ = case
    trace = normalized_output.get("trace")
    if not trace:
        return {
            "judge_name": "required_tools",
            "judge_type": "script",
            "status": "skipped",
            "score": None,
            "pass": False,
            "rationale": "Skipped because trace output is unavailable.",
            "evidence": [normalized_output.get("trace_error")],
            "error": None,
        }

    tool_calls = trace.get("tool_calls", [])
    tool_names = [call.get("name") for call in tool_calls if isinstance(call, dict)]
    required_tools = config.get("required_tools") or reference.get("required_tools") or []
    require_order = bool(config.get("require_order", reference.get("require_order", False)))

    missing_tools = [tool for tool in required_tools if tool not in tool_names]
    order_ok = True
    if require_order and not missing_tools:
        positions = [tool_names.index(tool) for tool in required_tools]
        order_ok = positions == sorted(positions)

    passed = not missing_tools and order_ok
    evidence = {
        "tool_names": tool_names,
        "missing_tools": missing_tools,
        "require_order": require_order,
    }
    if require_order:
        evidence["order_ok"] = order_ok

    return {
        "judge_name": "required_tools",
        "judge_type": "script",
        "status": "ok",
        "score": 1.0 if passed else 0.0,
        "pass": passed,
        "rationale": (
            "All required tools were called in the expected order."
            if passed
            else "The run did not call all required tools in the expected order."
        ),
        "evidence": evidence,
        "error": None,
    }
