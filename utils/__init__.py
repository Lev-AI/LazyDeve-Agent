"""
Utility modules for LazyDeve agent.
Extracted from agent.py for better code organization and maintainability.
"""

from utils.git_utils import (
    safe_git_command,
    safe_git_add,
    safe_git_commit,
    safe_git_push,
    safe_git_pull,
    safe_git_status,
    safe_git_rm,
    remove_via_git,
    remove_via_git_multi
)

from utils.translation import (
    configure_utf8,
    gpt_translate_to_english,
    translate_prompt
)

from utils.webhook import (
    log_network_error,
    fetch_with_retry,
    safe_webhook_notify,
    handle_response
)

from utils.path_utils import (
    extract_path_from_text,
    extract_paths_from_text,
    load_restricted_directories,
    is_restricted_path,
    is_safe_path
)

__all__ = [
    # Git operations
    "safe_git_command",
    "safe_git_add",
    "safe_git_commit",
    "safe_git_push",
    "safe_git_pull",
    "safe_git_status",
    "safe_git_rm",
    "remove_via_git",
    "remove_via_git_multi",
    # Translation
    "configure_utf8",
    "gpt_translate_to_english",
    "translate_prompt",
    # Webhook
    "log_network_error",
    "fetch_with_retry",
    "safe_webhook_notify",
    "handle_response",
    # Path utilities
    "extract_path_from_text",
    "extract_paths_from_text",
    "load_restricted_directories",
    "is_restricted_path",
    "is_safe_path",
]

