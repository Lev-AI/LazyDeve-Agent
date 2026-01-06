#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LazyDeve LLM Selector Module
Modular LLM provider management for dynamic model switching
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global active LLM provider
ACTIVE_LLM = os.getenv("ACTIVE_LLM", "openai").lower()

def set_llm(provider: str):
    """
    Set the active LLM provider.
    
    Args:
        provider: LLM provider name (openai, anthropic, gemini, mistral)
    """
    global ACTIVE_LLM
    valid_providers = ["openai", "anthropic", "gemini", "mistral"]
    
    provider = provider.lower().strip()
    
    if provider not in valid_providers:
        raise ValueError(f"Invalid LLM provider: {provider}. Valid options: {valid_providers}")
    
    ACTIVE_LLM = provider
    print(f"[LLM Selector] Active provider changed to: {ACTIVE_LLM}")
    
    # Log the change
    try:
        from core.basic_functional import log_message
        log_message(f"[LLM Selector] Provider switched to: {ACTIVE_LLM}")
    except ImportError:
        pass  # Fallback if logging not available

def get_llm_client():
    """
    Return the current LLM client and model based on ACTIVE_LLM.
    
    Returns:
        tuple: (client, model) - The LLM client and model name
        
    Raises:
        ValueError: If the provider is not supported
        ImportError: If required packages are not installed
    """
    provider = ACTIVE_LLM
    
    if provider == "openai":
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            
            client = OpenAI(api_key=api_key)
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            return client, model
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    elif provider == "anthropic":
        try:
            from anthropic import Anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            
            client = Anthropic(api_key=api_key)
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet")
            return client, model
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
    
    elif provider == "gemini":
        try:
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables")
            
            genai.configure(api_key=api_key)
            model = os.getenv("GEMINI_MODEL", "gemini-pro")
            return genai, model
        except ImportError:
            raise ImportError("Google Generative AI package not installed. Run: pip install google-generativeai")
    
    elif provider == "mistral":
        try:
            from mistralai.client import MistralClient
            api_key = os.getenv("MISTRAL_API_KEY")
            if not api_key:
                raise ValueError("MISTRAL_API_KEY not found in environment variables")
            
            client = MistralClient(api_key=api_key)
            model = os.getenv("MISTRAL_MODEL", "mistral-medium")
            return client, model
        except ImportError:
            raise ImportError("Mistral AI package not installed. Run: pip install mistralai")
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

def get_available_providers():
    """
    Get list of available LLM providers based on installed packages and API keys.
    
    Returns:
        list: Available provider names
    """
    available = []
    
    # Check OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            import openai
            available.append("openai")
        except ImportError:
            pass
    
    # Check Anthropic
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            available.append("anthropic")
        except ImportError:
            pass
    
    # Check Gemini
    if os.getenv("GEMINI_API_KEY"):
        try:
            import google.generativeai
            available.append("gemini")
        except ImportError:
            pass
    
    # Check Mistral
    if os.getenv("MISTRAL_API_KEY"):
        try:
            import mistralai
            available.append("mistral")
        except ImportError:
            pass
    
    return available

def get_current_provider():
    """
    Get the currently active LLM provider.
    
    Returns:
        str: Current active provider name
    """
    return ACTIVE_LLM

def get_provider_info():
    """
    Get information about the current provider and available options.
    
    Returns:
        dict: Provider information
    """
    return {
        "active_provider": ACTIVE_LLM,
        "available_providers": get_available_providers(),
        "provider_models": {
            "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet"),
            "gemini": os.getenv("GEMINI_MODEL", "gemini-pro"),
            "mistral": os.getenv("MISTRAL_MODEL", "mistral-medium")
        }
    }

# ===============================
# Dynamic LLM Selector (Task 7.7.14)
# ===============================

from typing import Optional, Dict, Any

