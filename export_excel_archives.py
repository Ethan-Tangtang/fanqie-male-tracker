#!/usr/bin/env python3
"""Export non-dashboard Fanqie archive data to standalone Excel workbooks."""
from __future__ import annotations

import json
from pathlib import Path

import xlsxwriter

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'

HEADERS = [
    '作品名', '公开评分', '质量指数', '记录日期', '作品链接', '当前在读', '在读变化',
    '连续追踪天数', '日均在读增长', '持续信号分', '首次达标日期', '最近达标日期',
    '达标天数', '历史最高质量指数', '达标日期列表',
]

def value(book: dict, key: str):
    if key == '作品名': return book.get('title') or ''
    if key == '公开评分': return book.get('platform_rating')
    if key == '质量指数': return book.get('quality_score')
    if key == '记录日期': return book.get('last_qualified_on') or book.get('generated_at') or ''
    if key == '作品链接': return book.get('url') or ''
    if key == '当前在读': return book.get('reading_value')
    if key == '在读变化': return book.get('reading_change')
    if key == '连续追踪天数': return book.get('continuous_tracking_days') or book.get('tracking_days')
    if key == '日均在读增长': return book.get('average_daily_reading_growth')
    if key == '持续信号分': return book.get('sustained_income_signal')
    if key == '首次达标日期': return book.get('first_qualified_on')
    if key == '最近达标日期': return book.get('last_qualified_on')
    if key == '达标天数': return book.get('qualified_days')
    if key == '历史最高质量指数': return book.get('best_quality_score')
    if key == '达标日期列表': return ', '.join(book.get('qualified_dates') or [])
    return None

def export(filename: str, title: str, note: str, generated_at: str, books: list[dict]) -> None:
    workbook = xlsxwriter.Workbook(DATA / filename)
    sheet = workbook.add_worksheet('作品数据')
    sheet.hide_gridlines(2)
    title_fmt = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#FFFFFF', 'bg_color': '#1F4E78', 'align': 'left', 'valign': 'vcenter'})
    note_fmt = workbook.add_format({'font_color': '#52616B', 'text_wrap': True, 'valign': 'top'})
    head_fmt = workbook.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#2F75B5', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#D9E2F3'})
    text_fmt = workbook.add_format({'valign': 'top', 'border': 1, 'border_color': '#E6E6E6'})
    num_fmt = workbook.add_format({'num_format': '#,##0.0', 'valign': 'top', 'border': 1, 'border_color': '#E6E6E6'})
    int_fmt = workbook.add_format({'num_format': '#,##0', 'valign': 'top', 'border': 1, 'border_color': '#E6E6E6'})
    link_fmt = workbook.add_format({'font_color': '#0563C1', 'underline': 1, 'valign': 'top', 'border': 1, 'border_color': '#E6E6E6'})
    sheet.merge_range(0, 0, 0, len(HEADERS) - 1, title, title_fmt)
    sheet.merge_range(1, 0, 1, len(HEADERS) - 1, f'生成时间：{generated_at or "—"}。{note}', note_fmt)
    sheet.set_row(0, 28); sheet.set_row(1, 35)
    for col, header in enumerate(HEADERS): sheet.write(3, col, header, head_fmt)
    for row, book in enumerate(books, start=4):
        for col, header in enumerate(HEADERS):
            cell = value(book, header)
            if header == '作品链接' and cell:
                sheet.write_url(row, col, cell, link_fmt, '打开作品')
            elif header in {'公开评分', '质量指数', '持续信号分', '历史最高质量指数'}:
                sheet.write_number(row, col, cell, num_fmt) if isinstance(cell, (int, float)) else sheet.write_blank(row, col, None, num_fmt)
            elif header in {'当前在读', '在读变化', '连续追踪天数', '日均在读增长', '达标天数'}:
                sheet.write_number(row, col, cell, int_fmt) if isinstance(cell, (int, float)) else sheet.write_blank(row, col, None, int_fmt)
            else:
                sheet.write(row, col, cell or '', text_fmt)
    sheet.autofilter(3, 0, max(4, len(books) + 3), len(HEADERS) - 1)
    sheet.freeze_panes(4, 1)
    widths = [28, 10, 11, 13, 15, 12, 12, 13, 14, 11, 13, 13, 10, 15, 28]
    for col, width in enumerate(widths): sheet.set_column(col, col, width)
    workbook.close()

def main() -> None:
    sustained = json.loads((DATA / 'sustained_income_candidates.json').read_text(encoding='utf-8'))
    high_quality = json.loads((DATA / 'high_quality_index.json').read_text(encoding='utf-8'))
    export('持续收益潜力作品.xlsx', '持续收益潜力作品', sustained.get('note', ''), sustained.get('generated_at', ''), sustained.get('candidates', []))
    export('高质量作品历史库.xlsx', '质量指数 ≥ 80 作品历史库（URL 去重）', high_quality.get('note', ''), high_quality.get('generated_at', ''), high_quality.get('books', []))
    print('Wrote Excel archives')

if __name__ == '__main__':
    main()
