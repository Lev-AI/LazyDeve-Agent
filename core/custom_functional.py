import os, logging
from .utils import init_project_env

def rename_project(src_project: str, dst_project: str):
    src, src_path, *_ = init_project_env(src_project)
    dst, dst_path, *_ = init_project_env(dst_project)
    logger = logging.getLogger(f"project.{src}")
    try:
        if os.path.abspath(src_path) == os.path.abspath(dst_path):
            return {"error": "source and destination are the same"}
        if not os.path.exists(src_path):
            return {"error": f"source not found: {src_path}"}
        if os.path.exists(dst_path):
            return {"error": f"destination already exists: {dst_path}"}
        os.rename(src_path, dst_path)
        logger.info(f"Project folder renamed: {src_path} -> {dst_path}")
        return {"status": "ok", "from": src_path, "to": dst_path}
    except Exception as e:
        logger.error(f"Failed to rename project: {e}")
        return {"error": str(e)}
