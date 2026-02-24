# 🧠 LazyDeve — Stateful Autonomous Development Agent

LazyDeve is a **working prototype** of a stateful AI development agent.

It demonstrates how an LLM can:
- operate on a real codebase,
- preserve project context across runs,
- execute changes deterministically,
- and maintain an auditable execution history.

This repository contains a functional FastAPI-based agent with persistent memory,
Git integration, and a closed-loop development workflow.

---


**LazyDeve** is not an IDE plugin and not a “stateless chat assistant”.  
It was created as an engineering experiment and evolved into a **stateful development agent** that can **plan, execute, verify, and iterate** on a real codebase — while preserving **project context as structured, inspectable artifacts**.
The architecture is modular by design, making it easy to adapt to different workflows and user needs.

LazyDeve is built around a simple idea:  
**the hardest part of AI-assisted development is not writing code — it’s making the LLM execute the *exact* intent.**  
Even a small mismatch between intended behavior and what gets implemented can break logic and lead to long-lasting issues, introduce regressions, or silently corrupt architecture.

LazyDeve exists to reduce that intent → implementation drift by turning development into a **closed-loop workflow** with persistent context, deterministic routing, and an auditable execution trail.

---


## 🧪 Architectural Experiment

**An experiment in turning ChatGPT into a deterministic, stateful and auditable software engineer.**

Core roles:

* **GPT — brain**
* **LazyDeve — discipline**
* **Aider — executor**
* **Git — truth**
* **Memory — context**

---

## 🧩 System Diagram

```
User → ChatGPT (Orchestrator) → LazyDeve (State + Memory + Control) → Aider (Code Executor) → Git (Truth)
                                        ↑
                               Memory (JSON / SQLite)
```


---
## 💡 Concept

LazyDeve is designed as a **development loop**, not a chat:

**intent → plan → execute → validate → record → iterate**

The agent interacts with a project through a controlled API surface (tools / actions), while maintaining a persistent project state that includes:
- what was changed,
- why it was changed,
- what happened during execution,
- and what should happen next.

Here, *context* is not just conversation history.  
It is a **structured memory layer** composed of human-readable and versionable artifacts (e.g., context snapshots, run metadata, commits), which makes the system reproducible and debuggable.

---

## ⚙️ What It Solves

LazyDeve targets a very specific failure mode of “vibe-coding” workflows:

### Intent → Implementation Drift
In many AI coding sessions, the LLM produces code that is *close* to the request, but subtly wrong:
- wrong file or wrong layer,
- inconsistent naming and structure,
- partial refactors that break interfaces,
- changes that ignore prior decisions or context,
- regressions because validation is out-of-band.

LazyDeve addresses this by enforcing:
- **persistent project state** (context is carried forward as artifacts, not vibes)
- **deterministic routing for commands** (CPL-style intent parsing to avoid ambiguous execution)
- **traceable execution** (actions/runs/changes are recorded and can be inspected)
- **iteration with memory** (the agent can reference what it did, what failed, and what was accepted)

This makes the assistant behave less like a prompt-completion engine and more like a **repeatable engineering process**.

---

## 🧩 What Makes LazyDeve Different

LazyDeve combines four practical properties that typical assistants don’t provide together:

- **Stateful Context Engine**  
  Project context is persisted across sessions as structured artifacts (JSON + SQLite indexing), enabling retrieval, inspection, and evolution over time.

- **Action-Centric Memory**  
  The system records *what the agent actually did* (runs, outcomes, changes), not only what was discussed.

- **Closed-Loop Development Workflow**  
  The architecture is built for iterative development cycles (execute → validate → adjust), with explicit boundaries between reasoning, execution, and memory.

- **Transparency by Design**  
  Context artifacts are human-readable, versionable, and suitable for debugging and collaboration.

---

## 🧱 Why It Exists

LazyDeve started as a personal attempt to build a helper that would follow my intent precisely during iterative development.  
The project evolved into a working prototype that demonstrates an architecture where an LLM-driven agent can operate with **persistent state, controlled execution, and an auditable history of decisions and actions**.

---

## 🚀 Why Explore LazyDeve

- A **functional prototype** of a stateful development agent (not just a concept)
- A practical demonstration of **LLM-driven development with memory and traceability**
- A showcase of systems thinking: **orchestration + execution + context engineering**
- A foundation for planned extensions (Knowledge/Vector Memory layer, MCP orchestration)


---

## 🏗️ Architecture Overview

For detailed architecture diagrams, internal flows, and design notes,
see the GitHub_full_architecture_and_future_modules/ directory.

