#!/usr/bin/env python3
from pathlib import Path
import json
root = Path(__file__).resolve().parent; data = json.loads((root/'data/latest.json').read_text(encoding='utf-8'))
def cards(books):
    return ''.join(f'<article><a href="{b["url"]}" target="_blank" rel="noreferrer">{b["title"] or "未命名"}</a><p>评分：{b["score"] if b["score"] is not None else "—"}　|　在读：{b["reading"] or "—"}</p></article>' for b in books)
sections = [('新书榜', [b for g in data['new_books'] for b in g['books']]), ('高分作品', data['high_score']), ('高阅读量作品', [b for g in data['high_reading'] for b in g['books']])]
html = '<!doctype html><meta charset="utf-8"><title>番茄男频追踪</title><style>body{max-width:900px;margin:40px auto;font:16px system-ui;background:#10131a;color:#eee}section{margin:28px 0}article{padding:12px;margin:8px 0;background:#1b2130;border-radius:8px}a{color:#82cfff}p{color:#b7c0d4}</style><h1>番茄男频数据追踪</h1><p>更新时间：'+data['generated_at']+'</p>'+''.join('<section><h2>'+name+'</h2>'+cards(books[:100])+'</section>' for name,books in sections)
(root/'index.html').write_text(html,encoding='utf-8')
