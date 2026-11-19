"""Check outgoing provider request formats without making network calls."""
import importlib.util,json,os
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('pal',Path(__file__).resolve().parent.parent/'server.py')
pal=importlib.util.module_from_spec(spec);spec.loader.exec_module(pal)
class FakeResponse:
 def __init__(self,body):self.body=body
 def __enter__(self):return self
 def __exit__(self,*args):return False
 def read(self):return json.dumps(self.body).encode()

with patch.dict(os.environ,{'OPENAI_API_KEY':'FAKE_FOR_TEST','GEMINI_API_KEY':'FAKE_FOR_TEST'},clear=True):
 with patch.object(pal,'urlopen') as http:
  http.return_value=FakeResponse({'choices':[{'message':{'content':'收到啦'}}], 'usage':{'prompt_tokens':55,'completion_tokens':8}})
  text,usage,model=pal.request_ai('openai','personality','你好',150)
  req=http.call_args[0][0]
  data=json.loads(req.data)
  assert req.full_url=='https://api.openai.com/v1/chat/completions'
  assert data['messages'][0]['content']=='personality' and data['max_completion_tokens']==150
  assert text=='收到啦' and usage=={'input_tokens':55,'output_tokens':8}
 with patch.object(pal,'urlopen') as http:
  http.return_value=FakeResponse({'candidates':[{'content':{'parts':[{'text':'你好，地球人'}]}}],
        'usageMetadata':{'promptTokenCount':20,'candidatesTokenCount':11}})
  text,usage,model=pal.request_ai('gemini','personality','你好',150)
  req=http.call_args[0][0];data=json.loads(req.data)
  assert ':generateContent' in req.full_url and data['system_instruction']['parts'][0]['text']=='personality'
  assert text=='你好，地球人' and usage=={'input_tokens':20,'output_tokens':11}
  assert model=='gemini-3.1-pro-preview'
  assert data['generationConfig']['thinkingConfig']=={'thinkingLevel':'LOW'}
  http.return_value=FakeResponse({
    'candidates':[{'content':{'parts':[{'text':'private thought','thought':True},{'text':'你好'}]}}],
    'usageMetadata':{'promptTokenCount':2000,'candidatesTokenCount':100,'thoughtsTokenCount':300},
  })
  with patch.dict(os.environ,{'GEMINI_CHAT_PROFILE':'backup'}):
   text,usage,model=pal.request_ai('gemini','personality','你好',2048)
   req=http.call_args[0][0]
   assert model=='gemini-3.8-flash' and '/gemini-3.8-flash:' in req.full_url
   assert json.loads(req.data)['generationConfig']['thinkingConfig']=={'thinkingLevel':'LOW'}
   assert text=='你好' and usage=={'input_tokens':2000,'output_tokens':400}
   _,_,thought_model=pal.request_ai('gemini','life','你好',550,'thought')
   req=http.call_args[0][0]
   assert thought_model=='gemini-2.5-flash-lite'
   assert 'thinkingConfig' not in json.loads(req.data)['generationConfig']
print('PASS OpenAI + Gemini request schemas & mocked response parsing')