### 🔄 Full Data Flow Process

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL CLIENT                                   │
│                    (Custom ChatGPT / REST Client / Scripts)                 │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ HTTP REST
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LazyDeve Agent (FastAPI)                            │
│                              Port 8001                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  /execute          → AI task execution (Aider integration)                  │
│  /projects/*       → Project management API                                 │
│  /api/v1/context/* → Unified context endpoints                              │
│  /git/*            → Git operations (commit, push, pull, status)            │
│  /openapi.yaml     → OpenAPI schema for ChatGPT Apps                        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
┌───────────────────────────┐      ┌───────────────────────────────────────────┐
│      EXECUTION LAYER      │      │           MEMORY/CONTEXT LAYER            │
│                           │      │                                           │
│  ├── Aider (AI coding)    │      │  ├── memory.json    (actions, semantic)   │
│  ├── Git operations       │      │  ├── context_full.json (unified context)  │
│  └── File management      │      │  ├── context.db    (SQLite index)         │
│                           │      │  └── run_*.json    (execution logs)       │
└───────────────────────────┘      └───────────────────────────────────────────┘
                    │                              │
                    ▼                              ▼
┌───────────────────────────┐      ┌───────────────────────────────────────────┐
│       GitHub Remote       │      │         ChatGPT Context Injection         │
│                           │      │                                           │
│  ├── Auto-commit          │      │  GET /projects/active                     │
│  ├── Auto-push            │      │  → Returns full unified context           │
│  └── Per-project repos    │      │  → Injected into ChatGPT on init          │
└───────────────────────────┘      └───────────────────────────────────────────┘
```

**Step-by-step flow:**

1. **Client Request**: ChatGPT (or any client) sends a task via `POST /execute`
2. **Task Processing**: Agent validates request, selects optimal LLM model
3. **AI Execution**: Aider executes the task using the selected LLM
4. **Memory Update**: Action logged to `memory.json["actions"]`
5. **Context Generation**: `generate_full_context()` creates unified `context_full.json`
6. **SQLite Indexing**: Context indexed to `context.db` for fast queries
7. **Git Operations**: Changes committed and pushed to GitHub
8. **Response**: Results returned to client with execution details

---

### Core System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LazyDeve Agent                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ORCHESTRATION LAYER (api/routes/)                                          │
│  ├── execute.py       → Main AI task execution with Aider                   │
│  ├── projects.py      → Project lifecycle management                        │
│  ├── context.py       → Unified context endpoints                           │
│  ├── git.py           → Git operations (commit, push, pull, diff)           │
│  ├── memory.py        → Memory management endpoints                         │
│  ├── system.py        → Health checks, OpenAPI schema                       │
│  ├── files.py         → File read/write operations                          │
│  ├── analysis.py      → Code analysis endpoints                             │
│  ├── run_local.py     → Local script execution                              │
│  └── llm.py           → LLM provider switching                              │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EXECUTION LAYER (core/)                                                    │
│  ├── basic_functional.py  → Aider integration, subprocess management        │
│  ├── llm_selector.py      → Multi-LLM provider selection and context-aware  │
│  ├── command_parser.py    → Command Precision Layer (CPL) for routing       │
│  └── event_bus.py         → Event-driven hooks and post-action triggers     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MEMORY/CONTEXT LAYER (core/)                                               │
│  ├── context_full.py      → Unified context generator (context_full.json)   │
│  ├── context_indexer.py   → SQLite indexing engine (context.db)             │
│  ├── memory_utils.py      → Memory I/O operations (memory.json)             │
│  ├── memory_processor.py  → Semantic analysis (tech stack, confidence)      │
│  ├── context_manager.py   → Session context lifecycle                       │
│  ├── context_initializer.py → Context initialization on startup/switch      │
│  ├── commit_tracker.py    → Git commit tracking and history                 │
│  └── readme_utils.py      → README extraction and processing                │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PROJECT LAYER (core/)                                                      │
│  ├── project_manager.py   → Project creation, switching, archival           │
│  ├── file_maintenance.py  → FIFO trimming for log files                     │
│  ├── system_protection.py → File/directory protection                       │
│  └── log_manager.py       → Unified JSON-based logging                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Memory Integration Flow

The memory pipeline provides unified context for AI operations:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY INTEGRATION FLOW                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SOURCES (JSON files in .lazydeve/)                                         │
│  ├── memory.json         → Actions history, semantic_context                │
│  ├── commit_history.json → Git commit records                               │
│  ├── snapshot.json       → Project state snapshot                           │
│  ├── config.json         → Project configuration, user_memory               │
│  └── session_context.json → README content, session metadata                │
│                                                                             │
│                              ↓ generate_full_context()                      │
│                                                                             │
│  UNIFIED OUTPUT                                                             │
│  └── context_full.json   → Single source of truth for ChatGPT               │
│      ├── project_name, description, tech_stack, keywords, confidence        │
│      ├── readme.preview (configurable, default: 1400 chars)                 │
│      ├── commits.last_commit, commits.recent[]                              │
│      ├── activity.total_actions, recent_actions[], error_patterns[]         │
│      ├── snapshot.last_run, status, pending_changes                         │
│      └── user_memory.notes (project rules/notes, max 300 chars)             │
│                                                                             │
│                              ↓ index_context_full()                         │
│                                                                             │
│  SQLITE INDEX                                                               │
│  └── context.db          → Fast queries for RAG/MCP integration             │ 
│      ├── commits table   → Commit history index                             │
│      ├── runs table      → Execution metadata (no stdout/stderr)            │
│      ├── embeddings table → Ready for RAG population (Task 9)               │
│      └── sync_metadata   → FIFO trim tracking                               │
│                                                                             │
│                              ↓ ChatGPT injection                            │
│                                                                             │
│  CONSUMPTION                                                                │
│  ├── GET /projects/active       → Returns full unified context              │
│  ├── GET /api/v1/context/full/* → Direct context access                     │
│  └── POST /api/v1/context/*/user-memory → Save project rules/notes          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key points:**
- **JSON is the source of truth** — SQLite mirrors for fast queries
- **context_full.json** is generated on: agent startup, project switch, API call
- **No caching layer** — context is always fresh from source files
- **FIFO trimming** — automatic cleanup of old log entries

