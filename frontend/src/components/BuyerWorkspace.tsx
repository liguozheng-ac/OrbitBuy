import { t, tValue } from "../i18n/index";
import { useCallback, useEffect, useRef, useState } from "react";
import Icon from "./Icon";
import Modal from "./Modal";
import "./buyerWorkspace.css";

type PersonalSkill = { id: string; version: string; title: string; description: string; body: string };
type Preference = { memory_id?: string; version?: number; source_kind?: string; source_ref?: string; kind: "like" | "dislike"; statement: string };
export type WorkspaceRequest = (path: string, method?: string, body?: Record<string, unknown>) => Promise<Record<string, unknown>>;
type Props = { mode: "skills" | "preferences"; busy: boolean; request: WorkspaceRequest; onSkillsChanged: () => Promise<void> };

export default function BuyerWorkspace({ mode, busy, request, onSkillsChanged }: Props) {
  const [skillEditorOpen, setSkillEditorOpen] = useState(false);
  const [skills, setSkills] = useState<PersonalSkill[]>([]);
  const [editingMemory, setEditingMemory] = useState<Preference | null>(null);
  const [preferences, setPreferences] = useState<Preference[]>([]);
  const [selected, setSelected] = useState<PersonalSkill | null>(null);
  const [title, setTitle] = useState(""), [description, setDescription] = useState(""), [body, setBody] = useState("");
  const [original, setOriginal] = useState<string | null>(null);
  const [kind, setKind] = useState<Preference["kind"]>("like"), [statement, setStatement] = useState("");
  const [loading, setLoading] = useState(true), [saving, setSaving] = useState(false);
  const [error, setError] = useState(""), [notice, setNotice] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);
  const [memoryHistory,setMemoryHistory] = useState<Record<string, { action: string; version: number; source_kind: string; occurred_at: string }[]>>({});
  const revision = useRef(0);
  const refresh = useCallback(async () => {
    const current = ++revision.current;
    setLoading(true); setError("");
    try {
      const data = await request(mode === "skills" ? "/my-skills" : "/preferences");
      if (current !== revision.current) return;
      if (mode === "skills") {
        if (!Array.isArray(data.skills)) throw new Error("Skill 列表格式无效");
        setSkills(data.skills as PersonalSkill[]);
      } else {
        if (!Array.isArray(data.preferences)) throw new Error("偏好列表格式无效");
        setPreferences(data.preferences as Preference[]);
      }
    } catch (e) { if (current === revision.current) setError(e instanceof Error ? e.message : "加载失败，请重试"); }
    finally { if (current === revision.current) setLoading(false); }
  }, [mode, request]);
  useEffect(() => { void refresh(); return () => { revision.current++; }; }, [refresh, busy]);
  const editSkill = (skill: PersonalSkill | null) => {
    setSkillEditorOpen(true);
    setSelected(skill); setTitle(skill?.title ?? ""); setDescription(skill?.description ?? "");
    setBody(skill?.body ?? ""); setNotice(""); setDeleting(null);
  };
  const editPreference = (preference: Preference | null) => {
    setEditingMemory(preference);
    setOriginal(preference?.statement ?? null); setStatement(preference?.statement ?? "");
    setKind(preference?.kind ?? "like"); setNotice(""); setDeleting(null);
  };
  const mutate = async (operation: () => Promise<unknown>, message: string, reset: () => void) => {
    if (saving || busy) return;
    setSaving(true); setError(""); setNotice("");
    try {
      await operation(); reset(); setNotice(message);
      await refresh();
      if (mode === "skills") await onSkillsChanged();
    } catch (e) { setError(e instanceof Error ? e.message : "未能保存，请重试。你的输入已保留。"); }
    finally { setSaving(false); }
  };
  const disabled = busy || saving || loading;
  const editor = <div className="workspace-editor">
        <div className="workspace-section-title"><h2>{tValue(mode === "skills" ? (selected ? "编辑 Skill" : "写一份新 Skill") : (original ? "修改偏好" : "添加一条长期偏好"))}</h2>
          <span>{t("仅用于你的选购")}</span></div>
        {mode === "skills" && error && <div role="alert" className="workspace-error">{tValue(error)}</div>}
        <form onSubmit={e => {
          e.preventDefault();
          if (mode === "skills") void mutate(
            () => request(selected ? "/my-skills/" + encodeURIComponent(selected.id) : "/my-skills", selected ? "PUT" : "POST",
              { title, description, body, ...(selected ? { expected_version: selected.version } : {}) }),
            "Skill 已保存。回到选购，输入 / 就能使用。", () => { editSkill(null); setSkillEditorOpen(false); });
          else void mutate(() => request("/preferences", "POST", { kind, statement, ...(original ? { previous_statement: original, memory_id: editingMemory?.memory_id, expected_version: editingMemory?.version } : {}) }),
            "偏好已保存，下一轮和新会话都会读取。", () => editPreference(null));
        }}>
          <fieldset disabled={disabled}>
            {mode === "skills" ? <>
              <label htmlFor="personal-skill-title">{t("名称")}<input id="personal-skill-title" required maxLength={120} value={title} onChange={e => setTitle(e.target.value)} placeholder={t("例如：我的轻装出行方案")} /></label>
              <label htmlFor="personal-skill-description">{t("什么时候使用")}<input id="personal-skill-description" required maxLength={400} value={description} onChange={e => setDescription(e.target.value)} placeholder={t("例如：周末出游，需要按重量和预算挑装备时")} /></label>
              <label htmlFor="personal-skill-body">{t("方法与步骤")}<textarea id="personal-skill-body" required maxLength={12000} rows={12} value={body} onChange={e => setBody(e.target.value)}
                placeholder={tValue(t("1. 先确认行程天数、预算和目的地。\n2. 按重量、容量、材质比较候选。\n3. 信息不确定时先询问，不猜商品参数。"))} /></label>
              <p className="workspace-help">{t("支持 Markdown。写清步骤、约束和期望的回答形式，用到时才读取全文。")}</p>
            </> : <>
              <label htmlFor="preference-kind">{t("偏好类型")}<select id="preference-kind" value={kind} onChange={e => setKind(e.target.value as Preference["kind"])}>
                <option value="like">{t("喜欢 · 希望优先考虑")}</option><option value="dislike">{t("避免 · 不想要的东西")}</option>
              </select></label>
              <label htmlFor="preference-statement">{t("记住这件事")}<textarea id="preference-statement" required maxLength={500} rows={5} value={statement} onChange={e => setStatement(e.target.value)} placeholder={t("例如：喜欢轻便、小众设计的商品")} /></label>
              <p className="workspace-help">{t("系统会先提炼稳定偏好、去除无关内容，再保存为独立记忆并建立语义索引。保存后请核对左侧实际记住的内容；临时需求请直接在对话中提出。")}</p>
              <details className="workspace-example"><summary>{t("在对话中管理偏好")}</summary><p>{t("“把喜欢黑色改成喜欢蓝色，以后都按这个偏好。”")}<br />{t("“以后不用避开真皮了，删除这条偏好。”")}</p></details>
            </>}
            <div className="workspace-form-footer"><span>{tValue(mode === "skills" ? body.length + " / 12000" : statement.length + " / 500")}</span>
              <button className="workspace-save" type="submit" disabled={disabled || (mode === "skills" ? !title.trim() || !description.trim() || !body.trim() : !statement.trim())}>
                {tValue(saving ? t("正在保存…") : mode === "skills" ? t("保存 Skill") : t("保存偏好"))}<Icon name="arrow" /></button></div>
          </fieldset>
        </form>
      </div>;
  return <section className={"buyer-workspace " + (mode === "preferences" ? "preferences-workspace" : "skills-workspace")} aria-label={tValue(mode === "skills" ? t("我的 Skill") : t("长期偏好"))}>
    {mode === "skills" ? <header className="skill-library-header"><div><h2>{t("我的方法库 ")}<span>{tValue(skills.length)}</span></h2><p>{t("保存你的选购方法，在对话中输入 / 随时调用。")}</p></div><button type="button" className="skill-create" disabled={disabled} onClick={() => { if (selected) editSkill(null); else setSkillEditorOpen(true); }}><Icon name="plus" />{t("新建 Skill")}</button></header> : <header className="workspace-heading">
      <div className="eyebrow">THE LITTLE THINGS ABOUT YOU</div>
      <h1>{t("你的偏好，")}<em>{t("一直记得。")}</em></h1>
      <p>{t("喜欢什么、想避开什么，都可以写在这里。每次开始选购，我会带上这些记忆。")}</p>
    </header>}
    {busy && <p className="workspace-note" role="status">{t("正在完成这次选购，结束后可编辑。新记忆从下一轮开始生效。")}</p>}
    {error && !(mode === "skills" && skillEditorOpen) && <div className="workspace-error" role="alert">{tValue(error)} <button type="button" onClick={() => void refresh()} disabled={saving}>{t("重新加载")}</button></div>}
    {notice && <p className="workspace-notice" role="status"><Icon name="check" />{tValue(notice)}</p>}
    <div className="workspace-grid">
      <aside className="workspace-library" aria-label={tValue(mode === "skills" ? t("已保存的 Skill") : t("已保存的偏好"))}>
        <div className="workspace-section-title"><h2>{tValue(mode === "skills" ? t("全部方法") : t("我的记忆"))}</h2>
          <button type="button" onClick={() => void refresh()} disabled={disabled}>{t("刷新")}</button></div>
        {mode === "preferences" && <button className="workspace-new" type="button" disabled={disabled}
          onClick={() => editPreference(null)}><Icon name="plus" />{t("添加偏好")}</button>}
        {loading ? <p role="status">{t("正在读取已保存的内容…")}</p> : mode === "skills" ? (
          skills.length ? skills.map(skill => <article key={skill.id} className={selected?.id === skill.id ? "workspace-item selected" : "workspace-item"}>
            <button type="button" className="workspace-item-main" disabled={disabled} onClick={() => editSkill(skill)}>
              <strong>{skill.title}</strong><span>{skill.description}</span><small>{t("个人 Skill · 修订 ")}{tValue(skill.version)}</small>
            </button>
            {deleting === skill.id ? <div className="workspace-delete">
              <span>{t("删除后将不能再调用。")}</span>
              <button type="button" disabled={disabled} onClick={() => void mutate(
                () => request("/my-skills/" + encodeURIComponent(skill.id) + "?expected_version=" + encodeURIComponent(skill.version), "DELETE"),
                "Skill 已删除，方案菜单已同步。", () => { if (selected?.id === skill.id) { editSkill(null); setSkillEditorOpen(false); } setDeleting(null); })}>{t("确认删除")}</button>
              <button type="button" onClick={() => setDeleting(null)}>{t("保留")}</button>
            </div> : <button type="button" className="workspace-delete-link" disabled={disabled} aria-label={"删除 Skill：" + skill.title} onClick={() => setDeleting(skill.id)}>{t("删除")}</button>}
          </article>) : <div className="workspace-empty"><Icon name="leaf" /><p>{t("你的第一份选购方法，")}<br />{t("点击右上角「新建 Skill」开始。")}</p></div>
        ) : preferences.length ? preferences.map(p => <article key={p.kind + p.statement} className="workspace-item">
          <span className={"preference-kind " + p.kind}>{tValue(p.kind === "like" ? t("喜欢") : t("避免"))}</span>
          <p>{p.statement}</p>
          {p.memory_id && <small>{t("第 ")}{tValue(p.version)}{t(" 版 · ")}{tValue(p.source_kind === "agent" ? t("对话确认保存") : p.source_kind === "legacy" ? t("历史偏好迁移") : t("页面保存"))}</small>}
          <div className="workspace-row-actions">
            {p.memory_id && <button type="button" disabled={disabled} onClick={() => {
              const id=p.memory_id!;
              if (memoryHistory[id]) { setMemoryHistory(current => {const next={...current};delete next[id];return next;});return; }
              void request("/preferences/"+encodeURIComponent(id)+"/history").then(data => setMemoryHistory(current => ({...current,[id]:data.events as typeof memoryHistory[string]}))).catch(() => setError("变更记录读取失败，请重试"));
            }}>{t("变更记录")}</button>}
            <button type="button" disabled={disabled} aria-label={"编辑偏好：" + p.statement} onClick={() => editPreference(p)}>{t("编辑")}</button>
            <button type="button" disabled={disabled} aria-label={"删除偏好：" + p.statement} onClick={() => void mutate(
              () => request("/preferences", "DELETE", { statement: p.statement, memory_id: p.memory_id, expected_version: p.version }), "这条偏好已删除，下一轮不再带入。", () => editPreference(null))}>{t("删除")}</button>
          </div>
          {p.memory_id && memoryHistory[p.memory_id] && <ul aria-label={t("记忆变更记录")}>{memoryHistory[p.memory_id].map((event,i) => <li key={i}>{tValue(event.action === "create" ? t("创建") : event.action === "update" ? t("修改") : t("删除"))}{t(" · 第 ")}{tValue(event.version)}{t(" 版 · ")}{tValue(new Date(event.occurred_at).toLocaleString())}</li>)}</ul>}
        </article>) : <div className="workspace-empty"><Icon name="heart" /><p>{t("这里还没有长期偏好。")}<br />{t("可以先写下一件你在意的小事。")}</p></div>}
      </aside>
      {mode === "preferences" ? editor : skillEditorOpen && <div className="skill-editor-overlay"><Modal title={tValue(selected ? t("编辑 Skill") : t("写一份新 Skill"))} onClose={() => setSkillEditorOpen(false)}>{tValue(editor)}</Modal></div>}

    </div>
  </section>;
}
