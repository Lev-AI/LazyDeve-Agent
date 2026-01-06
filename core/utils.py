import os
import json
import logging
import psutil
import time
import subprocess

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def init_project_env(project_name: str):
    proj = project_name.replace(" ", "_")
    project_path = os.path.join(PROJECTS_DIR, proj)
    logs_path = os.path.join(project_path, "logs")
    ensure_dir(logs_path)

    # Local copy of rules
    rules_path = os.path.join(project_path, "rules.json")
    if not os.path.exists(rules_path) and os.path.exists(GLOBAL_RULES_PATH):
        with open(GLOBAL_RULES_PATH, "r", encoding="utf-8") as src, open(rules_path, "w", encoding="utf-8") as dst:
            dst.write(src.read())

    log_path = os.path.join(logs_path, "run.log")

    # Per-project logger
    logger_name = f"project.{proj}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Avoid duplicating handlers
    if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == log_path for h in logger.handlers):
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    logger.info(f"Initialized project environment for {proj}")
    return proj, project_path, rules_path, log_path, logger

def get_system_diagnostics():
    """
    Gather system diagnostics including CPU and memory usage.
    Returns a dictionary with the diagnostics data.
    """
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    memory_usage = memory_info.percent
    return {
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "timestamp": time.time()
    }

def perform_full_system_analysis() -> dict:
    """
    Perform a full system analysis including Git history, file count, and memory sync validation.
    Returns a dictionary with the analysis results.
    """
    analysis_results = {}
    start_time = time.time()

    try:
        # Git history analysis
        commits = subprocess.run(
            ["git", "log", "--oneline"],
            capture_output=True, text=True, check=True
        ).stdout.strip().split('\n')
        analysis_results['git_history'] = commits

        # File count
        file_count = sum(len(files) for _, _, files in os.walk('.'))
        analysis_results['file_count'] = file_count

        # Memory sync validation
        memory_info = psutil.virtual_memory()
        analysis_results['memory_sync'] = {
            "total": memory_info.total,
            "available": memory_info.available,
            "used": memory_info.used,
            "percent": memory_info.percent
        }

        analysis_results['status'] = 'success'
    except Exception as e:
        analysis_results['status'] = 'error'
        analysis_results['error'] = str(e)

    end_time = time.time()
    analysis_results['execution_time'] = end_time - start_time

    return analysis_results
