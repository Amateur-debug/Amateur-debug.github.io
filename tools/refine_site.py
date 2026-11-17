"""Keep theme-independent presentation rules out of upstream templates."""
from pathlib import Path
import re
import sys

site = Path(sys.argv[1])
for path in site.rglob('*.html'):
    text = path.read_text(encoding='utf-8')
    if path.relative_to(site).as_posix() != 'blog/index.html':
        text = re.sub(r'<section\b[^>]*\bid="access-lastmod"[^>]*>.*?</section>', '', text, flags=re.S)
    # Only remove the theme credit paragraph, retaining copyright and license.
    text = re.sub(r'<footer\b[^>]*>.*?</footer>', lambda footer: re.sub(
        r'<p\b[^>]*>.*?</p>',
        lambda p: '' if 'https://github.com/cotes2020/jekyll-theme-chirpy' in p[0] else p[0],
        footer[0], flags=re.S), text, flags=re.S)
    path.write_text(text, encoding='utf-8')
