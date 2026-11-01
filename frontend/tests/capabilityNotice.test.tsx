// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import CapabilityNotice from "../src/components/CapabilityNotice";

it("explains unavailable memory while keeping shopping usable", async () => {
  (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  const host = document.createElement("div"), root = createRoot(host);
  const request = vi.fn().mockResolvedValue({ semantic_memory: { status: "unavailable" }, product_search: { status: "degraded" } });
  await act(async () => { root.render(<CapabilityNotice request={request} />); });
  expect(host.textContent).toContain("关键词检索");
  expect(host.textContent).toContain("长期偏好记忆暂不可用");
  await act(async () => { root.unmount(); });
});

it("shows no warning for verified startup capabilities", async () => {
  const host = document.createElement("div"), root = createRoot(host);
  await act(async () => { root.render(<CapabilityNotice request={async () => ({ semantic_memory: { status: "ready" }, product_search: { status: "ready" } })} />); });
  expect(host.textContent).toBe("");
  await act(async () => { root.unmount(); });
});
