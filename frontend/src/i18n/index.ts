import { useSyncExternalStore } from "react";
import messages from "./messages.json";

export const LOCALES = ["zh-CN", "ja-JP", "en-US"] as const;
export type Locale = typeof LOCALES[number];
const STORAGE_KEY = "globex.locale";
const catalog: Record<string, Partial<Record<Locale, string>>> = messages;
const valid = (value: unknown): value is Locale => LOCALES.includes(value as Locale);
let locale: Locale = "zh-CN";
try { const saved = localStorage.getItem(STORAGE_KEY); if (valid(saved)) locale = saved; } catch { /* 无存储时仍可切换。 */ }
const listeners = new Set<() => void>();
export const getLocale = (): Locale => locale;
export function setLocale(value: Locale) {
  if (!valid(value)) return;
  try { localStorage.setItem(STORAGE_KEY, value); } catch { /* 当前页面保持生效。 */ }
  if (typeof document !== "undefined") document.documentElement.lang = value;
  if (locale === value) return;
  locale = value;
  listeners.forEach(listener => listener());
}
export function useLocale() {
  return useSyncExternalStore(listener => { listeners.add(listener); return () => { listeners.delete(listener); }; }, getLocale, () => "zh-CN" as Locale);
}

/** 源文案作为稳定 key，参数只插值一次，不翻译用户内容或改变业务数据。 */
export function t(key: string, values: readonly unknown[] = []): string {
  const translated = locale === "zh-CN" ? key : catalog[key]?.[locale] ?? key;
  return translated.replace(/\{(\d+)\}/g, (match, index: string) =>
    Number(index) < values.length ? String(values[Number(index)] ?? "") : match);
}

const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
// 某些状态文本由既有客户端/服务端组合而成；只在显式展示边界匹配完整文案。
const patterns = Object.keys(catalog).filter(key => /\{\d+\}/.test(key)
  && key.replace(/\{\d+\}/g, "").trim().length >= 4).sort((a,b) => b.replace(/\{\d+\}/g, "").length - a.replace(/\{\d+\}/g, "").length)
  .map(key => {
    const slots = [...key.matchAll(/\{(\d+)\}/g)].map(match => Number(match[1]));
    return { key, slots, pattern: new RegExp("^" + key.split(/\{\d+\}/).map(escape).join("([\\s\\S]*?)") + "$") };
  });
export function tValue<T>(value: T): T {
  if (typeof value !== "string" || locale === "zh-CN") return value;
  if (catalog[value]) return t(value) as T;
  if (value.length > 2000) return value;
  for (const item of patterns) {
    const match = item.pattern.exec(value);
    if (match) {
      const args: string[] = [];
      item.slots.forEach((slot,index) => { args[slot] = match[index+1]; });
      return t(item.key, args) as T;
    }
  }
  return value;
}

export const weekdayNames = () => locale === "zh-CN" ? ["一", "二", "三", "四", "五", "六", "日"] : Array.from({length:7}, (_, index) =>
  new Intl.DateTimeFormat(locale, { weekday:"short", timeZone:"UTC" }).format(new Date(Date.UTC(2024,0,1+index))));
