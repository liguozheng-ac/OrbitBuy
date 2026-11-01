"""DeepSeek 兼容在真实 SDK 序列化边界验证，不调用外部服务。"""
from copy import deepcopy
from dataclasses import replace
import json

import httpx
import pytest
from agentscope.message import Msg, ThinkingBlock, ToolCallBlock, TextBlock, UserMsg

from app.infrastructure.llm import create_chat_model
from app.infrastructure.prompt_cache import PromptCacheFormatter
from app.infrastructure.provider_compat import adapt_chat_request
from app.infrastructure.throttle import GatewayThrottle
from tests.test_retrieval import _settings


@pytest.mark.parametrize("enabled", [True, False, None])
async def test_deepseek_parameters_at_sdk_http_boundary(tmp_path, enabled):
    requests = []
    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(200, json={
            "id": "fixture", "object": "chat.completion", "created": 1, "model": body["model"],
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
        })
    settings = replace(_settings(tmp_path), llm_api_key="fixture-not-a-secret", llm_model="fixture-model",
                       llm_base_url="https://api.deepseek.com", llm_fallback_model="", llm_enable_thinking=enabled)
    model = create_chat_model(settings, stream=False, throttle=GatewayThrottle(1, 0))
    await model.client.close()
    model.client._client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    try:
        await model([UserMsg("buyer", "测试")], max_completion_tokens=64)
        body = requests[0]
        assert body["max_tokens"] == 64
        assert "max_completion_tokens" not in body and "enable_thinking" not in body
        if enabled is None:
            assert "thinking" not in body
        else:
            assert body["thinking"] == {"type": "enabled" if enabled else "disabled"}
    finally:
        await model.client.close()


async def test_deepseek_formatter_preserves_reasoning_and_tool_identity():
    messages = [Msg(name="assistant", role="assistant", content=[
        ThinkingBlock(thinking="先核实商品"),
        ToolCallBlock(id="lookup-1", name="lookup", input="{}"),
    ])]
    original = deepcopy(messages[0].model_dump())
    formatted = await PromptCacheFormatter(provider="deepseek").format(messages)
    assert formatted[0]["reasoning_content"] == "先核实商品"
    assert formatted[0]["tool_calls"][0]["id"] == "lookup-1"
    assert messages[0].model_dump() == original


def test_endpoint_matching_and_output_budget_are_conservative():
    body = {"max_tokens": 16, "max_completion_tokens": 32, "extra_body": {"enable_thinking": False},
            "messages": [{"role": "assistant", "content": None, "tool_calls": [{"id": "a"}]}]}
    original = deepcopy(body)
    converted = adapt_chat_request("https://api.deepseek.com", body)
    assert converted["max_tokens"] == 16
    assert converted["messages"][0]["content"] == ""
    assert body == original
    assert adapt_chat_request("https://api.deepseek.com.attacker.invalid", body) is body
    assert adapt_chat_request("https://dashscope.aliyuncs.com/compatible-mode/v1", body) is body


def test_connection_probe_uses_the_same_raw_http_parameters():
    body = {"enable_thinking": False, "max_tokens": 1024}
    converted = adapt_chat_request("https://api.deepseek.com", body, sdk=False)
    assert converted == {"thinking": {"type": "disabled"}, "max_tokens": 1024}
    assert body == {"enable_thinking": False, "max_tokens": 1024}
