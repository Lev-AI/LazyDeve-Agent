"""
Webhook Utilities - Network operations with retry logic
Extracted from agent.py for better modularity.
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from core.basic_functional import log_message


def log_network_error(error_type: str, url: str, error_details: str, retry_count: int = 0):
    """
    Log network errors to both console and dedicated log file.
    Provides structured error information for debugging.
    """
    timestamp = datetime.now().isoformat()
    error_entry = {
        "timestamp": timestamp,
        "error_type": error_type,
        "url": url,
        "error_details": error_details,
        "retry_count": retry_count
    }
    
    # Log to console
    log_message(f"[Network Error] {error_type} - {url} - {error_details} (retry: {retry_count})")
    
    # Log to dedicated network errors file
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/network_errors.log", "a", encoding="utf-8") as f:
            f.write(f"{json.dumps(error_entry)}\n")
    except Exception as log_error:
        print(f"⚠️ Failed to write network error log: {log_error}")


async def handle_response(response: aiohttp.ClientResponse, url: str, method: str) -> dict:
    """
    Handle aiohttp response with proper error checking and data extraction.
    """
    try:
        # Check response status
        if response.status >= 400:
            error_msg = f"HTTP {response.status} - {response.reason}"
            log_network_error("HTTPError", url, error_msg)
            return {"status": "error", "data": None, "error": error_msg}
        
        # Extract response data
        try:
            response_data = await response.json()
        except aiohttp.ContentTypeError:
            # If not JSON, get text
            response_data = await response.text()
        
        log_message(f"[Network] {method} {url} → {response.status} OK")
        return {"status": "success", "data": response_data, "error": None}
        
    except Exception as e:
        error_msg = f"Response handling error - {str(e)}"
        log_network_error("ResponseError", url, error_msg)
        return {"status": "error", "data": None, "error": error_msg}


async def fetch_with_retry(url: str, method: str = "GET", payload: dict = None, 
                          max_retries: int = 3, timeout: int = 10) -> dict:
    """
    Robust aiohttp request with retry logic and comprehensive error handling.
    
    Args:
        url: Target URL
        method: HTTP method (GET, POST, etc.)
        payload: JSON payload for POST requests
        max_retries: Maximum retry attempts
        timeout: Request timeout in seconds
    
    Returns:
        dict: {"status": "success/error", "data": response_data, "error": error_message}
    """
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            async with aiohttp.ClientSession() as session:
                # Prepare request parameters
                request_params = {
                    "timeout": aiohttp.ClientTimeout(total=timeout),
                    "headers": {"Content-Type": "application/json"} if payload else {}
                }
                
                # Make request based on method
                if method.upper() == "POST" and payload:
                    async with session.post(url, json=payload, **request_params) as response:
                        return await handle_response(response, url, method)
                else:
                    async with session.get(url, **request_params) as response:
                        return await handle_response(response, url, method)
                        
        except aiohttp.ClientResponseError as e:
            error_msg = f"HTTP {e.status} - {e.message}"
            log_network_error("ClientResponseError", url, error_msg, retry_count)
            
            if retry_count < max_retries:
                retry_count += 1
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                continue
            else:
                return {"status": "error", "data": None, "error": error_msg}
                
        except asyncio.TimeoutError:
            error_msg = f"Request timeout after {timeout}s"
            log_network_error("TimeoutError", url, error_msg, retry_count)
            
            if retry_count < max_retries:
                retry_count += 1
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                continue
            else:
                return {"status": "error", "data": None, "error": error_msg}
                
        except aiohttp.ClientConnectorError as e:
            error_msg = f"Connection failed - {str(e)}"
            log_network_error("ClientConnectorError", url, error_msg, retry_count)
            
            if retry_count < max_retries:
                retry_count += 1
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                continue
            else:
                return {"status": "error", "data": None, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Unexpected error - {str(e)}"
            log_network_error("UnexpectedError", url, error_msg, retry_count)
            
            if retry_count < max_retries:
                retry_count += 1
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                continue
            else:
                return {"status": "error", "data": None, "error": error_msg}
    
    return {"status": "error", "data": None, "error": "Max retries exceeded"}


async def safe_webhook_notify(webhook_url: str, payload: dict, timeout: int = 10) -> bool:
    """
    Safe webhook notification with extended error handling.
    Replaces the basic aiohttp usage in run_aider_task_async.
    
    Returns:
        bool: True if notification succeeded, False otherwise
    """
    if not webhook_url:
        log_message("[Webhook] No webhook URL provided - skipping notification")
        return False
    
    result = await fetch_with_retry(
        url=webhook_url,
        method="POST",
        payload=payload,
        max_retries=2,  # Fewer retries for webhooks to avoid spam
        timeout=timeout
    )
    
    if result["status"] == "success":
        log_message(f"[Webhook] ✅ Notification sent successfully to {webhook_url}")
        return True
    else:
        log_message(f"[Webhook] ❌ Notification failed: {result['error']}")
        return False

