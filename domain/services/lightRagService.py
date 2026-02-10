import asyncio
import os
from typing import List, Optional

from lightrag import LightRAG, QueryParam
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.utils import setup_logger, EmbeddingFunc
from lightrag.llm.openai import openai_complete_if_cache, openai_embed

from infrastructure.config.settings import Settings


class LightRagService:
    def __init__(self):
        self._rag: Optional[LightRAG] = None
        self._initialized = False
        self._init_lock = asyncio.Lock()
        setup_logger("lightrag", level="INFO")

    async def initialize(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await self._ainitialize()
            self._initialized = True

    async def _ainitialize(self) -> None:
        self._prepare_env()
        embedding_func = EmbeddingFunc(
            embedding_dim=Settings.OPENROUTER_EMBED_DIM,
            model_name=Settings.OPENROUTER_EMBED_MODEL,
            func=lambda texts: openai_embed(
                texts,
                model=Settings.OPENROUTER_EMBED_MODEL,
                base_url=Settings.LLM_API_URL,
                api_key=Settings.LLM_API_KEY,
            ),
        )

        async def llm_model_func(
            prompt,
            system_prompt=None,
            history_messages=None,
            **kwargs,
        ):
            return await openai_complete_if_cache(
                model=Settings.OPENROUTER_CHAT_MODEL,
                prompt=prompt,
                system_prompt=system_prompt,
                history_messages=history_messages or [],
                base_url=Settings.LLM_API_URL,
                api_key=Settings.LLM_API_KEY,
                timeout=Settings.REQUEST_TIMEOUT_SECONDS,
                **kwargs,
            )

        self._rag = LightRAG(
            working_dir=Settings.LIGHTRAG_WORKING_DIR,
            workspace=Settings.LIGHTRAG_WORKSPACE,
            llm_model_func=llm_model_func,
            embedding_func=embedding_func,
            kv_storage="PGKVStorage",
            vector_storage="PGVectorStorage",
            graph_storage="NetworkXStorage",
            doc_status_storage="PGDocStatusStorage",
        )

        await self._rag.initialize_storages()
        await initialize_pipeline_status()

    async def insert_chunks(self, chunks: List[str], ids: Optional[List[str]] = None, file_path: Optional[str] = None) -> None:
        if not chunks:
            return
        await self.initialize()
        file_paths = [file_path] * len(chunks) if file_path else None
        await self._rag.ainsert(chunks, ids=ids, file_paths=file_paths)  

    async def query(self, question: str, mode: Optional[str] = None) -> str:
        await self.initialize()
        param = QueryParam(mode=mode or Settings.LIGHTRAG_QUERY_MODE)
        return await self._rag.aquery(question, param=param)  

    def _prepare_env(self) -> None:
        os.environ.setdefault("LIGHTRAG_KV_STORAGE", "PGKVStorage")
        os.environ.setdefault("LIGHTRAG_DOC_STATUS_STORAGE", "PGDocStatusStorage")
        os.environ.setdefault("LIGHTRAG_GRAPH_STORAGE", "PGGraphStorage")
        os.environ.setdefault("LIGHTRAG_VECTOR_STORAGE", "PGVectorStorage")
        os.environ.setdefault("MAX_ASYNC", str(Settings.LIGHTRAG_MAX_ASYNC))
        os.environ.setdefault("MAX_PARALLEL_INSERT", str(Settings.LIGHTRAG_MAX_PARALLEL_INSERT))
        os.environ.setdefault("LOG_DIR", Settings.LIGHTRAG_LOG_DIR)

        if Settings.SUPABASE_DB_HOST:
            os.environ.setdefault("POSTGRES_HOST", Settings.SUPABASE_DB_HOST)
        if Settings.SUPABASE_DB_PORT:
            os.environ.setdefault("POSTGRES_PORT", str(Settings.SUPABASE_DB_PORT))
        if Settings.SUPABASE_DB_USER:
            os.environ.setdefault("POSTGRES_USER", Settings.SUPABASE_DB_USER)
        if Settings.SUPABASE_DB_PASSWORD:
            os.environ.setdefault("POSTGRES_PASSWORD", Settings.SUPABASE_DB_PASSWORD)
        if Settings.SUPABASE_DB_NAME:
            os.environ.setdefault("POSTGRES_DATABASE", Settings.SUPABASE_DB_NAME)
        os.environ.setdefault("POSTGRES_MAX_CONNECTIONS", str(Settings.SUPABASE_DB_MAX_CONNECTIONS))

        os.environ.setdefault("POSTGRES_WORKSPACE", Settings.LIGHTRAG_WORKSPACE)
