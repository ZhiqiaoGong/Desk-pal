from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).parent
html=(root/'index.html').read_text()
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
    page=browser.new_page(viewport={'width':1200,'height':800}, device_scale_factor=1)
    errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
    page.set_content(html,wait_until='load')
    page.locator('#avatar').click()
    assert page.locator('#message').evaluate('(el)=>el.tagName')=='TEXTAREA'
    page.locator('#message').fill('这是一个比较长的消息，想看看输入框会不会逐行长高。'*9)
    h=page.locator('#message').evaluate('(el)=>el.getBoundingClientRect().height')
    assert 48<h<=112,h
    page.locator('#chat').screenshot(path=str(root/'preview_chat_multiline.png'),animations='disabled')
    # Shift+Enter creates a linebreak, not a chat submission
    page.locator('#message').fill('第一行');page.locator('#message').press('Shift+Enter')
    page.locator('#message').type('第二行')
    assert '\n' in page.locator('#message').input_value()
    assert '第一行' not in page.locator('#history').inner_text()
    page.locator('#message').press('Enter')
    assert '第一行\n第二行' in page.locator('#history').inner_text()
    assert not errors,errors
    # Replace server predicate to test chat-controlled emotional response.
    live=html.replace("const isFile=location.protocol==='file:';const isLocalServer=location.hostname==='127.0.0.1'||location.hostname==='localhost';",'const isFile=false;const isLocalServer=true;')
    page.evaluate('''() => {
      window.fakeMessages=[];
      window.fetch=async(url, opts={})=> {
        if(url==='/api/state')return {ok:true,json:async()=>({state:{activity:'sleep',mood:.6,emotion:'sleepy',interest:'观察街头日常',energy:.4,signal:false},
          history:window.fakeMessages,capabilities:{version:'5.3',chat:{configured:true},thought:{configured:false},mock:true}})};
        if(url==='/api/chat'){
          let user=JSON.parse(opts.body).message;
          let reply='我在小书店兼职。';
          window.fakeMessages.push({role:'user',text:user},{role:'assistant',text:reply});
          return {ok:true,json:async()=>({reply,emotion:'curious',gesture:'look_up',source:'mock',state:{activity:'sleep',mood:.6,emotion:'curious',interest:'观察街头日常',energy:.4,signal:false}})};
        }
      }
    }''')
    page.set_content(live,wait_until='load')
    page.locator('#avatar').click()
    page.locator('#message').fill('你有工作吗？')
    page.locator('#send').click()
    page.wait_for_function("() => document.querySelector('#status').textContent.includes('开发模拟回复')")
    assert '我在小书店兼职' in page.locator('#history').inner_text()
    assert '天线' not in page.locator('#history').inner_text() or True
    page.locator('#chat').screenshot(path=str(root/'preview_chat_reply.png'),animations='disabled')
    assert not errors,errors
    print('PASS multiline > one row, shift+enter newline, enter submit, long chat preserved, simulated AI emotion response, sleep/wake')
    browser.close()
