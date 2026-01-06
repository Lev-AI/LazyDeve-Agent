# Roadmap: MCP Server (Global Orchestration Layer)

## Scope

This document defines the engineering roadmap for implementing a Global MCP Server as the external orchestration and protocol layer for the LazyDeve ecosystem.

The MCP Server becomes the primary integration surface for external clients and standardizes how they interact with:
- LazyDeve Agent (reasoning + execution)
- RagCore / Knowledge Service (retrieval + indexing)

Internal services continue to communicate over HTTP within a trusted network. The MCP Server mediates and orchestrates external-facing flows.

---

## Target Architecture

### High-Level Topology

External Clients (Custom ChatGPT, Cline, Claude Desktop, etc.)
        |
        | MCP Protocol (tool calls)
        v
MCP Server (Global Boundary + Orchestrator)  [port: 8090 for health]
        |
        | HTTP (trusted network)
        +--------------------------+
        |                          |
        v                          v
LazyDeve Agent (FastAPI)           RagCore Service (FastAPI)
[port: 8001]                      [port: 8002]

Key rule:
- External clients never call LazyDeve or RagCore directly.
- External clients call MCP tools only.

---

## System Objectives

- Provide a single MCP-compatible tool interface for external clients
- Reduce exposed surface area by grouping many internal endpoints into a small set of stable tools
- Orchestrate multi-step flows across LazyDeve and RagCore when explicitly requested
- Enforce security and reliability at the boundary (auth, validation, timeouts, rate limiting)
- Keep LazyDeve core flows (including CPL) stable and unchanged
- Support Docker deployment and service-name routing

---

## Core Responsibilities

### 1. External Protocol Boundary

- MCP Server is the only public entry point
- Internal services are treated as upstream dependencies
- MCP normalizes responses and prevents internal detail leakage

### 2. Tool Surface Design (Grouping Strategy)

Goal: compress ~50 internal endpoints into ~6–10 MCP tools that represent stable capabilities.

Tool families (recommended):

- Execution (LazyDeve)
  - execute_task
  - project_admin (create/archive/list/info)
  - context_ops (refresh/query/sync)

- Knowledge (RagCore)
  - knowledge_query (ask)
  - knowledge_index (add/index)
  - knowledge_stats (frameworks/stats)

- Boundary / Ops (MCP-owned)
  - health
  - tool_catalog
  - dispatch (optional single entry tool)

Principles:
- Tools are capability-based, not endpoint-based
- Each tool has a fixed schema and validation
- Outputs are normalized for predictable client consumption

### 3. Deterministic Routing (Minimal CPL in MCP)

The MCP Server performs deterministic routing using a minimal command parser (CPL port in JavaScript).

Responsibilities:
- Identify intent (create project, archive project, execute task, etc.)
- Extract required parameters
- Select tool target and upstream endpoint mapping

Boundary rule:
- MCP routing is minimal and deterministic.
- LazyDeve remains the single source of truth for complex planning and execution behavior.

### 4. Orchestration Patterns

Pattern A: Single-Hop Routing
- One tool call maps to one upstream service call
- Examples:
  - list projects → LazyDeve
  - ask knowledge → RagCore

Pattern B: Two-Hop Orchestration (Retrieve-Then-Execute)
- MCP performs an explicit two-step sequence only when requested by the client/tool:
  - Step 1: knowledge_query → RagCore
  - Step 2: execute_task → LazyDeve (with retrieved context attached as a structured input)

Constraints:
- No automatic hidden retrieval injection
- MCP does not alter LazyDeve internal logic; it supplies validated additional inputs

### 5. Service Interaction Flows

Flow 1: Execute Task
- Client → chatGPT → MCP: execute_task
- MCP → LazyDeve: /execute
- MCP → Client: normalized execution result

Flow 2: Query Knowledge
- Client → chatGPT → MCP: knowledge_query
- MCP → RagCore: /ask
- MCP → Client: answer + sources/metadata (normalized)

Flow 3: Retrieve Then Execute
- Client → chatGPT → MCP: execute_with_knowledge
- MCP → RagCore: /ask
- MCP → LazyDeve: /execute (task + retrieved context payload)
- MCP → Client: combined result

Flow 4: Index Knowledge
- Client → chatGPT → MCP: knowledge_index
- MCP → RagCore: indexing endpoint or ingestion action
- MCP → Client: indexing status + identifiers

---

## Security and Reliability Requirements (Non-Negotiable)

### 1. Authentication

- INTERNAL_AUTH_TOKEN must be mandatory (no default fallback)
- MCP must attach internal auth headers to all upstream calls
- Internal services may rely on trusted-network auth + internal headers

### 2. Request Timeouts

- All upstream HTTP calls must have strict timeouts
- Different timeout classes:
  - project operations (short)
  - execute (longer but bounded)
  - retrieval (bounded)

### 3. Error Handling

- MCP must catch and normalize upstream failures
- No stack traces or internal URLs leaked to clients
- Provide stable error classes (timeout, auth, upstream unavailable)

### 4. Rate Limiting

- Per-client request limits enforced at MCP boundary
- Client identity derived from auth token or explicit client id

### 5. Health Endpoint (Docker / Ops)

- MCP must expose an HTTP health endpoint on port 8090
- Health response includes uptime and basic readiness indicators
- Graceful shutdown supported

---

## Implementation Source and Adaptation

The MCP Server is adapted from the existing RagCore MCP server implementation.

Required adaptations:
- Add LazyDeve tool set and routing
- Add mandatory internal authentication
- Add request timeouts and safe request wrappers
- Add missing CPL JavaScript module used for routing
- Add rate limiting
- Add HTTP health endpoint (MCP itself is stdio/protocol; health is separate HTTP)

---

## Docker and Deployment Constraints

- Use Docker service names for upstream routing:
  - lazydeve:8001
  - rag:8002
- External port exposure controlled at MCP only
- Internal ports remain in the private Docker network

---

## Observability and Audit

MCP must log, at minimum:
- tool invoked + validated inputs (redacted)
- routing decision (intent, chosen tool, upstream target)
- upstream latency + status + error class
- correlation id across multi-step flows

This supports:
- debugging
- routing refinement
- performance/cost analysis

---

## Milestones

Phase 0: Preconditions
- Verify Task 8.11 context endpoints and SQLite layer are stable
- Verify Task 9 knowledge service is reachable and stable

Phase 1: Baseline MCP Orchestration
- MCP server runs with:
  - health endpoint
  - mandatory auth
  - minimal tool set
  - deterministic routing (CPL JS)
  - upstream calls to LazyDeve and RagCore

Phase 2: Production Hardening
- Add:
  - rate limiting
  - strict timeouts by operation class
  - safe error normalization
  - structured audit logs

Phase 3: Expansion
- Add:
  - additional tools without expanding raw endpoint exposure
  - multi-agent registration
  - optional parallel orchestration patterns

---

## Verification Checklist

- MCP health endpoint returns 200 and readiness data
- Auth is mandatory; missing token blocks startup or requests
- All upstream calls enforce timeouts
- Rate limiting blocks abusive clients
- Minimal CPL routing works and is logged
- LazyDeve tools execute through MCP
- RagCore tools execute through MCP
- Two-hop retrieval-then-execute works only via explicit tool
- No direct external access to internal services is required

---

## Summary

The MCP Server is a boundary and orchestration layer that exposes a small, stable tool surface for external clients and mediates access to internal services with deterministic routing, strict security enforcement, and production-grade reliability controls. It enables ChatGPT ↔ MCP ↔ LazyDeve ↔ RagCore interaction without destabilizing the LazyDeve execution core.

