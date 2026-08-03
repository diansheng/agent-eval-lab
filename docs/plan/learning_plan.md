# OpenAI AI Deployment Engineer (Startups) - 12 Week Plan

## Goal

Demonstrate ability in:

* Agent Design
* Evaluation Design
* Failure Analysis
* Customer Workflow Understanding
* Product/Research Feedback Loops

## Final Deliverables

* Public GitHub repo (`agent-eval-lab`)
* Architecture diagram
* Evaluation framework
* Benchmark dataset
* Failure analysis report
* Demo video
* Interview notes

## Weekly Schedule (10h/week)

* Learning: 3h
* Building: 5h
* Writing/Analysis: 2h

---

# Week 1 - Build First Agent

## Learn

### Anthropic: Building Effective Agents

https://www.anthropic.com/engineering/building-effective-agents

Focus:

* Workflow vs Agent
* Agent patterns
* Failure modes

### OpenAI Cookbook

https://cookbook.openai.com

Read:

* Function Calling
* Structured Outputs

## Build

Create repo:

agent-eval-lab

Implement:

* CLI app
* Input: GitHub PR diff
* Output: review comments

No tools yet.

Single LLM call only.

## GitHub Deliverables

commit 1:
repo bootstrap

commit 2:
basic reviewer

commit 3:
structured JSON output

## Write

week1_notes.md

Answer:

* What is an agent?
* Why is this not yet an agent?

---

# Week 2 - Tool Calling

## Learn

### OpenAI Agents SDK

https://openai.github.io/openai-agents-python/

Read:

* Agents
* Tools

## Build

Add tools:

* fetch PR
* fetch changed files

Agent now calls tools.

## GitHub Deliverables

commit 4:
tool abstraction

commit 5:
github integration

commit 6:
tool tracing

## Write

agent_architecture_v1.md

Draw architecture diagram.

---

# Week 3 - Multi-Step Workflow

## Learn

### OpenAI Cookbook

Reasoning Models examples

### GAIA

https://arxiv.org/abs/2311.12983

Read:

* Intro
* Evaluation section

## Build

Workflow:

1. Fetch PR
2. Analyze diff
3. Verify findings
4. Generate report

## GitHub Deliverables

commit 7:
review stage

commit 8:
verification stage

commit 9:
report stage

## Write

workflow_design.md

Document each stage.

---

# Week 4 - Tracing & Observability

## Learn

OpenAI Agents SDK Tracing

## Build

Store:

* prompt
* tool calls
* outputs
* errors

Create execution logs.

## GitHub Deliverables

commit 10:
logging

commit 11:
trace viewer

## Write

10 examples of failures.

---

# Week 5 - Evaluation Basics

## Learn

### OpenAI Evals

https://platform.openai.com/docs/guides/evals

Read entire guide.

### SWE-Bench

https://arxiv.org/abs/2310.06770

Read:

* Abstract
* Evaluation

## Build

Create benchmark dataset.

Target:

30 PRs

Label manually.

## GitHub Deliverables

commit 12:
benchmark dataset

commit 13:
ground truth format

## Write

eval_design.md

Answer:

How should this agent be evaluated?

---

# Week 6 - Automated Evaluation

## Build

Metrics:

* precision
* recall
* hallucination rate
* latency
* cost

Build evaluation runner.

## GitHub Deliverables

commit 14:
metrics

commit 15:
eval runner

commit 16:
report generation

## Write

evaluation_report_v1.md

---

# Week 7 - Benchmark Expansion

## Build

Expand dataset:

30 → 100 PRs

Improve labeling quality.

## GitHub Deliverables

commit 17:
dataset expansion

commit 18:
data validation

## Write

benchmark_spec.md

---

# Week 8 - Failure Analysis

## Learn

### OpenAI System Cards

https://openai.com/safety

Read latest GPT/o-series system cards.

Focus:

* risk taxonomy
* evaluation methodology

## Build

Create failure taxonomy:

* Tool Failure
* Retrieval Failure
* Reasoning Failure
* Hallucination
* Instruction Failure

## GitHub Deliverables

commit 19:
failure tagging

commit 20:
failure reports

## Write

failure_analysis.md

Minimum:

20 real examples.

---

# Week 9 - Reliability Improvements

## Build

Implement fixes for top failures.

Measure improvement.

## GitHub Deliverables

commit 21:
fix 1

commit 22:
fix 2

commit 23:
re-evaluation

## Write

before_after_comparison.md

---

# Week 10 - Product Thinking

## Exercise

Choose:

* Cursor
* Windsurf
* Replit
* Perplexity
* Harvey

For each:

* workflow
* failure modes
* evaluation metrics

## Write

startup_casebook.md

---

# Week 11 - Research Feedback Loop

## Exercise

For each failure category answer:

* Prompt issue?
* Product issue?
* Tool issue?
* Model issue?

What should be sent back to OpenAI Research?

## Write

research_feedback.md

This is extremely relevant to the JD.

---

# Week 12 - Interview Prep

## Prepare Stories

1. Production ML system
2. Ambiguous problem
3. Evaluation design
4. Agent design
5. Failure analysis

## Create

* 15-slide deck
* Demo video
* Final README

## Mock Questions

* How do you evaluate an agent?
* What are common failure modes?
* How do you debug an AI workflow?
* How do you convert customer feedback into evals?
* How do you identify model vs tool failures?

---

# Success Criteria

By Week 12:

* 50+ commits
* 100+ benchmark examples
* Working agent
* Evaluation framework
* Failure taxonomy
* Research feedback report

Able to discuss any of these topics for 15+ minutes without preparation.
