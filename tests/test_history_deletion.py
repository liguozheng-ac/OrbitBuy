"""选购历史删除：实际 SQLite、HTTP 权限、重启与运行互斥。"""
import pytest
import httpx
from app.infrastructure.ag_ui_journal import AGUIJournal, JournalConflict, JournalForbidden, JournalNotFound
from app.presentation.ag_ui_runtime import AGUIRuntime
from tests.test_ag_ui_journal import body, application, ControlledOrchestrator, wait_status


async def finished(journal, session='s1', run='r1', buyer='b1'):
    await journal.reserve(body(run=run,session=session,buyer=buyer),buyer,'owner')
    await journal.end_owned(run,'owner')


async def test_delete_is_owned_persistent_and_idempotent_without_erasing_audit(tmp_path):
    path=tmp_path/'runs.db'; journal=AGUIJournal(path)
    await finished(journal); await finished(journal,'s2','r2')
    with pytest.raises(JournalForbidden): await journal.delete_session('s1','other')
    await journal.delete_session('s1','b1'); await journal.delete_session('s1','b1')
    reopened=AGUIJournal(path)
    assert [row['id'] for row in await reopened.sessions('b1')]==['s2']
    assert await reopened.deleted_sessions('b1')==['s1']
    assert await reopened.deleted_sessions('other')==[]
    with pytest.raises(JournalNotFound): await reopened.session('s1','b1')
    with pytest.raises(JournalConflict,match='已删除'):
        await reopened.reserve(body(run='new'),'b1','owner')
    assert (await reopened.run('r1','b1'))['status']!='running'  # 审计与业务引用保留。


async def test_running_and_pending_approval_cannot_be_deleted(tmp_path):
    journal=AGUIJournal(tmp_path/'runs.db')
    await journal.reserve(body(),'b1','owner')
    with pytest.raises(JournalConflict,match='执行'): await journal.delete_session('s1','b1')
    await journal.end_owned('r1','owner')
    async with journal._db(True) as db:
        await db.execute('UPDATE agui_sessions SET state_json=? WHERE session_id=?',('{"toolApprovals":[{"id":"pending"}]}','s1'))
    with pytest.raises(JournalConflict,match='确认'): await journal.delete_session('s1','b1')
    assert await journal.deleted_sessions('b1')==[]


async def test_linked_automation_requires_archive_so_resume_cannot_target_deleted_history(tmp_path):
    journal=AGUIJournal(tmp_path/'runs.db'); await finished(journal)
    async with journal._db(True) as db:
        await db.execute('CREATE TABLE automations (session_id TEXT,status TEXT)')
        await db.execute("INSERT INTO automations VALUES ('s1','active')")
    with pytest.raises(JournalConflict,match='自动化'): await journal.delete_session('s1','b1')
    async with journal._db(True) as db: await db.execute("UPDATE automations SET status='paused'")
    with pytest.raises(JournalConflict,match='自动化'): await journal.delete_session('s1','b1')
    async with journal._db(True) as db: await db.execute("UPDATE automations SET status='archived'")
    await journal.delete_session('s1','b1')
    assert await journal.sessions('b1')==[]


async def test_http_deletion_checks_buyer_and_survives_refresh(tmp_path):
    journal=AGUIJournal(tmp_path/'runs.db'); await finished(journal)
    runtime=AGUIRuntime(journal,ControlledOrchestrator())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(runtime)),base_url='http://test') as client:
        assert (await client.delete('/commerce/ag-ui/sessions/s1?buyer_id=other')).status_code==403
        assert (await client.delete('/commerce/ag-ui/sessions/missing?buyer_id=b1')).status_code==404
        assert (await client.delete('/commerce/ag-ui/sessions/s1?buyer_id=b1')).status_code==200
        assert (await client.delete('/commerce/ag-ui/sessions/s1?buyer_id=b1')).status_code==200
        data=(await client.get('/commerce/ag-ui/sessions?buyer_id=b1')).json()
        assert data=={'sessions':[],'deletedSessionIds':['s1']}
        assert (await client.get('/commerce/ag-ui/sessions/s1?buyer_id=b1')).status_code==404
