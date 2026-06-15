def judge(case, normalized_output, reference, config):
    trace = normalized_output.get("trace") or {}
    # For Week 3, trace_file is actually the state.json dumped from the planner
    
    current_step = trace.get("current_step")
    has_verification_results = "verification_results" in trace
    
    passed = current_step == "report" and has_verification_results
    
    return {
        "judge_name": "verify_step_executed",
        "judge_type": "script",
        "status": "ok",
        "score": 1.0 if passed else 0.0,
        "pass": passed,
        "rationale": "Agent completed the report step and outputted verification results." if passed else "Agent did not complete the multi-step verification.",
        "evidence": [f"current_step: {current_step}", f"has_verification_results: {has_verification_results}"],
        "error": None,
    }
