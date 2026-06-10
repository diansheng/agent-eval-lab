import json


SEVERITY_LEVELS = {"high", "medium", "low"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}


class ReviewFormatError(ValueError):
    """Raised when the model output does not match the expected review JSON shape."""


def parse_review_json(review_text: str) -> dict:
    """Parse model text into JSON and validate the final review shape."""

    cleaned = review_text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ReviewFormatError(
            "Model output was not valid JSON. Rerun or tighten the prompt."
        ) from error

    return validate_review_payload(payload)


def validate_review_payload(payload: object) -> dict:
    """Validate the final review JSON object and normalize string fields."""

    if not isinstance(payload, dict):
        raise ReviewFormatError("Top-level model output must be a JSON object.")

    required_keys = {"summary", "findings", "confidence", "needs_manual_review"}
    missing_keys = required_keys - payload.keys()
    if missing_keys:
        raise ReviewFormatError(
            "Model output is missing required keys: " + ", ".join(sorted(missing_keys))
        )

    summary = payload["summary"]
    findings = payload["findings"]
    confidence = payload["confidence"]
    needs_manual_review = payload["needs_manual_review"]

    if not isinstance(summary, str):
        raise ReviewFormatError("'summary' must be a string.")
    if not isinstance(findings, list):
        raise ReviewFormatError("'findings' must be an array.")
    if confidence not in CONFIDENCE_LEVELS:
        raise ReviewFormatError("'confidence' must be one of: high, medium, low.")
    if not isinstance(needs_manual_review, bool):
        raise ReviewFormatError("'needs_manual_review' must be true or false.")

    validated_findings = []
    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            raise ReviewFormatError(f"Finding {index} must be an object.")

        finding_keys = {"severity", "title", "file", "comment"}
        missing_finding_keys = finding_keys - finding.keys()
        if missing_finding_keys:
            raise ReviewFormatError(
                f"Finding {index} is missing keys: "
                + ", ".join(sorted(missing_finding_keys))
            )

        severity = finding["severity"]
        title = finding["title"]
        file_path = finding["file"]
        comment = finding["comment"]

        if severity not in SEVERITY_LEVELS:
            raise ReviewFormatError(
                f"Finding {index} has invalid severity: {severity!r}."
            )
        if not isinstance(title, str) or not title.strip():
            raise ReviewFormatError(f"Finding {index} has an empty title.")
        if not isinstance(file_path, str) or not file_path.strip():
            raise ReviewFormatError(f"Finding {index} has an empty file path.")
        if not isinstance(comment, str) or not comment.strip():
            raise ReviewFormatError(f"Finding {index} has an empty comment.")

        validated_findings.append(
            {
                "severity": severity,
                "title": title.strip(),
                "file": file_path.strip(),
                "comment": comment.strip(),
            }
        )

    return {
        "summary": summary.strip(),
        "findings": validated_findings,
        "confidence": confidence,
        "needs_manual_review": needs_manual_review,
    }
