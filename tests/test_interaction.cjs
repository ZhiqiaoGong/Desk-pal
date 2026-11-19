/* Tiny event-level smoke test, no browser or third-party packages required. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(__dirname+'/../index.html','utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element {
 constructor(id){this.id=id;this.style={};this.value='';this.disabled=false;this.children=[];this.handlers={};this.classList={values:new Set(id==='chat'||id==='bubble'?['hidden']:[]),contains(x){return this.values.has(x)},add(x){this.values.add(x)},remove(x){this.values.delete(x)}};this.textContent='';this.scrollHeight=0;this.scrollTop=0;}
 setAttribute(name,value){this[name]=value;}
 getBoundingClientRect(){return {top:0,bottom:20};}
 addEventListener(t,cb){this.handlers[t]=cb;}
 appendChild(el){this.children.push(el);this.scrollHeight=this.children.length;}
 replaceChildren(){this.children=[];}
 focus(){}
 requestSubmit(){return get('form').fire('submit')}
 fire(t,props={}){assert(this.handlers[t],`missing ${t} on ${this.id}`);return this.handlers[t]({preventDefault(){},stopPropagation(){},...props});}
 getContext(){return {imageSmoothingEnabled:false,clearRect(){},fillRect(){},beginPath(){},moveTo(){},lineTo(){},quadraticCurveTo(){},stroke(){},save(){},translate(){},rotate(angle){rotations.push(angle)},restore(){}};}
}
const rotations=[];
const els = new Map();const get=id=>{if(!els.has(id))els.set(id,new Element(id));return els.get(id)};
const doc={getElementById:get,createElement:(tag)=>new Element(tag),addEventListener(){},hidden:false};
const data = new Map();const localStorage={getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)};
const sandbox={document:doc,location:{protocol:'file:',hostname:''},localStorage,Intl,Date,Math,console,JSON,
 setTimeout(){return 1},clearTimeout(){},setInterval(){return 1},requestAnimationFrame(){},AbortSignal};
vm.runInNewContext(script.replace('start();', "globalThis.testDraw=()=>draw(0);globalThis.testWake=()=>{demoUntil=0;state.activity='sleep';draw(0)};start();"),sandbox,{timeout:5000});
(async()=>{
 get('avatar').fire('click');assert(!get('chat').classList.values.has('hidden'));
 get('message').value='还没写完的消息';
 get('history').clientHeight=200;
 const messagesBefore=get('history').children.slice();
 get('chat-size').fire('click');
 assert(get('chat').classList.contains('expanded'));
 assert.equal(get('chat-size')['aria-pressed'],'true');
 assert.equal(get('message').value,'还没写完的消息');
 assert.deepEqual(get('history').children,messagesBefore);
 get('chat-size').fire('click');
 assert(!get('chat').classList.contains('expanded'));
 assert.equal(get('chat-size')['aria-pressed'],'false');
 assert.equal(get('message').value,'还没写完的消息');
 get('message').value='你好';await get('form').fire('submit');
 assert(get('history').children.some(x=>x.textContent==='你好'));
 assert(get('history').children.length>=3);
 assert(get('send').disabled===false);
 get('message').value='演示做饭';await get('form').fire('submit');
 assert(get('history').children.at(-1).textContent.includes('演示'));
 get('message').value='演示睡觉';await get('form').fire('submit');
 sandbox.testDraw();
 assert(rotations.includes(-Math.PI/2),'Sleep demo must render while chat is open');
 rotations.length=0;
 sandbox.testWake();
 assert.equal(rotations.length,0,'Ordinary sleeping character wakes for chat');
 get('message').value='安静一会儿';await get('form').fire('submit');
 assert(get('history').children.at(-1).textContent.includes('安静'));
 get('close').fire('click');assert(get('chat').classList.values.has('hidden'));
 get('avatar').fire('keydown',{key:'Enter'});assert(!get('chat').classList.values.has('hidden'));
 console.log('PASS: chat opens, form submits, offline response, action demo, quiet command, Enter opens chat');
})().catch(err=>{console.error(err);process.exitCode=1});
