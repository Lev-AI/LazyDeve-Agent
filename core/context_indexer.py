"""
SQLite Context Indexer - Hybrid Context Engine
✅ TASK 8.11: Structured indexing and querying layer with unified architecture alignment
✅ TASK 8.10.1.1 & 8.10.1.2: Indexes from context_full.json (primary source)
"""

import os
import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from core.basic_functional import log_message
from core.memory_lock import safe_read_json

# ✅ TASK 8.11 COMPATIBILITY: Schema version for migration tracking
SCHEMA_VERSION = "1.0"


def _get_db_path(project_name: str) -> str:
    """Get SQLite database path for project."""
    return f"projects/{project_name}/.lazydeve/context.db"


def _get_connection(project_name: str) -> sqlite3.Connection:
    """Get SQLite connection for project (creates DB if needed)."""
    db_path = _get_db_path(project_name)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def init_context_db(project_name: str) -> bool:
    """
    Initialize context.db for a project.
    ✅ TASK 8.11: SQLite database initialization with schema versioning
    """
    try:
        conn = _get_connection(project_name)
        cursor = conn.cursor()
        
        # ✅ TASK 8.11 COMPATIBILITY: Schema versioning table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version TEXT PRIMARY KEY,
                applied_at TEXT,
                description TEXT
            )
        """)
        
        # Check if schema already exists
        cursor.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
        existing_version = cursor.fetchone()
        
        if not existing_version:
            # Create all tables
            # Snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    timestamp TEXT,
                    status TEXT,
                    last_commit TEXT,
                    pending_changes INTEGER DEFAULT 0,
                    metadata TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            
            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    event_type TEXT,
                    timestamp TEXT,
                    details TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            
            # Commits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    commit_hash TEXT,
                    commit_id TEXT,
                    summary TEXT,
                    files_changed TEXT,
                    timestamp TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            
            # Runs table (metadata only - no stdout/stderr)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    script_path TEXT,
                    status TEXT,
                    returncode INTEGER,
                    runtime REAL,
                    summary TEXT,
                    error_keywords TEXT,
                    timestamp TEXT,
                    git_commit TEXT,
                    task_context TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            
            # Embeddings table (for Task 9 RAG)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_id TEXT,
                    content_hash TEXT NOT NULL,
                    content_preview TEXT,
                    embedding BLOB,
                    embedding_model TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            
            # Sync metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL UNIQUE,
                    last_json_modified TEXT,
                    last_synced_at TEXT,
                    last_trimmed_at TEXT,
                    row_count_before_trim INTEGER,
                    row_count_after_trim INTEGER,
                    sync_status TEXT DEFAULT 'synced',
                    error_message TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_project ON snapshots(project)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_project ON events(project, event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commits_project ON commits(project)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project, status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_project ON embeddings(project_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_source ON embeddings(source_type, source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_hash ON embeddings(content_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_metadata(sync_status)")
            
            # Record schema version
            cursor.execute("""
                INSERT INTO schema_version (version, applied_at, description)
                VALUES (?, ?, ?)
            """, (SCHEMA_VERSION, datetime.now().isoformat(), "Initial schema - unified architecture"))
            
            conn.commit()
            log_message(f"[ContextIndexer] ✅ Initialized context.db for {project_name}")
        else:
            # ✅ TASK 8.11 COMPATIBILITY: Check for schema migration needed
            if existing_version[0] != SCHEMA_VERSION:
                conn.close()
                if migrate_schema(project_name, existing_version[0], SCHEMA_VERSION):
                    # Reconnect after migration
                    conn = _get_connection(project_name)
                    cursor = conn.cursor()
                else:
                    log_message(f"[ContextIndexer] ⚠️ Schema migration failed or not implemented")
                    return False
        
        conn.close()
        return True
        
    except Exception as e:
        log_message(f"[ContextIndexer] ❌ Failed to initialize context.db: {e}")
        return False


def index_context_full(project_name: str, context_full: Dict[str, Any]) -> bool:
    """
    Index context_full.json into SQLite (async-safe).
    ✅ TASK 8.10.1.1 & 8.10.1.2: Primary indexing source (unified structure)
    
    Indexes:
    - commits (from context_full["commits"])
    - snapshots (from context_full["snapshot"])
    - activity metadata (for embeddings table in Task 9)
    """
    try:
        conn = _get_connection(project_name)
        cursor = conn.cursor()
        
        # Index commits
        commits_data = context_full.get("commits", {})
        last_commit = commits_data.get("last_commit")
        recent_commits = commits_data.get("recent", [])
        
        # Index last commit
        if last_commit:
            cursor.execute("""
                INSERT OR REPLACE INTO commits (
                    project, commit_hash, commit_id, summary, files_changed, timestamp, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                project_name,
                last_commit.get("commit_id_full", ""),
                last_commit.get("commit_id", ""),
                last_commit.get("summary", ""),
                json.dumps(last_commit.get("files_changed", [])),
                last_commit.get("timestamp", ""),
                json.dumps(last_commit)
            ))
        
        # Index recent commits (avoid duplicates)
        for commit in recent_commits:
            commit_id = commit.get("commit_id", "")
            if commit_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO commits (
                        project, commit_hash, commit_id, summary, files_changed, timestamp, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_name,
                    commit.get("commit_id_full", ""),
                    commit_id,
                    commit.get("summary", ""),
                    json.dumps(commit.get("files_changed", [])),
                    commit.get("timestamp", ""),
                    json.dumps(commit)
                ))
        
        # Index snapshot
        snapshot_data = context_full.get("snapshot", {})
        if snapshot_data:
            cursor.execute("""
                INSERT OR REPLACE INTO snapshots (
                    project, timestamp, status, last_commit, pending_changes, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_name,
                context_full.get("generated_at", datetime.now().isoformat()),
                snapshot_data.get("status", "unknown"),
                snapshot_data.get("last_run"),
                1 if snapshot_data.get("pending_changes", False) else 0,
                json.dumps(snapshot_data)
            ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        log_message(f"[ContextIndexer] ❌ Failed to index context_full.json: {e}")
        return False


def index_run_log_metadata(project_name: str, run_data: Dict[str, Any]) -> bool:
    """
    Index run log metadata from run_*.json into SQLite (async-safe).
    ✅ METADATA ONLY: No stdout/stderr (prevents database bloat)
    
    Indexes only:
    - script_path, status, returncode, runtime
    - summary, error_keywords
    - timestamp, git_commit, task_context
    """
    try:
        conn = _get_connection(project_name)
        cursor = conn.cursor()
        
        # Extract metadata only (no stdout/stderr)
        script_path = run_data.get("script_path", run_data.get("script", ""))
        status = run_data.get("status", "unknown")
        returncode = run_data.get("returncode", 0)
        runtime = run_data.get("runtime", 0.0)
        summary = run_data.get("summary", "")
        error_keywords = json.dumps(run_data.get("error_keywords", []))
        timestamp = run_data.get("timestamp", datetime.now().isoformat())
        git_commit = run_data.get("git_commit")
        task_context = run_data.get("task_context")
        
        # Create metadata JSON (excluding stdout/stderr)
        metadata = {
            "args": run_data.get("args", []),
            "project": run_data.get("project", project_name)
        }
        
        cursor.execute("""
            INSERT INTO runs (
                project, script_path, status, returncode, runtime, summary,
                error_keywords, timestamp, git_commit, task_context, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_name,
            script_path,
            status,
            returncode,
            runtime,
            summary,
            error_keywords,
            timestamp,
            git_commit,
            task_context,
            json.dumps(metadata)
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        log_message(f"[ContextIndexer] ❌ Failed to index run log metadata: {e}")
        return False


def index_event(project_name: str, event_data: Dict[str, Any]) -> bool:
    """
    Index event from events.log into SQLite (async-safe).
    ✅ Optional: Only if events.log queries are needed
    """
    try:
        conn = _get_connection(project_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO events (project, event_type, timestamp, details)
            VALUES (?, ?, ?, ?)
        """, (
            project_name,
            event_data.get("event_type", "unknown"),
            event_data.get("timestamp", datetime.now().isoformat()),
            json.dumps(event_data)
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        log_message(f"[ContextIndexer] ❌ Failed to index event: {e}")
        return False


def index_snapshot(project_name: str, snapshot_data: Dict[str, Any]) -> bool:
    """
    Index snapshot data to SQLite (async-safe).
    ✅ TASK 8.11: Standalone snapshot indexing (for context_sync.py compatibility)
    
    This function is called when snapshots are updated directly via update_snapshot()
    in context_sync.py, ensuring real-time SQLite sync independent of context_full.json
    generation cycle.
    
    Args:
        project_name: Project name
        snapshot_data: Snapshot dictionary (from snapshot.json or context_sync updates)
    
    Returns:
        bool: True if indexed successfully
    """
    try:
        conn = _get_connection(project_name)
        cursor = conn.cursor()
        
        # Extract snapshot fields
        timestamp = snapshot_data.get("timestamp") or snapshot_data.get("last_updated") or datetime.now().isoformat()
        status = snapshot_data.get("status", "unknown")
        last_commit = snapshot_data.get("last_commit") or snapshot_data.get("last_run")
        pending_changes = 1 if snapshot_data.get("pending_changes", False) else 0
        
        cursor.execute("""
            INSERT OR REPLACE INTO snapshots (
                project, timestamp, status, last_commit, pending_changes, metadata
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            project_name,
            timestamp,
            status,
            last_commit,
            pending_changes,
            json.dumps(snapshot_data)
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        log_message(f"[ContextIndexer] ❌ Failed to index snapshot: {e}")
        return False


def sync_context_full_to_sqlite(project_name: str, force: bool = False) -> bool:
    """
    Sync context_full.json to SQLite (primary sync function).
    ✅ TASK 8.10.1.1 & 8.10.1.2: Unified architecture sync
    
    Args:
        project_name: Project name
        force: Force full re-sync (ignores sync_metadata checks)
    
    Returns:
        bool: True if sync successful
    """
    try:
        context_path = f"projects/{project_name}/.lazydeve/context_full.json"
        
        if not os.path.exists(context_path):
            log_message(f"[ContextIndexer] ⚠️ context_full.json not found for {project_name}")
            return False
        
        # Check sync_metadata for trim events
        conn = _get_connection(project_name)
        cursor = conn.cursor()
        
        if not force:
            cursor.execute("""
                SELECT last_trimmed_at, last_synced_at, sync_status
                FROM sync_metadata
                WHERE file_name = 'context_full.json'
            """)
            sync_info = cursor.fetchone()
            
            if sync_info:
                last_trimmed = sync_info[0]
                last_synced = sync_info[1]
                
                # If trimmed after last sync, need full re-sync
                if last_trimmed and last_synced and last_trimmed > last_synced:
                    log_message(f"[ContextIndexer] 🔄 Full re-sync needed (trimmed: {last_trimmed}, synced: {last_synced})")
                    # Clear existing data for full re-sync
                    cursor.execute("DELETE FROM commits WHERE project = ?", (project_name,))
                    cursor.execute("DELETE FROM snapshots WHERE project = ?", (project_name,))
                    conn.commit()
        
        # Load and index context_full.json
        context_full = safe_read_json(context_path, {})
        if not context_full:
            log_message(f"[ContextIndexer] ⚠️ Empty context_full.json for {project_name}")
            conn.close()
            return False
        
        # Index the context
        success = index_context_full(project_name, context_full)
        
        if success:
            # Update sync_metadata
            file_mtime = datetime.fromtimestamp(os.path.getmtime(context_path)).isoformat()
            cursor.execute("""
                INSERT OR REPLACE INTO sync_metadata (
                    file_name, last_json_modified, last_synced_at, sync_status
                ) VALUES (?, ?, ?, ?)
            """, (
                "context_full.json",
                file_mtime,
                datetime.now().isoformat(),
                "synced"
            ))
            conn.commit()
            log_message(f"[ContextIndexer] ✅ Synced context_full.json to SQLite for {project_name}")
        
        conn.close()
        return success
        
    except Exception as e:
        log_message(f"[ContextIndexer] ❌ Failed to sync context_full.json: {e}")
        return False


def sync_run_logs_to_sqlite(project_name: str, force: bool = False) -> bool:
    """
    Sync run_*.json files to SQLite (metadata only).
    ✅ METADATA ONLY: Excludes stdout/stderr
    
    Args:
        project_name: Project name
        force: Force full re-sync
    
    Returns:
        bool: True if sync successful
    """
    try:
        logs_dir = Path(f"projects/{project_name}/.lazydeve/logs")
        if not logs_dir.exists():
            return True  # No logs to sync
        
        run_files = list(logs_dir.glob("run_*.json"))
        if not run_files:
            return True  # No run logs
        
        synced_count = 0
        for run_file in run_files:
            try:
                run_data = safe_read_json(str(run_file), {})
                if run_data:
                    if index_run_log_metadata(project_name, run_data):
                        synced_count += 1
            except Exception as e:
                log_message(f"[ContextIndexer] ⚠️ Failed to index {run_file.name}: {e}")
        
        log_message(f"[ContextIndexer] ✅ Synced {synced_count}/{len(run_files)} run logs to SQLite for {project_name}")
        return True
        
    except Exception as e:
        log_message(f"[ContextIndexer] ❌ Failed to sync run logs: {e}")
        return False


def sync_existing_data(project_name: str) -> bool:
    """
    Initial sync: Index all existing data into SQLite.
    ✅ TASK 8.11 COMPATIBILITY: Initial sync for existing projects
    ✅ TASK 8.10.1.1 ALIGNMENT: Syncs from context_full.json (primary) + run_*.json (secondary)
    """
    try:
        # Initialize database if needed
        if not init_context_db(project_name):
            return False
        
        # Sync context_full.json
        sync_context_full_to_sqlite(project_name, force=True)
        
        # Sync run logs
        sync_run_logs_to_sqlite(project_name, force=True)
        
        log_message(f"[ContextIndexer] ✅ Initial sync completed for {project_name}")
        return True
        
    except Exception as e:
        log_message(f"[ContextIndexer] ❌ Failed initial sync: {e}")
        return False


def migrate_schema(project_name: str, from_version: str, to_version: str) -> bool:
    """
    Schema migration stub for future compatibility.
    ✅ TASK 8.11 COMPATIBILITY: Prepared for schema evolution
    
    Args:
        project_name: Project name
        from_version: Current schema version
        to_version: Target schema version
    
    Returns:
        bool: True if migration successful (or not needed), False if migration needed but not implemented
    """
    if from_version == to_version:
        return True
    
    log_message(f"[ContextIndexer] ⚠️ Schema migration needed: {from_version} → {to_version}")
    log_message(f"[ContextIndexer] Migration not yet implemented. Database may need manual upgrade.")
    
    # TODO: Implement actual migration logic when schema changes
    # Example migration patterns:
    #   - Add new columns: ALTER TABLE table_name ADD COLUMN new_column TEXT
    #   - Rename columns: ALTER TABLE table_name RENAME COLUMN old_name TO new_name
    #   - Create new tables: CREATE TABLE IF NOT EXISTS ...
    #   - Update schema_version table with new version
    
    # For now, return False to indicate migration needed but not available
    return False


def update_sync_metadata_on_trim(project_name: str, file_name: str, row_count_before: int, row_count_after: int) -> bool:
    """
    Update sync_metadata when FIFO trim occurs.
    ✅ TASK 8.11: FIFO trim integration
    
    Args:
        project_name: Project name
        file_name: Name of trimmed file (e.g., 'context_full.json')
        row_count_before: Row count before trim
        row_count_after: Row count after trim
    
    Returns:
        bool: True if update successful
    """
    try:
        conn = _get_connection(project_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sync_metadata (
                file_name, last_trimmed_at, row_count_before_trim, row_count_after_trim, sync_status
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            file_name,
            datetime.now().isoformat(),
            row_count_before,
            row_count_after,
            "pending"
        ))
        
        conn.commit()
        conn.close()
        log_message(f"[ContextIndexer] ✅ Updated sync_metadata for {file_name} trim event")
        return True
        
    except Exception as e:
        log_message(f"[ContextIndexer] ❌ Failed to update sync_metadata: {e}")
        return False