---

### Project Structure

Each project has an isolated Git repository and `.lazydeve/` context folder:

```
projects/<project_name>/
├── .lazydeve/                    # LazyDeve metadata (per-project)
│   ├── memory.json               # Actions history, semantic context
│   ├── context_full.json         # Unified context (generated)
│   ├── context.db                # SQLite index
│   ├── commit_history.json       # Git commit records
│   ├── snapshot.json             # Project state snapshot
│   ├── config.json               # Project configuration
│   ├── session_context.json      # README content, session metadata
│   ├── stats.json                # Project statistics
│   └── logs/                     # Execution logs
│       ├── run_*.json            # Run execution details
│       ├── actions.log           # Plaintext action log
│       └── errors.log            # Error tracking
├── src/                          # Source code
├── tests/                        # Test files
└── README.md                     # Project documentation
```

---


## 🔐 Security Layer

LazyDeve operates **directly on a developer’s local machine**, interacting with the real filesystem and project sources. This execution model requires explicit safeguards.

Security is enforced as a **multi-layered system**, independent of LLM behavior.

**Key principles:**
- The agent is treated as a privileged but constrained actor
- All constraints are enforced by code, not prompts
- Violations are deterministically blocked and logged

**Protection layers:**
- **Core boundary protection** — critical system and agent files are immutable
- **Root and config integrity** — environment and infrastructure artifacts are protected
- **Project-scoped execution** — all operations are restricted to the active project tree
- **Allow-list enforcement** — only explicitly permitted paths and actions are allowed
- **Backup and rollback safety** — file mutations are preceded by automatic backups
- **Audit logging** — all allowed and blocked actions are recorded

This layered approach allows autonomous execution while minimizing risk during local operation.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** with pip
- **Git** (for version control)
- **Aider** (`pip install aider-chat`)
- **LLM API Key** (at minimum, OpenAI)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/Lev-AI/LazyDeve.git
cd LazyDeve

# 2. Install dependencies
pip install fastapi uvicorn python-dotenv pydantic aiohttp requests langdetect openai anthropic google-generativeai mistralai aider-chat

# 3. Create .env file
cat > .env << 'EOF'
# Required
OPENAI_API_KEY=sk-your-openai-api-key-here
API_BEARER_TOKEN=your-secure-token-here
ENABLE_AUTH=false

# Optional (for multi-LLM support)
ANTHROPIC_API_KEY=sk-ant-your-key-here
GEMINI_API_KEY=your-gemini-key-here
MISTRAL_API_KEY=your-mistral-key-here

# Server
PORT=8001
PUBLIC_AGENT_URL=http://localhost:8001
EOF

# 4. Start the agent
uvicorn agent:app --host 0.0.0.0 --port 8001
```

### Verify Installation

```bash
# Health check
curl http://localhost:8001/ping-agent

# Expected response:
# {"message": "pong", "status": "healthy", ...}
```

---

## 📱 ChatGPT Apps Integration

### Setup

1. **Get OpenAPI Schema**
   ```bash
   curl http://localhost:8001/openapi.yaml > openapi.yaml
   ```

2. **Create ChatGPT App**
   - Go to ChatGPT → Explore GPTs → Create a GPT
   - Under "Actions", paste the OpenAPI schema
   - Set the server URL to your agent's public URL
   - Configure authentication: Bearer token with your `API_BEARER_TOKEN`

3. **Verification Checklist**
   - [ ] `GET /ping-agent` returns healthy status
   - [ ] `GET /projects/list` returns project array
   - [ ] `POST /execute` with simple task succeeds

### Base URL Configuration

| Environment | Base URL |
|-------------|----------|
| Local development | `http://localhost:8001` |
| Cloudflare tunnel | `https://your-tunnel.trycloudflare.com` |
| Production | `https://agent.yourdomain.com` |

