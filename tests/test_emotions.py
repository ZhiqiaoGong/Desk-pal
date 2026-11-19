from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent.parent
html=(ROOT/'index.html').read_text()
images=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':1200,'height':800})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html,wait_until='load')
    page.locator('#avatar').click()
    page.locator('#message').fill('演示散步')
    page.locator('#message').press('Enter')
    for name in ['平静','好奇','开心','烦躁','难过','困']:
        page.locator('#message').fill('演示'+name)
        page.locator('#message').press('Enter')
        page.wait_for_timeout(120)
        shot=ROOT/'previews'/f'emotion_{name}.png'
        page.locator('#avatar').screenshot(path=str(shot), animations='disabled')
        images.append((name,shot))
    # sleeping face unchanged in art geometry
    page.locator('#message').fill('演示睡觉')
    page.locator('#send').click()
    page.wait_for_timeout(120)
    page.locator('#avatar').screenshot(path=str(ROOT/'previews'/'sleep.png'),animations='disabled')
    assert not errors,errors
    browser.close()
font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
fnt=ImageFont.truetype(font,21) if Path(font).exists() else ImageFont.load_default()
w,h=290,300
sheet=Image.new('RGB',(3*w,2*h),'#f6eff6')
d=ImageDraw.Draw(sheet)
for i,(name,shot) in enumerate(images):
    im=Image.open(shot).convert('RGBA')
    x=(i%3)*w;y=(i//3)*h
    card=Image.new('RGB',im.size,'#f7eff7')
    card.paste(im,mask=im.getchannel('A'))
    sheet.paste(card,(x+(w-im.width)//2,y+8))
    d.text((x+10,y+260),name,fill='#514554',font=fnt)
sheet.save(ROOT/'previews'/'expressions_overview.png')
print('PASS six expressions displayed, screenshot:',ROOT/'previews'/'expressions_overview.png')
