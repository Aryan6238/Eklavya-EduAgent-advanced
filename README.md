# Engineering Design Note: Governed AI Assessment Pipeline

## Overview
This system implements a deterministic, multi-agent pipeline for the generation of educational content. Unlike standard "chat-and-hope" LLM implementations, this architecture treats content generation as a governed manufacturing process with explicit quality gating, bounded retries, and comprehensive audit trails.

## 🤖 Agent Roles & Responsibilities

| Agent | Responsibility | Implementation Note |
| :--- | :--- | :--- |
| **Generator** | Content Production | Primary source of truth. Uses strict JSON schemas to ensure output can be parsed by downstream systems. |
| **Reviewer** | Quality Gating | Quantitative scoring agent. Evaluates content on 4 dimensions (Age, Correctness, Clarity, Coverage) using a 1-5 scale. |
| **Refiner** | Targeted Correction | Delta agent. Takes Reviewer feedback and previous drafts to produce a corrected version, avoiding the "start from scratch" drift. |
| **Tagger** | Classification | Post-approval agent. Assumes content is safe/correct and applies Bloom's Taxonomy and educational metadata. |

## ✅ Pass/Fail Criteria
The pipeline enforces a strict **"High Quality or Nothing"** policy:
- **Approval Threshold**: Content must score **>= 4** across *all* four reviewer dimensions. If even one score is 3 or below, the draft is rejected and sent for refinement.
- **Structural Integrity**: Any response failing Pydantic schema validation triggers exactly **one** automatic recovery attempt before the run is marked as an error.

## 🧠 Orchestration Decisions

### 1. Sequential Determinism
The pipeline follows a strict linear sequence: `Generator` -> `Reviewer` -> `[Refiner -> Reviewer] x 2` -> `Tagger`. This ensures that the `Tagger` never operates on unverified content and that the audit trail is perfectly chronological.

### 2. Bounded Retries (Infinite Loop Prevention)
To prevent "Refinement Drift" or cost/latency spikes, the orchestrator enforces hard limits:
- **Max Refinement Cycles**: 2. If content remains below threshold after 2 refinements, the run is terminated with a `rejected` status.
- **Bounded Content Length**: Strict instruction sets prevent LLMs from generating overly verbose text that complicates review.

### 3. First-Class Run Artifacts
Every execution produces a `RunArtifact` JSON. This is not just a log; it is a restorable state object that captures inputs, intermediate drafts, specific scores, and final decisions.

## ⚖️ Engineering Trade-offs

### High Quality vs. Latency
The system significantly prioritizes quality and accuracy over speed. A single successful "Approved" run may involve 4-6 LLM calls (Initial Gen, 1-2 Reviews, 1-2 Refinements, Tagging). In a production literacy environment, a 30-second wait for a validated lesson is superior to a 2-second wait for a potentially hallucinated one.

### Strict Schema vs. AI Creativity
By enforcing Pydantic models at every step, we restrict the LLM's "creative freedom." While this occasionally requires retries if the model misses a field, it ensures 100% compatibility with the database and UI, which is critical for system stability.

### Stateless Agents vs. Stateful Orchestrator
The Agents themselves are stateless functions. All state (draft versions, review history) is managed by the `Orchestrator` and passed explicitly. This simplifies testing and allows for easier agent replacement or model upgrades (e.g., swapping Gemini 2.0 for 1.5) without refactoring logic.

---
*Document Version: 1.1 - Part 2 Governance Compliance*
