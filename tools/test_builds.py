"""Integration check: the same Markdown works with both themes and blog pagination."""
from pathlib import Path
import re
import json
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

root = Path(__file__).resolve().parent.parent
original = Path(sys.argv[1] if len(sys.argv) > 1 else root.parent / 'docs').resolve()
build = root / '.build'
build.mkdir(exist_ok=True)
fixture = Path(tempfile.mkdtemp(prefix='content-test-', dir=build))
shutil.copytree(original, fixture, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git'))
# Website configuration comes only from pages/, not unrelated personal files.
(fixture / 'site.yml').write_text('private_personal_setting: do-not-read\n', encoding='utf-8')
(fixture / 'data').mkdir(exist_ok=True)
(fixture / 'data/contact.yml').write_text('invalid: [\n', encoding='utf-8')
(fixture / 'posts/library').mkdir(parents=True, exist_ok=True)
(fixture / 'posts/library/private.md').write_text('PRIVATE-NOTES-NOT-FOR-PUBLICATION', encoding='utf-8')
# These temporary posts never enter the content repository or live website.
for n in range(2, 12):
    (fixture / 'posts' / f'2020-01-{n:02}-fixture-{n}.md').write_text(
        f'---\ntitle: Fixture {n}\nlayout: another-theme-layout\ncategories: [Testing]\ntags: [fixture]\n---\n\nTest body {n}.\n', encoding='utf-8')
(fixture / 'posts/library/published.md').write_text('# Fixture 1\n\nShared body 1.\n\n![Figure](figure.svg)\n', encoding='utf-8')
(fixture / 'posts/library/figure.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding='utf-8')
(fixture / 'posts/library/private.svg').write_text('PRIVATE-IMAGE-NOT-FOR-PUBLICATION', encoding='utf-8')
(fixture / 'pages/blog.yml').write_text('articles:\n  - source: posts/library/published.md\n    slug: fixture-1\n    title: Fixture 1\n', encoding='utf-8')
(fixture / 'pages/untranslated.md').write_text('---\ntitle: Untranslated\n---\nChinese-only fixture.\n', encoding='utf-8')

for theme in ('chirpy', 'minimal'):
    output = build / f'test-{theme}'
    subprocess.run(['ruby', '-S', 'bundle', 'exec', 'ruby', 'tools/build.rb', '--content', str(fixture),
                    '--theme', theme, '--destination', str(output)], cwd=root, check=True)
    subprocess.run([sys.executable, 'tools/check_site.py', str(output)], cwd=root, check=True)
    for route in ('', 'projects/', 'publications/', 'resume/', 'blog/', 'blog/page2/', 'posts/fixture-1/', 'en/'):
        rendered = (output / route / 'index.html').read_text(encoding='utf-8')
        elements = Elements(rendered).elements
        trackers = [attrs for tag, attrs in elements if tag == 'script' and 'data-website-id' in attrs]
        assert len(trackers) == 1
        assert trackers[0]['data-website-id'] == 'e9335f5a-3352-46be-b3e9-ffaf8ad8348d'
        assert trackers[0]['src'] == 'https://cloud.umami.is/script.js'
        assert trackers[0]['data-domains'] == 'amateur-debug.github.io'
        assert rendered.count('id="umami-counts"') == 1
        assert sum(attrs.get('src', '').startswith('/assets/js/umami-counts.js?v=') for tag, attrs in elements if tag == 'script') == 1
    for page in output.rglob('*.html'):
        rendered = page.read_text(encoding='utf-8')
        assert 'busuanzi' not in rendered and 'site-pageviews' not in rendered
        if page.name == '404.html' or 'shared-blog-redirect' in rendered:
            assert 'data-website-id=' not in rendered
            assert 'id="umami-counts"' not in rendered
    assert not (output / 'assets/js/pageviews.js').exists()
    print(f'PASS {theme}: Umami on pages, shared articles and pagination; no duplicate redirect tracking or Busuanzi.')
    first = (output / 'blog/index.html').read_text(encoding='utf-8')
    second = (output / 'blog/page2/index.html').read_text(encoding='utf-8')
    article = (output / 'posts/fixture-1/index.html').read_text(encoding='utf-8')
    for rendered in (first, second, article):
        assert 'data-ts=' not in rendered
        assert 'article:published_time' not in rendered and 'datePublished' not in rendered
        assert not re.search(r'<time[^>]*>\s*\d{4}[-/]\d{2}[-/]\d{2}', rendered)
    assert '发表于' not in article
    assert '<published>' not in (output / 'feed.xml').read_text(encoding='utf-8')
    for path in output.rglob('search.json'):
        assert all('date' not in item for item in json.loads(path.read_text(encoding='utf-8')))
    print(f'PASS {theme}: dateless manifest, no publication dates in blog UI, search or SEO.')
    def main_links(html):
        main = re.search(r'<main\b[^>]*>(.*?)</main>', html, re.S).group(1)
        return set(re.findall(r'href="(/posts/fixture-\d+/)"', main))
    assert len(main_links(first)) == 10
    assert len(main_links(second)) == 1
    assert not main_links((output / 'index.html').read_text(encoding='utf-8'))
    assert (output / 'resume/index.html').exists()
    assert (output / 'projects/index.html').exists()
    assert not (output / 'notes').exists()
    assert not (output / 'pages/site.yml').exists()
    pagination = re.search(r'<nav\b[^>]*aria-label="(?:Page Navigation|博客分页)"[^>]*>(.*?)</nav>', second, re.S).group(1)
    assert 'href="/blog/"' in pagination and 'href="/"' not in pagination
    print(f'PASS {theme}: configuration from pages/, private notes excluded, profile homepage, resume/projects, 10+1 pagination, correct return link.')
    if (fixture / 'pages/en').exists():
        for route in ('', 'projects/', 'publications/', 'resume/'):
            zh = (output / route / 'index.html').read_text(encoding='utf-8')
            en = (output / 'en' / route / 'index.html').read_text(encoding='utf-8')
            for text, target, language in [(zh, '/en/' + route, 'en'), (en, '/' + route, 'zh-CN')]:
                elements = Elements(text).elements
                switches = [attrs for tag, attrs in elements if tag == 'a' and attrs.get('hreflang') == language]
                assert len(switches) == 1 and switches[0]['href'] == target
                assert 'target' not in switches[0], 'Language switching stays in the current tab'
                assert len([1 for tag, attrs in elements if tag == 'link' and attrs.get('hreflang') in ('en', 'zh-CN')]) == 2
            assert re.search(r'<html\b[^>]*lang="en"', en)
            assert 'href="/en/projects/"' in en and 'href="/en/resume/"' in en
        for route in ('blog/', 'blog/page2/', 'posts/fixture-1/'):
            redirect = (output / 'en' / route / 'index.html').read_text(encoding='utf-8')
            assert 'shared-blog-redirect' in redirect
            assert f'content="0;url=/{route}"' in redirect
        en_home = (output / 'en/index.html').read_text(encoding='utf-8')
        assert 'href="/blog/"' in en_home and 'href="/en/blog/"' not in en_home
        article = (output / 'posts/fixture-1/index.html').read_text(encoding='utf-8')
        assert 'Shared body 1.' in article and 'PRIVATE-NOTES' not in article
        assert 'href="/en/" lang="en" hreflang="en"' in article
        assert '<link rel="alternate" hreflang="en"' not in article
        assert (output / 'assets/blog/fixture-1/figure.svg').is_file()
        assert not list(output.rglob('private.svg'))
        assert not list(output.rglob('*seedvr*')), 'Only selected library entries may be published'
        unpaired = (output / 'untranslated/index.html').read_text(encoding='utf-8')
        assert 'href="/en/" lang="en" hreflang="en"' in unpaired
        assert 'no translation for this page' in unpaired
        assert not (output / 'en/notes').exists()
        assert not (output / 'en/site.yml').exists()
        if theme == 'chirpy':
            en_search = (output / 'en/assets/js/data/search.json').read_text(encoding='utf-8')
            assert 'Shared body 1.' in en_search and '/posts/fixture-' in en_search
            assert '/en/posts/fixture-' not in en_search
        print(f'PASS {theme}: bilingual pages, shared blog/search/pagination, legacy redirects, manifest-only publication and image isolation.')
