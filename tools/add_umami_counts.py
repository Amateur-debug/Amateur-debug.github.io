"""Display read-only Umami share counts independently of theme templates."""
import argparse
import hashlib
import html
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument('site', type=Path)
for name in ('url', 'website-id', 'share-slug', 'api-base'):
    parser.add_argument('--' + name, required=True)
parser.add_argument('--baseurl', default='')
args = parser.parse_args()
asset = args.site / 'assets/js/umami-counts.js'
asset.parent.mkdir(parents=True, exist_ok=True)
asset.write_bytes(Path(__file__).with_name('umami-counts.js').read_bytes())
version = hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
style = '''<style id="umami-counts-style">
.umami-counts { display: flex; flex-wrap: wrap; gap: .35rem 1rem;
  margin: 2rem 0 1rem; font-size: .8125rem; line-height: 1.6;
  color: var(--text-muted-color, #757575); }
.umami-counts > span { white-space: nowrap; }
.umami-counts [data-count] { font-variant-numeric: tabular-nums; }
</style>'''
escape = lambda value: html.escape(value, quote=True)
for path in args.site.rglob('*.html'):
    text = path.read_text(encoding='utf-8')
    if path.name == '404.html' or re.search(r'http-equiv=["\']refresh["\']', text, re.I):
        continue
    if '<main' not in text or 'id="umami-counts"' in text:
        continue
    en = bool(re.search(r'<html\b[^>]*\blang=["\']en(?:-[^"\']*)?["\']', text))
    period, page, site, unit, title = (
        ('Last 6 months', 'Page views', 'Site views', '', 'Umami page views; updates may be delayed.') if en else
        ('近 6 个月', '本页浏览', '全站浏览', ' 次', 'Umami 浏览量，数据更新可能略有延迟。'))
    markup = (f'<div id="umami-counts" class="umami-counts" role="group" aria-label="{title}" title="{title}" '
              f'data-origin="{escape(args.url.rstrip("/"))}" data-api-base="{escape(args.api_base.rstrip("/"))}" '
              f'data-share-slug="{escape(args.share_slug)}" data-website-id="{escape(args.website_id)}">'
              f'<span>{period}</span><span>{page} <span data-count="page">—</span>{unit}</span>'
              f'<span>{site} <span data-count="site">—</span>{unit}</span></div>')
    text, placed = re.subn(r'</main>', lambda m: markup + m[0], text, count=1, flags=re.I)
    if placed != 1:
        raise ValueError(f'Cannot place Umami counts: {path}')
    script = f'<script defer src="{escape(args.baseurl.rstrip("/") + "/assets/js/umami-counts.js")}?v={version}"></script>'
    text, placed = re.subn(r'<head\b[^>]*>', lambda m: m[0] + style + script, text, count=1, flags=re.I)
    if placed != 1:
        raise ValueError(f'Cannot load Umami counts: {path}')
    path.write_text(text, encoding='utf-8')