### Authentication

All authenticated endpoints require:
```
Authorization: Bearer <your-api-token>
```

Set in `.env`:
```env
API_BEARER_TOKEN=your-secure-token-here
ENABLE_AUTH=true  # Enable for production
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `API_BEARER_TOKEN` | Yes | — | Bearer token for authentication |
| `ENABLE_AUTH` | No | `false` | Enable authentication |
| `PORT` | No | `8001` | Server port |
| `PUBLIC_AGENT_URL` | No | `http://localhost:8001` | Public URL for OpenAPI |
| `LLM_MODE` | No | `auto` | `auto` or `manual` |
| `MANUAL_LLM` | No | `gpt-4o` | Model when `LLM_MODE=manual` |
| `ANTHROPIC_API_KEY` | No | — | Anthropic API key |
| `GEMINI_API_KEY` | No | — | Google Gemini API key |
| `MISTRAL_API_KEY` | No | — | Mistral API key |
| `GITHUB_TOKEN` | No | — | GitHub personal access token |
| `GITHUB_USER` | No | — | GitHub username |

### LLM Mode Selection

```env
# Auto mode (default): Model selected based on task type + project context
LLM_MODE=auto

# Manual mode: All tasks use specified model
LLM_MODE=manual
MANUAL_LLM=gpt-4o
```

---

## 📊 Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ping-agent` | GET | Health check |
| `/projects/list` | GET | List all projects |
| `/projects/active` | GET | Get active project with full context |
| `/projects/set-active/{name}` | POST | Switch active project |
| `/execute` | POST | Execute AI task via Aider |
| `/api/v1/context/full/{project}` | GET | Get unified context |
| `/api/v1/context/{project}/user-memory` | POST | Save project rules/notes |
| `/git/commit` | POST | Commit changes |
| `/git/push` | POST | Push to remote |
| `/git/status` | GET | Git status |
| `/openapi.yaml` | GET | OpenAPI schema |

For complete API reference, see `GET /openapi.yaml`.

---

## 🔮 Roadmap / Planned

The following features are **planned but not yet implemented**:

| Feature | Status | Description |
|---------|--------|-------------|
| **RagCore Integration** | 🔜 Planned | External RAG service for semantic search and knowledge retrieval |
| **MCP Server** | 🔜 Planned | Model Context Protocol server for multi-agent orchestration |
| **Docker Deployment** | 🔜 Planned | Containerized deployment with persistent volumes |

---

## 🆘 Troubleshooting

### Common Issues

#### Agent Won't Start
```bash
# Check if port is in use
lsof -i :8001  # Linux/Mac
netstat -ano | findstr :8001  # Windows

# Verify environment
python -c "import os; print('OPENAI_API_KEY' in os.environ)"

# Check logs
tail -f logs/agent.log
```

#### Missing Dependencies
```bash
# Install all required packages
pip install fastapi  python-dotenv pydantic aiohttp requests langdetect openai anthropic google-generativeai mistralai aider-chat
```

#### Authentication Errors
```bash
# Verify token is set
echo $API_BEARER_TOKEN

# Test with token
curl -H "Authorization: Bearer your-token" http://localhost:8001/ping-agent
```

#### Git Push Failures
```bash
# Check GitHub token
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Verify remote
cd projects/your-project && git remote -v
```

### Getting Help

- **GitHub Issues**: Report bugs and feature requests
- **API Reference**: `GET /openapi.yaml` for complete endpoint documentation
- **Logs**: Check `logs/agent.log` for debugging information

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**LazyDeve Agent** — Autonomous AI development, from anywhere. 🚀


## 📚 Documentation

- [System Architecture Overview](docs/architecture/overview.md)
- [Memory & Context Layer](docs/architecture/memory-layer.md)
- [Security Model](docs/architecture/security-model.md)
- [MCP Orchestration Roadmap](docs/roadmap/mcp-server.md)

## 🛠 Setup & Usage
- [Local Setup](docs/setup/local-run.md)
- [Docker Setup (Optional)](docs/setup/docker.md)
- [Environment Variables](docs/setup/env-reference.md)

## 🎥 Demos & Examples
- [Usage Examples](docs/usage/examples.md)
- [Workflow Patterns](docs/usage/workflows.md)
- [Demo Videos](docs/media/videos.md)