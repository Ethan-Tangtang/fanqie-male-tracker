#!/usr/bin/env python3
'''Collect public Fanqie male-channel new and reading ranks, then derive high-score works.'''
from __future__ import annotations
import argparse, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
BASE = "https://fanqienovel.com"
RANKS = {"new_books": f"{BASE}/rank/1_1", "high_reading": f"{BASE}/rank/1_2"}
START_CODE = 58344
CHAR_SEQUENCE = ['D', '在', '主', '特', '家', '军', '然', '表', '场', '4', '要', '只', 'v', '和', '?', '6', '别', '还', 'g', '现', '儿', '岁', '?', '?', '此', '象', '月', '3', '出', '战', '工', '相', 'o', '男', '直', '失', '世', 'F', '都', '平', '文', '什', 'V', 'O', '将', '真', 'T', '那', '当', '?', '会', '立', '些', 'u', '是', '十', '张', '学', '气', '大', '爱', '两', '命', '全', '后', '东', '性', '通', '被', '1', '它', '乐', '接', '而', '感', '车', '山', '公', '了', '常', '以', '何', '可', '话', '先', 'p', 'i', '叫', '轻', 'M', '士', 'w', '着', '变', '尔', '快', 'l', '个', '说', '少', '色', '里', '安', '花', '远', '7', '难', '师', '放', 't', '报', '认', '面', '道', 'S', '?', '克', '地', '度', 'I', '好', '机', 'U', '民', '写', '把', '万', '同', '水', '新', '没', '书', '电', '吃', '像', '斯', '5', '为', 'y', '白', '几', '日', '教', '看', '但', '第', '加', '候', '作', '上', '拉', '住', '有', '法', 'r', '事', '应', '位', '利', '你', '声', '身', '国', '问', '马', '女', '他', 'Y', '比', '父', 'x', 'A', 'H', 'N', 's', 'X', '边', '美', '对', '所', '金', '活', '回', '意', '到', 'z', '从', 'j', '知', '又', '内', '因', '点', 'Q', '三', '定', '8', 'R', 'b', '正', '或', '夫', '向', '德', '听', '更', '?', '得', '告', '并', '本', 'q', '过', '记', 'L', '让', '打', 'f', '人', '就', '者', '去', '原', '满', '体', '做', '经', 'K', '走', '如', '孩', 'c', 'G', '给', '使', '物', '?', '最', '笑', '部', '?', '员', '等', '受', 'k', '行', '一', '条', '果', '动', '光', '门', '头', '见', '往', '自', '解', '成', '处', '天', '能', '于', '名', '其', '发', '总', '母', '的', '死', '手', '入', '路', '进', '心', '来', 'h', '时', '力', '多', '开', '已', '许', 'd', '至', '由', '很', '界', 'n', '小', '与', 'Z', '想', '代', '么', '分', '生', '口', '再', '妈', '望', '次', '西', '风', '种', '带', 'J', '?', '实', '情', '才', '这', '?', 'E', '我', '神', '格', '长', '觉', '间', '年', '眼', '无', '不', '亲', '关', '结', '0', '友', '信', '下', '却', '重', '己', '老', '2', '音', '字', 'm', '呢', '明', '之', '前', '高', 'P', 'B', '目', '太', 'e', '9', '起', '稜', '她', '也', 'W', '用', '方', '子', '英', '每', '理', '便', '四', '数', '期', '中', 'C', '外', '样', 'a', '海', '们', '任']

def decode_text(value: str) -> str:
    return ''.join(CHAR_SEQUENCE[ord(char) - START_CODE] if 0 <= ord(char) - START_CODE < len(CHAR_SEQUENCE) else char for char in (value or ''))

CARD_EXTRACTOR = r'''() => {
  const seen = new Set(), cards = [];
  for (const link of document.querySelectorAll('a[href^="/page/"]')) {
    const href = link.getAttribute('href'); if (seen.has(href)) continue;
    let node = link; for (let i=0; node && i<7; i++, node=node.parentElement) {
      const text = node.innerText || '';
      if (node.querySelector('img') && /在读|评分|分/.test(text)) {
        seen.add(href); cards.push({href, text, title: (node.querySelector('img')?.alt || link.innerText || '').trim(), cover: node.querySelector('img')?.src || ''}); break;
      }
    }
  } return cards;
}'''
DETAIL_SCORE_EXTRACTOR = r'''() => document.body.innerText || '' '''

