# LazyDeve Full Architecture Documentation

**Version:** 1.5.0  
**Last Updated:** 2025-12-20  
**Status:** Production Ready

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Architecture Diagram](#system-architecture-diagram)
3. [Main Entry Point](#main-entry-point)
4. [API Routes Layer](#api-routes-layer)
5. [Core Modules Layer](#core-modules-layer)
6. [Utilities Layer](#utilities-layer)
7. [Data Flow Architecture](#data-flow-architecture)
8. [Integration Points](#integration-points)
9. [Security Architecture](#security-architecture)
10. [Memory & Context Pipeline](#memory--context-pipeline)

---

## Architecture Overview

LazyDeve is a **stateful autonomous development agent** built on FastAPI that provides:
- **Persistent project context** across sessions
- **AI-powered code execution** via Aider integration
- **Structured memory system** (JSON + SQLite hybrid)
- **Per-project Git repositories** with auto-commit/push
- **Multi-LLM provider support** (OpenAI, Anthropic, Gemini, Mistral)
- **Command Precision Layer (CPL)** for deterministic routing
- **Comprehensive protection system** for system files

### Design Principles

1. **JSON as Source of Truth**: All context stored in human-readable JSON files
2. **SQLite as Performance Layer**: Fast queries and RAG readiness via SQLite indexing
3. **Modular Architecture**: Clear separation between routes, core logic, and utilities
4. **Per-Project Isolation**: Each project has its own Git repo and context folder
5. **Event-Driven Hooks**: Post-action events for extensibility
6. **Security by Design**: Multi-layer protection system

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL CLIENT LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   ChatGPT    │  │  REST Client │  │   Scripts    │  │   MCP Server │     │
│  │   Actions    │  │   (curl/API) │  │  (Python)    │  │  (Future)    │     │
│  └──────┬───────┘  └──────┬───────┘  └───────┬──────┘  └──────┬───────┘     │
└─────────┼─────────────────┼──────────────────┼────────────────┼─────────────┘
          │                 │                  │                │
          └─────────────────┴──────────────────┴────────────────┘
                              │ HTTP REST (Port 8001)
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LAZYDEVE AGENT (FastAPI Application)                     │
│                              agent.py                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    API ROUTES LAYER (api/routes/)                   │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │  execute.py      → AI task execution (Aider integration)            │  │
│  │  projects.py      → Project lifecycle management                     │  │
│  │  context.py      → Unified context endpoints                        │  │
│  │  memory.py       → Memory management endpoints                      │  │
│  │  docs.py         → Documentation generation                         │  │
│  │  git.py          → Git operations (commit, push, pull, status)      │  │
│  │  files.py        → File read/write operations                       │  │
│  │  analysis.py     → Code analysis and testing                        │  │
│  │  run_local.py    → Local script execution                           │  │
│  │  llm.py          → LLM provider switching                            │  │
│  │  system.py       → Health checks, OpenAPI schema                    │  │
│  │  protection.py   → System protection status                         │  │
│  │  admin.py        → Administrative operations                         │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    CORE MODULES LAYER (core/)                      │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │  Execution Layer:                                                   │  │
│  │    basic_functional.py  → Aider integration, subprocess management   │  │
│  │    llm_selector.py      → Multi-LLM provider selection              │  │
│  │    command_parser.py   → Command Precision Layer (CPL)             │  │
│  │    event_bus.py        → Event-driven hooks                        │  │
│  │                                                                     │  │
│  │  Memory/Context Layer:                                              │  │
│  │    context_full.py      → Unified context generator                │  │
│  │    context_indexer.py   → SQLite indexing engine                   │  │
│  │    memory_utils.py      → Memory I/O operations                    │  │
│  │    memory_processor.py → Semantic analysis                         │  │
│  │    context_manager.py  → Session context lifecycle                 │  │
│  │    context_initializer.py → Context initialization                 │  │
│  │    commit_tracker.py   → Git commit tracking                       │  │
│  │    readme_utils.py     → README extraction                         │  │
│  │                                                                     │  │
│  │  Project Layer:                                                     │  │
│  │    project_manager.py  → Project creation, switching               │  │
│  │    file_maintenance.py → FIFO trimming for logs                    │  │
│  │    system_protection.py → File/directory protection                │  │
│  │    log_manager.py      → Unified JSON-based logging                │  │
│  │                                                                     │  │
│  │  Support Layer:                                                     │  │
│  │    auth_middleware.py  → Bearer token authentication               │  │
│  │    config.py           → Configuration management                  │  │
│  │    error_handler.py    → Error handling                            │  │
│  │    ai_context.py       → AI context generation                     │  │
│  │    documentation_generator.py → README generation                  │  │
│  │    logs/run_logger.py  → Execution logging                         │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    UTILITIES LAYER (utils/)                          │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │  git_utils.py      → Git operations (safe wrappers)                │  │
│  │  github_api.py     → GitHub API integration                          │  │
│  │  path_utils.py     → Path validation and extraction                 │  │
│  │  translation.py    → Language detection and translation              │  │
│  │  webhook.py        → Webhook notifications                          │  │
│  │  startup.py        → Agent initialization                           │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXECUTION & STORAGE LAYER                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────┐      ┌───────────────────────────────────┐  │
│  │    EXECUTION LAYER        │      │     MEMORY/CONTEXT LAYER          │  │
│  │                           │      │                                   │  │
│  │  ├── Aider (AI coding)   │      │  ├── memory.json                  │  │
│  │  ├── Git operations       │      │  ├── context_full.json            │  │
│  │  └── File management      │      │  ├── context.db (SQLite)          │  │
│  │                           │      │  ├── run_*.json                   │  │
│  │                           │      │  ├── commit_history.json          │  │
│  │                           │      │  ├── snapshot.json                │  │
│  │                           │      │  └── config.json                  │  │
│  └──────────────────────────┘      └───────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Main Entry Point

### `agent.py`

**Purpose**: FastAPI application entry point and router registration

**Key Responsibilities**:
- FastAPI app initialization with lifespan management
- Router registration and endpoint organization
- Startup/shutdown event handling
- Auto-initialization middleware
- OpenAPI schema generation

**Key Components**:

```python
# App Configuration
app = FastAPI(
    title="LazyDeve Agent",
    version="1.3.0",
    servers=[{"url": PUBLIC_AGENT_URL}],
    lifespan=lifespan
)

# Router Registration
app.include_router(execute_router)      # /execute
app.include_router(projects_router)     # /projects/*
app.include_router(context_router)      # /api/v1/context/*
# ... (all other routers)
```

**Startup Sequence**:
1. Load environment variables
2. Configure UTF-8 encoding
3. Initialize context manager
4. Register all API routers
5. Run auto-initialization sequence
6. Start Uvicorn server (port 8001)

**Lifespan Events**:
- **Startup**: Context initialization, project validation
- **Shutdown**: Cleanup, state persistence

---

## API Routes Layer

All routes are located in `api/routes/` and follow FastAPI router patterns.

### 1. `execute.py` - AI Task Execution

**Prefix**: `/execute`  
**Authentication**: Required (Bearer token)

**Purpose**: Main endpoint for AI-powered development tasks via Aider

**Key Endpoints**:
- `POST /execute` - Execute AI task with automatic model selection

**Features**:
- Command Precision Layer (CPL) integration for deterministic routing
- Automatic LLM model selection based on task type
- File protection and validation
- Auto-commit after execution
- Memory hooks integration (TASK 8.11.1)
- Run execution logging to `run_*.json`

**Data Flow**:
```
Client Request → CPL Parsing → LLM Selection → Aider Execution → 
Memory Update → Run Logging → SQLite Indexing → Git Commit → Response
```

**Key Functions**:
- `execute_task_endpoint()` - Main handler
- Integrates with `command_parser.py` for intent detection
- Calls `log_run_execution()` for execution tracking

---

### 2. `projects.py` - Project Management

**Prefix**: `/projects`  
**Authentication**: Optional

**Purpose**: Project lifecycle management (create, list, switch, archive)

**Key Endpoints**:
- `GET /projects/list` - List all projects
- `POST /projects/create/{name}` - Create new project
- `GET /projects/active` - Get active project with full context
- `POST /projects/set-active/{name}` - Switch active project
- `POST /projects/archive/{name}` - Archive project
- `DELETE /projects/{name}` - Delete project

**Features**:
- Per-project Git repository creation
- Automatic GitHub repository creation (if enabled)
- Project context initialization
- Active project context management
- Project validation and sanitization

**Integration**:
- Uses `core/project_manager.py` for project operations
- Integrates with `context_initializer.py` for context setup
- Calls `context_full.py` for unified context generation

---

### 3. `context.py` - Unified Context API

**Prefix**: `/api/v1/context`  
**Authentication**: Optional

**Purpose**: Expose unified context endpoints for ChatGPT integration

**Key Endpoints**:
- `GET /api/v1/context/full/{project}` - Get full unified context
- `GET /api/v1/context/summary/{project}` - Get summary context
- `GET /api/v1/context/detailed/{project}` - Get detailed context
- `GET /api/v1/context/llm/{project}` - Get LLM-optimized context
- `POST /api/v1/context/{project}/user-memory` - Save user notes

**Features**:
- Unified context generation from multiple sources
- README preview (configurable size)
- Recent actions extraction
- Commit history integration
- User memory persistence (max 300 chars)

**Data Sources**:
- `memory.json` - Actions and semantic context
- `commit_history.json` - Git commit records
- `snapshot.json` - Project state
- `config.json` - Project configuration
- `session_context.json` - README content

---

### 4. `memory.py` - Memory Management

**Prefix**: `/api/v1/projects/{project_name}/memory`  
**Authentication**: Optional

**Purpose**: Semantic memory operations and analysis

**Key Endpoints**:
- `GET /api/v1/projects/{project_name}/memory` - Get complete memory
- `POST /api/v1/projects/{project_name}/memory/update` - Update memory
- `GET /api/v1/projects/{project_name}/memory/context` - Get AI context
- `POST /api/v1/projects/{project_name}/memory/context/invalidate` - Invalidate cache

**Features**:
- Memory I/O operations
- Semantic context analysis
- Tech stack extraction
- Activity summarization
- Cache invalidation

**Integration**:
- Uses `core/memory_utils.py` for I/O
- Uses `core/memory_processor.py` for analysis
- Uses `core/ai_context.py` for context generation

---

### 5. `docs.py` - Documentation Management

**Prefix**: `/api/v1/projects/{project_name}/docs`  
**Authentication**: Optional

**Purpose**: README generation and documentation management

**Key Endpoints**:
- `GET /api/v1/projects/{project_name}/docs` - Get project docs
- `POST /api/v1/projects/{project_name}/docs/update` - Update README
- `GET /api/v1/projects/{project_name}/docs/readme` - Get README content
- `DELETE /api/v1/projects/{project_name}/docs/semantic-section` - Remove semantic section

**Features**:
- Automatic README generation
- Semantic section management
- README content extraction
- Documentation metadata tracking

**Integration**:
- Uses `core/documentation_generator.py` for README operations
- Integrates with `core/readme_utils.py` for content extraction

---

### 6. `git.py` - Git Operations

**Prefix**: `/git` (no prefix)  
**Authentication**: Required (Bearer token)

**Purpose**: Per-project Git operations (commit, push, pull, status)

**Key Endpoints**:
- `POST /commit` - Commit changes to active project
- `POST /sync` - Pull from remote repository
- `POST /push` - Push to remote repository
- `GET /status` - Get Git status
- `GET /commits` - Get commit history

**Features**:
- Per-project Git repository isolation
- Automatic GitHub remote creation
- Memory hooks integration
- Event bus triggers
- Safe Git command execution

**Integration**:
- Uses `utils/git_utils.py` for Git operations
- Uses `core/commit_tracker.py` for commit tracking
- Uses `core/memory_utils.py` for action logging

---

### 7. `files.py` - File Operations

**Prefix**: `/` (no prefix)  
**Authentication**: Required (Bearer token)

**Purpose**: File read/write operations with project path injection

**Key Endpoints**:
- `POST /read-file` - Read file content
- `POST /update-file` - Create/update file
- `GET /list-files` - List project files

**Features**:
- Automatic project path injection
- Path validation and sanitization
- File protection checks
- Backup creation before updates
- Project-scoped operations

**Integration**:
- Uses `core/basic_functional.py` for file operations
- Uses `core/system_protection.py` for path validation
- Uses `core/context_manager.py` for active project detection

---

### 8. `analysis.py` - Code Analysis

**Prefix**: `/` (no prefix)  
**Authentication**: Required (Bearer token)

**Purpose**: Code analysis and testing endpoints

**Key Endpoints**:
- `POST /analyze-code` - Perform code analysis (AI or static)
- `POST /run-tests` - Run project tests

**Features**:
- AI-assisted analysis via Aider
- Static analysis via Pylint
- Test execution with timeout
- Security path validation
- Memory hooks integration

**Integration**:
- Uses `core/basic_functional.py` for Aider integration
- Uses `utils/path_utils.py` for path validation

---

### 9. `run_local.py` - Local Script Execution

**Prefix**: `/run-local`  
**Authentication**: Required (Bearer token)

**Purpose**: Execute project scripts in multiple languages

**Key Endpoints**:
- `POST /run-local` - Execute script with language detection

**Features**:
- Multi-language support (Python, Node.js, Bash, etc.)
- Automatic language detection
- Recursion protection (async-safe)
- Execution time tracking
- Run logging to `run_*.json`
- Memory hooks integration

**Integration**:
- Uses `core/logs/run_logger.py` for execution logging
- Uses `core/memory_utils.py` for action tracking
- Uses `core/event_bus.py` for post-execution events

---

### 10. `llm.py` - LLM Provider Management

**Prefix**: `/set-llm`  
**Authentication**: Optional

**Purpose**: Dynamic LLM provider switching

**Key Endpoints**:
- `POST /set-llm` - Switch LLM provider
- `GET /llm-info` - Get current provider info

**Features**:
- Multi-provider support (OpenAI, Anthropic, Gemini, Mistral)
- Provider availability checking
- Dynamic switching without restart
- Provider information retrieval

**Integration**:
- Uses `core/llm_selector.py` for provider management

---

### 11. `system.py` - System Endpoints

**Prefix**: `/` (no prefix)  
**Authentication**: Optional

**Purpose**: Health checks, OpenAPI schema, routing guide

**Key Endpoints**:
- `GET /ping-agent` - Health check
- `GET /ping-memory` - Memory system health check
- `GET /openapi.yaml` - OpenAPI schema for ChatGPT
- `GET /routing-guide` - Endpoint routing documentation

**Features**:
- System health monitoring
- OpenAPI schema generation
- Routing guide for agent guidance
- Memory system validation

---

### 12. `protection.py` - System Protection

**Prefix**: `/` (no prefix)  
**Authentication**: Optional

**Purpose**: System protection status and validation

**Key Endpoints**:
- `GET /protection-status` - Get protection status
- `POST /check-protection` - Check file operation protection

**Features**:
- Protection rules inspection
- File operation validation
- Protected files listing
- Protection configuration access

**Integration**:
- Uses `core/system_protection.py` for protection logic

---

### 13. `admin.py` - Administrative Operations

**Prefix**: `/admin`  
**Authentication**: Required (Admin secret key)

**Purpose**: Administrative operations (reset initialization)

**Key Endpoints**:
- `POST /admin/reset-init` - Reset initialization state

**Features**:
- Admin-only operations
- Secret key authentication
- Initialization state reset

**Integration**:
- Uses `core/lazydeve_boot.py` for initialization management

---

## Core Modules Layer

Core modules are located in `core/` and provide the business logic for the agent.

### Execution Layer

#### `basic_functional.py`
**Purpose**: Foundational functions for Aider integration and subprocess management

**Key Functions**:
- `run_aider_task_async()` - Execute Aider tasks asynchronously
- `read_file()`, `update_file()` - File I/O operations
- `log_message()` - Unified logging
- `configure_utf8()` - UTF-8 encoding setup

**Integration**: Used by all routes for file operations and Aider execution

---

#### `llm_selector.py`
**Purpose**: Multi-LLM provider selection and context-aware model selection

**Key Functions**:
- `get_llm_selector()` - Get LLM selector instance
- `select_model()` - Context-aware model selection
- `set_llm()` - Switch provider
- `get_provider_info()` - Get provider information

**Features**:
- Automatic model selection based on task type
- Provider availability checking
- Fallback to default model
- Semantic context consideration

**Supported Providers**:
- OpenAI (gpt-4o, gpt-4o-mini, gpt-4-turbo)
- Anthropic (claude-3-5-sonnet, claude-3-opus)
- Google Gemini (gemini-pro, gemini-ultra)
- Mistral (mistral-medium, mistral-large)

---

#### `command_parser.py` - Command Precision Layer (CPL)
**Purpose**: Centralized, deterministic command routing

**Key Functions**:
- `parse_command()` - Parse command intent
- `log_parsed_command()` - Log parsing results
- `inject_project_path()` - Auto-inject project paths

**Intents Detected**:
- `archive_project` - Archive/delete project
- `delete_file` - Delete file (Git-driven)
- `update_file` - Create/update file
- `run_local` - Execute script directly
- `execute_aider` - Default fallback to Aider

**Features**:
- Deterministic routing (same input → same output)
- Regex-based intent detection
- No LLM calls (lightweight)
- Logging to `logs/command_parser.log`

**Integration**: Used by `/execute` endpoint for command routing

---

#### `event_bus.py`
**Purpose**: Event-driven hooks and post-action triggers

**Key Functions**:
- `trigger_event()` - Trigger event with handlers
- Event registration system
- Async event support

**Event Types**:
- `post_action` - After any action
- `post_execute` - After task execution
- `post_commit` - After Git commit
- `post_file_update` - After file update

**Integration**: Used throughout the system for extensibility

---

### Memory/Context Layer

#### `context_full.py`
**Purpose**: Unified context generator (creates `context_full.json`)

**Key Functions**:
- `generate_full_context()` - Generate unified context
- `extract_recent_actions()` - Extract actions from memory.json

**Output Structure**:
```json
{
  "version": "1.0",
  "project_name": "...",
  "description": "...",
  "tech_stack": [...],
  "readme": {...},
  "commits": {...},
  "activity": {
    "recent_actions": [...]
  },
  "snapshot": {...},
  "stats": {...},
  "user_memory": {...}
}
```

**Data Sources**:
- `memory.json` - Actions and semantic context
- `commit_history.json` - Git commits
- `snapshot.json` - Project state
- `config.json` - Configuration
- `session_context.json` - README content

**Integration**: Called by `/projects/active` and `/api/v1/context/full/*`

---

#### `context_indexer.py`
**Purpose**: SQLite indexing engine (creates and maintains `context.db`)

**Key Functions**:
- `init_context_db()` - Initialize database schema
- `index_context_full()` - Index context_full.json
- `index_run_log_metadata()` - Index run_*.json files
- `sync_run_logs_to_sqlite()` - Batch sync run logs
- `update_sync_metadata_on_trim()` - Track FIFO trim events

**Database Schema**:
- `schema_version` - Schema versioning
- `snapshots` - Project snapshots
- `events` - Event history
- `commits` - Commit records
- `runs` - Execution metadata (no stdout/stderr)
- `embeddings` - RAG embeddings (Task 9)
- `sync_metadata` - JSON ↔ SQLite sync tracking

**Features**:
- Metadata-only indexing (no stdout/stderr in runs table)
- Schema versioning for migrations
- Async-safe writes
- FIFO trim tracking

**Integration**: Called automatically when context_full.json or run_*.json are created

---

#### `memory_utils.py`
**Purpose**: Memory I/O operations (manages `memory.json`)

**Key Functions**:
- `load_memory()` - Load project memory
- `save_memory()` - Save project memory
- `update_memory()` - Update memory with action
- `init_project_memory()` - Initialize new project memory
- `log_project_action()` - Log action to plaintext log

**Memory Structure**:
```json
{
  "project_name": "...",
  "stats": {...},
  "actions": [...],
  "semantic_context": {...},
  "documentation": {...}
}
```

**Features**:
- Thread-safe JSON operations
- Automatic backup creation
- FIFO trimming integration
- Action history tracking (last 100 actions)

**Integration**: Used by all routes that need to track actions

---

#### `memory_processor.py`
**Purpose**: Semantic analysis and context processing

**Key Functions**:
- `analyze_project_context()` - Analyze project for semantic context
- `update_memory_context()` - Update semantic context
- `summarize_activity()` - Summarize action history

**Features**:
- Tech stack extraction
- Activity summarization
- Error pattern detection
- Confidence scoring

**Integration**: Used by `/api/v1/projects/{project}/memory/update`

---

#### `context_manager.py`
**Purpose**: Session context lifecycle management

**Key Functions**:
- `context_manager.get_project()` - Get active project
- `context_manager.set_project()` - Set active project
- `load_context()` - Load session context
- `save_context()` - Save session context

**Features**:
- Active project tracking
- Session context persistence
- Project switching

**Integration**: Used throughout the system for project context

---

#### `context_initializer.py`
**Purpose**: Context initialization on startup/project switch

**Key Functions**:
- `initialize_context_on_start()` - Initialize on agent startup
- Context validation
- Schema version checking

**Features**:
- Automatic context generation
- Schema migration support
- Project validation

**Integration**: Called during agent startup and project switching

---

#### `commit_tracker.py`
**Purpose**: Git commit tracking and history

**Key Functions**:
- `load_commit_data()` - Load commit history
- `save_commit_data()` - Save commit record
- `track_commit()` - Track new commit

**Features**:
- Commit history persistence
- File change tracking
- Commit metadata storage

**Integration**: Used by `/git/commit` and context generation

---

#### `readme_utils.py`
**Purpose**: README extraction and processing

**Key Functions**:
- `extract_readme_summary()` - Extract README preview
- `get_readme_content()` - Get full README
- README checksum calculation

**Features**:
- Configurable preview size (default: 1400 chars)
- Checksum tracking
- Last update timestamp

**Integration**: Used by `context_full.py` for README preview

---

### Project Layer

#### `project_manager.py`
**Purpose**: Project lifecycle management

**Key Functions**:
- `create_project()` - Create new project
- `list_projects()` - List all projects
- `archive_project()` - Archive project
- `delete_project()` - Delete project
- `validate_project_name()` - Validate project name

**Features**:
- Per-project Git repository creation
- GitHub repository creation (optional)
- Project structure initialization
- Project validation

**Integration**: Used by `/projects/*` endpoints

---

#### `file_maintenance.py`
**Purpose**: FIFO trimming for log files

**Key Functions**:
- `maintain_lazydeve_json_files()` - Unified maintenance
- `trim_memory_actions()` - Trim memory.json actions
- `rotate_logs()` - Rotate log files

**Features**:
- Automatic file size management
- FIFO trimming (keep last N entries)
- Unified maintenance trigger
- SQLite sync metadata tracking

**Integration**: Called automatically when files exceed size limits

---

#### `system_protection.py`
**Purpose**: File and directory protection system

**Key Functions**:
- `get_protection_status()` - Get protection status
- `check_file_operation_protection()` - Validate file operations
- `list_protected_files()` - List protected files
- `get_active_project_context()` - Get active project

**Protection Rules**:
- Root file protection (agent.py, README.md, etc.)
- Directory protection (core/, api/, utils/)
- Project-scoped execution
- Allow-list enforcement

**Integration**: Used by all file operation endpoints

---

#### `log_manager.py`
**Purpose**: Unified JSON-based logging

**Key Functions**:
- Structured logging
- Log rotation
- Error tracking

**Integration**: Used throughout the system for logging

---

### Support Layer

#### `auth_middleware.py`
**Purpose**: Bearer token authentication

**Key Functions**:
- `verify_token()` - Verify Bearer token
- `get_auth_status()` - Get authentication status

**Features**:
- Optional authentication (ENABLE_AUTH env var)
- Bearer token validation
- Development mode (auth disabled by default)

**Integration**: Used as dependency in protected routes

---

#### `config.py`
**Purpose**: Configuration management

**Key Functions**:
- Environment variable loading
- Configuration validation
- Runtime configuration access

**Configuration Sources**:
- `.env` file
- Environment variables
- Runtime updates

**Integration**: Used throughout the system for configuration

---

#### `error_handler.py`
**Purpose**: Error handling and reporting

**Key Functions**:
- Structured error responses
- Error logging
- Exception handling

**Integration**: Used by all routes for error handling

---

#### `ai_context.py`
**Purpose**: AI context generation

**Key Functions**:
- `get_project_context_summary()` - Get context summary
- `invalidate_project_cache()` - Invalidate cache

**Features**:
- Multiple format support (summary, detailed, llm)
- Cache management
- Context optimization

**Integration**: Used by `/api/v1/context/*` endpoints

---

#### `documentation_generator.py`
**Purpose**: README generation

**Key Functions**:
- `generate_project_docs()` - Generate documentation
- `update_readme()` - Update README
- `get_readme_content()` - Get README

**Integration**: Used by `/api/v1/projects/{project}/docs/*`

---

#### `logs/run_logger.py`
**Purpose**: Execution logging (creates `run_*.json` files)

**Key Functions**:
- `log_run_execution()` - Log execution result
- `_generate_summary()` - Generate execution summary
- `_extract_error_keywords()` - Extract error keywords

**Features**:
- Structured JSON logging
- Markdown report generation
- Secret masking
- SQLite indexing integration (TASK 8.11.1)
- Memory.json update integration (TASK 8.11.1)

**Output Files**:
- `run_YYYYMMDD_HHMMSS.json` - Structured execution log
- `run_YYYYMMDD_HHMMSS.md` - Markdown summary

**Integration**: Called by `/execute` and `/run-local` endpoints

---

## Utilities Layer

Utilities are located in `utils/` and provide helper functions for common operations.

### `git_utils.py`
**Purpose**: Safe Git operation wrappers

**Key Functions**:
- `safe_git_command()` - Execute Git command safely
- `safe_git_add()` - Stage files
- `safe_git_commit()` - Commit changes
- `safe_git_push()` - Push to remote
- `safe_git_pull()` - Pull from remote
- `safe_git_status()` - Get Git status
- `remove_via_git()` - Delete file via Git
- `remove_via_git_multi()` - Delete multiple files

**Features**:
- Per-project Git repository isolation
- Error handling
- Command validation
- Working directory management

**Integration**: Used by `/git/*` endpoints and file deletion operations

---

### `github_api.py`
**Purpose**: GitHub API integration

**Key Functions**:
- GitHub repository creation
- Remote repository management
- GitHub API calls

**Features**:
- Repository creation
- Remote URL management
- API authentication

**Integration**: Used by `project_manager.py` for GitHub operations

---

### `path_utils.py`
**Purpose**: Path validation and extraction

**Key Functions**:
- `extract_path_from_text()` - Extract path from text
- `extract_paths_from_text()` - Extract multiple paths
- `is_safe_path()` - Validate path safety
- `is_restricted_path()` - Check if path is restricted
- `load_restricted_directories()` - Load protection rules

**Features**:
- Path sanitization
- Security validation
- Project path injection
- Restricted directory checking

**Integration**: Used by all file operation endpoints

---

### `translation.py`
**Purpose**: Language detection and translation

**Key Functions**:
- `translate_prompt()` - Translate prompt to English
- `gpt_translate_to_english()` - GPT-based translation
- `configure_utf8()` - Configure UTF-8 encoding

**Features**:
- Automatic language detection
- Translation to English (for LLM compatibility)
- UTF-8 encoding support

**Integration**: Used by `/execute` endpoint for multilingual support

---

### `webhook.py`
**Purpose**: Webhook notifications

**Key Functions**:
- `safe_webhook_notify()` - Send webhook notification
- `fetch_with_retry()` - HTTP request with retry
- `log_network_error()` - Log network errors
- `handle_response()` - Handle HTTP response

**Features**:
- Retry logic
- Error logging
- Network error handling

**Integration**: Used for external notifications

---

### `startup.py`
**Purpose**: Agent initialization

**Key Functions**:
- `load_agent_rules()` - Load agent rules
- `sync_agent_memory()` - Sync agent memory
- `agent_intro()` - Display agent introduction
- `update_agent_state()` - Update agent state
- `notify_agent_ready()` - Notify agent ready

**Features**:
- Startup sequence management
- State initialization
- Memory synchronization

**Integration**: Called during agent startup

---

## Data Flow Architecture

### Complete Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLIENT REQUEST                                      │
│                    POST /execute {"task": "..."}                           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    API ROUTE: execute.py                                     │
│  - Verify authentication                                                    │
│  - Parse request body                                                       │
│  - Get active project from context_manager                                  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              COMMAND PRECISION LAYER (command_parser.py)                    │
│  - Parse command intent (archive, delete, update, run_local, execute_aider) │
│  - Route to appropriate endpoint                                            │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              LLM SELECTOR (llm_selector.py)                                  │
│  - Select optimal LLM model based on task type and context                  │
│  - Fallback to default if provider unavailable                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              AIDER EXECUTION (basic_functional.py)                          │
│  - Execute task via Aider CLI                                               │
│  - Track execution time                                                      │
│  - Capture stdout/stderr                                                     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              RUN LOGGING (logs/run_logger.py)                                │
│  - Create run_*.json file                                                   │
│  - Generate Markdown summary                                                 │
│  - Index to SQLite (index_run_log_metadata)                                  │
│  - Update memory.json (update_memory)                                        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              MEMORY UPDATE (memory_utils.py)                                 │
│  - Add execute action to memory.json["actions"]                             │
│  - Update stats (executions++, total_actions++)                              │
│  - Trigger FIFO trimming if needed                                           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              CONTEXT GENERATION (context_full.py)                            │
│  - Generate context_full.json from all sources                               │
│  - Extract recent_actions from memory.json                                   │
│  - Index to SQLite (index_context_full)                                      │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              GIT OPERATIONS (git_utils.py)                                   │
│  - Auto-commit changes                                                       │
│  - Push to remote (if enabled)                                               │
│  - Track commit in commit_history.json                                       │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              EVENT BUS (event_bus.py)                                       │
│  - Trigger post_action events                                                │
│  - Trigger post_execute events                                               │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RESPONSE TO CLIENT                                   │
│              {"status": "success", "result": {...}}                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Memory Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SOURCE FILES (.lazydeve/)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  memory.json         → Actions history, semantic_context                    │
│  commit_history.json → Git commit records                                   │
│  snapshot.json       → Project state snapshot                               │
│  config.json         → Project configuration, user_memory                  │
│  session_context.json → README content, session metadata                    │
│  run_*.json          → Execution logs (detailed)                           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              CONTEXT FULL GENERATOR (context_full.py)                        │
│  generate_full_context()                                                    │
│  - Loads all source files                                                   │
│  - Merges into unified structure                                            │
│  - Extracts recent_actions from memory.json                                 │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    context_full.json                                        │
│  - Unified context structure                                                │
│  - Single source of truth for ChatGPT                                       │
│  - Generated on: startup, project switch, API call                          │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              SQLITE INDEXER (context_indexer.py)                            │
│  index_context_full()                                                       │
│  - Indexes to context.db                                                    │
│  - Tables: commits, snapshots, runs, embeddings                             │
│  - Metadata only (no stdout/stderr)                                         │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    context.db (SQLite)                                       │
│  - Fast queries for RAG/MCP                                                 │
│  - Metadata indexing                                                        │
│  - Ready for Task 9 (RAG embeddings)                                        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CHATGPT INJECTION                                        │
│  GET /projects/active                                                       │
│  GET /api/v1/context/full/{project}                                         │
│  - Returns full unified context                                             │
│  - Injected into ChatGPT on init                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Integration Points

### 1. Aider Integration
- **Module**: `core/basic_functional.py`
- **Function**: `run_aider_task_async()`
- **Usage**: `/execute` endpoint
- **Features**: Async execution, timeout handling, output capture

### 2. Git Integration
- **Module**: `utils/git_utils.py`
- **Usage**: `/git/*` endpoints, auto-commit after execution
- **Features**: Per-project repositories, safe command execution

### 3. GitHub Integration
- **Module**: `utils/github_api.py`
- **Usage**: Project creation, remote management
- **Features**: Repository creation, remote URL management

### 4. LLM Provider Integration
- **Module**: `core/llm_selector.py`
- **Providers**: OpenAI, Anthropic, Gemini, Mistral
- **Usage**: Automatic model selection, dynamic switching

### 5. SQLite Integration
- **Module**: `core/context_indexer.py`
- **Usage**: Context indexing, run log indexing
- **Features**: Schema versioning, async-safe writes, metadata tracking

### 6. Event System Integration
- **Module**: `core/event_bus.py`
- **Usage**: Post-action hooks throughout the system
- **Features**: Extensible event system, async support

---

## Security Architecture

### Protection Layers

1. **Authentication Layer**
   - Bearer token authentication (optional)
   - Admin secret key for admin operations
   - Environment-based configuration

2. **Path Protection Layer**
   - Root file protection (agent.py, README.md, etc.)
   - Directory protection (core/, api/, utils/)
   - Restricted directory checking

3. **Project Scoping**
   - All operations scoped to active project
   - Automatic project path injection
   - Project context validation

4. **File Operation Protection**
   - Pre-operation validation
   - Backup creation before updates
   - Rollback capability

5. **Git Protection**
   - Per-project repository isolation
   - Safe command execution
   - Remote validation

### Security Modules

- `core/auth_middleware.py` - Authentication
- `core/system_protection.py` - File/directory protection
- `utils/path_utils.py` - Path validation
- `core/system_protection.py` - Operation validation

---

## Memory & Context Pipeline

### Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ACTION EXECUTION                                          │
│  /execute, /run-local, /git/commit, etc.                                    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              ACTION LOGGING (memory_utils.py)                                │
│  update_memory(project, "execute", description, extra)                      │
│  - Adds action to memory.json["actions"]                                     │
│  - Updates stats (executions++, total_actions++)                             │
│  - Keeps last 100 actions (FIFO)                                            │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              RUN LOGGING (logs/run_logger.py)                                │
│  log_run_execution(project, script_path, status, ...)                       │
│  - Creates run_*.json file                                                   │
│  - Updates memory.json (TASK 8.11.1)                                         │
│  - Indexes to SQLite (index_run_log_metadata)                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              CONTEXT GENERATION (context_full.py)                            │
│  generate_full_context(project)                                              │
│  - Reads memory.json["actions"]                                              │
│  - Extracts recent_actions (last 5)                                         │
│  - Generates context_full.json                                               │
│  - Indexes to SQLite (index_context_full)                                    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATA STORAGE                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  memory.json                                                                 │
│    ├── actions[]        → All actions (last 100)                            │
│    ├── stats            → Execution statistics                               │
│    └── semantic_context → Tech stack, keywords, confidence                  │
│                                                                              │
│  context_full.json                                                           │
│    ├── activity.recent_actions[] → Last 5 actions (for ChatGPT)             │
│    ├── stats                    → Execution statistics                      │
│    ├── commits                  → Git commit history                         │
│    └── snapshot                 → Project state                             │
│                                                                              │
│  context.db (SQLite)                                                         │
│    ├── runs table      → Execution metadata (no stdout/stderr)             │
│    ├── commits table   → Commit records                                     │
│    ├── snapshots table → Project snapshots                                  │
│    └── embeddings table → Ready for RAG (Task 9)                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Data Structures

**memory.json**:
```json
{
  "project_name": "MyProject",
  "stats": {
    "commits": 10,
    "executions": 25,
    "analyses": 5,
    "total_actions": 40
  },
  "actions": [
    {
      "timestamp": "2025-12-20T13:00:00Z",
      "type": "execute",
      "description": "Executed: script.py (success)",
      "extra": {
        "status": "success",
        "returncode": 0,
        "runtime": 2.5,
        "script_path": "script.py"
      }
    }
  ],
  "semantic_context": {
    "description": "...",
    "tech_stack": ["Python", "FastAPI"],
    "keywords": [...],
    "activity_summary": {...}
  }
}
```

**context_full.json**:
```json
{
  "version": "1.0",
  "project_name": "MyProject",
  "activity": {
    "recent_actions": [
      {
        "time": "2025-12-20T13:00:00Z",
        "action": "Executed: script.py (success)",
        "status": "success"
      }
    ]
  },
  "stats": {...},
  "commits": {...},
  "snapshot": {...}
}
```

---

## Module Dependencies

### Core Dependencies

```
agent.py
├── api/routes/* (all route modules)
├── core/basic_functional.py
├── core/context_manager.py
├── core/llm_selector.py
├── core/lazydeve_boot.py
├── core/event_bus.py
├── core/auth_middleware.py
└── utils/* (all utility modules)

api/routes/execute.py
├── core/command_parser.py
├── core/basic_functional.py
├── core/llm_selector.py
├── core/logs/run_logger.py
├── core/memory_utils.py
└── core/context_manager.py

core/context_full.py
├── core/memory_utils.py
├── core/context_manager.py
├── core/commit_tracker.py
├── core/readme_utils.py
└── core/context_indexer.py

core/context_indexer.py
├── core/memory_lock.py (safe_read_json)
└── sqlite3 (standard library)

core/memory_utils.py
├── core/memory_lock.py
└── core/file_maintenance.py
```

---

## File Structure

```
LazyDeve/
├── agent.py                    # Main entry point
├── api/
│   ├── routes/                # API route modules
│   │   ├── execute.py
│   │   ├── projects.py
│   │   ├── context.py
│   │   ├── memory.py
│   │   ├── docs.py
│   │   ├── git.py
│   │   ├── files.py
│   │   ├── analysis.py
│   │   ├── run_local.py
│   │   ├── llm.py
│   │   ├── system.py
│   │   ├── protection.py
│   │   └── admin.py
│   ├── schemas.py             # Pydantic models
│   └── dependencies.py        # Route dependencies
├── core/                      # Core business logic
│   ├── basic_functional.py
│   ├── llm_selector.py
│   ├── command_parser.py
│   ├── event_bus.py
│   ├── context_full.py
│   ├── context_indexer.py
│   ├── memory_utils.py
│   ├── memory_processor.py
│   ├── context_manager.py
│   ├── context_initializer.py
│   ├── commit_tracker.py
│   ├── readme_utils.py
│   ├── project_manager.py
│   ├── file_maintenance.py
│   ├── system_protection.py
│   ├── auth_middleware.py
│   ├── config.py
│   ├── ai_context.py
│   ├── documentation_generator.py
│   └── logs/
│       └── run_logger.py
├── utils/                     # Utility functions
│   ├── git_utils.py
│   ├── github_api.py
│   ├── path_utils.py
│   ├── translation.py
│   ├── webhook.py
│   └── startup.py
├── projects/                  # Project storage
│   └── <project_name>/
│       ├── .lazydeve/         # LazyDeve metadata
│       │   ├── memory.json
│       │   ├── context_full.json
│       │   ├── context.db
│       │   ├── commit_history.json
│       │   ├── snapshot.json
│       │   ├── config.json
│       │   └── logs/
│       │       └── run_*.json
│       └── src/               # Project source code
└── logs/                      # Agent logs
    └── agent.log
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `API_BEARER_TOKEN` | Yes | — | Bearer token for authentication |
| `ENABLE_AUTH` | No | `false` | Enable authentication |
| `PORT` | No | `8001` | Server port |
| `PUBLIC_AGENT_URL` | No | `http://localhost:8001` | Public URL for OpenAPI |
| `LLM_MODE` | No | `auto` | `auto` or `manual` |
| `ANTHROPIC_API_KEY` | No | — | Anthropic API key |
| `GEMINI_API_KEY` | No | — | Google Gemini API key |
| `MISTRAL_API_KEY` | No | — | Mistral API key |
| `GITHUB_TOKEN` | No | — | GitHub personal access token |
| `GITHUB_USER` | No | — | GitHub username |
| `allow_github_access` | No | `false` | Enable GitHub operations |

### Project Configuration

Each project has `.lazydeve/config.json`:
```json
{
  "readme_chars": 1400,
  "user_memory": {
    "notes": "Project rules and notes (max 300 chars)",
    "last_updated": "2025-12-20T13:00:00Z"
  }
}
```

---

## API Endpoint Summary

### Core Endpoints

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/execute` | POST | Execute AI task | Required |
| `/run-local` | POST | Execute local script | Required |
| `/projects/list` | GET | List projects | Optional |
| `/projects/active` | GET | Get active project | Optional |
| `/projects/set-active/{name}` | POST | Switch project | Optional |
| `/projects/create/{name}` | POST | Create project | Optional |
| `/git/commit` | POST | Commit changes | Required |
| `/git/push` | POST | Push to remote | Required |
| `/git/status` | GET | Git status | Optional |
| `/read-file` | POST | Read file | Required |
| `/update-file` | POST | Update file | Required |
| `/list-files` | GET | List files | Optional |

### Context Endpoints

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/api/v1/context/full/{project}` | GET | Full unified context | Optional |
| `/api/v1/context/summary/{project}` | GET | Summary context | Optional |
| `/api/v1/context/{project}/user-memory` | POST | Save user notes | Optional |

### Memory Endpoints

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/api/v1/projects/{project}/memory` | GET | Get memory | Optional |
| `/api/v1/projects/{project}/memory/update` | POST | Update memory | Optional |

### System Endpoints

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/ping-agent` | GET | Health check | Optional |
| `/openapi.yaml` | GET | OpenAPI schema | Optional |
| `/protection-status` | GET | Protection status | Optional |

---

## Extension Points

### 1. Event Bus
- Register custom event handlers
- Post-action hooks
- Extensible event system

### 2. Command Parser
- Add new intent patterns
- Custom routing logic
- Intent-specific handlers

### 3. LLM Selector
- Add new providers
- Custom model selection logic
- Provider-specific configurations

### 4. Memory Processor
- Custom semantic analysis
- Activity summarization
- Error pattern detection

### 5. Context Indexer
- Custom SQLite tables
- Additional indexing logic
- Sync strategies

---

## Future Roadmap Integration

### Task 9: RAG Integration
- **Module**: `core/context_indexer.py` (embeddings table ready)
- **Integration**: Embeddings table populated from context sources
- **Usage**: Semantic search, knowledge retrieval

### Task 10: MCP Server
- **Module**: New MCP server module
- **Integration**: GraphQL/REST interface to context.db
- **Usage**: Multi-agent orchestration

### Task 11: Docker Deployment
- **Module**: Docker configuration
- **Integration**: Persistent volumes for projects and context
- **Usage**: Containerized deployment

---

## Conclusion

LazyDeve is a **modular, extensible architecture** designed for:
- **Stateful development** with persistent context
- **AI-powered execution** with deterministic routing
- **Structured memory** with JSON + SQLite hybrid storage
- **Per-project isolation** with independent Git repositories
- **Security by design** with multi-layer protection
- **Extensibility** through event system and modular design

The architecture separates concerns clearly:
- **Routes** handle HTTP requests and validation
- **Core modules** provide business logic
- **Utilities** provide reusable helper functions
- **Data layer** manages persistence and indexing

This design enables:
- Easy testing and maintenance
- Clear extension points
- Scalable architecture
- Production-ready deployment

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-20  
**Maintained By**: LazyDeve Development Team

