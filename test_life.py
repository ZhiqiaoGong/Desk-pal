"""No paid calls: validates real-time schedule / AI planning / persistence and caps."""
import importlib.util, json, os, tempfile, threading
from pathlib import Path
from datetime import datetime as TrueDateTime
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('palv51',HERE/'server.py')
pal=importlib.util.module_from_spec(sp);sp.loader.exec_module(pal)
class Saturday(TrueDateTime):
    @classmethod
    def now(cls, tz=None):return cls(2026,10,24,15,0,0)

def req(base, route, body=None):
    if body is None:
        with urlopen(base+route,timeout=10) as r:return json.load(r)
    data=json.dumps(body).encode()
    request=Request(base+route,data=data,headers={'Content-Type':'application/json','Origin':base},method='POST')
    with urlopen(request,timeout=10) as r:return json.load(r)

with tempfile.TemporaryDirectory() as td:
    pal.DB=Path(td)/'pal.sqlite3'
    os.environ['PAL_MOCK_AI']='1'
    with patch.object(pal,'datetime',Saturday):
        pal.init()
        with pal.connect() as c:
            s=pal.get_state(c);s.update({'date':'2026-10-20','interest':'练习画街角的小速写','goal':'画完街角速写的一角',
                'goal_step':2,'goal_notes':['画好了街景轮廓'],'next_thought':0,'last_event':int(pal.time.time()),'emotion':'neutral'})
            pal.put_state(c,s)
            current=pal.refresh(c)
            assert current['goal_step']==2 and current['interest']=='练习画街角的小速写',current
            print('PASS across dates: unfinished goal remains unfinished')
        server=ThreadingHTTPServer(('127.0.0.1',0),pal.Handler)
        base='http://127.0.0.1:'+str(server.server_port)
        bg=threading.Thread(target=server.serve_forever,daemon=True);bg.start()
        try:
            thought=req(base,'/api/think',{})
            assert 'reply' in thought and thought['state']['activity']=='hobby',thought
            assert thought['state']['goal_step']==3,thought
            assert thought['state']['emotion']=='curious',thought
            state=req(base,'/api/state')['state']
            assert state['interest']=='练习画街角的小速写' and state['goal_step']==3,state
            assert state['goal_notes'][-1]=='记录了一条新的观察',state
            assert req(base,'/api/think',{}).get('reason')=='not_time'
            with pal.connect() as c:
                assert pal.get_state(c)['goal_step']==3
                assert pal.attempts_today(c,'thought')==1
            print('PASS autonomous mock AI: persists activity, emotion, objective, event, cooldown')
            # Mandatory work overrides flexible plan but doesn't erase it.
            class Weekday(TrueDateTime):
                @classmethod
                def now(cls,tz=None):return cls(2026,10,21,14,0,0)
            with patch.object(pal,'datetime',Weekday):
                with pal.connect() as c:
                    s=pal.get_state(c);s['date']='2026-10-21';pal.put_state(c,s)
                    assert pal.refresh(c)['activity']=='work'
            print('PASS work skeleton remains in place')
        finally:
            server.shutdown();server.server_close()
    os.environ.pop('PAL_MOCK_AI',None)
