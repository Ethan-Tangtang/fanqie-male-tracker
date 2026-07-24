#!/usr/bin/env python3
"""Render the static dashboard from the latest public snapshot."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / 'data/latest.json').read_text(encoding='utf-8'))
sustained_path = ROOT / 'data/sustained_income_candidates.json'
sustained = json.loads(sustained_path.read_text(encoding='utf-8')) if sustained_path.exists() else {'candidates': []}

def flatten(groups):
    return [book for group in groups for book in group.get('books', [])]

def metric(book):
    platform_rating = book.get('platform_rating')
    rating = f'{platform_rating:.1f}' if isinstance(platform_rating, (float, int)) else '暂无公开评分'
    delta = book.get('reading_change', 0)
    delta_text = f'+{delta:,}' if delta > 0 else f'{delta:,}'
    return f'''<article>
      <a href="{html.escape(book['url'])}" target="_blank" rel="noreferrer">{html.escape(book.get('title') or '未命名')}</a>
      <p><b>平台评分：</b>{rating}　<b>质量指数：</b>{book.get('quality_score', '—')} / 100</p>
      <p>在读：{html.escape(book.get('reading') or '—')}　排名：#{book.get('rank', '—')}　追踪：{book.get('tracking_days', 1)} 天　较上次：{delta_text}</p>
    </article>'''

sections = [
    ('新书榜 Top 30', flatten(data.get('new_books', []))),
    ('高质量作品 Top 30', data.get('high_score', [])),
    ('潜力新书榜', data.get('potential_new', [])),
    ('持续收益潜力候选', sustained.get('candidates', [])),
    ('高阅读量作品 Top 30', flatten(data.get('high_reading', []))),
]
body = ''.join(f'<section><h2>{title}</h2>{"".join(metric(book) for book in books[:30]) or "<p>暂无数据</p>"}</section>' for title, books in sections)
page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>番茄男频数据追踪</title>
<style>body{{max-width:960px;margin:38px auto;padding:0 18px;font:16px system-ui;background:#10131a;color:#edf2fa}}h1{{margin-bottom:4px}}h2{{margin-top:36px}}section{{border-top:1px solid #2a3447}}article{{padding:13px 15px;margin:9px 0;background:#1b2130;border-radius:9px}}a{{font-size:17px;color:#82cfff;text-decoration:none}}p{{margin:7px 0 0;color:#bac6da;line-height:1.55}}.note{{font-size:14px;color:#93a3bf}}</style>
<h1>番茄男频数据追踪</h1><p>最近更新：{html.escape(data.get('generated_at', '—'))}</p>
<p class="note">“平台评分”仅在番茄公开页可读取时显示；“质量指数”基于公开排名、在读与变化计算。追踪天数是本项目连续快照出现天数，不代表读者停留时长、完读率或用户行为。</p>{body}</html>'''
(ROOT / 'index.html').write_text(page, encoding='utf-8')
