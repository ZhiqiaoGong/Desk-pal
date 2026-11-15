from playwright.sync_api import sync_playwright
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import time
here=Path(__file__).parent
outputs=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--disable-dev-shm-usage','--no-sandbox','--disable-gpu'])
 page=browser.new_page(viewport={'width':900,'height':700},device_scale_factor=2)
 errors=[]
 page.on('pageerror', lambda e: errors.append(str(e)))
 page.set_content((here/'index.html').read_text(),wait_until='load',timeout=20000)
 for action,cmd in [('站立','演示发呆'),('散步','演示散步'),('做饭','演示做饭'),('睡觉','演示睡觉')]:
  page.locator('#avatar').click()
  page.locator('#message').fill(cmd)
  page.locator('#message').press('Enter')
  page.wait_for_timeout(400)
  assert '演示' in page.locator('#history').inner_text()
  page.locator('#close').click()
  page.wait_for_timeout(300)
  dest=here / f'preview_{ {"站立":"idle","散步":"walk","做饭":"cook","睡觉":"sleep"}[action]}.png'
  page.locator('#avatar').screenshot(path=str(dest), animations='disabled')
  outputs.append((action,dest))
  page.wait_for_timeout(1000)
 # Check button explicitly with offline reply
 page.locator('#avatar').click();page.locator('#message').fill('你好');page.locator('#send').click()
 assert '你好' in page.locator('#history').inner_text()
 assert not errors,errors
 browser.close()
items=[]
for name,path in outputs:
 im=Image.open(path).convert('RGB')
 canvas=Image.new('RGB',(im.width+30,im.height+58),'#ffffff')
 d=ImageDraw.Draw(canvas)
 d.text((15,5),name,fill='#303030',font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22))
 canvas.paste(im,(15,42))
 items.append(canvas)
montage=Image.new('RGB',(sum(i.width for i in items),max(i.height for i in items)),'#ffffff')
x=0
for im in items:montage.paste(im,(x,0));x+=im.width
montage.save(here/'preview_all.png')
print('visual screenshots saved, no page errors')
