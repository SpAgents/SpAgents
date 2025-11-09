import os
from typing import Optional


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Helper to read environment variables with an optional fallback."""
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


DEEPSEEK_API_KEY = _get_env("DEEPSEEK_API_KEY", "")
DOUBAO_API_KEY = _get_env("DOUBAO_API_KEY", "")
QWEN_API_KEY = _get_env("QWEN_API_KEY", "")

HUATUO_API_URL = _get_env("HUATUO_API_URL", "http://127.0.0.1:8000/generate_response/")

MODEL_BASE_DIR = _get_env("MODEL_BASE_DIR", "model")
LONG_TERM_DB_PATH = _get_env("LONG_TERM_DB_PATH", "db/long_term_memory.db")
LONG_TERM_MODEL_DIR = _get_env("LONG_TERM_MODEL_DIR", "Bio_ClinicalBERT")
DATA_BASE_DIR = _get_env("DATA_BASE_DIR")


def model_path(*parts: str) -> str:
    """Return a model path rooted at MODEL_BASE_DIR unless overridden."""
    if MODEL_BASE_DIR:
        return os.path.join(MODEL_BASE_DIR, *parts)
    return os.path.join(*parts)


def data_path(*parts: str) -> str:
    """Return a data path rooted at DATA_BASE_DIR unless overridden."""
    if DATA_BASE_DIR:
        return os.path.join(DATA_BASE_DIR, *parts)
    return os.path.join(*parts)


def long_term_model_path(*parts: str) -> str:
    """Return path under LONG_TERM_MODEL_DIR."""
    if LONG_TERM_MODEL_DIR:
        return os.path.join(LONG_TERM_MODEL_DIR, *parts)
    return os.path.join(*parts)

