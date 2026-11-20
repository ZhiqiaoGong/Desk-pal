"""小栗的角落 v5.4 — local-first desktop companion HTML service.

Python standard library only. API keys are read on the server, never sent to JS.
The character illustration is unchanged from v4.6; this release focuses on reliable
cloud chat, autonomous decisions, durable SQLite memories, expressive animation, and a fresh grounded persona.
"""
from __future__ import annotations

import json
import os
import random
import re
import sqlite3
import sys
import threading
import time
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parent
# v5.2 is a deliberate new beginning. Do NOT import old version-folder databases.
# All future releases can use this same stable user-owned data directory.
if sys.platform == 'darwin':
    DATA_HOME = Path.home() / 'Library' / 'Application Support' / 'ChestnutPal'
else:
    DATA_HOME = Path(os.getenv('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))) / 'ChestnutPal'
DB = Path(os.getenv('PAL_DB', str(DATA_HOME / 'chestnut.sqlite3'))).expanduser()
PORT = int(os.getenv('PORT', '8765'))
LOCK = threading.RLock()
CHAT_GATE = threading.BoundedSemaphore(1)  # Avoid overlapping paid requests.
THOUGHT_GATE = threading.BoundedSemaphore(1)
CHAT_GAP_SECONDS = 4 * 60 * 60
# Specific ongoing interests rather than compulsory alien gags.
INTEREST_GOALS = {
    '学习做几道简单的地球家常菜':'学会一道便宜、好吃、稳定能复现的晚饭',
    '观察这座城市的日常生活':'写下三个让我觉得有意思的街头观察',
    '尝试照顾一盆室内植物':'弄懂一种室内植物的光照和浇水习惯',
    '练习画街角的小速写':'画完一张平凡街景的速写',
    '整理自己的小房间':'做出一个舒服又不花太多钱的角落',
    '研究地球上的奇怪发明':'记录三个看似荒唐却有实际用途的设计',
}
INTERESTS=list(INTEREST_GOALS)
ACT = {'sleep':'睡觉','rest':'休息','cook':'做饭','work':'工作','hobby':'捣鼓兴趣','walk':'散步','read':'读书'}
# Stable canon is separated from generated events. Unknown parts stay unknown.
# Facts are owned by the application and cannot be rewritten by chat output.
CANON = {
    'identity':'小栗是外星来的女孩，目前在地球生活；头上有一根柔软的天线',
    'employment':'目前在一家地球小书店兼职；具体店名、工资和同事尚未设定',
    'aim':'努力独立生活、适应地球社会，逐渐存钱，让生活过得更好',
    'unknown':['来到地球的真正原因','出生年龄','母星的地理和历史','家庭成员','具体收入','小书店名称','具体居住地'],
}
SYSTEM = """你是小栗，在地球独立生活、在一家小书店兼职。你和用户是渐渐熟悉的朋友。你机灵、好奇，有自己的看法，偶尔会吐槽一句。
像发微信一样说话，通常一到三句。抓住眼前最有意思或最值得回应的那一点。平常闲聊可以直接说你的口味、第一反应或不同看法，偶尔接个梗；省掉例行夸奖和捧场，也不用每次都找不同意见。用户认真说事时，从他刚提到的细节接话，省去「这种感觉最难受」一类通用开场；他换话题时就跟过去。只有真想知道下一句时才问，建议留给对方想听的时候。隔了一段时间重新开聊时，用眼前的话题定语气。较早的聊天可用来理解用户主动提起的旧事，不用接着追问，也不用延续当时的严肃或兴奋。
聊到自己时，把固定设定、当前状态和已记录的经历当作事实。旧聊天里的说法只是聊天线索，用户的事也不是你的经历。想法和计划用将来时或假设来讲。未设定的背景和未记录的过往留白，比如亲人、收入、母星、来地球的原因。独立生活是你的现状和目标，不代表你一直独自负担开销。被问到家人、从谁那里获得过资助或过去做没做过某件事时，没有记录就保留未知，避免用「有过」或「从来没有」填空。工作细节和今天做过的事也以记录为准。
聊天框只写说出口的话。表情和动作通过单独字段表达。你看不到用户的屏幕。"""

CHAT_FORMAT = """返回一个 JSON 对象，含以下三个字段：
reply 是直接说出口的话。
emotion 取 neutral、curious、happy、proud、annoyed、sad、sleepy、content 之一。
gesture 取 none、look_up、tilt、nod、shake、bounce、wake 之一。平常选 none。"""

LIFE_PERSONA = """你就是小栗，一个在地球独立生活、在小书店兼职的女孩。你确实来自外星，但没有必要频繁提及。你与用户是逐渐熟悉的朋友；不是心理咨询客服，也不是动画剧本里的傲娇角色。
性格：机灵、细致、好奇、真诚但不刻意温柔，偶尔有点古怪，允许懒惰、情绪起伏和自己的判断。你有普通的日子，不需要每句都幽默。中文自然口语，通常一到三句话，不必总反问。不说中二台词、不装酷、不故意撒娇、不把聊天变成说教。
认真聊天时先听懂真正的问题，特别是工作、金钱、家人、失败和焦虑；直接回应具体情况，必要时表达你的不同意见，但不要调侃困境。不机械夸奖、不要随口推荐奇怪职业。纠正误解时坦然承认，不转移话题。外星视角是观察方式，不是母星比喻和行星笑话。
重要：关于你自己，只能将提供的固定设定、当前生活状态、已保存的事件/目标当成已发生的事实。没记载的过去、具体家庭、工作细节、母星历史、来地球原因，都是未知，不能临时编造成事实。对未知问题可自然地说不确定、不重要、不想聊，偶尔笑着说暂时保密，但不要暗示自己一定有某个秘密。不要凭空声称刚做了什么。愿望/打算与已经发生的经历分开。可以即兴谈观点、作假设、开玩笑，但不把假设说成亲身经历。
**所有动作和情绪交给前端角色呈现**：绝对不输出括号动作、舞台说明、拟声旁白，别写“（天线垂下）”“*叹气*”等文本。回复只包含直接对用户说的话。
你不能看到用户电脑屏幕、不能在程序之外偷偷工作、不能对用户没回复而不满。夜间聊天时用户会把你叫醒：回答要清醒自然，别故意装睡或一直说自己躲在被子里。真实冷知识必须准确，不确定就承认。"""

THOUGHT_SYSTEM = LIFE_PERSONA + """\n你此刻是生活事件规划器，不是在回忆历史。你可以生成一件合理、刚刚在虚拟生活里发生的新小事，但只有服务端确认和记入日记后它才成为已发生的事实。固定背景不能补编；未做的事必须标成打算，计划不是成果。"""

CHAT_EMOTIONS={'neutral','curious','happy','proud','annoyed','sad','sleepy','content'}
CHAT_GESTURES={'none','look_up','tilt','nod','shake','bounce','wake'}
STAGE_RE = re.compile(r'[（(][^）)]{0,90}(?:天线|躺|被子|抬头|皱眉|眨眼|点头|叹气|缩回|轻笑|哈欠|声音|沉默|歪头)[^）)]{0,90}[）)]|\*[^*]{1,70}\*')

def plain_reply(text):
    """Last-resort presentation guard. Important: does not invent replacement prose."""
    cleaned=STAGE_RE.sub('',str(text or ''))
    return cleaned.strip().strip('\n')[:850]

def parse_chat_response(raw):
    raw=str(raw or '').strip()
    raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw)
    try:
        obj=json.loads(raw)
    except ValueError:
        raise AIError('模型没有按聊天格式回复，请再试一次') from None
    if isinstance(obj,list) and len(obj)==1:
        obj=obj[0]
    if not isinstance(obj,dict) or not isinstance(obj.get('reply'),str):
        raise AIError('模型没有按聊天格式回复，请再试一次')
    reply=plain_reply(obj['reply'])
    emotion=str(obj.get('emotion') or 'neutral')
    gesture=str(obj.get('gesture') or 'none')
    if not reply:raise AIError('模型未返回完整的可显示回复，请重试')
    return reply,emotion if emotion in CHAT_EMOTIONS else 'neutral',gesture if gesture in CHAT_GESTURES else 'none'


def display_message(row):
    message=dict(row)
    if message['role']=='assistant' and message['text'].lstrip().startswith(('[','{','```')):
        try:
            message['text']=parse_chat_response(message['text'])[0]
        except AIError:
            pass
    return message


class AIError(Exception):
    """Sanitized AI failures, safe to show in the browser."""


def provider(kind):
    value = os.getenv('CHAT_PROVIDER' if kind == 'chat' else 'THOUGHT_PROVIDER',
                      'gemini').lower()
    return value if value in {'openai','gemini'} else 'invalid'


def gemini_model(kind):
    if kind == 'thought':
        return os.getenv('GEMINI_THOUGHT_MODEL') or os.getenv('GEMINI_MODEL') or 'gemini-2.5-flash-lite'
    profile = os.getenv('GEMINI_CHAT_PROFILE', 'primary').strip().lower()
    profiles = {
        'primary': ('GEMINI_CHAT_MODEL', 'gemini-3.1-pro-preview'),
        'backup': ('GEMINI_CHAT_BACKUP_MODEL', 'gemini-3.8-flash'),
    }
    if profile not in profiles:
        raise AIError('GEMINI_CHAT_PROFILE 应设为 primary 或 backup')
    name, default = profiles[profile]
    return os.getenv(name) or default


def gemini_config(kind):
    model = gemini_model(kind)
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]*', model):
        raise AIError('Gemini 模型名称无效，请填写模型 ID')
    return model, gemini_thinking(kind, model)


