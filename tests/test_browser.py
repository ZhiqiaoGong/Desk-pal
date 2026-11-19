"""Browser UI test without actual loopback network (restricted in sandbox)."""
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE=Path(__file__).resolve().parent.parent
html=(HERE/'index.html').read_text()
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',
       args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
    page=browser.new_page(viewport={'width':1200,'height':800})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html,wait_until='load')
    page.locator('#avatar').click()
    page.locator('#message').fill('你好')
    page.locator('#send').click()
    assert '[离线预设]' in page.locator('#history').inner_text()
    assert '未调用 AI' in page.locator('#status').inner_text()
    page.locator('#message').fill('演示睡觉');page.locator('#message').press('Enter')
    assert '演示' in page.locator('#history').inner_text()
    assert not errors,errors
    print('PASS browser: offline button, Enter, explicit offline reply')
    # Patch environment predicate only for browser-network simulation.
    server_html=html.replace("const isFile=location.protocol==='file:';const isLocalServer=location.hostname==='127.0.0.1'||location.hostname==='localhost';",
                   'const isFile=false;const isLocalServer=true;')
    page.evaluate('''() => {
       window.fakeMsgs=[];window.failReply=false;window.ready=true;
       window.fetch=async(url,options={})=>{
          if(url==='/api/state')return {ok:true,json:async()=>({
              state:{activity:'read',mood:0.7,interest:'给云取名字',energy:0.8,signal:false},
              history:window.fakeMsgs,
              capabilities:{version:'5.4',chat:{configured:window.ready},thought:{configured:false},mock:true}
          })};
          if(url==='/api/chat'){
              if(window.failReply)return {ok:false,json:async()=>({error:'模拟服务故障'})};
              const message=JSON.parse(options.body).message;
              const reply='模拟回复：'+message;
              window.fakeMsgs.push({role:'user',text:message},{role:'assistant',text:reply});
              return {ok:true,json:async()=>({reply,source:'mock',emotion:'curious',gesture:'nod',state:{activity:'read',emotion:'curious',mood:0.7}})};
          }
          throw Error('unexpected URL '+url);
       };
    }''')
    page.set_content(server_html,wait_until='load')
    page.locator('#avatar').click()
    page.locator('#message').fill('今天在做什么？');page.locator('#message').press('Enter')
    page.wait_for_function("() => document.querySelector('#status').textContent.includes('开发模拟回复')")
    assert '模拟回复：今天在做什么？' in page.locator('#history').inner_text()
    page.evaluate('window.failReply=true')
    page.locator('#message').fill('失败消息');page.locator('#send').click()
    page.wait_for_function("() => document.querySelector('#status').textContent.includes('发送失败')")
    assert page.locator('#message').input_value()=='失败消息'
    assert '模拟服务故障' in page.locator('#history').inner_text()
    assert '模拟回复：失败消息' not in page.locator('#history').inner_text()
    print('PASS browser: mocked API Enter, meaningful error and retry text restored')
    # Re-enter page with mock state persisted (simulates browser reopening).
    page.evaluate('window.failReply=false')
    page.set_content(server_html,wait_until='load')
    page.locator('#avatar').click()
    assert '模拟回复：今天在做什么？' in page.locator('#history').inner_text()
    print('PASS browser: conversation restored from backend history')
    assert not errors,errors
    page.locator('#close').click()
    page.locator('#avatar').screenshot(path=str(HERE/'previews'/'preview_character.png'),animations='disabled')
    browser.close()
