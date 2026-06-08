# Generic Evaluation Suite Design Plan

## Goal

Design a reusable evaluation suite that lets a developer:

- define test cases with input, setup, explicit run commands, and judges
- execute those cases repeatedly against a system under test
- evaluate outputs with scripts, LLM judges, or hybrid judges
- inspect failures with enough artifacts to debug them
- improve prompts, code, tools, or workflows based on the evidence

This is intended to be generic, not tied only to PR review. The same framework should work for:

- prompt-only apps
- tool-using agents
- multi-step workflows
- CLI programs
- API services
- batch pipelines

## Design Principles

- `Explicit over implicit`: every case should declare exactly what gets run and how it is judged
- `Artifact-first`: every run should leave behind inputs, outputs, logs, metadata, and judge decisions
- `Composable judges`: allow script judges, LLM judges, and judge pipelines
- `Deterministic where possible`: prefer script judges for exact checks and use LLM judges where semantic judgment is required
- `Re-runnable`: the same case should be easy to run locally, in CI, and during regression checks
- `Failure analysis friendly`: outputs should be easy to cluster, tag, and compare over time
- `Improvement loop built in`: evaluation is not just scoring, it should support diagnosis and iteration

## High-Level Architecture

The evaluation suite has six core layers:

1. `Case Definition Layer`
   Stores test case manifests, input files, expected references, and judge configs.

2. `Execution Layer`
   Runs the system under test using explicit commands and captures raw artifacts.

3. `Normalization Layer`
   Converts raw outputs into a stable, structured representation for downstream judging.

4. `Judging Layer`
   Applies one or more judges to each case result.

5. `Reporting Layer`
   Aggregates scores, errors, failures, and metadata into summaries and drill-down views.

6. `Investigation + Improvement Layer`
   Supports failure tagging, root-cause notes, and targeted re-runs after changes.

## Proposed Repository Structure

```text
evals/
  cases/
    pr_review/
      case_001/
        case.yaml
        input.diff
        reference.json
      case_002/
        case.yaml
        input.diff
        reference.json
    support_chat/
      case_001/
        case.yaml
        input.json
        reference.json
  judges/
    scripts/
      exact_json_fields.py
      finding_recall.py
    llm/
      semantic_match.yaml
      groundedness.yaml
    rubrics/
      pr_review_rubric.md
  suites/
    smoke.yaml
    regression.yaml
    release.yaml
  runs/
    2026-06-07_001/
      manifest.json
      summary.json
      cases/
        pr_review__case_001/
          input_snapshot/
          command.txt
          stdout.txt
          stderr.txt
          output.json
          normalized.json
          judge_results.json
          investigation.md
  reports/
    latest_summary.md
    trend_history.json
  configs/
    providers.yaml
    environments.yaml
    judge_defaults.yaml
```

## Core Concepts

### 1. Test Case

A test case is the smallest unit of evaluation.

It should define:

- `id`
- `task_type`
- `description`
- `input_files` or inline input payload
- `run_command`
- `expected_output_type`
- `judges`
- `tags`
- `difficulty`
- `priority`

Optional fields:

- `setup_commands`
- `teardown_commands`
- `env_overrides`
- `timeout_seconds`
- `retry_policy`
- `reference_output`
- `notes`

### 2. Suite

A suite is a named collection of cases used for a purpose such as:

- `smoke`: fast confidence check
- `regression`: stable quality gate
- `adversarial`: stress edge cases
- `release`: slower and broader final check

### 3. Run

A run is one execution of one suite against one specific system configuration.

Each run should record:

- code version or git commit
- prompt version
- model/provider config
- environment config
- suite name
- timestamp
- run-level summary metrics

### 4. Judge

A judge evaluates an output and emits a structured result.

Each judge should return:

- `judge_name`
- `judge_type`
- `status`
- `score`
- `pass`
- `rationale`
- `evidence`
- `error` if applicable

## Case Specification

Use YAML for human readability and explicit structure.

Example:

