"""
LLM Routes - LLM provider management and configuration
Extracted from agent.py for Task 7 Phase 2
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from datetime import datetime
from core.llm_selector import set_llm, get_provider_info
from core.basic_functional import log_message

router = APIRouter()


@router.post("/set-llm")
async def set_llm_endpoint(request: Request):
    """
    Set the active LLM provider.
    Allows dynamic switching between OpenAI, Anthropic, Gemini, and Mistral.
    
    Args:
        provider: LLM provider name (openai, anthropic, gemini, mistral)
    
    Returns:
        Success/error status with provider information
    """
    try:
        data = await request.json()
        provider = data.get("provider", "").lower().strip()
        
        if not provider:
            return JSONResponse({
                "status": "error",
                "message": "Provider parameter is required",
                "available_providers": ["openai", "anthropic", "gemini", "mistral"]
            }, status_code=400)
        
        # Set the LLM provider
        set_llm(provider)
        
        # Get updated provider info
        info = get_provider_info()
        
        log_message(f"[LLM Selector] Provider switched to: {provider}")
        
        return JSONResponse({
            "status": "success",
            "message": f"LLM provider switched to: {provider}",
            "active_provider": provider,
            "available_providers": info["available_providers"],
            "provider_models": info["provider_models"]
        }, status_code=200)
        
    except ValueError as e:
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "available_providers": ["openai", "anthropic", "gemini", "mistral"]
        }, status_code=400)
        
    except Exception as e:
        log_message(f"[LLM Selector] Error switching provider: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error switching LLM provider: {str(e)}"
        }, status_code=500)


@router.get("/llm-info")
def get_llm_info():
    """
    Get information about the current LLM provider and available options.
    Returns active provider, available providers list, and their models.
    """
    try:
        info = get_provider_info()
        return JSONResponse({
            "status": "success",
            "active_provider": info["active_provider"],
            "available_providers": info["available_providers"],
            "provider_models": info["provider_models"],
            "timestamp": datetime.now().isoformat()
        }, status_code=200)
        
    except Exception as e:
        log_message(f"[LLM Selector] Error getting provider info: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error getting LLM info: {str(e)}"
        }, status_code=500)

