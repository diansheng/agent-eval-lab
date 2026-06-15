# Week 5: RAG Evaluation - Step-by-Step Guide

## Overview
This week focuses on evaluating the Retrieval-Augmented Generation (RAG) system you built in Week 4. You will build a benchmark of QA pairs and write an evaluation runner to measure retrieval recall, answer accuracy, and citation quality.

## Step 1: Reading & Research
- **Task**: Read up on evaluation framework references.
- **Focus**: Review SWE-Bench-style task evaluation patterns and familiarize yourself with writing benchmark runners and scoring scripts.
- **Reference Links**:
  - [SWE-Bench Paper (arXiv)](https://arxiv.org/abs/2310.06770) - *For task evaluation patterns.*
  - [Ragas: Automated Evaluation of RAG](https://docs.ragas.io/) - *Good reference for scoring metrics like Answer Accuracy and Retrieval Recall.*
  - [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) - *Best practices for building your own benchmark runners and evaluation suites.*

## Step 2: Create Benchmark Dataset
- **Task**: Create 30 Question-Answer pairs based on your knowledge base.
- **Action**: Manually generate 30 questions that can be answered using the project docs, design docs, etc. you embedded in Week 4.
- **Action**: For each question, define the expected "Gold" answer and the exact source chunk/document that contains the answer. Save this as a JSON or CSV file (e.g., `rag_benchmark.json`).

## Step 3: Build the Evaluation Runner
- **Task**: Write a script to automate running the benchmark.
- **Action**: Create an eval script that iterates through your 30 QA pairs.
- **Action**: For each question, invoke your Agent/RAG pipeline and capture:
  1. The retrieved contexts.
  2. The final generated answer.
  3. Any citations produced.

## Step 4: Implement Scoring Metrics
- **Task**: Score the results based on three criteria.
- **Action**: 
  - **Retrieval Recall**: Did the system retrieve the exact document/chunk needed to answer the question? (Calculate the % of questions where the gold source was in the `top_k` retrieved chunks).
  - **Answer Accuracy**: Use an LLM-as-a-judge (via MiniMax API) to compare the agent's answer against the gold answer. Grade it on a scale (e.g., 1-5) or as binary (Pass/Fail).
  - **Citation Quality**: Did the agent correctly cite the source in its final response? (Check if the generated text references the retrieved document).

## Step 5: Run Eval & Analyze
- **Task**: Execute the evaluation and review the results.
- **Action**: Run your evaluation script and calculate the final scores for Recall, Accuracy, and Citation Quality.
- **Action**: Identify patterns in where the system fails (e.g., is it failing because it can't retrieve the document, or because the reasoning over the document is poor?).

## Step 6: Final Deliverables
- **Commits**:
  - `test: add 30 QA pairs for rag benchmark`
  - `feat: implement rag evaluation runner and scoring scripts`
- **Documentation**: Write `rag_eval_report.md` detailing the methodology, the final scores, and your analysis of where the RAG pipeline needs improvement.