```yaml
id: pr_review_case_001
task_type: pr_review
description: Catch an obvious integer division regression
tags: [correctness, obvious_bug, python]
difficulty: easy
priority: high

inputs:
  diff_file: input.diff

run:
  command: python main.py --diff-file {{inputs.diff_file}} --output-file output.json
  cwd: /workspace/agent-eval-lab
  timeout_seconds: 60
  env:
    LLM_PROVIDER: minimax_anthropic

expected:
  output_type: json_file
  output_path: output.json
  reference_file: reference.json

judges:
  - name: schema_valid
    type: script
    config:
      script: judges/scripts/exact_json_fields.py

  - name: finding_recall
    type: script
    config:
      script: judges/scripts/finding_recall.py
      required_titles:
        - Integer division changes behavior

  - name: groundedness
    type: llm
    config:
      rubric: judges/rubrics/pr_review_rubric.md
      prompt_template: judges/llm/groundedness.yaml
      threshold: 0.8
```

## Execution Model

The execution layer should support:

- local process execution via shell command
- API request execution for service-style systems
- reusable environment variables
- input templating
- timeouts
- retries for flaky infrastructure failures
- artifact capture

Minimum per-case artifacts:

- resolved command
- environment snapshot, excluding secrets
- input snapshot
- stdout
- stderr
- exit code
- runtime duration
- raw output file or response body

## Output Normalization

Different systems return output in different shapes. Judging becomes easier if the suite normalizes results into a standard schema before applying judges.

Example normalized schema:

```json
{
  "case_id": "pr_review_case_001",
  "run_id": "2026-06-07_001",
  "execution": {
    "status": "completed",
    "exit_code": 0,
    "duration_ms": 4123
  },
  "raw_output": {
    "path": "output.json"
  },
  "parsed_output": {
    "summary": "Detected one likely correctness regression.",
    "findings": [
      {
        "severity": "high",
        "title": "Integer division changes behavior",
        "file": "math_utils.py",
        "comment": "Using // changes non-integer division semantics."
      }
    ]
  }
}
```

Benefits:

- the same judge can work across many systems
- it is easier to compute aggregate metrics
- debugging is simpler because execution metadata and output live together

## Judge Types

### 1. Script Judge

Best for:

- schema validation
- exact field checks
- numeric tolerances
- keyword presence
- deterministic scoring

Strengths:

- cheap
- fast
- reproducible

Weaknesses:

- brittle for nuanced language judgments

### 2. LLM Judge

Best for:

- semantic correctness
- helpfulness
- groundedness
- rubric-based quality scoring
- comparing answer quality when exact string matching is too weak

Strengths:

- flexible
- handles semantic equivalence better

Weaknesses:

- can be noisy
- more expensive
- must be validated carefully

### 3. Hybrid Judge

Best for:

- exact preconditions checked by scripts
- nuanced final scoring by LLM

Example:

- script judge verifies JSON schema and required fields
- script judge extracts candidate findings
- LLM judge scores whether the findings are grounded and materially useful

## Judge Interface

Every judge should implement a shared interface conceptually like:

```python
def judge(case, normalized_output, reference, config) -> dict:
    return {
        "judge_name": "groundedness",
        "judge_type": "llm",
        "status": "ok",
        "score": 0.91,
        "pass": True,
        "rationale": "All findings are grounded in the diff.",
        "evidence": ["Finding 1 maps to changed line in math_utils.py"],
        "error": None,
    }
```

This keeps reporting and aggregation generic.

## Metrics

The suite should support both case-level and suite-level metrics.

Case-level:

- pass/fail
- judge scores
- latency
- cost
- retries
- parse success

Suite-level:

- overall pass rate
- parse success rate
- average judge score
- precision
- recall
- hallucination rate
- groundedness score
- average latency
- average cost
- failure cluster counts

Not every metric applies to every task type. Metrics should be opt-in per suite.

## Reporting

The reporting layer should produce:

- `summary.json`: machine-readable aggregate results
- `summary.md`: human-readable overview
- per-case drill-down artifact folders
- optional comparison reports between two runs

Suggested summary sections:

- run metadata
- top-level metrics
- failed cases
- flaky cases
- new regressions
- resolved regressions
- judge disagreement cases
- recommended next actions

