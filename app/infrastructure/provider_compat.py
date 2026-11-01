"""按实际端点适配供应商协议；不根据模型名称猜测能力。"""
from copy import deepcopy
from urllib.parse import urlsplit


def chat_provider(base_url: str) -> str:
    return "deepseek" if urlsplit(str(base_url)).hostname == "api.deepseek.com" else "openai"


def adapt_chat_request(base_url: str, request: dict, *, sdk: bool = True) -> dict:
    if chat_provider(base_url) != "deepseek":
        return request
    result = deepcopy(request)
    # DeepSeek Chat 使用 max_tokens，保留调用方已经计算的输出预算上限。
    limit = result.pop("max_completion_tokens", None)
    if limit is not None:
        result["max_tokens"] = min(limit, result.get("max_tokens", limit))
    parameters = result.setdefault("extra_body", {}) if sdk else result
    enabled = parameters.pop("enable_thinking", None)
    if enabled is not None:
        parameters["thinking"] = {"type": "enabled" if enabled else "disabled"}
    if sdk and not parameters:
        result.pop("extra_body", None)
    # 工具往返的 assistant 消息保留正文键，避免上游拒绝 null。
    for message in result.get("messages", []):
        if message.get("role") == "assistant" and message.get("tool_calls") and message.get("content") is None:
            message["content"] = ""
    return result
