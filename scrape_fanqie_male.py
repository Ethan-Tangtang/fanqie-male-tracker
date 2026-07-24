#!/usr/bin/env python3
'''Collect public Fanqie male-channel new and reading ranks, then derive high-score works.'''
from __future__ import annotations
import argparse, json, math, re, time
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
    try:
        page.goto(rank_url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(800)
    except Exception as exc:
        print(f"category index skipped: {rank_url} ({exc})")
        return []
    rows = page.eval_on_selector_all('a[href*="/rank/1_"]', "els => els.map(e => [e.innerText.trim(), e.getAttribute('href')])")
    out, seen = [], set()
    for name, href in rows:
        if href and href not in seen and re.match(r"/rank/1_[12]_\d+", href):
            seen.add(href); out.append((decode_text(name) or href.rsplit('_', 1)[-1], BASE + href))
    return out

def collect_rank(page, label: str, url: str, limit: int, delay: float, category_limit: int) -> list[dict]:
    result = []
    for category, rank_url in categories(page, url)[:category_limit or None]:
        try:
            page.goto(rank_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(800)
            # Rank pages are lazy-loaded; three larger scrolls reveal the top 30 cards.
            for _ in range(3):
                page.mouse.wheel(0, 1100)
                page.wait_for_timeout(600)
            books = [parse_card(x) for x in page.evaluate(CARD_EXTRACTOR)[:limit]]
        except Exception as exc:
            print(f"{label}: {category}: skipped ({exc})")
            continue
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

def previous_index() -> dict:
    latest = DATA / 'latest.json'
    if not latest.exists():
        return {}
    try:
        payload = json.loads(latest.read_text(encoding='utf-8'))
        books = [b for group in payload.get('new_books', []) + payload.get('high_reading', []) for b in group.get('books', [])]
        return {book['url']: book for book in books if book.get('url')}
    except (OSError, json.JSONDecodeError):
        return {}

def enrich_observations(groups: list[dict], previous: dict, is_new_rank: bool) -> None:
    for group in groups:
        for position, book in enumerate(group['books'], start=1):
            prior = previous.get(book['url'], {})
            old_reading = float(prior.get('reading_value') or 0)
            reading_delta = round(book['reading_value'] - old_reading)
            tracking_days = int(prior.get('tracking_days') or 0) + 1
            rank_component = max(0, 1 - (position - 1) / 30) * 25
            reading_component = min(1, math.log10(book['reading_value'] + 1) / 7) * 35
            trend_component = min(15, max(-5, reading_delta / max(1, old_reading) * 100)) if old_reading else 5
            quality_score = round(min(100, max(0, 25 + rank_component + reading_component + trend_component + (10 if is_new_rank else 0))), 1)
            platform_rating = book.get('score')
            book.update({
                'book_id': book['url'].rsplit('/', 1)[-1],
                'rank': position,
                'platform_rating': platform_rating,
                'rating_source': 'public_page' if platform_rating is not None else 'not_public',
                'quality_score': quality_score,
                'quality_score_note': '公开信号指数（排名、在读、变化），不是番茄平台评分',
                'tracking_days': tracking_days,
                'reading_change': reading_delta,
            })

def unique_books(groups: list[dict]) -> list[dict]:
    result = {}
    for group in groups:
        for book in group['books']:
            current = result.get(book['url'])
            if current is None or book['quality_score'] > current['quality_score']:
                result[book['url']] = book
    return list(result.values())

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--limit', type=int, default=30); ap.add_argument('--sleep', type=float, default=0.5); ap.add_argument('--category-limit', type=int, default=0, help='Limit categories for a smoke test; 0 means all'); ap.add_argument('--enrich-platform-ratings', action='store_true', help='Visit public detail pages to attempt rating extraction; may be slower'); ap.add_argument('--headed', action='store_true'); args = ap.parse_args()
    previous = previous_index()
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36')
        new = collect_rank(page, 'new_books', RANKS['new_books'], args.limit, args.sleep, args.category_limit)
        reading = collect_rank(page, 'high_reading', RANKS['high_reading'], args.limit, args.sleep, args.category_limit)
        rated = enrich_scores(page, new + reading, args.sleep) if args.enrich_platform_ratings else []
        browser.close()
    enrich_observations(new, previous, True)
    enrich_observations(reading, previous, False)
    all_books = unique_books(new + reading)
    rated_by_url = {book['url']: book for book in rated}
    for book in all_books:
        if book['url'] in rated_by_url:
            book['platform_rating'] = rated_by_url[book['url']]['score']
            book['score'] = book['platform_rating']
            book['rating_source'] = 'public_page'
    high_score = sorted(all_books, key=lambda book: (book.get('platform_rating') is not None, book.get('platform_rating') or 0, book['quality_score'], book['reading_value']), reverse=True)[:30]
    potential_new = sorted(unique_books(new), key=lambda book: (book['quality_score'], book['reading_value']), reverse=True)[:20]
    stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
    payload = {"generated_at": stamp, "channel": "male", "new_books": new, "high_reading": reading, "high_score": high_score, "potential_new": potential_new, "metrics_note": {"platform_rating": "番茄公开页未提供时显示暂无公开评分", "tracking_days": "本项目连续快照中出现的天数，不是用户阅读时长或完读率", "reading_change": "相对上一份快照的在读数变化"}}
    (SNAPSHOTS / f"male_{datetime.now().strftime('%Y%m%d')}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (DATA / 'latest.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Wrote data/latest.json')
if __name__ == '__main__': main()
