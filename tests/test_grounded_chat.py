"""v5.4: schema, true/future boundary, stage removal, persistence and real chat round trip (fake model)."""
import os
import json
import tempfile
import importlib.util
import threading
import time
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

spec=importlib.util.spec_from_file_location('pal',Path(__file__).resolve().parent.parent/'server.py')
pal=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pal)
assert pal.CANON['employment'].find('小书店')>=0
assert pal.parse_chat_response('{"reply":"（天线耷拉）我在小书店兼职。","emotion":"curious","gesture":"nod"}')==('我在小书店兼职。','curious','nod')
assert pal.parse_chat_response('{"reply":"我还没想过。","emotion":"INVALID","gesture":"laser"}')[1:]==('neutral','none')

array_reply='[{"reply":"番茄炒蛋。","emotion":"proud","gesture":"tilt"}]'
assert pal.parse_chat_response(array_reply)==('番茄炒蛋。','proud','tilt')
assert pal.display_message({'role':'assistant','text':array_reply})['text']=='番茄炒蛋。'
assert pal.display_message({'role':'user','text':array_reply})['text']==array_reply
try:
    pal.parse_chat_response('[{"reply":"截断了"')
except pal.AIError:
    pass
else:
    raise AssertionError('Incomplete JSON must not become chat text')

with tempfile.TemporaryDirectory() as tmp:
    pal.DB=Path(tmp)/'chestnut.sqlite3'
    pal.init()
    with pal.connect() as c:
        pal.memorize(c,'story','天线曾收到一段信号',3)
        c.execute('INSERT INTO messages(at,role,text) VALUES(?,?,?)',(1,'assistant','（天线弯成问号）在气态行星上开工。'))
        c.execute('INSERT INTO messages(at,role,text) VALUES(?,?,?)',(2,'user','那你有工作吗？'))
        pal.journal(c,'idea','明天想练习做汤')
        pal.journal(c,'experience','昨晚做了蛋炒饭')
        pal.memorize(c,'user','用户喜欢红茶',4)
        context=pal.context(c,pal.get_state(c),'有工作吗')
        assert '气态行星上开工' not in context and '小书店兼职' in context
        facts=json.loads(context)
        assert facts['想法与计划']==['明天想练习做汤']
        assert facts['已记录的近期经历']==['昨晚做了蛋炒饭']
        assert facts['相关经历']==['天线曾收到一段信号']
        assert facts['用户相关记忆']==['用户喜欢红茶']
        assert facts['本次聊天']==[]
        assert facts['较早的聊天（仅供接续旧话题）']==[{'role':'user','text':'那你有工作吗？'}]
        c.execute('INSERT INTO messages(at,role,text) VALUES(?,?,?)',
                  (int(time.time()),'user','今天喝到蜜桃抹茶了'))
        resumed=json.loads(pal.context(c,pal.get_state(c),'味道不错'))
        assert resumed['本次聊天']==[{'role':'user','text':'今天喝到蜜桃抹茶了'}]
        assert resumed['较早的聊天（仅供接续旧话题）']==facts['较早的聊天（仅供接续旧话题）']
    orig=pal.request_ai
    calls=[]
    def fake(which,system,prompt,max_tokens,kind='chat'):
        assert kind=='chat'; assert '小书店' in prompt
        calls.append(prompt)
        if '你有工作吗' in prompt.split('用户刚说：')[-1]:
            reply='我在小书店兼职。具体工资嘛，暂时还不想聊。'
        else:
            reply='找了这么久还没有结果，确实很磨人。你担心的不只是收入，还有一直没法独立的感觉吧。'
        return json.dumps({'reply':'（天线耷拉）'+reply, 'emotion':'sad','gesture':'look_up'},ensure_ascii=False),{},'FAKE'
    pal.request_ai=fake
    os.environ['PAL_MOCK_AI']='1'
    server=ThreadingHTTPServer(('127.0.0.1',0),pal.Handler)
    bg=threading.Thread(target=server.serve_forever,daemon=True);bg.start()
    try:
        base=f'http://127.0.0.1:{server.server_port}'
        for msg in ['你有工作吗？','我找了一年工作，还是没收入，真的烦恼。']:
            req=Request(base+'/api/chat',method='POST',data=json.dumps({'message':msg}).encode(),headers={'Content-Type':'application/json'})
            with urlopen(req,timeout=5) as resp:obj=json.load(resp)
            assert obj['emotion']=='sad' and obj['gesture']=='look_up'
            assert '（天线' not in obj['reply']
        with pal.connect() as c:
            rows=c.execute('SELECT role,text FROM messages ORDER BY id DESC LIMIT 4').fetchall()
            assert sum('天线耷拉' in r['text'] for r in rows)==0
            state=pal.get_state(c);assert state['emotion']=='sad' and state['chat_gesture']=='look_up'
        with urlopen(base+'/api/state',timeout=5) as r:state=json.load(r)
        assert state['capabilities']['version']=='5.4'
        print('PASS canon / unknown facts / stage-free JSON reply / emotional event / stable SQLite')
    finally:
        server.shutdown();server.server_close();pal.request_ai=orig
        os.environ.pop('PAL_MOCK_AI',None)
