const assert=require('node:assert/strict');
const vm=require('node:vm');
const html=require('node:fs').readFileSync(__dirname+'/../index.html','utf8');
const source=html.slice(html.indexOf('const OPENINGS='),html.indexOf('function start()'));
let now=10000000;
const spoken=[],saved=[];
const context={desktopChat:false,desktopPet:true,chatOpen:false,offlineQuietUntil:0,
 window:{petPreferences:{opening:{}}},state:{activity:'read'},Date:{now:()=>now},
 NOW:()=>({getHours:()=>12}),rand:arr=>arr[0],speak:line=>spoken.push(line),
 nativeMessage:message=>saved.push(message)};
vm.createContext(context);vm.runInContext(source,context);
context.openingMurmur();assert.equal(spoken.length,1);assert.match(spoken[0],/页|书/);
context.openingMurmur();assert.equal(spoken.length,1,'rapid restart stays quiet');
for(let i=0;i<8;i++){now+=600001;context.openingMurmur();}
assert.notEqual(spoken[0],spoken[1]);assert.equal(saved.at(-1).value.recent.length,6);
context.desktopChat=true;now+=600001;context.openingMurmur();assert.equal(spoken.length,9);
console.log('PASS activity openings, cooldown, recent phrases, chat window stays quiet');
