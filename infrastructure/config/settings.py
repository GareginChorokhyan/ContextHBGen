import os
from dotenv import load_dotenv

load_dotenv()

class Settings:

    LLM_API_KEY: str = os.getenv("OPENROUTER_API_KEY")

    LLM_API_URL: str = os.getenv("LLM_API_URL")

    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")

    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", 20000))

    OPENROUTER_CHAT_MODEL: str = os.getenv("OPENROUTER_CHAT_MODEL", "z-ai/glm-4.5-air:free")
    OPENROUTER_EMBED_MODEL: str = os.getenv("OPENROUTER_EMBED_MODEL", "text-embedding-3-small")
    OPENROUTER_EMBED_DIM: int = int(os.getenv("OPENROUTER_EMBED_DIM", 1536))

    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", 60))

    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", 6))
    RAG_MIN_SCORE: float = float(os.getenv("RAG_MIN_SCORE", 0.0))

    USE_LIGHTRAG: bool = os.getenv("USE_LIGHTRAG", "true").lower() in ("1", "true", "yes")
    LIGHTRAG_WORKING_DIR: str = os.getenv("LIGHTRAG_WORKING_DIR", "./lightrag_storage")
    LIGHTRAG_WORKSPACE: str = os.getenv("LIGHTRAG_WORKSPACE", "default_workspace")
    LIGHTRAG_QUERY_MODE: str = os.getenv("LIGHTRAG_QUERY_MODE", "hybrid")
    LIGHTRAG_LOG_DIR: str = os.getenv("LIGHTRAG_LOG_DIR", "./lightrag_storage")

    SUPABASE_DB_HOST: str = os.getenv("SUPABASE_DB_HOST", "")
    SUPABASE_DB_PORT: int = int(os.getenv("SUPABASE_DB_PORT", 5432))
    SUPABASE_DB_USER: str = os.getenv("SUPABASE_DB_USER", "")
    SUPABASE_DB_PASSWORD: str = os.getenv("SUPABASE_DB_PASSWORD", "")
    SUPABASE_DB_NAME: str = os.getenv("SUPABASE_DB_NAME", "")
    SUPABASE_DB_MAX_CONNECTIONS: int = int(os.getenv("SUPABASE_DB_MAX_CONNECTIONS", 2))

    LIGHTRAG_MAX_ASYNC: int = int(os.getenv("LIGHTRAG_MAX_ASYNC", 2))
    LIGHTRAG_MAX_PARALLEL_INSERT: int = int(os.getenv("LIGHTRAG_MAX_PARALLEL_INSERT", 1))

    HANDBOOK_TARGET_WORDS: int = int(os.getenv("HANDBOOK_TARGET_WORDS", 20000))
    HANDBOOK_SECTION_WORDS: int = int(os.getenv("HANDBOOK_SECTION_WORDS", 1200))