def number(value: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*([万亿]?)", value or "")
    if not m: return 0.0
    return float(m.group(1)) * {"万": 1e4, "亿": 1e8}.get(m.group(2), 1)

def parse_card(card: dict) -> dict:
    text = re.sub(r"\s+", " ", decode_text(card["text"]))
    read = re.search(r"(?:在读|阅读)\s*[:：]?\s*(\d+(?:\.\d+)?[万亿]?)", text)
    score = re.search(r"(?<!\d)([6-9](?:\.\d)?|10(?:\.0)?)\s*分", text)
    return {"title": decode_text(card["title"]), "url": BASE + card["href"], "cover": card["cover"],
            "reading": read.group(1) if read else None, "reading_value": number(read.group(1) if read else ''),
            "score": float(score.group(1)) if score else None}

def categories(page, rank_url: str) -> list[tuple[str, str]]:
    page.goto(rank_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)
    rows = page.eval_on_selector_all('a[href*="/rank/1_"]', "els => els.map(e => [e.innerText.trim(), e.getAttribute('href')])")
    out, seen = [], set()
    for name, href in rows:
        if href and href not in seen and re.match(r"/rank/1_[12]_\d+", href):
            seen.add(href); out.append((decode_text(name) or href.rsplit('_', 1)[-1], BASE + href))
    return out

def collect_rank(page, label: str, url: str, limit: int, delay: float, category_limit: int) -> list[dict]:
    result = []
    for category, rank_url in categories(page, url)[:category_limit or None]:
        page.goto(rank_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1200)
        # 排行页为懒加载；较大滚动距离可稳定呈现前 30 张卡片。
        for _ in range(3): page.mouse.wheel(0, 1100); page.wait_for_timeout(700)
        books = [parse_card(x) for x in page.evaluate(CARD_EXTRACTOR)[:limit]]
        result.append({"category": category, "books": books})
        print(f"{label}: {category}: {len(books)} books")
        time.sleep(delay)
    return result

def enrich_scores(page, groups: list[dict], delay: float) -> list[dict]:
    unique = {b['url']: b.copy() for group in groups for b in group['books']}
    for book in unique.values():
        if book['score'] is not None: continue
        try:
            page.goto(book['url'], wait_until="domcontentloaded", timeout=30000); page.wait_for_timeout(500)
            text = page.evaluate(DETAIL_SCORE_EXTRACTOR)
            m = re.search(r"(?<!\d)([6-9](?:\.\d+)?|10(?:\.0)?)\s*分", text)
            if m: book['score'] = float(m.group(1))
        except Exception as exc: print(f"score skipped: {book['url']} ({exc})")
        time.sleep(delay)
    return sorted((b for b in unique.values() if b['score'] is not None), key=lambda b: (b['score'], b['reading_value']), reverse=True)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--limit', type=int, default=30); ap.add_argument('--sleep', type=float, default=4); ap.add_argument('--category-limit', type=int, default=0, help='Limit categories for a smoke test; 0 means all'); ap.add_argument('--skip-scores', action='store_true', help='Save rank data without visiting detail pages for score enrichment'); ap.add_argument('--headed', action='store_true'); args = ap.parse_args()
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36')
        new = collect_rank(page, 'new_books', RANKS['new_books'], args.limit, args.sleep, args.category_limit)
        reading = collect_rank(page, 'high_reading', RANKS['high_reading'], args.limit, args.sleep, args.category_limit)
        high_score = [] if args.skip_scores else enrich_scores(page, new + reading, args.sleep)
        browser.close()
    stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
    payload = {"generated_at": stamp, "channel": "male", "new_books": new, "high_reading": reading, "high_score": high_score}
    (SNAPSHOTS / f"male_{datetime.now().strftime('%Y%m%d')}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (DATA / 'latest.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Wrote data/latest.json')
if __name__ == '__main__': main()
