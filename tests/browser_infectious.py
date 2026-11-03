"""Exercise adding the public course to an already-used browser, without user data."""
import json
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
content = json.loads((ROOT / 'data/courses.json').read_text())
new = next(c for c in content['courses'] if c['id'] == 'derm-infectious-skin')
old = {**content, 'courses': [c for c in content['courses'] if c['id'] != new['id']]}
oldq = old['courses'][0]['questions'][0]
newq = next(q for q in new['questions'] if q['type'] == 'mcq')

with tempfile.TemporaryDirectory(prefix='infectious-browser-') as tmp, sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    ctx = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('dialog', lambda d: d.accept())
    # Simulate a browser which loaded the previous two-course release.
    page.route('**/data/courses.json', lambda route: route.fulfill(json=old))
    page.goto('http://127.0.0.1:4173')
    page.get_by_role('heading', name='把知识，梳理成自己的体系。').wait_for()
    page.locator('[data-action="read"]').first.click()
    page.locator('nav [data-page="practice"]').click()
    page.locator('.question').first.locator(f'[data-option="{oldq["answer"]}"]').click()
    page.locator('.question').first.get_by_role('button', name='提交并查看解析').click()
    page.locator('.question .answer').wait_for()
    page.unroute('**/data/courses.json')
    page.reload()
    page.locator('nav [data-page="cards"]').click()
    assert page.locator('.card-table').count() == 2  # New server JSON does not overwrite IndexedDB.

    def export_state(filename):
        page.locator('nav [data-page="settings"]').click()
        path = Path(tmp) / filename
        with page.expect_download() as download:
            page.get_by_role('button', name='导出完整JSON备份 ↓').click()
        download.value.save_as(str(path))
        return json.loads(path.read_text()), path

    before, _ = export_state('before.json')
    assert len(before['state']['attempts']) == 1
    page.locator('#import-file').set_input_files(str(ROOT / 'data/infectious-skin-v1.json'))
    page.locator('#import-result').get_by_text('新增 1', exact=False).wait_for()
    imported, _ = export_state('imported.json')
    assert imported['state'] == before['state']
    assert len(imported['courses']) == 3
    page.locator('#import-file').set_input_files(str(ROOT / 'data/infectious-skin-v1.json'))
    page.locator('#import-result').get_by_text('跳过 1', exact=False).wait_for()

    # Reject same-version conflicts without altering stored state or course contents.
    conflict = json.loads((ROOT / 'data/infectious-skin-v1.json').read_text())
    conflict['courses'][0]['title'] += '冲突'
    badpath = Path(tmp) / 'conflict.json'
    badpath.write_text(json.dumps(conflict))
    page.locator('#import-file').set_input_files(str(badpath))
    page.locator('#import-result').get_by_text('同版本内容冲突', exact=False).wait_for()
    unchanged, _ = export_state('unchanged.json')
    assert unchanged['courses'] == imported['courses']
    assert unchanged['state'] == before['state']

    def tab(name):
        page.locator(f'nav [data-page="{name}"]').click()
        page.locator('#course-filter').select_option(new['id'])

    tab('library')
    assert page.locator('#nodes article').count() == 17
    tab('cards')
    assert page.locator('.card-table').count() == 1
    assert page.locator('.card-table tbody tr').count() == 12
    page.get_by_role('button', name='翻开全部答案', exact=True).click()
    page.screenshot(path=str(ROOT / 'preview-infectious-card.png'), full_page=True)
    tab('practice')
    assert '匹配 100 题' in page.locator('.bank-note').inner_text()
    # Traverse all ten pages: all 100 questions are reachable and explanations start hidden.
    ids = []
    for i in range(10):
        assert page.locator('.question').count() == 10
        assert page.locator('.question .answer').count() == 0
        ids.extend(page.locator('.question').evaluate_all('(els) => els.map(e => e.id)'))
        if i < 9:
            page.get_by_role('button', name='下一页 →', exact=True).click()
    assert len(set(ids)) == 100
    tab('practice')
    first = page.locator('.question').first
    # Browsing an answer alone must not create a scored attempt.
    first.get_by_role('button', name='仅展开答案与解析', exact=True).click()
    first.locator('.answer').wait_for()
    browsed, _ = export_state('browsed.json')
    assert browsed['state'] == before['state']
    tab('practice')
    first = page.locator('.question').first
    wrong = (newq['answer'] + 1) % 4
    first.locator(f'[data-option="{wrong}"]').click()
    first.get_by_role('button', name='提交并查看解析').click()
    assert '正确答案' in first.locator('.answer').inner_text()
    assert '页' in first.locator('.answer').inner_text()
    page.reload()
    tab('practice')
    page.locator('#bank-filter').select_option('wrong')
    assert page.locator('.question').count() == 1
    first = page.locator('.question').first
    first.locator(f'[data-option="{newq["answer"]}"]').click()
    first.get_by_role('button', name='提交并查看解析').click()
    first.wait_for(state='detached')
    page.locator('#bank-filter').select_option('all')
    page.locator('[data-action="q-type"][data-type="short"]').click()
    assert '匹配 12 题' in page.locator('.bank-note').inner_text()
    first = page.locator('.question').first
    first.locator('textarea').fill('临时测试回答：结合形态、部位、复发史与检查。')
    first.get_by_role('button', name='展开参考要点并自评').click()
    first.get_by_role('button', name='自评：仍需巩固', exact=True).click()
    final, backup = export_state('final.json')
    assert len(final['state']['attempts']) == 4
    assert final['state']['attempts'][0] == before['state']['attempts'][0]
    assert len([a for a in final['state']['attempts'] if a['courseId'] == new['id']]) == 3
    # A fresh browser can restore both courses and the independently entered test records.
    ctx2 = browser.new_context()
    restored = ctx2.new_page()
    restored.on('dialog', lambda d: d.accept())
    restored.goto('http://127.0.0.1:4173')
    restored.locator('nav [data-page="settings"]').click()
    restored.locator('#import-file').set_input_files(str(backup))
    restored.locator('#import-result').get_by_text('导入完成', exact=False).wait_for()
    with restored.expect_download() as dl:
        restored.get_by_role('button', name='导出完整JSON备份 ↓').click()
    restored_path = Path(tmp) / 'restored.json'
    dl.value.save_as(str(restored_path))
    assert json.loads(restored_path.read_text())['state'] == final['state']

    # Original-node jump must expose the source context for the new course.
    tab('practice')
    page.locator('[data-action="q-type"][data-type="mcq"]').click()
    page.locator('.question').first.get_by_role('button', name='原知识点 ↗').click()
    assert page.locator('#nodes article').count() == 1
    assert '页' in page.locator('#nodes article').inner_text()
    for width, height in [(1280,800),(800,1280),(390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        for name in ['library','cards','practice','weak']:
            tab(name)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), (width,name)
    assert not errors, errors
    browser.close()
    print('PASS: existing-browser upgrade, prior history preserved, duplicate/conflict import, 100 reachable MCQs, one card, reveal/scoring/persistence, short self-grade, backup restore, sources and 3 viewport layouts; no JS errors.')
