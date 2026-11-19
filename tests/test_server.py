"""No-key and fake-provider tests: never calls a paid AI service."""
import importlib.util
import json
import os
import sqlite3
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

HERE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('chestnut_server',HERE/'server.py')
pal=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pal)

def get(base,path):
    with urlopen(base+path,timeout=5) as r:return json.load(r)

def post(base,path,body,origin='http://127.0.0.1:8765'):
    req=Request(base+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':origin},method='POST')
    try:
        with urlopen(req,timeout=5) as r:return r.status,json.load(r)
    except HTTPError as e:return e.code,json.load(e)

with tempfile.TemporaryDirectory() as td:
    pal.DB=Path(td)/'pal.sqlite3'
    pal.init()
    server=ThreadingHTTPServer(('127.0.0.1',0),pal.Handler)
    base=f'http://127.0.0.1:{server.server_port}'
    bg=threading.Thread(target=server.serve_forever,daemon=True)
    bg.start()
    try:
        os.environ.pop('PAL_MOCK_AI',None)
        os.environ.pop('OPENAI_API_KEY',None)
        os.environ.pop('GEMINI_API_KEY',None)
        h=get(base,'/api/health')
        assert h['server'] and not h['chat']['configured'] and not h['thought']['configured']
        status,body=post(base,'/api/chat',{'message':'你好'})
        assert status==503 and body['code']=='NOT_CONFIGURED',body
        with pal.connect() as c:
            assert c.execute('select count(*) from messages').fetchone()[0]==0
        print('PASS no-key status / no false saved reply')
        os.environ['PAL_MOCK_AI']='1'
        assert get(base,'/api/health')['mock'] is True
        for message in ['我喜欢画画','还记得我刚才说了什么吗']:
            status,body=post(base,'/api/chat',{'message':message})
            assert status==200 and body['source']=='mock' and body['reply'],body
        reloaded=get(base,'/api/state')
        assert len(reloaded['history'])==4 and reloaded['history'][0]['text']=='我喜欢画画',reloaded
        with pal.connect() as c:
            assert c.execute('select count(*) from memories').fetchone()[0]>=1
            assert c.execute('select count(*) from usage where kind="chat"').fetchone()[0]==2
            s=pal.get_state(c);s['next_thought']=0;pal.put_state(c,s)
        # Time window may be at night on the testing machine, so no forced thought call.
        os.environ['DAILY_CHAT_LIMIT']='2'
        status,body=post(base,'/api/chat',{'message':'第三条'})
        assert status==429 and body['code']=='DAILY_LIMIT',body
        badstatus,badbody=post(base,'/api/chat',{'message':'攻击'},'http://example.com')
        assert badstatus==403
        print('PASS mock API reply / persisted history and memory / usage / daily limit / origin block')
        with pal.connect() as c:
            journal=c.execute('select count(*) from journal').fetchone()[0]
        pal.init() # Like app restart: existing DB must remain intact.
        assert len(get(base,'/api/state')['history'])==4
        print('PASS database survives server re-initialization')
    finally:
        server.shutdown();server.server_close()
        os.environ.pop('PAL_MOCK_AI',None)
        os.environ.pop('DAILY_CHAT_LIMIT',None)
