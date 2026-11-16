"""Integration check: the same Markdown works with both themes and blog pagination."""
from pathlib import Path
import re
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
(fixture / 'notes').mkdir(exist_ok=True)
(fixture / 'notes/private.md').write_text('PRIVATE-NOTES-NOT-FOR-PUBLICATION', encoding='utf-8')
# These temporary posts never enter the content repository or live website.
for n in range(1, 12):
    (fixture / 'posts' / f'2020-01-{n:02}-fixture-{n}.md').write_text(
        f'---\ntitle: Fixture {n}\nlayout: another-theme-layout\ncategories: [Testing]\ntags: [fixture]\n---\n\nTest body {n}.\n', encoding='utf-8')
    if (fixture / 'pages/en').exists():
        (fixture / 'posts/en').mkdir(exist_ok=True)
        (fixture / 'posts/en' / f'2020-01-{n:02}-fixture-{n}.md').write_text(
            f'---\ntitle: English fixture {n}\ncategories: [Testing]\ntags: [fixture]\n---\n\nEnglish body {n}.\n', encoding='utf-8')
(fixture / 'pages/untranslated.md').write_text('---\ntitle: Untranslated\n---\nChinese-only fixture.\n', encoding='utf-8')

for theme in ('chirpy', 'minimal'):
    output = build / f'test-{theme}'
    subprocess.run(['ruby', '-S', 'bundle', 'exec', 'ruby', 'tools/build.rb', '--content', str(fixture),
                    '--theme', theme, '--destination', str(output)], cwd=root, check=True)
    subprocess.run([sys.executable, 'tools/check_site.py', str(output)], cwd=root, check=True)
    first = (output / 'blog/index.html').read_text(encoding='utf-8')
    second = (output / 'blog/page2/index.html').read_text(encoding='utf-8')
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
        for route in ('', 'projects/', 'publications/', 'resume/', 'blog/', 'blog/page2/', 'posts/fixture-1/'):
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
        en_first = (output / 'en/blog/index.html').read_text(encoding='utf-8')
        en_second = (output / 'en/blog/page2/index.html').read_text(encoding='utf-8')
        en_first_main = re.search(r'<main\b[^>]*>(.*?)</main>', en_first, re.S).group(1)
        en_second_main = re.search(r'<main\b[^>]*>(.*?)</main>', en_second, re.S).group(1)
        assert len(set(re.findall(r'href="(/en/posts/fixture-\d+/)"', en_first_main))) == 10
        assert len(set(re.findall(r'href="(/en/posts/fixture-\d+/)"', en_second_main))) == 1
        assert 'English fixture' in en_first and 'English fixture' not in first
        assert 'href="/en/blog/"' in en_second
        assert '学习笔记' not in en_first and '>博客<' not in en_first
        unpaired = (output / 'untranslated/index.html').read_text(encoding='utf-8')
        assert 'href="/en/blog/" lang="en" hreflang="en"' in unpaired
        assert 'no translation for this page' in unpaired
        assert not (output / 'en/notes').exists()
        assert not (output / 'en/site.yml').exists()
        if theme == 'chirpy':
            zh_search = (output / 'assets/js/data/search.json').read_text(encoding='utf-8')
            en_search = (output / 'en/assets/js/data/search.json').read_text(encoding='utf-8')
            assert 'English fixture' not in zh_search and 'English fixture' in en_search
            assert '/en/posts/fixture-' in en_search
        print(f'PASS {theme}: reciprocal language switches, translated navigation, independent English posts/search/pagination, missing-translation fallback.')
