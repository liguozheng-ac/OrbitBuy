// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it } from "vitest";
import LanguageSwitcher from "../src/components/LanguageSwitcher";
import ConversationTurns from "../src/components/ConversationTurns";
import { getLocale, setLocale, t, tValue, type Locale } from "../src/i18n";
import messages from "../src/i18n/messages.json";
import { CommerceClient } from "../src/lib/commerceClient";
import { money } from "../src/components/ProductCards";

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { setLocale("zh-CN"); });

it("all catalog entries have both translations and preserve numbered placeholders", () => {
  expect(Object.keys(messages).length).toBeGreaterThan(1000);
  for (const [key, entries] of Object.entries(messages)) {
    for (const locale of ["ja-JP","en-US"] as const) {
      expect(entries[locale]?.trim(), key).toBeTruthy();
      expect(entries[locale].match(/\{\d+\}/g)?.sort() ?? [], key).toEqual(key.match(/\{\d+\}/g)?.sort() ?? []);
    }
  }
});

it("switches repeatedly, persists the locale and leaves authored messages untouched", async () => {
  const host=document.createElement('div'),root=createRoot(host);
  function Example() { return <><LanguageSwitcher /><ConversationTurns running={false} activities={[]}
    messages={[{id:'u',role:'user',content:'新的选购'},{id:'a',role:'assistant',content:'已完成'}]} /></>; }
  await act(async()=>{root.render(<Example />);});
  for(const locale of ['ja-JP','en-US','zh-CN'] as const){
    await act(async()=>{const select=host.querySelector('select')!;select.value=locale;select.dispatchEvent(new Event('change',{bubbles:true}));});
    expect(getLocale()).toBe(locale);
    expect(localStorage.getItem('globex.locale')).toBe(locale);
    expect(document.documentElement.lang).toBe(locale);
    expect(host.querySelector('.query-bubble')?.textContent).toBe('新的选购');
    expect(host.querySelector('.assistant-text')?.textContent).toBe('已完成');
    expect(host.querySelector('select')?.getAttribute('aria-label')).toBe(t('界面语言'));
  }
  await act(async()=>{root.unmount();});
});

it("forwards each selected locale while keeping CNY, buyer input and saved messages unchanged", async () => {
  const bodies:any[]=[];
  const client=new CommerceClient({url:'/commerce/ag-ui/run',fetch:async(_url,init)=>{
    const body=JSON.parse(String(init.body));bodies.push(body);
    const events=[{type:'RUN_STARTED',threadId:body.threadId,runId:body.runId},
      {type:'MESSAGES_SNAPSHOT',messages:[...body.messages,{id:'answer-'+body.runId,role:'assistant',content:'原始回复'}]},
      {type:'RUN_FINISHED',threadId:body.threadId,runId:body.runId}];
    return new Response(events.map(event=>'data: '+JSON.stringify(event)+'\n\n').join(''),{headers:{'Content-Type':'text/event-stream'}});
  }});
  for(const locale of ['ja-JP','en-US','zh-CN'] as const){
    setLocale(locale);await client.submit('原始中文问题，预算300 CNY');
    expect(bodies.at(-1).forwardedProps).toMatchObject({locale,currency:'CNY'});
    expect(bodies.at(-1).messages.at(-1).content).toBe('原始中文问题，预算300 CNY');
    expect(client.getSnapshot().messages.at(-1)?.content).toBe('原始回复');
  }
});

it("formats CNY without converting its value, supports templates and rejects unknown locale", () => {
  for(const locale of ['ja-JP','en-US','zh-CN'] as const){setLocale(locale);expect(money(129,'CNY')).toContain('129');}
  setLocale('en-US');expect(t('查看 {0} 详情',['原商品名'])).toContain('原商品名');
  expect(tValue('等待你确认')).not.toBe('等待你确认');
  setLocale('invalid' as Locale);expect(getLocale()).toBe('en-US');
});
