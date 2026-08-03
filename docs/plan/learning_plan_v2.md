# OpenAI AI Deployment Engineer (Startups) - 12 Week Plan (v2)

## Goal

Demonstrate capability in:

* Agent Design
* RAG Systems
* Evaluation Design
* Failure Analysis
* Agent Memory
* Customer Workflow Understanding
* Product/Research Feedback Loops

## Default Build Stack

Use MiniMax CN API throughout the implementation work for this plan.

Preferred approach:

* MiniMax native / compatible API endpoints
* MiniMax tool calling / function calling
* MiniMax embeddings where available
* Vendor-neutral evaluation code you own

## Final Deliverables

GitHub Repo: agent-eval-lab

Includes:

* Tool Calling
* Multi-Step Agent Workflow
* RAG
* Task Memory
* Evaluation Framework
* Failure Taxonomy
* Benchmark Dataset
* Demo Video

## Weekly Allocation (10h)

* Reading: 2-3h
* Coding: 5-6h
* Analysis/Writing: 1-2h

---

# Project Architecture

User
↓
Agent
↓
Planner
↓
Tools
├── GitHub PR Tool
├── Retrieval Tool (RAG)
├── File Search Tool
└── Memory Store
↓
Evaluator
↓
Failure Analysis

---

# Week 1 - Bootstrap

## Read

Anthropic Building Effective Agents
https://www.anthropic.com/engineering/building-effective-agents

MiniMax Quick Start
https://platform.minimax.io/docs/guides/quickstart

MiniMax Compatible OpenAI API
https://platform.minimax.io/docs/api-reference/text-openai-api

Read:

* Function Calling
* JSON / structured output patterns

## Build

Create repo.
Implement:
review_pr(diff) -> JSON
Single LLM call.
No tools.
No RAG.

## Deliverables

Commits:

* repo setup
* basic reviewer
* structured output

Write:

week1_notes.md

---

# Week 2 - Tool Calling

## Read

MiniMax Tool Use & Interleaved Thinking
https://platform.minimax.io/docs/guides/text-m2-function-call

Read:
* Tool Use
* Tools
* Multi-turn tool call loop design

## Build

Add:
GitHub Tool
Functions:
* fetch_pr()
* fetch_files()

Agent can now call tools.

## Deliverables

Commits:

* tool layer
* github integration
* tracing

Write:

wk2/architecture_v1.md

---

# Week 3 - Multi-Step Agent

## Read

GAIA Benchmark

https://arxiv.org/abs/2311.12983

Focus:

* tasks
* evaluation

## Build

Workflow:

1. Gather files
2. Review
3. Verify findings
4. Generate report

Introduce state object.

Example:

files_reviewed
issues_found
verification_results

This is your first memory layer.

## Deliverables

Commits:

* planner
* verification step
* memory state

Write:

workflow_design.md

---

# Week 4 - Add RAG

## Read

MiniMax Embeddings / Retrieval docs

Read:

* Embeddings
* Retrieval

## Build

Knowledge Base:

* markdown docs
* project docs
* design docs

Use:

* MiniMax Embeddings
* FAISS

Agent can answer:
"Has this bug happened before?"
"Where is authentication implemented?"

## Deliverables

Commits:

* embedding pipeline
* retrieval layer
* rag integration

Write:

rag_design.md

---

# Week 5 - RAG Evaluation

## Read

Evaluation framework references:

* SWE-Bench-style task evaluation patterns
* Your own benchmark runner and scoring scripts

## Build

Create 30 QA pairs.

Evaluate:

* retrieval recall
* answer accuracy
* citation quality

## Deliverables

Commits:

* rag benchmark
* rag eval

Write:

rag_eval_report.md

---

# Week 6 - Agent Evaluation

## Read

SWE-Bench

https://arxiv.org/abs/2310.06770

Focus:

* benchmark design
* evaluation setup

## Build

Metrics:

* precision
* recall
* hallucination rate
* latency
* cost

Build evaluation runner.

## Deliverables

Commits:

* metrics
* eval runner

Write:

eval_design.md

---

# Week 7 - Memory Improvements

## Read

MiniMax agent/tool loop docs and current memory-related product docs/blogs.

## Build

Short-term memory:

Track:

* previous findings
* previous reviews
* current task state

Agent should avoid repeating work.

## Deliverables

Commits:

* memory manager
* state persistence

Write:

memory_design.md

---

# Week 8 - Failure Taxonomy

## Read

Latest frontier model system cards / safety reports.

Focus:

* risk categories
* eval methodology

## Build

Tag failures:

* Retrieval Failure
* Memory Failure
* Tool Failure
* Reasoning Failure
* Hallucination
* Instruction Failure

## Deliverables

Commits:

* failure tagging
* failure reporting

Write:

failure_analysis.md

20+ examples.

---

# Week 9 - Reliability Improvements

## Build

Fix top 3 failure categories.

Re-run evaluations.

Measure gains.

## Deliverables

Commits:

* fix #1
* fix #2
* re-evaluation

Write:

improvement_report.md

---

# Week 10 - Startup Customer Thinking

## Analyze

Cursor

Perplexity

Replit

Harvey

Windsurf

For each:

* workflow
* likely failure modes
* success metrics
* eval strategy

## Deliverable

startup_casebook.md

---

# Week 11 - Research Feedback Loop

## Exercise

For every major failure:

Determine:

* Prompt issue?
* Tool issue?
* Product issue?
* Model issue?

For model issues:

Design reproducible evaluation.

This mirrors the actual JD.

## Deliverable

research_feedback.md

---

# Week 12 - Interview Package

## Create

Architecture Diagram

Demo Video

15 Slide Deck

Final README

## Mock Questions

* Evaluate an agent
* Improve an agent
* Design an eval
* Design a benchmark
* RAG failure analysis
* Memory failure analysis
* Customer workflow debugging

## Success Criteria

By Week 12:

* 50+ commits
* Working agent
* Working RAG
* Memory layer
* Benchmark dataset
* Evaluation framework
* Failure taxonomy
* Startup casebook

Able to discuss:

* Agent Design
* RAG
* Evaluation
* Memory
* Failure Analysis
* Customer Feedback Loops

for 15-20 minutes each without preparation.
