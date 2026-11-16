"""Check generated site routing and local assets without third-party dependencies."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json
import sys


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.links = []
        self.text = path.read_text(encoding='utf-8')
        self.feed(self.text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('href', 'src'):
            value = attrs.get(key)
            if value:
                self.links.append(value)


site = Path(sys.argv[1]).resolve()
baseurl = sys.argv[2].rstrip('/') if len(sys.argv) > 2 else ''
pages = {p: Page(p) for p in site.rglob('*.html')}
for route in ('index.html', 'blog/index.html'):
    assert site / route in pages, f'Missing page: {route}'
assert 'class="post-preview' not in pages[site / 'index.html'].text
manifest = json.loads((site / 'site-build.json').read_text(encoding='utf-8'))
assert manifest['theme']
missing = []
for path, page in pages.items():
    for link in page.links:
        url = urlsplit(link)
        if url.scheme or url.netloc or not url.path:
            continue
        pathname = unquote(url.path)
        if pathname.startswith('/'):
            if baseurl and pathname.startswith(baseurl + '/'):
                pathname = pathname[len(baseurl):]
            destination = site / pathname.lstrip('/')
        else:
            destination = path.parent / pathname
        if destination.is_dir():
            destination /= 'index.html'
        if not destination.exists():
            missing.append((str(path.relative_to(site)), link))
assert not missing, f'Broken local links: {missing}'
assert not (site / 'site.yml').exists(), 'Do not publish content-source configuration'
assert not (site / 'examples').exists(), 'Do not publish examples'
if (site / 'en/index.html').exists():
    # Cached pages from before inline styles must not lose their language control.
    for legacy in ('assets/css/language-switch.css', 'en/assets/css/language-switch.css'):
        assert (site / legacy).is_file(), f'Missing compatibility stylesheet: {legacy}'
    for path, page in pages.items():
        if '<meta name="shared-blog-redirect"' in page.text:
            assert 'http-equiv="refresh"' in page.text and 'rel="canonical"' in page.text
            continue
        assert '<style id="language-switch-style">' in page.text, f'Missing inline switch style: {path}'
        assert 'class="site-language-switch"' in page.text, f'Missing language switch: {path}'
print(f"PASS: {manifest['theme']}; profile and blog; {len(pages)} HTML pages and all local links.")
