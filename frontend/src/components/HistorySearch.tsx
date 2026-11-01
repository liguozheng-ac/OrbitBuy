import { t, tValue , getLocale } from "../i18n/index";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { SessionSummary } from "../types";
import Icon from "./Icon";
import Modal from "./Modal";
import "./historySearch.css";

function updatedLabel(timestamp: number) {
  const date = new Date(timestamp);
  if (!Number.isFinite(date.getTime())) return "";
  return date.toDateString() === new Date().toDateString()
    ? date.toLocaleTimeString(getLocale(), { hour: "2-digit", minute: "2-digit", hour12: false })
    : date.toLocaleDateString(getLocale(), { month: "short", day: "numeric" });
}

export default function HistorySearch({ history, currentSessionId, busy, error, onOpen, onClose }: {
  history: SessionSummary[];
  currentSessionId: string;
  busy: boolean;
  error?: string | null;
  onOpen: (id: string) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [activeId, setActiveId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const listId = useId();
  const matches = useMemo(() => {
    const value = query.trim().toLocaleLowerCase();
    return history.filter(item => `${item.title}\n${item.id}`.toLocaleLowerCase().includes(value));
  }, [history, query]);
  // 用稳定 ID 保留光标；查询或服务端列表变化后不沿用失效的下标。
  const activeIndex = Math.max(0, matches.findIndex(item => item.id === activeId));
  const active = matches[activeIndex];
  useEffect(() => {
    listRef.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
  }, [active?.id]);
  const open = (id: string) => { if (!busy) onOpen(id); };

  return <Modal title={t("搜索选购记录")} onClose={onClose} initialFocusRef={inputRef}>
    <div className="conversation-search">
      <div className="conversation-search-input">
        <Icon name="search" />
        <input ref={inputRef} role="combobox" aria-label={t("搜索选购标题或会话 ID")}
          aria-autocomplete="list" aria-expanded="true" aria-controls={listId}
          aria-activedescendant={active ? `${listId}-${activeIndex}` : undefined}
          placeholder={t("搜索选购标题或会话 ID…")} value={query}
          onChange={event => { setQuery(event.target.value); setActiveId(null); }}
          onKeyDown={event => {
            if (event.nativeEvent.isComposing || event.keyCode === 229) return;
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault();
              if (matches.length) setActiveId(matches[(activeIndex + (event.key === "ArrowDown" ? 1 : -1) + matches.length) % matches.length].id);
            } else if (event.key === "Enter") {
              event.preventDefault();
              if (active) open(active.id);
            }
          }} />
        {query && <button className="conversation-search-clear" aria-label={t("清除搜索")} onClick={() => {
          setQuery(""); setActiveId(null); inputRef.current?.focus();
        }}><Icon name="close" /></button>}
      </div>
      <div className="conversation-search-meta">
        <span>{tValue(query.trim() ? t("搜索结果") : t("最近选购"))}<small>{tValue(matches.length)}{t(" 条")}</small></span>
        <span className="conversation-search-keys"><kbd>↑</kbd><kbd>↓</kbd>{t("选择")}<kbd>Enter</kbd>{t("打开")}</span>
      </div>
      {error && <p className="conversation-search-notice" role="status">{tValue(error)}</p>}
      {busy && <p className="conversation-search-notice" role="status">{t("当前选购正在处理中，完成或停止后可打开其他记录。")}</p>}
      <div ref={listRef} id={listId} role="listbox" aria-label={t("选购记录")} className="conversation-search-results">
        {matches.map((item, index) => <button key={item.id} id={`${listId}-${index}`} role="option" tabIndex={-1}
          aria-selected={index === activeIndex} aria-disabled={busy} className="conversation-search-result"
          onMouseEnter={() => setActiveId(item.id)} onMouseDown={event => event.preventDefault()} onClick={() => open(item.id)}>
          <Icon name="chat" />
          <span className="conversation-search-title" title={item.title}>{item.title}</span>
          {item.id === currentSessionId && <span className="conversation-search-current">{t("当前")}</span>}
          <span className="conversation-search-id" title={tValue(item.id)}>{tValue(item.id)}</span>
          <time dateTime={Number.isFinite(new Date(item.updatedAt).getTime()) ? new Date(item.updatedAt).toISOString() : undefined}>{tValue(updatedLabel(item.updatedAt))}</time>
        </button>)}
      </div>
      {!matches.length && <div className="conversation-search-empty" role="status"><Icon name="search" />
        <strong>{tValue(query.trim() ? t("没有找到匹配记录") : t("还没有选购记录"))}</strong>
        <p>{tValue(query.trim() ? t("试试其他标题关键词，或输入会话 ID。") : t("开始一次选购后，可以在这里快速找回。"))}</p>
      </div>}
      <div className="conversation-search-footer"><span>{t("按标题或会话 ID 查找已加载记录")}</span><span><kbd>Esc</kbd>{t("关闭")}</span></div>
    </div>
  </Modal>;
}
