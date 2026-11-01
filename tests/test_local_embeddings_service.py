"""本机服务边界验证；真实权重下载与向量质量由独立联调保留证据。"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx

from scripts.local_embeddings import MODEL, create_app


async def test_local_embedding_api_enforces_model_and_input_bounds(tmp_path):
    api = create_app(tmp_path)
    encoder = SimpleNamespace(embed_batch=AsyncMock(return_value=[[1., 0.], [0., 1.]]))
    import asyncio
    api.state.encoder, api.state.lock = encoder, asyncio.Lock()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url="http://test") as client:
        response = await client.post('/v1/embeddings', json={"model": MODEL, "input": ["背包", "backpack"]})
        assert response.status_code == 200
        assert [r['index'] for r in response.json()['data']] == [0, 1]
        for texts in ([], [""], ["a"] * 65, ["x" * 20001]):
            assert (await client.post('/v1/embeddings', json={"model": MODEL, "input": texts})).status_code == 422
        assert (await client.post('/v1/embeddings', json={"model": 'unknown', "input": '背包'})).status_code == 404
    assert encoder.embed_batch.await_count == 1
