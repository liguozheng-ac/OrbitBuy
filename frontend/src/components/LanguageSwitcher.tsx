import { getLocale, setLocale, t, useLocale, type Locale } from "../i18n";

export default function LanguageSwitcher() {
  useLocale();
  return <label className="language-switcher">
    <span aria-hidden="true">◎</span>
    <select aria-label={t("界面语言")} value={getLocale()} onChange={event => setLocale(event.target.value as Locale)}>
      <option value="zh-CN">中文</option>
      <option value="ja-JP">日本語</option>
      <option value="en-US">English</option>
    </select>
  </label>;
}
