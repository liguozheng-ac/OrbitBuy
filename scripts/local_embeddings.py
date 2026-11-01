"""可选本机 Embedding HTTP 服务，复用 retrieval extra，不需要云 API key。

安装：uv sync --extra retrieval --frozen --python .venv/Scripts/python.exe
启动：python -m scripts.local_embeddings --port 8001
首次启动需要下载模型；仅监听 127.0.0.1，不作为公开网关。
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from app.infrastructure.embedding.local_model import MODEL, LocalMultilingualEmbedding, model_version


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str
    input: str | list[str]
    encoding_format: Literal["float"] = "float"


def create_app(cache_dir: Path, *, loader=LocalMultilingualEmbedding):
    @asynccontextmanager
    async def lifespan(api):
        api.state.encoder = await asyncio.to_thread(loader, cache_dir)
        api.state.version = await asyncio.to_thread(model_version, cache_dir)
        api.state.lock = asyncio.Lock()
        yield

    api = FastAPI(title="OrbitBuy local embeddings", lifespan=lifespan)

    @api.get("/health")
    async def health():
        return {"status": "ok", "model": MODEL, "dimension": 384, "version": api.state.version}

    @api.post("/v1/embeddings")
    async def embed(body: EmbeddingRequest):
        if body.model != MODEL:
            raise HTTPException(404, "本机服务不提供该模型")
        texts = [body.input] if isinstance(body.input, str) else body.input
        if not 1 <= len(texts) <= 64 or any(not text.strip() or len(text) > 20000 for text in texts):
            raise HTTPException(422, "每批 1～64 条，每条 1～20000 字符")
        async with api.state.lock:
            vectors = await api.state.encoder.embed_batch(texts)
            tokenizer = getattr(getattr(getattr(api.state.encoder, "model", None), "model", None), "tokenizer", None)
            # AgentScope RAG 需要标准 usage；统计原始输入的真实 tokenizer token，
            # 不把本地推理计数解释为云端计费或包含分块附加 token 的执行量。
            tokens = sum(len(tokenizer.encode(text).ids) for text in texts) if tokenizer is not None else None
        result = {"object": "list", "model": MODEL,
                "data": [{"object": "embedding", "index": i, "embedding": vector}
                         for i, vector in enumerate(vectors)]}
        if tokens is not None:
            result["usage"] = {"prompt_tokens": tokens, "total_tokens": tokens}
        return result

    return api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/models/embeddings"))
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(create_app(args.cache_dir), host="127.0.0.1", port=args.port, workers=1)


if __name__ == "__main__":
    main()
