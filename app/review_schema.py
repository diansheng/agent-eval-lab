import json


SEVERITY_LEVELS = {"high", "medium", "low"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
REVIEW_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": sorted(SEVERITY_LEVELS),
                    },
                    "title": {"type": "string"},
                    "file": {"type": "string"},
                    "comment": {"type": "string"},
                },
                "required": ["severity", "title", "file", "comment"],
                "additionalProperties": False,
            },
        },
        "confidence": {
            "type": "string",
            "enum": sorted(CONFIDENCE_LEVELS),
        },
        "needs_manual_review": {"type": "boolean"},
    },
    "required": ["summary", "findings", "confidence", "needs_manual_review"],
    "additionalProperties": False,
}
REVIEW_OUTPUT_EXAMPLE = {
    "summary": "short overall summary",
    "findings": [
        {
            "severity": "low | medium | high",
            "title": "short finding title",
            "file": "path/to/file.ext",
            "comment": "concise review comment",
        }
    ],
    "confidence": "low | medium | high",
    "needs_manual_review": True,
}


class ReviewFormatError(ValueError):
    """Raised when the model output does not match the expected review JSON shape."""


def render_review_output_example() -> str:
    """Render the shared review JSON example for prompt instructions."""

    return json.dumps(REVIEW_OUTPUT_EXAMPLE, indent=2)


def _extract_embedded_json_object(review_text: str) -> dict | None:
    """Recover a top-level JSON object when the model adds prose around it."""

    decoder = json.JSONDecoder()
    for start_index, character in enumerate(review_text):
        if character != "{":
            continue

        try:
            payload, end_index = decoder.raw_decode(review_text[start_index:])
        except json.JSONDecodeError:
            continue

        trailing = review_text[start_index + end_index :].strip()
        if trailing:
            continue
        if isinstance(payload, dict):
            return payload

    return None


def _extract_fenced_json_object(review_text: str) -> dict | None:
    """Recover JSON from a fenced code block anywhere in the response."""

    for fence in ("```json", "```JSON", "```"):
        start_index = review_text.find(fence)
        if start_index == -1:
            continue

        content_start = start_index + len(fence)
        end_index = review_text.find("```", content_start)
        if end_index == -1:
            continue

        candidate = review_text[content_start:end_index].strip()
        if not candidate:
            continue

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if isinstance(payload, dict):
            return payload

    return None


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
        payload = _extract_fenced_json_object(cleaned)
        if payload is None:
            payload = _extract_embedded_json_object(cleaned)
        if payload is None:
            raise ReviewFormatError(
                "Model output was not valid JSON. Rerun or tighten the prompt."
            ) from error

    return validate_review_payload(payload)


def validate_review_payload(payload: object) -> dict:
    """Validate the final review JSON object and normalize string fields."""

    if not isinstance(payload, dict):
        raise ReviewFormatError("Top-level model output must be a JSON object.")

    required_keys = set(REVIEW_OUTPUT_SCHEMA["required"])
    allowed_keys = set(REVIEW_OUTPUT_SCHEMA["properties"])
    missing_keys = required_keys - payload.keys()
    if missing_keys:
        raise ReviewFormatError(
            "Model output is missing required keys: " + ", ".join(sorted(missing_keys))
        )
    extra_keys = payload.keys() - allowed_keys
    if extra_keys:
        raise ReviewFormatError(
            "Model output has unexpected keys: " + ", ".join(sorted(extra_keys))
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
    finding_schema = REVIEW_OUTPUT_SCHEMA["properties"]["findings"]["items"]
    finding_keys = set(finding_schema["required"])
    allowed_finding_keys = set(finding_schema["properties"])
    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            raise ReviewFormatError(f"Finding {index} must be an object.")

        missing_finding_keys = finding_keys - finding.keys()
        if missing_finding_keys:
            raise ReviewFormatError(
                f"Finding {index} is missing keys: "
                + ", ".join(sorted(missing_finding_keys))
            )
        extra_finding_keys = finding.keys() - allowed_finding_keys
        if extra_finding_keys:
            raise ReviewFormatError(
                f"Finding {index} has unexpected keys: "
                + ", ".join(sorted(extra_finding_keys))
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
