"""Check outgoing provider request formats without making network calls."""
import importlib.util,json,os
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('pal',Path(__file__).parent/'server.py')
pal=importlib.util.module_from_spec(spec);spec.loader.exec_module(pal)
class FakeResponse:
 def __init__(self,body):self.body=body
 def __enter__(self):return self
 def __exit__(self,*args):return False
 def read(self):return json.dumps(self.body).encode()

with patch.dict(os.environ,{'OPENAI_API_KEY':'FAKE_FOR_TEST','GEMINI_API_KEY':'FAKE_FOR_TEST'},clear=False):
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
print('PASS OpenAI + Gemini request schemas & mocked response parsing')