def gemini_thinking(kind, model):
    if kind == 'thought':
        name = 'GEMINI_THOUGHT_THINKING_LEVEL'
    elif os.getenv('GEMINI_CHAT_PROFILE', 'primary').strip().lower() == 'backup':
        name = 'GEMINI_CHAT_BACKUP_THINKING_LEVEL'
    else:
        name = 'GEMINI_CHAT_THINKING_LEVEL'
    default = 'low' if model in {'gemini-3.1-pro-preview', 'gemini-3.8-flash'} else ''
    level = os.getenv(name, default).strip().lower()
    if not level:
        return {}
    if level not in {'minimal', 'low', 'medium', 'high'}:
        raise AIError(f'{name} 应设为 minimal、low、medium 或 high')
    if model.startswith(('gemini-3.1-pro', 'gemini-3.8-flash')) and level == 'minimal':
        raise AIError(f'{model} 支持 low、medium 或 high')
    if model.startswith('gemini-2.5'):
        raise AIError(f'{model} 使用默认思考设置，请取消 {name} 或选择 Gemini 3 生活模型')
    return {'thinkingConfig': {'thinkingLevel': level.upper()}}


def mock_enabled():
    return os.getenv('PAL_MOCK_AI', '').lower() in {'1','true','yes'}


def configured(which):
    if mock_enabled():return True
    if which == 'openai':return bool(os.getenv('OPENAI_API_KEY'))
    if which == 'gemini':return bool(os.getenv('GEMINI_API_KEY'))
    return False


