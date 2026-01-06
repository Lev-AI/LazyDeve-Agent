import os, requests, logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[Config] Environment variables loaded from .env file")
except ImportError:
    print("[Config] python-dotenv not installed, using system environment variables")
except Exception as e:
    print(f"[Config] Error loading .env file: {e}")

def get_ngrok_url():
    try:
        data = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=1.5).json()
        for t in data.get("tunnels", []):
            url = t.get("public_url", "")
            if url.startswith("https"):
                return url
    except Exception:
        pass
    return "http://127.0.0.1:8001"

def get_public_agent_url():
    """Get PUBLIC_AGENT_URL from environment, fallback to ngrok or localhost"""
    public_url = os.getenv("PUBLIC_AGENT_URL")
    if public_url:
        return public_url
    
    # Fallback to ngrok if available
    try:
        ngrok_url = get_ngrok_url()
        if ngrok_url != "http://127.0.0.1:8001":
            return ngrok_url
    except Exception:
        pass
    
    # Final fallback
    return "http://127.0.0.1:8001"

REPO_DIR = os.getcwd()
PROJECTS_DIR = os.path.join(REPO_DIR, "projects")
GLOBAL_RULES_PATH = os.path.join(REPO_DIR, "rules.json")

# Legacy ngrok support (for backward compatibility)
NGROK_URL = get_ngrok_url()

# New Cloudflare/public URL support
PUBLIC_AGENT_URL = get_public_agent_url()

# ===============================
# Environment Variables with Validation
# ===============================

# Server Configuration
PORT = int(os.getenv("PORT", 8001))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Webhook Configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GPT_WEBHOOK_URL = os.getenv("GPT_WEBHOOK_URL")

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USER = os.getenv("GITHUB_USER")
REPO_NAME = os.getenv("REPO_NAME", "LazyDeve")
# ✅ TASK 4.2 FIX: Environment-based GitHub access control
allow_github_access = os.getenv("allow_github_access", "false").lower() == "true"

# ===============================
# Environment Validation
# ===============================

def validate_environment():
    """Validate that required environment variables are set"""
    missing_vars = []
    
    # Check required variables based on environment
    if ENVIRONMENT == "production":
        required_vars = ["OPENAI_API_KEY", "WEBHOOK_URL", "GITHUB_TOKEN", "GITHUB_USER"]
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
    
    if missing_vars:
        logging.warning(f"[WARN] Missing required environment variables: {', '.join(missing_vars)}. Check .env configuration.")
        print(f"[WARN] Missing required environment variables: {', '.join(missing_vars)}. Check .env configuration.")
    else:
        logging.info("[Agent] Environment variables loaded successfully")
        print("[Agent] Environment variables loaded successfully")

# Validate environment on import
validate_environment()

os.makedirs(PROJECTS_DIR, exist_ok=True)

# Global log directory for the agent
AGENT_LOG_DIR = os.path.join(REPO_DIR, "logs")
os.makedirs(AGENT_LOG_DIR, exist_ok=True)
AGENT_LOG_PATH = os.path.join(AGENT_LOG_DIR, "agent.log")

# ===============================
# Dynamic LLM Selection Configuration (Task 7.7.14)
# ===============================
# Configure in .env file:
#   LLM_MODE=auto    → Automatically select model based on task type (default)
#   LLM_MODE=manual  → Always use MANUAL_LLM for all tasks
#   MANUAL_LLM=gpt-4o → Model to use when LLM_MODE=manual
# 
# Auto mode model mapping:
#   - Test/Refactor tasks → mistral-medium
#   - Analysis tasks → gemini-pro
#   - Generation tasks → gpt-4o
#   - Documentation tasks → claude-3.5-sonnet
#   - Default tasks → gpt-4o-mini
LLM_MODE = os.getenv("LLM_MODE", "auto")  # "auto" or "manual"
MANUAL_LLM = os.getenv("MANUAL_LLM", "gpt-4o")  # Model to use in manual mode

logging.basicConfig(
    filename=AGENT_LOG_PATH,
    filemode="a",
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    encoding="utf-8"
)
logging.info(f"Agent boot. PUBLIC_AGENT_URL={PUBLIC_AGENT_URL}")
logging.info(f"Agent boot. NGROK_URL={NGROK_URL} (legacy)")
logging.info(f"Agent boot. PORT={PORT}, ENVIRONMENT={ENVIRONMENT}")
logging.info(f"Agent boot. REPO_NAME={REPO_NAME}")
