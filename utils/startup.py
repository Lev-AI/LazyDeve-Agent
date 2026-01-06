"""
Startup Utilities - Agent initialization and intro functions
Extracted from agent.py for Task 7 Phase 3
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from core.basic_functional import log_message
from utils.git_utils import safe_git_pull


def load_agent_rules():
    """
    Load operational rules from rules.json.
    
    Returns:
        dict: Agent rules configuration
    """
    try:
        with open("rules.json", "r", encoding="utf-8") as f:
            return json.load(f).get("agent_rules", {})
    except Exception as e:
        log_message(f"[Agent Rules] Failed to load: {e}")
        return {}


def sync_agent_memory():
    """
    Perform lightweight Git and project memory sync.
    Ensures agent code and internal projects are up to date.
    """
    try:
        pull_result = safe_git_pull()
        if pull_result["status"] == "success":
            log_message("[Memory Sync] Git repository refreshed.")
        else:
            log_message(f"[Memory Sync] Git pull warning: {pull_result['error']}")
        
        if os.path.isdir("projects"):
            log_message("[Memory Sync] Local project directory verified.")
    except Exception as e:
        log_message(f"[Memory Sync] Error: {e}")


def agent_intro():
    """
    Display intro message, sync memory, and list active rules.
    Shows available endpoints and initializes agent state.
    """
    load_dotenv()
    intro = os.getenv("AGENT_INTRO", "")
    version = os.getenv("AGENT_VERSION", "unknown")
    rules = load_agent_rules()

    print("\n" + "=" * 70)
    print(f"🤖 LazyDeve Agent – Initialization Report (v{version})")
    print("=" * 70)

    if intro:
        print(f"{intro}\n")

    if rules:
        print("📘 Active Capabilities:")
        for key, val in rules.items():
            status = "✅ Enabled" if val else "❌ Disabled"
            print(f"   - {key}: {status}")
    else:
        print("⚠️ No rules.json found or rules are empty.")

    print("\n🔧 Available Endpoints:")
    endpoints = [
        ("/ping-agent", "check agent status"),
        ("/execute", "run AI-assisted tasks"),
        ("/status", "get Git repository status"),
        ("/commits", "retrieve recent Git commit history"),
        ("/list-files", "get recursive project file listing"),
        ("/set-llm", "switch LLM provider"),
        ("/llm-info", "get current LLM provider information"),
        ("/sync", "pull updates from GitHub"),
        ("/logs", "view recent activity"),
        ("/read-file", "read file contents"),
        ("/update-file", "update file contents"),
        ("/commit", "commit changes"),
        ("/format-commit", "format commit messages"),
        ("/rename-project", "rename project"),
        ("/ping-memory", "check memory sync status"),
        ("/analyze-code", "perform AI-assisted or static code analysis"),
        ("/run-tests", "execute unit/integration tests"),
        ("/openapi.yaml", "get API schema for ChatGPT Apps"),
        ("/protection-status", "get system protection status"),
        ("/check-protection", "check file operation protection"),
        ("/projects/list", "list all projects"),
        ("/projects/create/{name}", "create new project"),
        ("/projects/active", "get active project"),
        ("/projects/set-active/{name}", "set active project"),
        ("/projects/info/{name}", "get project information"),
        ("/projects/commit", "commit project changes"),
        ("/projects/archive/{name}", "archive project (soft delete)"),
        ("/admin/reset-init", "reset initialization state (admin)"),
    ]
    
    for endpoint, description in endpoints:
        print(f"  • {endpoint:30s} → {description}")
    print()

    sync_agent_memory()  # 🔁 Memory sync before startup confirmation
    print(f"[{datetime.now().isoformat()}] ✅ Agent memory synced and ready.\n")
    print("=" * 70 + "\n")

    log_message(f"[Agent Intro] Startup completed (v{version}), memory synced and ready.")


def update_agent_state(status="ready"):
    """
    Update local state file after startup or update.
    
    Args:
        status: Agent status (default: "ready")
    
    Returns:
        dict: Agent state information
    """
    state = {
        "timestamp": datetime.now().isoformat(),
        "agent_version": os.getenv("AGENT_VERSION", "unknown"),
        "status": status
    }
    os.makedirs("logs", exist_ok=True)
    with open("logs/agent_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    log_message(f"[Agent State] Updated: {status}")
    return state


def notify_agent_ready():
    """
    Send webhook/system notification after update or startup.
    Only sends if WEBHOOK_URL is configured in environment.
    """
    import requests
    
    load_dotenv()
    webhook_url = os.getenv("WEBHOOK_URL")
    version = os.getenv("AGENT_VERSION", "unknown")

    if not webhook_url:
        log_message("[Agent Notifier] No WEBHOOK_URL defined — skipping notification.")
        return

    payload = {
        "event": "agent_ready",
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "status": "online"
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.ok:
            log_message(f"[Agent Notifier] ✅ LazyDeve {version} initialized and ready.")
        else:
            log_message(f"[Agent Notifier] ⚠️ Webhook returned {response.status_code}")
    except Exception as e:
        log_message(f"[Agent Notifier] ❌ Failed to send webhook: {e}")