## Investigation Workflow

When a case fails, the suite should make it easy to inspect:

- what input was used
- what exact command ran
- what raw output came back
- which judge failed
- why it failed
- whether the failure is due to execution, parsing, reasoning, grounding, or rubric mismatch

Each failed case should support an `investigation.md` note containing:

- failure summary
- suspected root cause
- category
- supporting evidence
- proposed fix
- follow-up action

Suggested failure taxonomy:

- `execution_failure`
- `parse_failure`
- `schema_failure`
- `grounding_failure`
- `reasoning_failure`
- `instruction_failure`
- `tool_failure`
- `retrieval_failure`
- `judge_failure`
- `dataset_issue`

## Improvement Loop

The suite should explicitly support the following loop:

1. Define or expand cases
2. Run the suite
3. Inspect failures
4. Cluster failures by category
5. Decide fix type
6. Implement one focused change
7. Re-run a targeted subset
8. Re-run the broader regression suite
9. Record whether metrics improved or regressed

Possible fix types:

- prompt fix
- output format fix
- parsing fix
- tool selection fix
- retrieval fix
- model choice fix
- judge improvement
- dataset correction

## LLM Judge Design Guidelines

LLM judges can become a source of noise. To keep them useful:

- use a written rubric
- ask for structured outputs
- ask for evidence, not just a score
- include the task input and candidate output
- avoid vague judging prompts
- calibrate on a small hand-labeled set first
- compare judge outputs against human review periodically

A good LLM judge output schema:

```json
{
  "score": 0.86,
  "pass": true,
  "grounded": true,
  "issues": [],
  "rationale": "The finding directly references a changed semantic behavior.",
  "evidence": [
    "The diff changes '/' to '//', which changes float division to floor division."
  ]
}
```

## Example CLI

The suite can be exposed with a simple CLI:

```bash
evalctl run --suite evals/suites/smoke.yaml
evalctl run --case evals/cases/pr_review/case_001/case.yaml
evalctl run --suite evals/suites/regression.yaml --filter tag=auth
evalctl compare --baseline runs/2026-06-07_001 --candidate runs/2026-06-10_002
evalctl investigate --run runs/2026-06-07_001 --failed-only
evalctl report --run runs/2026-06-07_001
```

## Suggested Implementation Phases

### Phase 1: Minimal Useful Eval Runner

Build:

- YAML case loader
- shell command execution
- artifact capture
- JSON output normalization
- script judge support
- markdown and JSON summary

This is enough to evaluate a simple Week 1 CLI reliably.

### Phase 2: LLM Judge Support

Add:

- LLM judge adapters
- judge prompt templates
- structured judge outputs
- cost and latency tracking
- judge calibration workflow

### Phase 3: Failure Analysis Layer

Add:

- failure tagging
- comparison between runs
- trend tracking
- investigation templates

### Phase 4: Improvement Loop Automation

Add:

- automatic rerun of failed cases
- filtered reruns by tag or failure type
- regression detection versus baseline
- optional recommendation generation for likely fix areas

## Recommended First Version For This Repo

For `agent-eval-lab`, the first implementation should stay small:

- task type: `pr_review`
- input type: diff file
- run command: your existing `python main.py --diff-file ... --output-file ...`
- output type: structured JSON
- judges:
  - schema valid
  - required finding present
  - hallucination check
  - optional LLM groundedness judge

This gives you a practical bridge from Week 1 to Week 5 and Week 6 of your plan.

## Open Questions

Before implementation, decide:

- Should cases live in repo or external dataset storage?
- Should run commands be shell-only, or also native Python callables?
- Should LLM judges run by default, or only in a slower evaluation suite?
- How should secrets be injected safely into run environments?
- What counts as a regression: pass/fail only, or score drop beyond threshold?
- How much human review should be required before updating references or judge logic?

## Success Criteria

The design is successful if the eventual system lets you:

- add a new case in minutes
- rerun a focused subset of cases quickly
- tell exactly why a case failed
- compare two system versions without manual diffing
- quantify whether a change improved or worsened quality
- build a durable feedback loop from failures to fixes
