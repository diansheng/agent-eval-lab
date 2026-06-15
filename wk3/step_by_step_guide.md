# Week 3: Multi-Step Agent Step-by-Step Guide

This guide breaks down the Week 3 tasks from the learning plan into actionable steps to build your first multi-step agent with a memory layer.

## Step 1: Reading Phase
**Goal:** Understand complex task evaluation and memory requirements.
- **Read:** [GAIA: A Benchmark for General AI Assistants](https://arxiv.org/abs/2311.12983)
- **Focus:** Pay attention to the "tasks" and "evaluation" sections. Notice how multi-step reasoning requires the agent to maintain context across different actions to arrive at a definitive answer.

## Step 2: Design the State Object (Memory Layer)
**Goal:** Create a memory structure to hold data between workflow steps. The agent can no longer be stateless.
- Create a new file for your state schema (e.g., `state.py` or `memory.py`).
- Define a class (e.g., using `pydantic.BaseModel` or Python `dataclasses`) to hold the state.
- **Required Fields:**
  - `files_reviewed`: A list to store the file paths or URLs gathered in step 1.
  - `issues_found`: A list/dictionary to store the raw issues identified by the initial review step.
  - `verification_results`: A list/dictionary to store issues that passed the verification step.

*Example:*
```python
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    files_reviewed: List[str] = Field(default_factory=list)
    issues_found: List[Dict[str, Any]] = Field(default_factory=list)
    verification_results: List[Dict[str, Any]] = Field(default_factory=list)
```

## Step 3: Implement the Workflow Planner
**Goal:** Orchestrate the multi-step process.
- Create a new file (e.g., `planner.py`).
- Implement a main loop or sequential function that executes the 4 main steps using the `AgentState` object:
  1. **Gather files:** Use the GitHub tools you built in Week 2 to fetch PR files. Save them to `state.files_reviewed`.
  2. **Review:** Loop through `state.files_reviewed`, call your Week 1 LLM review function for each, and store results in `state.issues_found`.
  3. **Verify findings:** Pass `state.issues_found` to a new LLM call to filter out false positives. Store the filtered list in `state.verification_results`.
  4. **Generate report:** Pass `state.verification_results` to a final LLM call to format a clean markdown/JSON report.

## Step 4: Write the Verification Step
**Goal:** Add a self-correction mechanism to improve accuracy.
- Create a specific prompt/function for verification (e.g., `verify_findings(issues)`).
- The prompt should provide the LLM with the raw `issues_found` and ask it to play the role of a senior reviewer: "Are these issues valid? Discard any false positives, nitpicks, or hallucinations."

## Step 5: Finalize Deliverables
**Goal:** Wrap up Week 3 requirements.
- **Code:** Commit the `planner`, `verification step`, and `memory state` implementations to your repository.
- **Documentation:** Write `workflow_design.md` explaining your `AgentState` object, how data flows through your 4-step process, and your architectural decisions. Place this in the appropriate folder.
