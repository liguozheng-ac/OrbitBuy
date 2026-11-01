import {expect,it} from 'vitest';
import {CommerceClient} from '../src/lib/commerceClient';

function storage() {
  const entries=new Map<string,string>();
  return {getItem:(key:string)=>entries.get(key)??null,setItem:(key:string,value:string)=>{entries.set(key,value);}};
}
const summary={id:'old',title:'已有选购',updatedAt:1};
const cached={...summary,messages:[{id:'u',role:'user',content:'旧正文'}],products:[],searchCompleted:false};

it('首页模式忽略旧会话指针和最新表单，只加载最近目录；点击历史才恢复正文',async()=>{
  const store=storage();store.setItem('globex.buyer','b');store.setItem('globex.agui.active-session','old');
  store.setItem('globex.agui.sessions.v1',JSON.stringify([cached]));
  const paths:string[]=[];
  const client=new CommerceClient({url:'/commerce/ag-ui/run',buyerId:'b',storage:store,startAtHome:true,fetch:async url=>{
    paths.push(String(url));
    if(String(url).includes('/sessions?')) return Response.json({sessions:[summary]});
    if(String(url).includes('/shopping-forms?')) return Response.json({form:{session_id:'old',created_at:9999}});
    return Response.json({run:{runId:'r',threadId:'old',status:'completed',state:{}},messages:cached.messages});
  }});
  await client.initialize();
  expect(client.getSnapshot().messages).toEqual([]);
  expect(client.getSnapshot().shoppingForm).toBeFalsy();
  expect(client.getSnapshot().sessionId).not.toBe('old');
  expect(client.getSnapshot().history[0].id).toBe('old');
  expect(paths.some(path=>path.includes('/sessions/old'))).toBe(false);
  client.setSession('old');await Promise.resolve();await Promise.resolve();
  expect(client.getSnapshot().messages[0].content).toBe('旧正文');
});

it('删除当前记录后回到空白首页，目录刷新和再次启动均不复活本地缓存',async()=>{
  const store=storage();store.setItem('globex.buyer','b');store.setItem('globex.agui.sessions.v1',JSON.stringify([cached]));
  let deleted=false;
  const calls:string[]=[];
  const fetch=async (url:string,init?:RequestInit)=>{
    calls.push(`${init?.method??'GET'} ${url}`);
    if(init?.method==='DELETE'){deleted=true;return Response.json({deleted:true});}
    if(String(url).includes('/sessions?'))return Response.json({sessions:deleted?[]:[summary],deletedSessionIds:deleted?['old']:[]});
    return Response.json({run:{runId:'r',threadId:'old',status:'completed',state:{}},messages:cached.messages});
  };
  const client=new CommerceClient({url:'/commerce/ag-ui/run',buyerId:'b',storage:store,startAtHome:true,fetch});
  await client.initialize();client.setSession('old');
  await client.deleteSession('old');await client.refreshHistory();
  expect(client.getSnapshot().history).toEqual([]);expect(client.getSnapshot().messages).toEqual([]);
  expect(calls.some(path=>path.startsWith('DELETE ')&&path.includes('buyer_id=b'))).toBe(true);
  store.setItem('globex.agui.sessions.v1',JSON.stringify([cached])); // 模拟其它浏览器遗留的旧缓存。
  const restarted=new CommerceClient({url:'/commerce/ag-ui/run',buyerId:'b',storage:store,startAtHome:true,fetch});
  await restarted.initialize();expect(restarted.getSnapshot().history).toEqual([]);
});

it('删除接口失败时保留缓存、历史和当前正文',async()=>{
  const store=storage();store.setItem('globex.buyer','b');store.setItem('globex.agui.active-session','old');
  store.setItem('globex.agui.sessions.v1',JSON.stringify([cached]));
  const client=new CommerceClient({url:'/commerce/ag-ui/run',buyerId:'b',storage:store,fetch:async()=>Response.json({}, {status:503})});
  await expect(client.deleteSession('old')).rejects.toThrow('删除失败');
  expect(client.getSnapshot().history).toHaveLength(1);expect(client.getSnapshot().messages[0].content).toBe('旧正文');
  expect(JSON.parse(store.getItem('globex.agui.sessions.v1')!)).toHaveLength(1);
});
