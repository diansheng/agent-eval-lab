def _match_requirement(findings, requirement):
    expected_file = requirement.get("file", "").strip().lower()
    keywords = [keyword.lower() for keyword in requirement.get("keywords", [])]
    min_keyword_hits = int(requirement.get("min_keyword_hits", 1))

    for finding in findings:
        finding_file = str(finding.get("file", "")).strip().lower()
        haystack = f"{finding.get('title', '')} {finding.get('comment', '')}".lower()
        keyword_hits = sum(1 for keyword in keywords if keyword in haystack)
        file_matches = not expected_file or finding_file == expected_file
        if file_matches and keyword_hits >= min_keyword_hits:
            return True, finding

    return False, None


def judge(case, normalized_output, reference, config):
    parsed_output = normalized_output.get("parsed_output")
    if not parsed_output:
        return {
            "judge_name": "finding_recall",
            "judge_type": "script",
            "status": "skipped",
            "score": None,
            "pass": False,
            "rationale": "Skipped because parsed output is unavailable.",
            "evidence": [normalized_output.get("parse_error")],
            "error": None,
        }

    findings = parsed_output.get("findings", [])
    requirements = config.get("required_matches") or reference.get("required_matches") or []
    if not requirements:
        return {
            "judge_name": "finding_recall",
            "judge_type": "script",
            "status": "ok",
            "score": 1.0,
            "pass": True,
            "rationale": "No required matches were configured for this case.",
            "evidence": [],
            "error": None,
        }

    matched = []
    missing = []
    for requirement in requirements:
        ok, finding = _match_requirement(findings, requirement)
        if ok:
            matched.append({"requirement": requirement, "matched_finding": finding})
        else:
            missing.append(requirement)

    score = len(matched) / len(requirements)
    passed = not missing
    return {
        "judge_name": "finding_recall",
        "judge_type": "script",
        "status": "ok",
        "score": round(score, 4),
        "pass": passed,
        "rationale": "All expected findings were present." if passed else "Some expected findings were missing.",
        "evidence": matched if passed else missing,
        "error": None,
    }
