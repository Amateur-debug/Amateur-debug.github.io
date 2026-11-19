"""Render the public Umami dashboard without changing theme templates."""
import argparse
import hashlib
from html import escape
from pathlib import Path
import re
import shutil

p = argparse.ArgumentParser()
p.add_argument('site', type=Path)
for name in ('website-id', 'share-slug', 'api-base'):
    p.add_argument('--' + name, required=True)
p.add_argument('--baseurl', default='')
args = p.parse_args()
source = Path(__file__).with_name('analytics')
destination = args.site / 'assets/analytics'
shutil.copytree(source, destination, dirs_exist_ok=True)
version = hashlib.sha256(b''.join(f.read_bytes() for f in sorted(source.rglob('*')) if f.is_file())).hexdigest()[:12]
asset = escape(args.baseurl.rstrip('/') + '/assets/analytics', quote=True)
for language, route in [('zh', 'analytics/index.html'), ('en', 'en/analytics/index.html')]:
    path = args.site / route
    if not path.exists():
        continue
    en = language == 'en'
    t = lambda zh, english: english if en else zh
    marker = '<div id="site-analytics"></div>'
    text = path.read_text(encoding='utf-8')
    if marker not in text:
        continue
    cards = ''.join(f'<div class="analytics-card"><span>{label}</span><strong data-stat="{key}">—</strong></div>'
                    for key, label in [('pageviews', t('浏览量', 'Page views')), ('visitors', t('访客数', 'Visitors')), ('visits', t('访问次数', 'Visits'))])
    panels = ''.join(f'<section class="analytics-panel"><h2>{label}</h2><div data-list="{key}"></div></section>'
                     for key, label in [('path', t('页面排行', 'Top pages')), ('referrer', t('来源网站', 'Referring websites')), ('browser', t('浏览器', 'Browsers')), ('device', t('设备', 'Devices'))])
    markup = f'''<div id="site-analytics" class="analytics" data-api-base="{escape(args.api_base, quote=True)}" data-share-slug="{escape(args.share_slug, quote=True)}" data-website-id="{escape(args.website_id, quote=True)}" data-assets="{asset}">
<form class="analytics-controls">
<label>{t('时间范围', 'Date range')}<select name="period"><option value="7">{t('近 7 天', 'Last 7 days')}</option><option value="30" selected>{t('近 30 天', 'Last 30 days')}</option><option value="90">{t('近 90 天', 'Last 90 days')}</option><option value="6month">{t('近 6 个月', 'Last 6 months')}</option></select></label>
<label class="analytics-path">{t('页面', 'Page')}<input name="path" list="analytics-paths" placeholder="{t('所有页面；或输入 /projects/', 'All pages; or enter /projects/')}" maxlength="2048" autocomplete="off"><datalist id="analytics-paths"></datalist></label>
<button type="submit">{t('查看', 'Apply')}</button><button type="button" data-reset>{t('重置', 'Reset')}</button>
</form>
<p class="analytics-status" role="status" aria-live="polite">{t('正在读取访问数据…', 'Loading traffic data…')}</p>
<div class="analytics-cards">{cards}</div>
<section class="analytics-panel"><h2>{t('访问趋势', 'Traffic over time')}</h2><div data-chart></div><details><summary>{t('查看每日数据', 'View daily data')}</summary><div data-daily></div></details></section>
<section class="analytics-panel"><h2>{t('访客地区', 'Visitor locations')}</h2><div class="analytics-geography"><div><div data-map></div><p class="analytics-map-label" aria-live="polite">{t('将鼠标移到地图上查看访客数', 'Hover over the map to see visitor counts')}</p></div><div data-list="country"></div></div>
</section>
<div class="analytics-grid">{panels}</div>
<p class="analytics-note">{t('数据来自 Umami · 时区 Asia/Shanghai · 排行按访客数排序，同一访客可能访问多个页面。数据更新可能略有延迟。', 'Data from Umami · Time zone: Asia/Shanghai · Rankings show visitors; a visitor may visit multiple pages. Data updates may be delayed.')}</p>
<noscript>{t('请启用 JavaScript 查看统计面板。', 'Enable JavaScript to view the dashboard.')}</noscript>
</div>'''
    includes = f'<link rel="stylesheet" href="{asset}/dashboard.css?v={version}"><script defer src="{asset}/vendor/d3.min.js?v={version}"></script><script defer src="{asset}/dashboard.js?v={version}"></script>'
    text = text.replace(marker, markup)
    text, placed = re.subn(r'<head\b[^>]*>', lambda match: match[0] + includes, text, count=1, flags=re.I)
    if placed != 1:
        raise ValueError(f'Missing HTML head: {path}')
    path.write_text(text, encoding='utf-8')
