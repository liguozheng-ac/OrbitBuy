import { t, tValue , getLocale } from "../i18n/index";
import type { DiagnosticEvent, SkillUsage } from "../types";
import Icon from "./Icon";
export default function EventTimeline({
  events, skillUsages = [], running = false,
}: {
  events: DiagnosticEvent[];
  skillUsages?: SkillUsage[];
  running?: boolean;
}) {
  return (
    <details className="diagnostics">
      <summary>
        <Icon name="clock" />
        <span>{t("查看运行记录")}</span>
        <span className="diagnostic-count">{tValue(events.length + skillUsages.length)}</span>
      </summary>
      <p className="diagnostic-description">
        {t("展示最近的可见执行步骤与状态，不包含模型隐式推理。")}</p>
      {events.length === 0 && skillUsages.length === 0 ? (
        <p className="diagnostic-empty">
          {t("开始一次选购后，执行记录会出现在这里。")}</p>
      ) : (
        <ol>
          {skillUsages.map((usage) => <li key={`skill-${usage.toolCallId}`}>
            <div className="event-heading"><span>{tValue(usage.status === "reading" && !running ? t("方案读取未完成") : usage.status === "used" ? t("方案已读取") : usage.status === "error" ? t("方案读取失败") : t("正在读取方案"))}</span></div>
            <p className="skill-event-name">{usage.title || t("选购方案")}{tValue(usage.version ? ` · ${usage.version}` : "")}</p>
            <span className="event-type">{tValue(usage.status === "used" ? usage.source === "server_preload" ? t("服务端已读取指定版本") : t("工具成功返回") : usage.status === "reading" && !running ? t("本轮已结束，未收到读取成功结果") : usage.source === "server_preload" ? t("服务端读取状态") : t("工具执行状态"))}</span>
          </li>)}
          {events.slice(-60).map((event) => (
            <li key={event.id}>
              <div className="event-heading">
                <span>{tValue(event.label || event.type)}</span>
                {event.timestamp !== null && <time>
                  {tValue(new Date(event.timestamp).toLocaleTimeString(getLocale(), {
    hour12: false,
}))}
                </time>}
              </div>
              <span className="event-type">{tValue(event.type)}</span>
              {event.detail && <p>{tValue(event.detail)}</p>}
            </li>
          ))}
        </ol>
      )}
    </details>
  );
}
