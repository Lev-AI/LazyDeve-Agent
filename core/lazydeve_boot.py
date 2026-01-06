import yaml
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any
from core.basic_functional import log_message
from core.config import PORT, PUBLIC_AGENT_URL, REPO_DIR

INIT_FILE = os.path.join(REPO_DIR, "docs", "lazydeve_init.yaml")
STATE_FILE = os.path.join(REPO_DIR, ".initialized")

class LazyDeveInitializer:
    def __init__(self):
        self.initialized = os.path.exists(STATE_FILE)
        self._lock = asyncio.Lock()
        self.config = None
        
    def is_initialized(self) -> bool:
        """Check if agent has been initialized"""
        return self.initialized
    
    def load_config(self) -> Dict[str, Any]:
        """Load initialization configuration from YAML"""
        if self.config:
            return self.config
            
        try:
            with open(INIT_FILE, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            return self.config
        except FileNotFoundError:
            log_message(f"[Init] Configuration file not found: {INIT_FILE}")
            return {}
        except Exception as e:
            log_message(f"[Init] Error loading configuration: {e}")
            return {}
    
    async def run_initialization(self) -> Dict[str, Any]:
        """
        Run the initialization sequence.
        Uses async lock to prevent race conditions.
        """
        async with self._lock:
            # Double-check after acquiring lock
            if self.initialized:
                log_message("[Init] Already initialized, skipping")
                return {"status": "already_initialized"}
            
            log_message("\n" + "="*50)
            log_message("🧠 LazyDeve Initialization Protocol Started")
            log_message("="*50)
            
            config = self.load_config()
            if not config:
                log_message("[Init] No configuration loaded, skipping initialization")
                return {"status": "error", "message": "No configuration"}
            
            # Display identity
            identity = config.get("identity", {})
            log_message(f"[Init] Agent: {identity.get('name', 'Unknown')}")
            log_message(f"[Init] Version: {identity.get('version', 'Unknown')}")
            log_message(f"[Init] Role: {identity.get('role', 'Unknown')}")
            log_message(f"[Init] Port: {PORT}")
            log_message(f"[Init] URL: {PUBLIC_AGENT_URL}")
            
            # Execute boot sequence
            results = {}
            boot_sequence = config.get("boot_sequence", [])
            
            for endpoint in boot_sequence:
                try:
                    result = await self._check_endpoint(endpoint)
                    results[endpoint] = result
                    status_emoji = "✅" if result.get("success") else "❌"
                    log_message(f"[Init] {status_emoji} {endpoint}: {result.get('status', 'unknown')}")
                except Exception as e:
                    results[endpoint] = {"success": False, "error": str(e)}
                    log_message(f"[Init] ❌ {endpoint} failed: {e}")
            
            # Save initialization state
            try:
                init_data = {
                    "initialized": True,
                    "timestamp": datetime.now().isoformat(),
                    "port": PORT,
                    "url": PUBLIC_AGENT_URL,
                    "boot_results": results
                }
                
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(init_data, f, indent=2)
                
                self.initialized = True
                log_message("\n✅ Initialization Complete. Agent is Ready.\n")
                log_message("="*50 + "\n")
                
                return {
                    "status": "success",
                    "message": "Initialization complete",
                    "results": results,
                    "timestamp": init_data["timestamp"]
                }
                
            except Exception as e:
                log_message(f"[Init] Error saving state: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to save state: {e}",
                    "results": results
                }
    
    async def _check_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """
        Check endpoint status using internal HTTP call.
        Falls back gracefully on errors.
        """
        import aiohttp
        
        url = f"http://127.0.0.1:{PORT}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "success": True,
                            "status": "ok",
                            "status_code": resp.status,
                            "data": data
                        }
                    else:
                        return {
                            "success": False,
                            "status": "error",
                            "status_code": resp.status
                        }
        except asyncio.TimeoutError:
            return {"success": False, "status": "timeout", "error": "Request timed out"}
        except aiohttp.ClientError as e:
            return {"success": False, "status": "error", "error": f"Client error: {e}"}
        except Exception as e:
            return {"success": False, "status": "error", "error": str(e)}
    
    def reset(self):
        """Reset initialization state (for testing/debugging)"""
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            self.initialized = False
            log_message("[Init] Initialization state reset")
            return {"status": "success", "message": "State reset"}
        return {"status": "info", "message": "Already reset"}

# Singleton instance
initializer = LazyDeveInitializer()


