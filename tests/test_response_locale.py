"""回复语言只取白名单，原始问题不改写；语言之间不能共用最终文本缓存。"""
import pytest

from app.application.agents.orchestrator import SubmitIntentInput, MainAgentOrchestrator
from app.infrastructure.context import ShoppingContext, ShoppingContextSnapshot
from tests.test_ag_ui import make_orchestrator


@pytest.mark.parametrize('locale,expected', [('zh-CN','简体中文'),('ja-JP','日本語'),('en-US','English'),('bad\ninjected',None)])
async def test_response_language_is_whitelisted_without_rewriting_buyer_input(locale, expected):
    orchestrator, agent, _ = make_orchestrator()
    original = agent.reply_stream
    received = []
    async def capture(inputs, **kwargs):
        received.extend(inputs or [])
        async for event in original(inputs, **kwargs): yield event
    agent.reply_stream = capture
    query = '查询旅行背包，金额保持 CNY，不下单。'
    result = await orchestrator.handle_intent(SubmitIntentInput('session-test','buyer-test',locale,'CNY',query))
    assert not result.error
    assert next(m for m in received if m.name == 'buyer-test').get_text_content() == query
    hints = [m for m in received if m.name == 'response_language']
    if expected:
        assert len(hints) == 1 and expected in hints[0].get_text_content()
        assert 'does not change currency' in hints[0].get_text_content()
    else:
        assert not hints


def test_final_text_cache_is_isolated_by_interface_locale():
    scopes = []
    for locale in ('zh-CN','ja-JP','en-US'):
        token = ShoppingContext.set(ShoppingContextSnapshot('s','b',locale,'CNY'))
        try: scopes.append(MainAgentOrchestrator._model_cache_scope())
        finally: ShoppingContext.reset(token)
    assert len(set(scopes)) == 3
