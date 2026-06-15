# Week 3: Multi-Step Workflow Design

## Overview
This document outlines the architecture for the Week 3 multi-step agent. The agent transitions from a simple single-turn prompt into a structured state machine.

## 1. The State Object (Memory Layer)
To support multi-step reasoning, we introduced a centralized `AgentState` object (implemented via Python `dataclasses`). It persists information across different workflow steps.

### Structure
- `pr_url`: Target PR identifier.
- `files_reviewed`: A list of file paths gathered by the initial tools.
- `issues_found`: The raw list of potential issues generated during the first review pass.
- `verification_results`: The filtered list of genuine issues that passed the secondary verification step.
- `false_positives_discarded`: A metric tracking how many issues were rejected.
- `current_step`: Tracks workflow progress (`gather_and_review`, `verify`, `report`).

## 2. The 4-Step Workflow

### Steps 1 & 2: Gather & Review
*Using the ReAct tool loop from Week 2.*
- **Action:** The agent is given a target PR and provided with GitHub tools (`fetch_pr`, `fetch_files`). 
- **Execution:** It autonomously fetches the PR metadata, retrieves the file diffs, and performs an initial review to identify potential bugs, logic errors, and risks.
- **State Update:** The files fetched and the findings generated are saved to `state.files_reviewed` and `state.issues_found`.

### Step 3: Verify Findings
*Adding a self-correction loop.*
- **Action:** A dedicated LLM call acts as a "Senior Reviewer."
- **Execution:** It evaluates the raw `issues_found` list. It discards hallucinations, nitpicks, or false positives, ensuring only critical and genuine issues proceed.
- **State Update:** The validated list is saved to `state.verification_results`.

### Step 4: Generate Report
*Finalizing the output.*
- **Action:** A final LLM call formats the data.
- **Execution:** It takes the `verification_results` and generates a clean, readable Markdown report.
- **State Update:** The final state is serialized to JSON, acting as a complete trace of the agent's memory for debugging or persistence.

## 3. Why This Design?
By separating the **Review** and **Verify** steps, the agent's reliability increases drastically. A single LLM call is prone to hallucinations and nitpicking. By forcing the agent to double-check its own work in a separate context window (Step 3), we simulate a "peer review" process that drastically improves precision.