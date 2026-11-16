"""Integration check: the same Markdown works with both themes and blog pagination."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

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
