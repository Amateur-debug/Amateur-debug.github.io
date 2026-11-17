"""Add page/site PV counters to rendered pages, independently of the theme."""
import argparse
import html
from pathlib import Path
import re


STYLE = '''
.site-pageviews { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem 1rem;
  margin: 2rem 0 1rem; font-size: .8125rem; line-height: 1.6;
  color: var(--text-muted-color, #757575); }
.site-pageviews > span { white-space: nowrap; }
.site-pageviews .view-count { font-variant-numeric: tabular-nums; }
'''.strip()


def add_pageviews(site, url, baseurl=''):
    asset = site / 'assets/js/pageviews.js'
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text(Path(__file__).with_name('pageviews.js').read_text(encoding='utf-8'), encoding='utf-8')
    count = 0
    for path in sorted(site.rglob('*.html')):
        text = path.read_text(encoding='utf-8')
        # Redirects must not count a visit twice; error pages are not content.
        if path.name == '404.html' or re.search(r'http-equiv=["\']refresh["\']', text, re.I):
            continue
        if '<main' not in text or 'id="site-pageviews"' in text:
            continue
        english = bool(re.search(r'<html\b[^>]*\blang=["\']en(?:-[^"\']*)?["\']', text))
        label, page_label, site_label, unit = (
            ('View counts', 'Page views', 'Site views', '') if english else
            ('浏览量统计', '本页浏览', '全站浏览', ' 次'))
        tip = ('Counts since tracking was enabled; refreshes count as views.' if english else
               '从启用统计后累计；刷新页面也计入浏览量。')
        markup = (f'<div id="site-pageviews" class="site-pageviews" role="group" '
                  f'aria-label="{label}" title="{tip}" '
                  f'data-origin="{html.escape(url.rstrip("/"), quote=True)}">'
                  f'<span>{page_label} <span class="view-count" id="busuanzi_value_page_pv">—</span>{unit}</span>'
                  f'<span>{site_label} <span class="view-count" id="busuanzi_value_site_pv">—</span>{unit}</span>'
                  '</div>')
        text, placed = re.subn(r'</main>', lambda m: markup + m[0], text, count=1, flags=re.I)
        if not placed:
            raise ValueError(f'Cannot place page views: {path}')
        head = (f'<style id="site-pageviews-style">{STYLE}</style>'
                f'<script defer src="{html.escape(baseurl.rstrip("/") + "/assets/js/pageviews.js", quote=True)}"></script>')
        text, placed = re.subn(r'<head\b[^>]*>', lambda m: m[0] + head, text, count=1, flags=re.I)
        if not placed:
            raise ValueError(f'Cannot load page views: {path}')
        path.write_text(text, encoding='utf-8')
        count += 1
    print(f'Added page/site view counters to {count} pages.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('site', type=Path)
    parser.add_argument('--url', required=True)
    parser.add_argument('--baseurl', default='')
    args = parser.parse_args()
    add_pageviews(args.site, args.url, args.baseurl)
