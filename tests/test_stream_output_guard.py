"""出口安全：跨分片、失败/取消、历史分页重放不泄露未审核的正文。"""
import asyncio
import json
from types import SimpleNamespace

import pytest
from ag_ui.core import RunAgentInput
from agentscope.event import TextBlockStartEvent, TextBlockDeltaEvent, TextBlockEndEvent
from agentscope.message import AssistantMsg

from app.application.agents.ag_ui_adapter import AGUIRunAdapter
from app.application.agents.orchestrator import MainAgentOrchestrator
from app.infrastructure.eventbus import TradeEventBus
from app.infrastructure.ag_ui_journal import AGUIJournal


@pytest.mark.parametrize("text,split", [
    ("合成 http://qdrant:6333/private 内容", 15),
    ("合成 sk-abcdefghijklmnopqrstuvwxyz123456 内容", 14),
    ("调用 product_search_tool 后回答", 13),
])
@pytest.mark.parametrize("ending", ["success", "error", "cancel"])
async def test_guard_waits_for_complete_reply_and_rejects_partial_output(text, split, ending):
    entered, release = asyncio.Event(), asyncio.Event()
    class Agent:
        name = "synthetic"
        state = SimpleNamespace()
        async def reply_stream(self, inputs, yield_final_msg=True):
            yield TextBlockStartEvent(reply_id="reply", block_id="block")
            yield TextBlockDeltaEvent(reply_id="reply", block_id="block", delta=text[:split])
            entered.set()
            await release.wait()
            yield TextBlockDeltaEvent(reply_id="reply", block_id="block", delta=text[split:])
            if ending == "error":
                raise RuntimeError("synthetic failure")
            yield TextBlockEndEvent(reply_id="reply", block_id="block")
            yield AssistantMsg(self.name, text)

    bus = TradeEventBus()
    queue = bus.subscribe("session")
    orchestrator = MainAgentOrchestrator(None, bus, None)
    events = []
    adapter = AGUIRunAdapter(RunAgentInput.model_validate({"threadId": "session", "runId": "run",
        "messages": [], "state": {}, "tools": [], "context": [], "forwardedProps": {}}), events.append)
    token = orchestrator._native_observer.set(adapter.on_agent_event)
    try:
        task = asyncio.create_task(orchestrator._consume_reply("session", Agent(), []))
        await entered.wait()
        assert not events and queue.empty()
        if ending == "cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError): await task
        else:
            release.set()
            if ending == "error":
                with pytest.raises(RuntimeError): await task
            else:
                final = await task
                streamed = "".join(e.delta for e in events if e.type == "TEXT_MESSAGE_CONTENT")
                assert streamed == final and "[已脱敏]" in final and text not in final
        if ending != "success":
            assert not events and queue.empty()
        assert all(text not in json.dumps(e.model_dump()) for e in events)
    finally:
        orchestrator._native_observer.reset(token)


async def test_legacy_replay_audits_across_cursor_pages_without_changing_evidence(tmp_path):
    journal = AGUIJournal(tmp_path / "runs.db")
    body = {"threadId": "s", "runId": "r", "messages": [{"id": "u", "role": "user", "content": "test"}],
            "state": {}, "tools": [], "context": [], "forwardedProps": {"buyerId": "b"}}
    await journal.reserve(body, "b", "owner")
    await journal.append("r", "owner", [
        {"type": "TEXT_MESSAGE_START", "messageId": "m", "role": "assistant"},
        {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "http://qd"},
        {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "rant:6333/private"},
    ])
    before, _, _ = await journal.events("r", "b", 0)
    assert all(not r["event"].get("delta") for r in before)
    await journal.append("r", "owner", [
        {"type": "TEXT_MESSAGE_END", "messageId": "m"},
        {"type": "RUN_FINISHED", "threadId": "s", "runId": "r"},
    ])
    deltas = []
    for after in (1, 2):
        page, _, _ = await journal.events("r", "b", after, limit=1)
        deltas.append(page[0]["event"]["delta"])
    assert "".join(deltas) == "[已脱敏]"
    assert "qdrant" not in json.dumps(await journal.session("s", "b"))
    async with journal._db() as db:
        rows = await (await db.execute("SELECT event_json FROM agui_events ORDER BY seq")).fetchall()
    assert "rant:6333/private" in "".join(r[0] for r in rows)
