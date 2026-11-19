"""Verify dashboard assembly against HTML with optional head end tags."""
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

root = Path(__file__).resolve().parent
with TemporaryDirectory() as temporary:
    site = Path(temporary)
    for route in ('analytics', 'en/analytics'):
        path = site / route / 'index.html'
        path.parent.mkdir(parents=True)
        path.write_text('<!doctype html><html><head><title>Analytics</title><body><main><div id="site-analytics"></div></main></html>', encoding='utf-8')
    subprocess.run([sys.executable, str(root / 'add_analytics.py'), str(site), '--baseurl', '/preview', '--website-id', 'test-id', '--share-slug', 'public-share', '--api-base', 'https://example.com/api'], check=True)
    for route in ('analytics', 'en/analytics'):
        rendered = (site / route / 'index.html').read_text(encoding='utf-8')
        assert rendered.count('id="site-analytics"') == 1
        assert rendered.count('/preview/assets/analytics/dashboard.js?v=') == 1
        assert rendered.count('/preview/assets/analytics/dashboard.css?v=') == 1
        assert rendered.index('dashboard.js') < rendered.index('<body>')
        assert 'iframe' not in rendered
        assert ('Date range' in rendered) == route.startswith('en/')
    assert (site / 'assets/analytics/world.json').read_bytes() == (root / 'analytics/world.json').read_bytes()
print('PASS: bilingual dashboard, optional head closing tag, base URL, assets, and map provenance.')
