#!/usr/bin/env python3
"""手搖飲菜單工具：新增／更新 bubble-tea-menus.json 裡的品牌或單一分店菜單。

只用 Python 標準函式庫。常用指令：

  # 新增或更新一家店（菜單用文字檔，每行「分類：品項、品項…」）
  python3 tools/menu_tool.py add --id mili-qishan --name "米里 旗山店" \
      --match "米里.*旗山" --menu-file menu.txt \
      --source "https://..." --source-date 2026-10 --source-type 官方粉專 --confidence high

  # 菜單也可以用 JSON 檔：{"menu":[{"cat":"…","items":["…"]}], "url":"…", ...}
  python3 tools/menu_tool.py add --id mili-qishan --name "米里 旗山店" --match "米里.*旗山" --menu-json m.json

  python3 tools/menu_tool.py list            # 列出所有品牌／分店
  python3 tools/menu_tool.py show mili-qishan  # 看某家的菜單
  python3 tools/menu_tool.py remove mili-qishan
  python3 tools/menu_tool.py check           # 只檢查格式

每次 add／remove 都會把該筆的 updated 與檔案最上方的 version 設為今天，
推上 GitHub Pages 後，使用者開啟頁面時就會收到「菜單已更新」提示。
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

MENU_PATH = Path(__file__).resolve().parent.parent / 'bubble-tea-menus.json'
FIELDS = ['id', 'name', 'match', 'url', 'updated']
SOURCE_FIELDS = ['source', 'source_date', 'source_type', 'confidence']


def today():
    return datetime.date.today().isoformat()


def load():
    return json.loads(MENU_PATH.read_text(encoding='utf-8'))


def fmt_menu(menu, ind):
    rows = [f'{ind}  {{"cat": {json.dumps(x["cat"], ensure_ascii=False)}, "items": {json.dumps(x["items"], ensure_ascii=False)}}}' for x in menu]
    return '[\n' + ',\n'.join(rows) + f'\n{ind}]'


def dump(d):
    """用固定格式寫回（每個分類一行），方便看 git diff。"""
    js = lambda v: json.dumps(v, ensure_ascii=False)
    out = ['{', f' "version": {js(d["version"])},', f' "note": {js(d["note"])},', ' "chains": [']
    chains = []
    for c in d['chains']:
        head = ', '.join(f'"{k}": {js(c.get(k, ""))}' for k in FIELDS)
        src = ', '.join(f'"{k}": {js(c[k])}' for k in SOURCE_FIELDS if c.get(k))
        chains.append(f'  {{{head},\n' + (f'   {src},\n' if src else '') + f'   "menu": {fmt_menu(c["menu"], "   ")}}}')
    out.append(',\n'.join(chains))
    out.append(' ],')
    g = d['generic']
    out.append(f' "generic": {{"name": {js(g["name"])},\n  "menu": {fmt_menu(g["menu"], "  ")}}}')
    out.append('}')
    text = '\n'.join(out) + '\n'
    if json.loads(text) != d:
        sys.exit('內部錯誤：格式化結果與資料不一致，未寫入')
    MENU_PATH.write_text(text, encoding='utf-8')


def parse_menu_text(text):
    """與網頁「✏️ 更新菜單」相同的規則：每行「分類：品項、品項」，
    只寫「分類：」時，下面沒有冒號的行都歸入該分類；品項後的價格會去掉。"""
    cats, cur = {}, '其他'
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^([^:：、,，]{1,20})[:：](.*)$', line)
        rest = line
        if m:
            cur = re.sub(r'^[#【\[「]+|[】\]」]+$', '', m.group(1).strip()).strip() or '其他'
            rest = m.group(2)
        items = [re.sub(r'\s*(NT)?\$?\s*\d+\s*元?(\s*[/／]\s*\$?\d+\s*元?)?$', '', x.strip(), flags=re.I).strip()
                 for x in re.split(r'[、,，;；|｜\t]+|\s{2,}', rest)]
        arr = cats.setdefault(cur, [])
        for it in items:
            if it and it not in arr:
                arr.append(it)
    return [{'cat': c, 'items': it} for c, it in cats.items() if it]


def validate(d):
    errs = []
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', d.get('version', '')):
        errs.append('version 必須是 YYYY-MM-DD')
    ids = set()
    for c in d.get('chains', []):
        cid = c.get('id', '?')
        if not re.match(r'^[a-z0-9][a-z0-9-]*$', cid):
            errs.append(f'{cid}: id 只能用小寫英數與 -')
        if cid in ids:
            errs.append(f'{cid}: id 重複')
        ids.add(cid)
        if not c.get('name'):
            errs.append(f'{cid}: 缺 name')
        pat = c.get('match') or re.escape(c.get('name', ''))
        try:
            re.compile(pat, re.I)
        except re.error as e:
            errs.append(f'{cid}: match 不是合法的正規表示式（{e}）')
        # 網頁用 JavaScript 的 RegExp 解讀，只允許兩邊語法相同的寫法：
        # 群組只能是 ( )、(?: )、(?= )、(?! )；不能用 Python 專屬的 (?P…)、(?i) 等行內旗標、\A \Z
        if re.search(r'\(\?(?![:=!])', pat) or re.search(r'(?<!\\)\\[AZ]', pat):
            errs.append(f'{cid}: match 用了 JavaScript 不支援的語法（如 (?P…)、(?i)、\\A、\\Z），請改用一般寫法')
        if not isinstance(c.get('menu'), list) or not c['menu']:
            errs.append(f'{cid}: menu 不可為空')
        else:
            for m in c['menu']:
                ok = (isinstance(m, dict) and isinstance(m.get('cat'), str) and m['cat']
                      and isinstance(m.get('items'), list) and m['items']
                      and all(isinstance(i, str) and i for i in m['items']))
                if not ok:
                    errs.append(f'{cid}: 每個分類都要有 cat（文字）與 items（非空的文字清單），問題出在 {json.dumps(m, ensure_ascii=False)[:60]}')
    if not d.get('generic', {}).get('menu'):
        errs.append('generic 菜單不可為空')
    return errs


def cmd_add(a):
    d = load()
    if a.menu_json:
        j = json.loads(Path(a.menu_json).read_text(encoding='utf-8'))
        menu = j['menu'] if isinstance(j, dict) else j
        extra = j if isinstance(j, dict) else {}
    elif a.menu_file:
        menu, extra = parse_menu_text(Path(a.menu_file).read_text(encoding='utf-8')), {}
    else:
        menu, extra = parse_menu_text(sys.stdin.read()), {}
    if not menu:
        sys.exit('讀不到任何品項，請檢查菜單內容')
    old = next((c for c in d['chains'] if c['id'] == a.id), None)
    entry = dict(old or {})
    entry.update({k: v for k, v in extra.items() if k in FIELDS + SOURCE_FIELDS and v})
    for k in ['name', 'match', 'url'] + SOURCE_FIELDS:
        v = getattr(a, k)
        if v is not None:
            entry[k] = v
    entry['id'] = a.id
    entry.setdefault('name', a.id)
    entry.setdefault('match', re.escape(entry['name']))
    entry.setdefault('url', '')
    entry['updated'] = d['version'] = today()
    entry['menu'] = menu
    if old:
        d['chains'][d['chains'].index(old)] = entry
    else:
        d['chains'].append(entry)
    errs = validate(d)
    if errs:
        sys.exit('未寫入，格式有誤：\n  ' + '\n  '.join(errs))
    dump(d)
    n = sum(len(m['items']) for m in menu)
    print(f'{"更新" if old else "新增"} {entry["name"]}（{a.id}）：{len(menu)} 個分類、{n} 個品項；version → {d["version"]}')
    # 提醒：其他規則也比對得到這個名稱時，網頁會選比對到最長文字的那一筆
    others = [c['name'] for c in d['chains'] if c['id'] != a.id and re.search(c['match'], entry['name'], re.I)]
    if others:
        print(f'注意：店名「{entry["name"]}」也符合 {"、".join(others)} 的規則；網頁會採用比對到最長文字的那一筆。')


def cmd_remove(a):
    d = load()
    before = len(d['chains'])
    d['chains'] = [c for c in d['chains'] if c['id'] != a.id]
    if len(d['chains']) == before:
        sys.exit(f'找不到 {a.id}')
    d['version'] = today()
    dump(d)
    print(f'已移除 {a.id}；version → {d["version"]}')


def cmd_list(a):
    d = load()
    print(f'version {d["version"]}，共 {len(d["chains"])} 筆')
    for c in d['chains']:
        n = sum(len(m['items']) for m in c['menu'])
        print(f'  {c["id"]:16} {c["name"]:16} {n:3} 項  更新 {c.get("updated", "")}  比對 /{c.get("match", "")}/')


def cmd_show(a):
    c = next((c for c in load()['chains'] if c['id'] == a.id), None)
    if not c:
        sys.exit(f'找不到 {a.id}')
    print(f'{c["name"]}（{c["id"]}） 比對 /{c["match"]}/  {c.get("url", "")}')
    for m in c['menu']:
        print(f'{m["cat"]}：{"、".join(m["items"])}')


def cmd_check(a):
    errs = validate(load())
    if errs:
        sys.exit('格式有誤：\n  ' + '\n  '.join(errs))
    print('bubble-tea-menus.json 格式正確')


def main():
    p = argparse.ArgumentParser(description='手搖飲菜單工具（bubble-tea-menus.json）')
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('add', help='新增或更新一家品牌／分店的菜單')
    s.add_argument('--id', required=True, help='小寫英數與 -，例如 mili-qishan')
    s.add_argument('--name', help='顯示名稱，例如「米里 旗山店」')
    s.add_argument('--match', help='比對 OpenStreetMap 店名的正規表示式，例如「米里.*旗山」')
    s.add_argument('--url', help='官方網站或粉專')
    s.add_argument('--source', help='這份菜單的來源網址')
    s.add_argument('--source-date', dest='source_date', help='菜單版本日期，例如 2026-10')
    s.add_argument('--source-type', dest='source_type', help='官網、官方粉專、外送平台、媒體整理…')
    s.add_argument('--confidence', choices=['high', 'medium', 'low'])
    g = s.add_mutually_exclusive_group()
    g.add_argument('--menu-file', help='文字菜單檔（每行「分類：品項、品項」）；省略則從標準輸入讀')
    g.add_argument('--menu-json', help='JSON 菜單檔')
    s.set_defaults(fn=cmd_add)
    s = sub.add_parser('remove', help='移除一筆')
    s.add_argument('id')
    s.set_defaults(fn=cmd_remove)
    s = sub.add_parser('show', help='顯示一筆的菜單')
    s.add_argument('id')
    s.set_defaults(fn=cmd_show)
    sub.add_parser('list', help='列出全部').set_defaults(fn=cmd_list)
    sub.add_parser('check', help='檢查格式').set_defaults(fn=cmd_check)
    a = p.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