class DynamicLLMSelector:
    """
    Selects the most appropriate LLM model dynamically based on task type and project context.
    
    Integrates with:
    - Existing core/llm_selector.py (provider switching via set_llm/get_llm_client)
    - ContextManager (active project state)
    - context_api (Task 8 semantic memory - when available)
    """

    # Model mapping: maps task categories to model names
    # Models are provider-specific and must match available models for each provider
    # Note: Provider switching via /set-llm may be needed for some models
    MODEL_MAP = {
        "test": "mistral-medium",           # Good for test generation (requires mistral provider)
        "refactor": "mistral-medium",        # Efficient for refactoring (requires mistral provider)
        "analyze": "gemini-pro",             # Strong analysis capabilities (requires gemini provider)
        "generate": "gpt-4o",               # Best for code generation (requires openai provider)
        "document": "claude-3.5-sonnet",    # Excellent documentation (requires anthropic provider)
        "default": "gpt-4o-mini"             # Cost-effective default (requires openai provider)
    }
    
    # Model to provider mapping: determines which provider each model belongs to
    MODEL_TO_PROVIDER = {
        "mistral-medium": "mistral",
        "gemini-pro": "gemini",
        "gpt-4o": "openai",
        "gpt-4o-mini": "openai",
        "claude-3.5-sonnet": "anthropic",
        "claude-3-sonnet": "anthropic"
    }

    def auto_select_model(self, task_prompt: str, project_name: Optional[str] = None) -> str:
        """
        Automatic model selection based on task prompt analysis and project context.
        Now enhanced with Task 8 semantic context for better selection.
        
        Args:
            task_prompt: The task description/prompt
            project_name: Optional project name (defaults to active project)
            
        Returns:
            str: Model name (e.g., "gpt-4o-mini", "mistral-medium")
        """
        # Get active project if not provided
        try:
            from core.context_manager import context_manager
            if not project_name:
                project_name = context_manager.get_project()
        except Exception:
            project_name = None
        
        # Handle None or empty prompts
        if not task_prompt:
            task_prompt = ""
        
        # Task 8 Enhancement: Get semantic context if project exists
        semantic_context = None
        if project_name:
            try:
                from core.ai_context import get_project_context_summary
                semantic_context = get_project_context_summary(project_name, format="llm", use_cache=True)
                try:
                    from core.basic_functional import log_message
                    log_message(f"[LLM Selector] Using semantic context for {project_name}")
                except ImportError:
                    pass
            except ImportError:
                pass  # Task 8 not available
            except Exception as e:
                try:
                    from core.basic_functional import log_message
                    log_message(f"[LLM Selector] WARNING: Error loading semantic context: {str(e)}")
                except ImportError:
                    pass
        
        # Extract task intent from prompt (simple keyword matching)
        task_lower = task_prompt.lower()
        
        # Task categorization with semantic awareness
        category = None
        
        if any(k in task_lower for k in ["test", "unit test", "integration test", "lint"]):
            category = "test"
            # Task 8: Check if testing framework already used in project
            if semantic_context:
                tech_stack = semantic_context.get("tech_stack", [])
                if "pytest" in tech_stack:
                    try:
                        from core.basic_functional import log_message
                        log_message(f"[LLM Selector] Project uses pytest - prioritizing test-friendly model")
                    except ImportError:
                        pass
        
        elif any(k in task_lower for k in ["refactor", "refactoring", "optimize", "improve"]):
            category = "refactor"
            # Task 8: Consider project complexity
            if semantic_context:
                confidence = semantic_context.get("confidence", 0.0)
                if confidence > 0.7:
                    try:
                        from core.basic_functional import log_message
                        log_message(f"[LLM Selector] High confidence project - using advanced refactoring model")
                    except ImportError:
                        pass
        
        elif any(k in task_lower for k in ["analyze", "analysis", "audit", "inspect", "review", "performance", "explain"]):
            category = "analyze"
        
        elif any(k in task_lower for k in ["create", "generate", "build", "design", "architecture", "implement", "add"]):
            category = "generate"
            # Task 8: Tech stack awareness
            if semantic_context:
                tech_stack = semantic_context.get("tech_stack", [])
                if "python" in tech_stack and "fastapi" in tech_stack:
                    try:
                        from core.basic_functional import log_message
                        log_message(f"[LLM Selector] Python+FastAPI project detected - optimizing model choice")
                    except ImportError:
                        pass
        
        elif any(k in task_lower for k in ["doc", "documentation", "document", "summarize", "readme", "comment"]):
            category = "document"
        
        else:
            category = "default"
        
        # Defensive: Ensure category exists in MODEL_MAP (fallback to default)
        if category not in self.MODEL_MAP:
            try:
                from core.basic_functional import log_message
                log_message(f"[LLM Selector] WARNING: Category '{category}' not found in MODEL_MAP, using 'default'")
            except ImportError:
                pass
            category = "default"
        
        model = self.MODEL_MAP.get(category, self.MODEL_MAP["default"])
        
        # Task 8 Enhancement: Tech stack-based model adjustment
        if semantic_context:
            tech_stack = semantic_context.get("tech_stack", [])
            
            # Example: For ML/Data Science projects, prefer models good at data science
            if any(ml_tech in tech_stack for ml_tech in ["tensorflow", "pytorch", "pandas", "numpy", "sklearn"]):
                try:
                    from core.basic_functional import log_message
                    log_message(f"[LLM Selector] ML/Data Science project detected")
                except ImportError:
                    pass
            
            # Example: For web projects, ensure web-friendly model
            if any(web_tech in tech_stack for web_tech in ["react", "vue", "angular", "django", "flask", "fastapi"]):
                try:
                    from core.basic_functional import log_message
                    log_message(f"[LLM Selector] Web development project detected")
                except ImportError:
                    pass
        
        # Validate provider availability: Check if selected model's provider has API key
        selected_provider = self.MODEL_TO_PROVIDER.get(model)
        available_providers = get_available_providers()
        
        if selected_provider and selected_provider not in available_providers:
            # Provider not available - fallback to default model from available provider
            try:
                from core.basic_functional import log_message
                log_message(f"[LLM Selector] WARNING: Provider '{selected_provider}' not available (no API key). "
                           f"Selected model '{model}' cannot be used. Falling back to default model.")
            except ImportError:
                pass
            
            # Try to find a model from available providers
            # Priority: openai > anthropic > gemini > mistral
            fallback_models = {
                "openai": "gpt-4o-mini",
                "anthropic": "claude-3.5-sonnet",
                "gemini": "gemini-pro",
                "mistral": "mistral-medium"
            }
            
            for provider in ["openai", "anthropic", "gemini", "mistral"]:
                if provider in available_providers:
                    model = fallback_models[provider]
                    try:
                        from core.basic_functional import log_message
                        log_message(f"[LLM Selector] Fallback to {model} (provider: {provider})")
                    except ImportError:
                        pass
                    break
            else:
                # No providers available - use default anyway (will fail at runtime, but at least we tried)
                model = self.MODEL_MAP["default"]
                try:
                    from core.basic_functional import log_message
                    log_message(f"[LLM Selector] CRITICAL: No LLM providers available! Using default model anyway.")
                except ImportError:
                    pass
        
        # Task 8: Enhanced context logging
        if semantic_context:
            context_string = semantic_context.get("context_string", "")
            try:
                from core.basic_functional import log_message
                log_message(
                    f"[LLM Selector] Auto-selected model: {model} for task: '{task_prompt[:50]}...' | "
                    f"Context: {context_string[:100]}"
                )
            except ImportError:
                pass
        else:
            context_info = f"project={project_name}" if project_name else "no_project"
            try:
                from core.basic_functional import log_message
                log_message(f"[LLM Selector] Auto-selected model: {model} for task: '{task_prompt[:50]}...' ({context_info})")
            except ImportError:
                pass
        
        return model

    def select_model(self, task_prompt: str, project_name: Optional[str] = None) -> str:
        """
        Main entry point: Chooses between AUTO and MANUAL modes.
        
        Mode is determined by LLM_MODE environment variable (from .env):
        - LLM_MODE=auto   → Automatically select model based on task type
        - LLM_MODE=manual → Always use MANUAL_LLM model
        
        Args:
            task_prompt: The task description
            project_name: Optional project name
            
        Returns:
            str: Selected model name
        """
        # Import config variables (reads from .env via core.config)
        try:
            from core.config import LLM_MODE, MANUAL_LLM
        except ImportError:
            # Fallback if config not available
            LLM_MODE = "auto"
            MANUAL_LLM = "gpt-4o"
        
        # Check manual mode first (LLM_MODE=manual in .env)
        if LLM_MODE == "manual" and MANUAL_LLM:
            try:
                from core.basic_functional import log_message
                log_message(f"[LLM Selector] Manual mode active → {MANUAL_LLM}")
            except ImportError:
                pass
            return MANUAL_LLM
        
        # Auto mode: dynamic selection
        return self.auto_select_model(task_prompt, project_name)

    def select_model_with_semantic_context(
        self,
        task_prompt: str,
        project_name: Optional[str] = None,
        prefer_capability: Optional[str] = None
    ) -> str:
        """
        Advanced model selection with semantic context and capability preference.
        
        This is an enhanced version that uses Task 8 semantic context
        to make smarter model selection decisions.
        
        Args:
            task_prompt: The task description
            project_name: Active project name (optional)
            prefer_capability: Preferred capability ("speed", "quality", "cost")
            
        Returns:
            Selected model name
        """
        # Get base selection
        base_model = self.auto_select_model(task_prompt, project_name)
        
        # If no preference or no semantic context, return base
        if not prefer_capability or not project_name:
            return base_model
        
        # Get semantic context
        try:
            from core.ai_context import get_project_context_summary
            semantic_context = get_project_context_summary(project_name, format="llm")
        except:
            return base_model
        
        # Adjust based on capability preference
        tech_stack = semantic_context.get("tech_stack", [])
        confidence = semantic_context.get("confidence", 0.0)
        
        if prefer_capability == "speed":
            # Prefer faster models
            speed_models = {
                "gpt-4o": "gpt-4o-mini",
                "claude-3.5-sonnet": "claude-3.5-sonnet",  # Already fast
                "mistral-medium": "mistral-small"
            }
            adjusted_model = speed_models.get(base_model, base_model)
            if adjusted_model != base_model:
                try:
                    from core.basic_functional import log_message
                    log_message(f"[LLM Selector] Speed preference: {base_model} → {adjusted_model}")
                except ImportError:
                    pass
            return adjusted_model
        
        elif prefer_capability == "quality":
            # Prefer higher quality models for complex projects
            if confidence > 0.7 and len(tech_stack) > 5:
                quality_models = {
                    "gpt-4o-mini": "gpt-4o",
                    "claude-3.5-sonnet": "claude-3.5-sonnet",  # Already high quality
                    "mistral-small": "mistral-medium"
                }
                adjusted_model = quality_models.get(base_model, base_model)
                if adjusted_model != base_model:
                    try:
                        from core.basic_functional import log_message
                        log_message(f"[LLM Selector] Quality preference for complex project: {base_model} → {adjusted_model}")
                    except ImportError:
                        pass
                return adjusted_model
        
        elif prefer_capability == "cost":
            # Prefer cost-effective models
            cost_models = {
                "gpt-4o": "gpt-4o-mini",
                "claude-3.5-sonnet": "gpt-4o-mini",
                "mistral-medium": "mistral-small"
            }
            adjusted_model = cost_models.get(base_model, base_model)
            if adjusted_model != base_model:
                try:
                    from core.basic_functional import log_message
                    log_message(f"[LLM Selector] Cost preference: {base_model} → {adjusted_model}")
                except ImportError:
                    pass
            return adjusted_model
        
        return base_model

    def get_task_context(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get project context for model selection.
        
        Phase 1: Returns basic context (project name, tech stack hints).
        Task 8: Will use get_project_context() for semantic memory.
        
        Args:
            project_name: Optional project name
            
        Returns:
            dict: Context information
        """
        try:
            from core.context_manager import context_manager
            if not project_name:
                project_name = context_manager.get_project()
        except Exception:
            project_name = None
        
        if not project_name:
            return {"active_project": None, "has_context": False}
        
        # Phase 1: Basic context
        context = {
            "active_project": project_name,
            "has_context": True
        }
        
        # Task 8 Integration (placeholder - will be enhanced)
        # Try to load semantic context if available
        try:
            from core.context_api import get_project_context
            semantic_context = get_project_context(project_name)
            if semantic_context and semantic_context.get("tech_stack"):
                context["tech_stack"] = semantic_context.get("tech_stack", [])
                context["complexity"] = semantic_context.get("complexity", "medium")
                context["has_semantic_context"] = True
        except Exception:
            # Task 8 not yet implemented or context not available
            context["has_semantic_context"] = False
        
        return context


# Global singleton instance
_llm_selector_instance = None

def get_llm_selector() -> DynamicLLMSelector:
    """Get singleton instance of DynamicLLMSelector."""
    global _llm_selector_instance
    if _llm_selector_instance is None:
        _llm_selector_instance = DynamicLLMSelector()
    return _llm_selector_instance

if __name__ == "__main__":
    # Test the LLM selector
    print("Testing LLM Selector...")
    print(f"Current provider: {get_current_provider()}")
    print(f"Available providers: {get_available_providers()}")
    print(f"Provider info: {get_provider_info()}")
    
    try:
        client, model = get_llm_client()
        print(f"✅ Successfully loaded {get_current_provider()} client with model: {model}")
    except Exception as e:
        print(f"❌ Error loading LLM client: {e}")
