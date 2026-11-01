import { tValue } from "../i18n/index";
import { useEffect, useState } from "react";
import type { WorkspaceRequest } from "./BuyerWorkspace";

type Status = { status?: string };

export default function CapabilityNotice({ request }: { request: WorkspaceRequest }) {
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    void request("/capabilities").then(data => {
      if (!active) return;
      const memory = data.semantic_memory as Status | undefined;
      const search = data.product_search as Status | undefined;
      const messages: string[] = [];
      if (search?.status === "degraded") messages.push("商品搜索当前使用关键词检索");
      if (memory?.status === "unavailable") messages.push("长期偏好记忆暂不可用，仍可直接在对话中说明本次要求");
      setNotice(messages.join("；"));
    }).catch(() => { /* 独立状态提示失败不阻断购物。 */ });
    return () => { active = false; };
  }, [request]);
  return notice ? <p role="status" className="capability-notice">{tValue(notice)}。</p> : null;
}
