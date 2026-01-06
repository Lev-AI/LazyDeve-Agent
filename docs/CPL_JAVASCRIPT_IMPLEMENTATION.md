# JavaScript CPL Implementation - Placeholder

## ⚠️ Status: **BLOCKED - Waiting for RagCore Project (Tasks 9-10)**

This document serves as a placeholder for the JavaScript implementation of the Command Precision Layer (CPL), which will be needed for MCP server integration in Task 10.

## 📋 Prerequisites

Before implementing JavaScript CPL, the following must be completed:

- [ ] **Task 9**: RagCore Integration - Creates `RagCore_and_mcp_serever/` project
- [ ] **Task 10**: MCP Server Setup - Creates `RagCore_and_mcp_serever/mcp-server/` directory

## 📝 Implementation Location

**File**: `RagCore_and_mcp_serever/mcp-server/cpl-integration.js`

This file will be created during Task 10 implementation.

## 🎯 Purpose

The JavaScript CPL must **match the Python implementation** in `core/command_parser.py` to ensure:
- Deterministic routing across both Python (LazyDeve) and JavaScript (MCP Server)
- Identical intent detection results for the same inputs
- Consistent parameter extraction logic

## 🔧 Implementation Code (Ready for Task 10)

When RagCore project exists, create the file with this content:

```javascript
/**
 * Command Precision Layer - JavaScript Implementation for MCP Server
 * Matches Python implementation in core/command_parser.py
 * 
 * ⚠️ CRITICAL: This MUST produce identical results to Python CPL
 */

export function parseCommand(task) {
  const taskLower = task.toLowerCase();
  const timestamp = new Date().toISOString();
  
  // ============================================================
  // INTENT 1: Archive Project
  // ============================================================
  const archiveMatch = taskLower.match(/archive\s+(?:the\s+)?project\s+["\']?(\w+)["\']?/);
  if (archiveMatch) {
    return {
      intent: 'archive_project',
      params: { project_name: archiveMatch[1] },
      confidence: 0.95,
      original_task: task,
      timestamp: timestamp
    };
  }
  
  // ============================================================
  // INTENT 2: Create Project
  // ============================================================
  const createMatch = taskLower.match(/create\s+(?:a\s+)?(?:new\s+)?project\s+["\']?(\w+)["\']?/);
  if (createMatch) {
    return {
      intent: 'create_project',
      params: { project_name: createMatch[1] },
      confidence: 0.95,
      original_task: task,
      timestamp: timestamp
    };
  }
  
  // ============================================================
  // INTENT 3: Commit Changes
  // ============================================================
  const commitPhrases = ['commit changes', 'commit the changes', 'git commit', 'push changes', 'push to git'];
  const commitDetected = commitPhrases.some(phrase => taskLower.includes(phrase));
  
  if (commitDetected) {
    const codeActions = ['add', 'create', 'implement', 'fix', 'refactor', 'delete', 'remove', 'update', 'modify'];
    const hasCodeAction = codeActions.some(action => taskLower.includes(action));
    
    if (!hasCodeAction) {
      return {
        intent: 'commit_changes',
        params: {},
        confidence: 0.90,
        original_task: task,
        timestamp: timestamp
      };
    }
  }
  
  // ============================================================
  // INTENT 4: Delete File
  // ============================================================
  const deleteMatch = taskLower.match(/delete\s+(?:file\s+)?["\']?([^"']+\.\w+)["\']?/);
  if (deleteMatch && !taskLower.includes('project')) {
    return {
      intent: 'delete_file',
      params: { file_path: deleteMatch[1] },
      confidence: 0.90,
      original_task: task,
      timestamp: timestamp
    };
  }
  
  // ============================================================
  // INTENT 5: Read File
  // ============================================================
  const readMatch = taskLower.match(/read\s+(?:file\s+)?["\']?([^"']+\.\w+)["\']?/);
  if (readMatch) {
    return {
      intent: 'read_file',
      params: { file_path: readMatch[1] },
      confidence: 0.90,
      original_task: task,
      timestamp: timestamp
    };
  }
  
  // ============================================================
  // DEFAULT: Execute via Aider (fallback)
  // ============================================================
  return {
    intent: 'execute_aider',
    params: { task },
    confidence: 0.50,
    original_task: task,
    timestamp: timestamp
  };
}

/**
 * Log parsed command for debugging
 */
export function logParsedCommand(result) {
  const timestamp = new Date().toISOString();
  console.error(`[CPL] ${timestamp} - Intent: ${result.intent}, Confidence: ${result.confidence}`);
  return result;
}

/**
 * Get routing information for a given intent
 */
export function getIntentAction(intent) {
  const intentRouting = {
    archive_project: {
      endpoint: '/projects/archive/{project_name}',
      method: 'POST',
      handler: 'archive_project'
    },
    create_project: {
      endpoint: '/projects/create/{project_name}',
      method: 'POST',
      handler: 'create_project'
    },
    commit_changes: {
      endpoint: '/commit',
      method: 'POST',
      handler: 'commit_changes'
    },
    delete_file: {
      endpoint: '/update-file',
      method: 'POST',
      handler: 'remove_via_git'
    },
    read_file: {
      endpoint: '/read-file',
      method: 'POST',
      handler: 'read_file'
    },
    execute_aider: {
      endpoint: '/execute',
      method: 'POST',
      handler: 'run_aider_task_async'
    }
  };
  
  return intentRouting[intent] || intentRouting.execute_aider;
}
```

## ✅ Testing Requirements

When implementing, ensure:
- [ ] Python CPL and JavaScript CPL produce **identical results** for same inputs
- [ ] Test cases:
  - `"archive project test_project"` → `intent: archive_project, params: {project_name: "test_project"}`
  - `"create project new_app"` → `intent: create_project, params: {project_name: "new_app"}`
  - `"delete file test.py"` → `intent: delete_file, params: {file_path: "test.py"}`
  - `"read file main.py"` → `intent: read_file, params: {file_path: "main.py"}`
  - `"commit changes"` → `intent: commit_changes`
  - `"refactor code in main.py"` → `intent: execute_aider` (fallback)
- [ ] Logging works correctly in MCP server context
- [ ] Error handling matches Python implementation

## 📚 Related Files

- **Python CPL**: `core/command_parser.py` (✅ Completed in Task 8)
- **Execute Endpoint**: `api/routes/execute.py` (✅ Updated in Task 8)
- **JavaScript CPL**: `RagCore_and_mcp_serever/mcp-server/cpl-integration.js` (⏸️ Waiting for Task 10)

## 🔄 Integration with MCP Server

When Task 10 is implemented, the JavaScript CPL will be used in `enhanced-mcp-server.js`:

```javascript
import { parseCommand, logParsedCommand } from './cpl-integration.js';

// In MCP tool handler
const cplResult = parseCommand(task);
logParsedCommand(cplResult);

// Route based on intent
if (cplResult.intent === 'archive_project') {
  // Call LazyDeve's /projects/archive/{name} endpoint
  const response = await axios.post(
    `${LAZYDEVE_URL}/projects/archive/${cplResult.params.project_name}`,
    {},
    { headers: authHeaders }
  );
  return response.data;
}

// ... other intents ...
```

## 📝 Notes

- Task 8 (Python CPL) is **COMPLETE** ✅
- JavaScript CPL implementation is **DEFERRED** to Task 10 ⏸️
- Python CPL is fully functional and being used by `/execute` endpoint
- MCP Server will use JavaScript CPL for deterministic routing once implemented

---

**Status**: ⏸️ Placeholder - Implementation deferred to Task 10  
**Last Updated**: Task 8 Completion (11/14/2025)

