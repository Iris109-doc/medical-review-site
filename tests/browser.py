import json
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path('/workspace/medical-review-site')
content=json.loads((root/'data/courses.json').read_text())
c=content['courses'][0];q=c['questions'][0]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 ctx=browser.new_context(viewport={'width':1280,'height':800},has_touch=True)
 page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:4173');page.get_by_role('heading',name='把知识，梳理成自己的体系。').wait_for()
 page.screenshot(path=str(root/'preview-desktop.png'),full_page=False)
 page.locator('#search').fill('DRESS');assert page.locator('#nodes article').count()==1
 page.get_by_role('button',name='重置',exact=True).click()
 page.locator('[data-action="read"]').first.click();page.get_by_role('button',name='✓ 已读 · 点击撤销').wait_for()
 page.reload();page.get_by_role('button',name='✓ 已读 · 点击撤销').wait_for()
 page.locator('nav [data-page="cards"]').click();assert page.locator('.card-table').count()==len(content['courses'])
 flip=page.locator('[data-action="flip"]').first;assert flip.get_attribute('aria-expanded')=='false';flip.click();assert page.locator('[data-action="flip"]').first.get_attribute('aria-expanded')=='true'
 page.get_by_role('button',name='完成本次速览').first.click();page.get_by_role('button',name='✓ 本卡已复习 · 再次记录').wait_for()
 page.locator('nav [data-page="practice"]').click();assert page.locator('.question').count()==10
 first=page.locator('.question').first;assert first.locator('.answer').count()==0
 wrong=(q['answer']+1)%4
 first.locator(f'[data-option="{wrong}"]').click();first.get_by_role('button',name='提交并查看解析').click();first.locator('.answer').wait_for()
 page.locator('nav [data-page="weak"]').click();page.get_by_role('button',name='集中重练 →').click();assert page.locator('.question').count()==1
 page.locator('.question').first.locator(f'[data-option="{q["answer"]}"]').click();page.get_by_role('button',name='提交并查看解析').click();page.locator('.question').wait_for(state='detached')
 page.locator('#bank-filter').select_option('all');page.locator('[data-action="q-type"][data-type="short"]').click();assert page.locator('.question').count()==10
 first=page.locator('.question').first;first.locator('textarea').fill('按剥脱面积分为重叠，不按红斑范围。');first.get_by_role('button',name='展开参考要点并自评').click();first.get_by_role('button',name='自评：要点完整').click()
 page.locator('nav [data-page="weak"]').click();page.locator('.mastery-select').first.select_option('learning');page.reload();page.locator('nav [data-page="weak"]').click();assert page.locator('.mastery-select').first.input_value()=='learning'
 page.locator('nav [data-page="settings"]').click()
 with page.expect_download() as d:page.get_by_role('button',name='导出完整JSON备份 ↓').click()
 backup=root/'tests/temporary-backup.json';d.value.save_as(str(backup));b=json.loads(backup.read_text());assert len(b['state']['attempts'])==3
 page.on('dialog',lambda d:d.accept())
 page.locator('#import-file').set_input_files(str(backup));page.locator('#import-result').get_by_text('导入完成',exact=False).wait_for()
 with page.expect_download() as d:page.get_by_role('button',name='导出完整JSON备份 ↓').click()
 d.value.save_as(str(backup));assert len(json.loads(backup.read_text())['state']['attempts'])==3
 # New browser context restores backup, not merely current memory
 ctx2=browser.new_context();p2=ctx2.new_page();p2.goto('http://127.0.0.1:4173');p2.locator('nav [data-page="settings"]').click();p2.on('dialog',lambda d:d.accept());p2.locator('#import-file').set_input_files(str(backup));p2.locator('#import-result').get_by_text('导入完成',exact=False).wait_for();p2.locator('nav [data-page="weak"]').click();assert p2.locator('.mastery-select').first.input_value()=='learning'
 # Invalid content rejected without modifying courses
 bad=root/'tests/temporary-invalid.json';bad.write_text(json.dumps({'schemaVersion':1,'kind':'medical-review-content','courses':[]}));page.locator('#import-file').set_input_files(str(bad));page.get_by_text('未导入：课程必须为1–100项的数组',exact=False).wait_for()
 # Incremental new course import and duplicate skip
 new= json.loads(json.dumps(content));new['courses']=[new['courses'][0]];new['courses'][0]['id']='derm-second-course';new['courses'][0]['title']='增量课程测试';newfile=root/'tests/temporary-new.json';newfile.write_text(json.dumps(new));page.locator('#import-file').set_input_files(str(newfile));page.locator('#import-result').get_by_text('新增 1',exact=False).wait_for()
 page.locator('nav [data-page="cards"]').click();assert page.locator('.card-table').count()==len(content['courses'])+1;page.locator('#course-filter').select_option('derm-second-course');assert page.locator('.card-table').count()==1
 # Real new course filter, single card, answer display and source association
 page.locator('#course-filter').select_option('derm-autoimmune-skin')
 assert page.locator('.card-table').count()==1
 page.locator('nav [data-page="library"]').click();page.locator('#course-filter').select_option('derm-autoimmune-skin');assert page.locator('#nodes article').count()==11
 page.locator('nav [data-page="practice"]').click();page.locator('#course-filter').select_option('derm-autoimmune-skin');page.locator('#bank-filter').select_option('all')
 page.locator('[data-action="q-type"][data-type="mcq"]').click();assert page.locator('.question').count()==10
 nq=content['courses'][1]['questions'][0];first=page.locator('.question').first
 assert first.locator('.answer').count()==0
 first.locator(f'[data-option="{nq["answer"]}"]').click();first.get_by_role('button',name='提交并查看解析').click();first.locator('.answer').wait_for()
 assert '来源' in first.inner_text() or '页' in first.inner_text()
 page.locator('[data-action="q-type"][data-type="short"]').click();assert page.locator('.question').count()==10
 page.locator('nav [data-page="settings"]').click()
 page.locator('#import-file').set_input_files(str(root/'data/autoimmune-skin-v1.json'))
 page.locator('#import-result').get_by_text('跳过 1',exact=False).wait_for()
 # Tablet portrait, landscape and phone overflow checks
 for width,height in [(1280,800),(800,1280),(390,844)]:
  page.set_viewport_size({'width':width,'height':height})
  for tab in ['library','cards','practice','weak','settings']:
   page.locator(f'nav [data-page="{tab}"]').click()
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),(width,tab)
  page.locator('nav [data-page="library"]').click()
  
 # Produce clean previews with fresh records and only the real course.
 clean=browser.new_context(viewport={'width':1280,'height':800},has_touch=True)
 preview=clean.new_page();preview.goto('http://127.0.0.1:4173');preview.get_by_role('heading',name='把知识，梳理成自己的体系。').wait_for();preview.wait_for_timeout(300)
 preview.screenshot(path=str(root/'preview-desktop.png'))
 preview.set_viewport_size({'width':800,'height':1280});preview.wait_for_timeout(300);preview.screenshot(path=str(root/'preview-tablet.png'))
 preview.locator('nav [data-page="cards"]').click();preview.get_by_role('button',name='翻开全部答案').first.click();preview.wait_for_timeout(300);preview.screenshot(path=str(root/'preview-cards.png'),full_page=True)
 assert not errors,errors
 for f in [backup,bad,newfile]:f.unlink()
 browser.close()
 print('PASS: search, reading persistence, one-card flip, MCQ scoring and wrong-question recovery, short self-grade, mastery persistence, export, deduplicated restore in fresh context, invalid rejection, incremental content, filters and 3 viewport layouts. No JS errors.')