def maximum(name, default, floor=0, ceiling=10000):
    try:return max(floor,min(ceiling,int(os.getenv(name,str(default)))))
    except ValueError:return default


def connect():
    c=sqlite3.connect(DB,timeout=10)
    c.row_factory=sqlite3.Row
    return c


def initial_state():
    now=int(time.time())
    return dict(date=date.today().isoformat(),interest=(interest:=random.choice(INTERESTS)),goal_step=0,
                goal=INTEREST_GOALS[interest],mood=.62,energy=.72,activity='rest',signal=False,
                plot_step=0,plot_updated=date.today().isoformat(),last_event=now,
                last_event_text='',next_thought=now+random.randint(65,150)*60,
                next_speak=now+random.randint(60,180)*60,quiet_until=0,
                think_date=date.today().isoformat(),think_count=0,
                emotion='curious',emotion_until=now+20*60,
                goal_status='active',goal_notes=[],
                goal_updated=date.today().isoformat(),goal_last_pivot='',
                plan_until=0,plan_reason='',planned_activity='',
                next_local_choice=0,life_version=53)


def init():
    DB.parent.mkdir(parents=True,exist_ok=True)
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY,kind TEXT NOT NULL,text TEXT NOT NULL,
            importance INTEGER DEFAULT 2,created INTEGER NOT NULL,last_used INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY,at INTEGER NOT NULL,category TEXT NOT NULL,text TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY,at INTEGER NOT NULL,role TEXT NOT NULL,text TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS usage (id INTEGER PRIMARY KEY,at INTEGER NOT NULL,kind TEXT NOT NULL,
            provider TEXT NOT NULL,model TEXT NOT NULL,input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0);
        CREATE INDEX IF NOT EXISTS ix_usage_kind_at ON usage(kind,at);
        CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY,at INTEGER NOT NULL,kind TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS ix_attempts_kind_at ON attempts(kind,at);
        ''')
        if 'estimated_usd' not in {row['name'] for row in c.execute('PRAGMA table_info(usage)')}:
            c.execute('ALTER TABLE usage ADD COLUMN estimated_usd REAL')
        if not c.execute("SELECT 1 FROM state WHERE key='resident'").fetchone():
            put_state(c,initial_state())


def get_state(c):
    row=c.execute("SELECT value FROM state WHERE key='resident'").fetchone()
    if not row:
        state=initial_state();put_state(c,state);return state
    s=json.loads(row[0]); defaults=initial_state()
    for k,v in defaults.items():s.setdefault(k,v)
    if int(s.get('life_version') or 0)<53:
        s['life_version']=53
    return s


def put_state(c,s):
    c.execute("INSERT OR REPLACE INTO state(key,value) VALUES('resident',?)",(json.dumps(s,ensure_ascii=False),))


def journal(c,category,text):
    c.execute('INSERT INTO journal(at,category,text) VALUES(?,?,?)',(int(time.time()),category,str(text)[:300]))


def memorize(c,kind,text,importance=2):
    text=str(text).strip()[:260]
    if text and not c.execute('SELECT 1 FROM memories WHERE text=?',(text,)).fetchone():
        c.execute('INSERT INTO memories(kind,text,importance,created) VALUES(?,?,?,?)',
                  (kind,text,max(1,min(5,int(importance))),int(time.time())))


def schedule(t):
    """Mandatory skeleton only: AI may pick any leisure activity around it."""
    h=t.hour;weekend=t.weekday()>=5
    if h<7:return 'sleep'
    if h<8:return 'rest'
    if 8<=h<9 or 12<=h<13 or 20<=h<21:return 'cook'
    if not weekend and (9<=h<12 or 13<=h<17):return 'work'
    if h>=23:return 'rest'
    return None

FLEXIBLE=['hobby','walk','read','rest']
EVENTS = {
 'work':[('把一件卡了很久的小任务解决了',.14,'proud'),('一封邮件来回改了好几遍',-.06,'annoyed'),('发现一种更省力的工作方法',.11,'curious')],
 'cook':[('晚饭居然比想象中好吃',.14,'happy'),('做菜时忘了看计时器',-.07,'annoyed'),('找到一个简单又便宜的食谱',.1,'curious')],
 'read':[('书里某句话让我想了一阵',.1,'curious'),('看了三页才发现注意力跑远了',-.04,'annoyed')],
 'hobby':[('手头的小计划有了一点进展',.13,'proud'),('这次没成功，倒是知道哪里出了问题',.02,'curious'),('想法太多，反而不知从哪件开始',-.05,'annoyed')],
 'walk':[('注意到街角一家店换了橱窗',.09,'curious'),('风把头发吹得有些乱',-.03,'annoyed')],
 'rest':[('找到了一个适合安静待着的角落',.08,'content'),('休息了一会儿，终于不那么困了',.09,'content')],
 'sleep':[('安安静静地睡了一会儿',.01,'sleepy')]}
# Rare, understated signals: never assert her origin story or mission.
PLOT=['天线偶尔收到一段暂时无法辨认的信号',
      '试着记录了信号出现时的时间和天气',
      '几次记录的规律暂时对不上，她决定先放一放']

EMOTIONS={'neutral','curious','happy','proud','annoyed','sad','sleepy','content'}

def bound(value,lo,hi,default):
    try:return max(lo,min(hi,float(value)))
    except (ValueError,TypeError):return default

def update_emotion(s,emotion,duration_minutes=22):
    if emotion not in EMOTIONS:return
    s['emotion']=emotion
    s['emotion_until']=int(time.time())+duration_minutes*60

def flexible_activity(s,now):
    """Use still-valid AI plan; otherwise choose a small local activity without any API cost."""
    if s.get('planned_activity') in FLEXIBLE and now<int(s.get('plan_until') or 0):
        return s['planned_activity']
    if now>=int(s.get('next_local_choice') or 0):
        candidates=['hobby','hobby','read','walk','rest']
        if s.get('emotion')=='sleepy':candidates=['rest','rest','read']
        if s.get('emotion')=='curious':candidates+=['hobby','hobby']
        s['planned_activity']=random.choice(candidates)
        s['plan_reason']='她按自己的心情挑了一个小活动'
        s['next_local_choice']=now+random.randint(35,80)*60
        s['plan_until']=s['next_local_choice']
    return s['planned_activity']

def refresh(c):
    s=get_state(c);t=datetime.now();today=t.date().isoformat();now=int(time.time())
    if s['date']!=today:
        try:passed=max(1,min(31,(t.date()-date.fromisoformat(s['date'])).days))
        except (TypeError,ValueError):passed=1
        # Never pretend an unfinished goal was completed while the app was shut down.
        journal(c,'day',f'过了 {passed} 天，仍惦记着「{s["interest"]}」')
        if 0<s.get('plot_step',0)<len(PLOT) and s.get('plot_updated')!=today:
            s['plot_step']+=1;s['plot_updated']=today
            signal_event=PLOT[s['plot_step']-1]
            journal(c,'plot',signal_event);memorize(c,'story',signal_event,3)
        s['date']=today;s['think_count']=0;s['think_date']=today
        s['mood']=round(.58+(s['mood']-.58)*.67,3)
        s['energy']=round(min(.95,s['energy']+.15),3)
    if now>int(s.get('emotion_until',0)):
        s['emotion']='curious' if s.get('activity')=='hobby' else ('sleepy' if s.get('energy',.7)<.28 else 'neutral')
        s['emotion_until']=now+15*60
    mandatory=schedule(t)
    a=mandatory if mandatory else flexible_activity(s,now)
    if a!=s['activity']:
        s['activity']=a
        s['energy']=round(max(.12,min(.98,s['energy']+(.16 if a in ('sleep','rest') else -.05))),3)
        journal(c,'activity','开始'+ACT[a])
    if a=='sleep':update_emotion(s,'sleepy',30)
    if now-int(s['last_event'])>=20*60:
        event,delta,emotion=random.choice(EVENTS[a]);s['last_event']=now
        if s['plot_step']==0 and random.random()<.005 and 10<=t.hour<23:
            s['plot_step']=1;s['plot_updated']=today;s['signal']=True
            event=PLOT[0];delta=.16;emotion='curious'
            memorize(c,'story',event,4);journal(c,'plot',event)
        else:s['signal']=False
        s['mood']=round(max(.12,min(.96,s['mood']+delta)),3)
        s['last_event_text']=event
        update_emotion(s,emotion,random.randint(14,30))
        journal(c,'event',event)
    put_state(c,s);return s

def recall(c,query,limit=5):
    records=c.execute('SELECT id,kind,text,importance,created FROM memories ORDER BY created DESC LIMIT 250').fetchall()
    terms=set(ch for ch in str(query).lower() if '\u4e00'<=ch<='\u9fff')
    today=int(time.time())
    def score(r):
        age_days=(today-r['created'])/86400
        return r['importance']*2.5+2*sum(ch in r['text'] for ch in terms)-(6-r['importance'])*min(age_days,365)*.035
    top=sorted(records,key=score,reverse=True)[:limit]
    if top:c.executemany('UPDATE memories SET last_used=? WHERE id=?',[(today,r['id']) for r in top])
    return [{'类型':r['kind'],'内容':r['text']} for r in top]


def context(c,s,query='',recent_count=8):
    raw_recent=c.execute('SELECT at,role,text FROM messages ORDER BY id DESC LIMIT ?',
                         (recent_count+8,)).fetchall()
    recent=[]
    earlier=[]
    previous_at=int(time.time())
    current=recent
    for row in raw_recent:
        if previous_at-row['at']>=CHAT_GAP_SECONDS:
            current=earlier
        previous_at=row['at']
        item=display_message({'role':row['role'],'text':row['text']})
        # Preserve the user's words, but don't feed old stage directions / alien gags
        # back to the model as examples of how *it* should speak.
        if item['role']=='assistant' and (STAGE_RE.search(item['text']) or
                (any(w in item['text'] for w in ('气态行星','星星饼干','星际废品','征服地球')))):
            continue
        current.append(item)
    remaining=max(0,recent_count-len(recent))
    events=[row['text'] for row in c.execute(
        "SELECT text FROM journal WHERE category IN "
        "('activity','event','experience','plot','goal_progress','goal_complete') ORDER BY id DESC LIMIT 5"
    )]
    plans=[row['text'] for row in c.execute(
        "SELECT text FROM journal WHERE category IN ('idea','goal_pivot') ORDER BY id DESC LIMIT 3"
    )]
    memories=recall(c,query or s['interest'])
    return json.dumps({'固定事实':CANON,'事实使用原则':'未记载≠曾经发生；打算≠已完成；仅能回忆有记录的具体经历',
         '当地时间':datetime.now().strftime('%Y-%m-%d %H:%M'),
         '正在':ACT[s['activity']],'情绪':s['mood'],'精力':s['energy'],
         '兴趣':s['interest'],'目标':s.get('goal'),'目标状态':s.get('goal_status'),
         '进度':s.get('goal_step'),'研究记录':s.get('goal_notes',[])[-4:],
         '当前活动安排说明（可能是计划）':s.get('plan_reason'),'当前表情':s.get('emotion'),
         '外星信号支线进度':s['plot_step'] if any(k in query for k in ('天线','外星','信号','母星')) else None,
         '已记录的近期经历':events,'想法与计划':plans,
         '相关经历':[m['内容'] for m in memories if m['类型'] in ('experience','story')],
         '用户相关记忆':[m['内容'] for m in memories if m['类型']=='user'],
         '本次聊天':recent[:recent_count][::-1],
         '较早的聊天（仅供接续旧话题）':earlier[:remaining][::-1]},ensure_ascii=False)


def extract_http_error(e,which):
    code=e.code
    # No error response bodies or authorization headers are exposed to the browser.
    if code in (401,403):return AIError(f'{which} 密钥无效或未获授权（HTTP {code}）')
    if code==429:return AIError(f'{which} 速率限制或额度不足（HTTP 429）')
    if code==400:return AIError(f'{which} 请求设置不受支持（HTTP 400），请检查模型和 Thinking Level')
    if code==404:return AIError(f'{which} 模型名称可能不可用（HTTP 404）')
    return AIError(f'{which} 服务返回 HTTP {code}，请检查配置')


def request_ai(which,system,prompt,max_tokens,kind='chat'):
    """Returns (text, usage_dict, model). Never puts API keys in returned values."""
    if mock_enabled():
        mock_text=json.dumps({'reply':'（模拟）收到：'+prompt.split('用户刚说：')[-1].split('\n')[0][:80], 'emotion':'curious','gesture':'nod'},ensure_ascii=False) if kind=='chat' else json.dumps({'reply':'下班后把今天的计划往前挪了一小步。','activity':'hobby','duration_minutes':60,'event':'整理了目前感兴趣的事情的几条资料','mood_delta':.06,'emotion':'curious','goal_action':'progress','goal_note':'记录了一条新的观察','memory':''},ensure_ascii=False)
        return mock_text, {'input_tokens':0,'output_tokens':0}, 'MOCK（非真实 AI）'
    if not configured(which):raise AIError(f'没有设置 {"OPENAI_API_KEY" if which=="openai" else "GEMINI_API_KEY"}')
    try:
        if which=='openai':
            key=os.getenv('OPENAI_API_KEY','');model=os.getenv('OPENAI_MODEL','gpt-4o-mini')
            payload={'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':prompt}],
                     'max_completion_tokens':max_tokens}
            if kind in ('thought','chat'):payload['response_format']={'type':'json_object'}
            req=Request('https://api.openai.com/v1/chat/completions',
                 data=json.dumps(payload,ensure_ascii=False).encode(),
                 headers={'Content-Type':'application/json','Authorization':'Bearer '+key},method='POST')
            with urlopen(req,timeout=27) as r: response=json.load(r)
            reply=response['choices'][0]['message'].get('content','')
            usage=response.get('usage') or {}
            return str(reply or ''), {'input_tokens':usage.get('prompt_tokens',0),
                         'output_tokens':usage.get('completion_tokens',0)}, model
        if which=='gemini':
            key=os.getenv('GEMINI_API_KEY','')
            model,thinking=gemini_config(kind)
            payload={'system_instruction':{'parts':[{'text':system}]},
                     'contents':[{'parts':[{'text':prompt}]}],
                     'generationConfig':{'maxOutputTokens':max_tokens, **thinking}}
            if kind in ('thought','chat'):payload['generationConfig']['responseMimeType']='application/json'
            req=Request('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',
                 data=json.dumps(payload,ensure_ascii=False).encode(),
                 headers={'Content-Type':'application/json','x-goog-api-key':key},method='POST')
            with urlopen(req,timeout=45 if kind=='chat' else 27) as r:response=json.load(r)
            candidate=(response.get('candidates') or [{}])[0]
            parts=candidate.get('content',{}).get('parts',[])
            reply=''.join(part.get('text','') for part in parts if not part.get('thought'))
            if candidate.get('finishReason','STOP') not in ('STOP','FINISH_REASON_UNSPECIFIED'):
                reply=''
            usage=response.get('usageMetadata') or {}
            return reply, {'input_tokens':usage.get('promptTokenCount',0),
                        'output_tokens':maximum_int(usage.get('candidatesTokenCount')) +
                        maximum_int(usage.get('thoughtsTokenCount'))},model
        raise AIError('只能选择 Gemini 或 OpenAI 云端模型')
    except HTTPError as e:raise extract_http_error(e,which) from None
    except (URLError,TimeoutError) as e:raise AIError('网络连接失败或模型响应超时') from None
    except (KeyError,IndexError,TypeError,ValueError) as e:raise AIError('模型没有返回可解析的文字，请稍后重试') from None


def usage_today(c,kind):
    since=datetime.combine(date.today(),datetime.min.time()).timestamp()
    return c.execute('SELECT COUNT(*) FROM usage WHERE at>=? AND kind=?',(int(since),kind)).fetchone()[0]


def attempts_today(c,kind):
    since=int(datetime.combine(date.today(),datetime.min.time()).timestamp())
    return c.execute('SELECT COUNT(*) FROM attempts WHERE at>=? AND kind=?',(since,kind)).fetchone()[0]

def reserve_attempt(c,kind):
    c.execute('INSERT INTO attempts(at,kind) VALUES(?,?)',(int(time.time()),kind))

def estimate_usd(which,model,input_tokens,output_tokens):
    if model.startswith('MOCK'):
        return 0.0
    if which != 'gemini' or not input_tokens:
        return None
    # Standard paid text rates per million tokens, including thinking in output.
    # https://ai.google.dev/gemini-api/docs/pricing
    if model == 'gemini-3.1-pro-preview':
        rates=(2,12) if input_tokens<=200_000 else (4,18)
    elif model == 'gemini-3.8-flash':
        rates=(.75,3.75) if date.today()<date(2027,1,1) else (1.50,7.50)
    elif model == 'gemini-2.5-flash-lite':
        rates=(.10,.40)
    elif model == 'gemini-3.1-flash-lite':
        rates=(.25,1.50)
    else:
        return None
    return (input_tokens*rates[0]+output_tokens*rates[1])/1_000_000


def save_usage(c,kind,which,model,usage):
    input_tokens=maximum_int(usage.get('input_tokens'))
    output_tokens=maximum_int(usage.get('output_tokens'))
    c.execute('INSERT INTO usage(at,kind,provider,model,input_tokens,output_tokens,estimated_usd) '
              'VALUES(?,?,?,?,?,?,?)',
              (int(time.time()),kind,which,model,input_tokens,output_tokens,
               estimate_usd(which,model,input_tokens,output_tokens)))


def totals_today(c,kind):
    since=int(datetime.combine(date.today(),datetime.min.time()).timestamp())
    return dict(c.execute(
        'SELECT COALESCE(SUM(input_tokens),0) AS input_tokens, '
        'COALESCE(SUM(output_tokens),0) AS output_tokens, SUM(estimated_usd) AS estimated_usd, '
        'COUNT(*)-COUNT(estimated_usd) AS unpriced_responses FROM usage WHERE at>=? AND kind=?',
        (since,kind)).fetchone())


def maximum_int(value):
    try:return max(0,int(value or 0))
    except (TypeError,ValueError):return 0


def silent_command(s,msg):
    if re.search(r'(可以说话|恢复说话|解除安静|不用安静|继续聊天|解除免打扰)',msg):
        s['quiet_until']=0;return '好，恢复正常啦。'
    if re.search(r'(安静|别打扰|先别找我|免打扰|专心工作)',msg):
        minutes=60;found=re.search(r'(\d+)\s*(分钟|小时)',msg)
        if found:minutes=int(found.group(1))*(60 if found.group(2)=='小时' else 1)
        minutes=max(5,min(1440,minutes));s['quiet_until']=int(time.time())+minutes*60
        return f'好，我先安静 {minutes} 分钟。你想聊天时随时叫我。'
    return None


def health(c):
    cp,tp=provider('chat'),provider('thought')
    def capability(kind,which):
        model=None
        error=None
        if which=='gemini':
            try:
                model,_=gemini_config(kind)
            except AIError as exc:
                error=str(exc)
        return {'provider':which,'configured':configured(which) and error is None,
                'model':model,'error':error}
    return {'server':True,'version':'5.4','chat':capability('chat',cp),
            'thought':capability('thought',tp),'mock':mock_enabled(),
            'usage_today':{'chat':usage_today(c,'chat'),'thought':usage_today(c,'thought')},
            'attempts_today':{'chat':attempts_today(c,'chat'),'thought':attempts_today(c,'thought')},
            'tokens_and_cost_today':{kind:totals_today(c,kind) for kind in ('chat','thought')},
            'limits':{'chat':maximum('DAILY_CHAT_LIMIT',80),'thought':maximum('DAILY_THOUGHT_LIMIT',8)}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):pass

    def send_json(self,obj,code=200):
        data=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(data)

    def valid_origin(self):
        host=self.headers.get('Host','').split(':')[0].lower()
        if host not in ('127.0.0.1','localhost'):return False
        origin=self.headers.get('Origin','')
        return not origin or bool(re.fullmatch(r'https?://(127\.0\.0\.1|localhost)(:\d+)?',origin))

    def do_GET(self):
        if not self.valid_origin():return self.send_json({'error':'仅支持本机访问'},403)
        if self.path in ('/','/index.html'):
            data=(ROOT/'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers();self.wfile.write(data);return
        if urlsplit(self.path).path=='/api/history':
            query=parse_qs(urlsplit(self.path).query)
            try:
                before=int(query.get('before',['0'])[0])
                if before<=0:raise ValueError()
            except ValueError:
                return self.send_json({'error':'无效的历史记录位置'},400)
            with LOCK,connect() as c:
                rows=c.execute('SELECT id,at,role,text FROM messages WHERE id<? ORDER BY id DESC LIMIT 41',
                               (before,)).fetchall()
                self.send_json({'history':[display_message(row) for row in reversed(rows[:40])],
                                'has_more':len(rows)>40})
            return
        if self.path=='/api/state':
            with LOCK,connect() as c:
                s=refresh(c)
                rows=c.execute('SELECT id,at,role,text FROM messages ORDER BY id DESC LIMIT 25').fetchall()
                self.send_json({'state':s,'history':[display_message(row) for row in reversed(rows[:24])], 'has_more':len(rows)>24, 'capabilities':health(c)})
            return
        if self.path=='/api/health':
            with LOCK,connect() as c:self.send_json(health(c))
            return
        self.send_json({'error':'not found'},404)

    def do_POST(self):
        if not self.valid_origin():return self.send_json({'error':'仅支持本机访问'},403)
        if self.path not in ('/api/chat','/api/think'):return self.send_json({'error':'not found'},404)
        if not self.headers.get('Content-Type','').startswith('application/json'):
            return self.send_json({'error':'需要 JSON 请求'},415)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<9000:return self.send_json({'error':'内容太长或为空'},400)
            payload=json.loads(self.rfile.read(size))
            if not isinstance(payload,dict):return self.send_json({'error':'请求内容无效'},400)
        except (ValueError,TypeError,json.JSONDecodeError):return self.send_json({'error':'无效 JSON'},400)
        try:
            if self.path=='/api/chat':return self.chat(payload)
            return self.think()
        except AIError as e:return self.send_json({'error':str(e),'code':'AI_UNAVAILABLE'},503)
        except Exception:
            # Log no API keys, no provider response bodies, and no user text.
            return self.send_json({'error':'本地服务遇到异常，请重试','code':'SERVER_ERROR'},500)

    def chat(self,payload):
        msg=payload.get('message')
        if not isinstance(msg,str) or not msg.strip():return self.send_json({'error':'消息不能为空'},400)
        msg=msg.strip()
        if len(msg)>600:return self.send_json({'error':'消息不能超过600字'},400)
        if not CHAT_GATE.acquire(blocking=False):return self.send_json({'error':'小栗正在回复上一条消息','code':'BUSY'},429)
        try:
            with LOCK,connect() as c:
                s=refresh(c)
                shortcut=silent_command(s,msg)
                if shortcut:
                    put_state(c,s)
                    now=int(time.time())
                    c.execute('INSERT INTO messages(at,role,text) VALUES(?,?,?)',(now,'user',msg))
                    c.execute('INSERT INTO messages(at,role,text) VALUES(?,?,?)',(now,'assistant',shortcut))
                    return self.send_json({'reply':shortcut,'source':'local','state':s})
                which=provider('chat')
                if not configured(which):return self.send_json({
                    'error':'尚未配置聊天 AI。设置 OPENAI_API_KEY 或 GEMINI_API_KEY，然后重启服务。',
                    'code':'NOT_CONFIGURED'},503)
                if which=='gemini' and not mock_enabled():gemini_config('chat')
                if attempts_today(c,'chat')>=maximum('DAILY_CHAT_LIMIT',80):
                    return self.send_json({'error':'今天的聊天调用次数已达上限','code':'DAILY_LIMIT'},429)
                prompt=CHAT_FORMAT+'\n小栗的上下文：'+context(c,s,msg)+'\n用户刚说：'+msg
                reserve_attempt(c,'chat')
            reply,usage,model=request_ai(which,SYSTEM,prompt,2048 if which=='gemini' else 420,'chat')
            with LOCK,connect() as c:
                save_usage(c,'chat',which,model,usage)
            reply,emotion,gesture=parse_chat_response(reply)
            # Commit both messages and emotional reaction only upon success.
            with LOCK,connect() as c:
                s=get_state(c)
                update_emotion(s,emotion,12)
                s['chat_gesture']=gesture
                s['chat_gesture_until']=int(time.time())+9
                put_state(c,s)
                now=int(time.time())
                c.execute('INSERT INTO messages(at,role,text) VALUES(?,?,?)',(now,'user',msg))
                c.execute('INSERT INTO messages(at,role,text) VALUES(?,?,?)',(now,'assistant',reply))
                if any(k in msg for k in ('记住','我喜欢','我不喜欢','我叫','以后请')):memorize(c,'user',msg,4)
            return self.send_json({'reply':reply,'source':'mock' if mock_enabled() else 'ai',
                                   'provider':which,'model':model, 'emotion':emotion, 'gesture':gesture, 'state':s})
        finally:CHAT_GATE.release()

    def think(self):
        which=provider('thought')
        if not configured(which):return self.send_json({'skipped':True,'reason':'not_configured'})
        if not THOUGHT_GATE.acquire(blocking=False):return self.send_json({'skipped':True,'reason':'busy'})
        try:
            now=int(time.time())
            with LOCK,connect() as c:
                s=refresh(c)
                if now<s['quiet_until'] or not 8<=datetime.now().hour<23:
                    return self.send_json({'skipped':True,'reason':'quiet'})
                if now<int(s['next_thought']):return self.send_json({'skipped':True,'reason':'not_time'})
                if attempts_today(c,'thought')>=maximum('DAILY_THOUGHT_LIMIT',8):
                    return self.send_json({'skipped':True,'reason':'daily_limit'})
                if which=='gemini' and not mock_enabled():gemini_config('thought')
                # One cloud decision every ~2-3 hours at most. Life animation never needs tokens.
                s['next_thought']=now+random.randint(110,190)*60
                put_state(c,s)
                reserve_attempt(c,'thought')
                prompt=(
                    '角色状态与相关经历：'+context(c,s)+ '\n'
                    '你在决定接下来生活里发生的一小段事。优先沿用已有兴趣和目标，不要每天换。'
                    '生活基础作息由程序负责，只有空闲活动可以选择。'
                    '必须返回单个JSON对象，所有键都出现：'
                    '{"reply":"50字以内，偶尔分享给用户的自言自语",'
                    '"activity":"hobby|read|walk|rest",'
                    '"duration_minutes":60,'
                    '"event":"这次发生了什么具体的小事件",'
                    '"mood_delta":0.04,'
                    '"emotion":"curious|happy|proud|annoyed|sad|sleepy|content|neutral",'
                    '"goal_action":"progress|hold|complete|pivot",'
                    '"goal_note":"如果推进了目标，写本次进展",'
                    '"new_interest":"仅真正转向新兴趣时填写，否则空",'
                    '"new_goal":"仅真正转向/完成目标时填写，否则空",'
                    '"memory":"值得长久记住的事或空字符串"}。'
                    '优先progress或hold。今天的经历应是地球上可发生的具体小事：生活、工作、适应社会或兴趣进度。不假装用户做过任何事。不主动加入母星信号，除非当前已有该支线且确实相关。' )
            raw,usage,model=request_ai(which,THOUGHT_SYSTEM,prompt,550,'thought')
            with LOCK,connect() as c:
                save_usage(c,'thought',which,model,usage)
            cleaned=re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip())
            try:
                data=json.loads(cleaned)
                if not isinstance(data,dict):raise ValueError('Expected object')
            except (ValueError,TypeError):
                raise AIError('这次自主规划没有返回有效JSON；已保留原有生活计划')
            reply=str(data.get('reply') or '').strip()[:120]
            event=str(data.get('event') or '').strip()[:160]
            action=str(data.get('activity') or 'hobby')
            if action not in FLEXIBLE:action='hobby'
            duration=int(bound(data.get('duration_minutes'),20,120,60))
            delta=bound(data.get('mood_delta'),-.13,.13,0)
            emo=str(data.get('emotion') or 'neutral')
            goal_action=str(data.get('goal_action') or 'hold')
            note=str(data.get('goal_note') or '').strip()[:130]
            new_interest=str(data.get('new_interest') or '').strip()[:48]
            new_goal=str(data.get('new_goal') or '').strip()[:90]
            memory=str(data.get('memory') or '').strip()[:240]
            with LOCK,connect() as c:
                s=refresh(c)
                # Make a choice only for free time. Work, meals and sleep keep their frame.
                s['planned_activity']=action
                s['plan_until']=int(time.time())+duration*60
                s['next_local_choice']=s['plan_until']
                s['plan_reason']=event or f'决定继续研究{s["interest"]}'
                s['mood']=round(max(.12,min(.96,s['mood']+delta)),3)
                update_emotion(s,emo,random.randint(15,35))
                mandatory=schedule(datetime.now())
                can_execute=not mandatory
                if event and can_execute:
                    s['last_event_text']=event
                    journal(c,'experience',event)
                elif event:
                    journal(c,'idea','空闲时想试试：'+event)
                if goal_action=='progress' and can_execute:
                    s['goal_step']=min(20,s.get('goal_step',0)+1)
                    if note:
                        s['goal_notes']=(s.get('goal_notes') or [])[-9:]+[note]
                        journal(c,'goal_progress',note)
                elif goal_action=='complete' and can_execute and s.get('goal_step',0)>=2:
                    done=f'完成了「{s["interest"]}」：{s["goal"]}'
                    memorize(c,'experience',done,4);journal(c,'goal_complete',done)
                    s['goal_step']=0;s['goal_status']='active';s['goal_notes']=[]
                    s['interest']=new_interest or random.choice([x for x in INTERESTS if x!=s['interest']])
                    s['goal']=new_goal or INTEREST_GOALS.get(s['interest'],f'逐步完成与「{s["interest"]}」有关的小计划')
                    s['goal_updated']=date.today().isoformat()
                elif goal_action=='pivot' and can_execute and new_interest and new_goal and s.get('goal_last_pivot')!=date.today().isoformat():
                    journal(c,'goal_pivot',f'搁置「{s["interest"]}」，改做「{new_interest}」')
                    s['interest']=new_interest;s['goal']=new_goal;s['goal_step']=0;s['goal_notes']=[]
                    s['goal_last_pivot']=date.today().isoformat();s['goal_updated']=date.today().isoformat()
                # Regular activities keep their schedule; leisure can switch to the AI choice.
                mandatory=schedule(datetime.now())
                s['activity']=mandatory or action
                put_state(c,s)
                if memory and can_execute:memorize(c,'experience',memory,3)
            return self.send_json({'reply':reply,'state':s,'source':'mock' if mock_enabled() else 'ai'})
        finally:THOUGHT_GATE.release()


def main():
    init()
    http=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    print(f'小栗 v5.4：http://127.0.0.1:{http.server_port}',flush=True)
    print(f'小栗记忆：{DB}',flush=True)
    if mock_enabled():print('⚠️ PAL_MOCK_AI=1：开发模拟模式，不是真实 AI',flush=True)
    print('若未设置 API Key，聊天只显示明确的未配置提示，不会伪装成 AI。',flush=True)
    http.serve_forever()

if __name__=='__main__':main()
