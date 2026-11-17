"""Keep theme-independent presentation rules out of upstream templates."""
from pathlib import Path
import re
import sys

site = Path(sys.argv[1])
for path in site.rglob('*.html'):
    text = path.read_text(encoding='utf-8')
    if path.relative_to(site).as_posix() != 'blog/index.html':
        text = re.sub(r'<section\b[^>]*\bid="access-lastmod"[^>]*>.*?</section>', '', text, flags=re.S)
    else:
        navigation = re.search(r'<nav class="blog-sections-nav"[^>]*>(.*?)</nav>', text, re.S)
        if navigation and 'id="access-lastmod"' in text:
            links = re.findall(r'<a\b[^>]*>.*?</a>', navigation[1], re.S)
            sidebar = ('<section id="blog-category-nav"><h2 class="panel-heading">博客分类</h2>'
                       '<nav aria-label="博客分类"><ul class="content list-unstyled ps-0 pb-1 ms-1 mt-2">' +
                       ''.join('<li class="lh-lg">' + link + '</li>' for link in links) +
                       '</ul></nav></section>')
            text = text.replace(navigation[0], navigation[0].replace(
                'class="blog-sections-nav"', 'class="blog-sections-nav blog-mobile-nav"'), 1)
            text = re.sub(r'(<section\b[^>]*\bid="access-lastmod"[^>]*>)',
                          lambda m: sidebar + m[0], text, count=1)
            style = '''<style id="blog-sidebar-navigation-style">
@media (min-width:1200px) { .blog-mobile-nav { display:none; } }
#blog-category-nav a { color:inherit; border-bottom:0; }
#blog-category-nav a:hover { color:var(--link-color); }
#blog-category-nav + #access-lastmod { margin-top:2rem; }
</style>'''
            text = re.sub(r'<head\b[^>]*>', lambda m: m[0] + style, text, count=1)
    # Only remove the theme credit paragraph, retaining copyright and license.
    text = re.sub(r'<footer\b[^>]*>.*?</footer>', lambda footer: re.sub(
        r'<p\b[^>]*>.*?</p>',
        lambda p: '' if 'https://github.com/cotes2020/jekyll-theme-chirpy' in p[0] else p[0],
        footer[0], flags=re.S), text, flags=re.S)
    path.write_text(text, encoding='utf-8')
