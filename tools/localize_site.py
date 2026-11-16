"""Add language navigation to generated HTML without changing theme templates."""
import argparse
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re


class TranslateHTML(HTMLParser):
    """Translate exact UI text and accessibility labels, preserving scripts and markup."""

    def __init__(self, translations):
        super().__init__(convert_charrefs=False)
        self.translations = translations
        self.parts = []
        self.raw_tag = None

    def translate(self, value):
        stripped = value.strip()
        if stripped in self.translations:
            return value.replace(stripped, self.translations[stripped], 1)
        return value

    def handle_starttag(self, tag, attrs):
        raw = self.get_starttag_text()
        for name, value in attrs:
            if name in ('aria-label', 'title', 'placeholder', 'alt') and value:
                translated = self.translate(value)
                if translated != value:
                    pattern = r'(' + re.escape(name) + r'\s*=\s*)([\"\'])(.*?)\2'
                    raw = re.sub(pattern, lambda m: m[1] + m[2] + html.escape(translated, quote=True) + m[2], raw, count=1)
        self.parts.append(raw)
        if tag in ('script', 'style'):
            self.raw_tag = tag

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.parts.append(f'</{tag}>')
        if tag == self.raw_tag:
            self.raw_tag = None

    def handle_data(self, data):
        self.parts.append(data if self.raw_tag else self.translate(data))

    def handle_entityref(self, name):
        self.parts.append(f'&{name};')

    def handle_charref(self, name):
        self.parts.append(f'&#{name};')

    def handle_comment(self, data):
        self.parts.append(f'<!--{data}-->')

    def handle_decl(self, decl):
        self.parts.append(f'<!{decl}>')


def route(path):
    name = path.as_posix()
    return '/' + (name[:-10] if name.endswith('index.html') else name)


def localize(site, baseurl, url, translations):
    pages = {p.relative_to(site) for p in site.rglob('*.html')}
    css = site / 'assets/css/language-switch.css'
    css.parent.mkdir(parents=True, exist_ok=True)
    css.write_text('''
.site-language-switch { display: flex; justify-content: flex-end; margin: .5rem 0 1rem; }
.site-language-switch a { display: inline-flex; align-items: center; min-height: 1.75rem;
  padding: .2rem .4rem; border: 0; border-radius: .25rem;
  font-size: .75rem; line-height: 1.4; font-weight: 500; color: inherit; text-decoration: none; }
.site-language-switch a:hover { opacity: .75; }
.site-language-switch a:focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
#topbar .site-language-switch { flex-shrink: 0; margin: 0 .65rem 0 auto; }
@media (max-width: 991.98px) {
  #topbar #topbar-title { flex: 1; min-width: 0; width: auto; overflow: hidden;
    white-space: nowrap; text-overflow: ellipsis; }
  #topbar .site-language-switch { margin: 0 .25rem; }
}
'''.lstrip(), encoding='utf-8')
    for relative in sorted(pages):
        english = relative.parts[0] == 'en'
        counterpart = Path(*relative.parts[1:]) if english else Path('en') / relative
        paired = counterpart in pages
        target = counterpart if paired else Path('blog/index.html' if english else 'en/blog/index.html')
        lang = 'zh-CN' if english else 'en'
        title = ('切换到中文' if english else 'Switch to English') if paired else (
            '查看中文博客（此页面暂无对应译文）' if english else 'View the English blog (no translation for this page)')
        button = (f'<nav class="site-language-switch" aria-label="Language">'
                  f'<a href="{html.escape(baseurl + route(target), quote=True)}" lang="{lang}" hreflang="{lang}" '
                  f'title="{html.escape(title, quote=True)}" aria-label="{html.escape(title, quote=True)}">中/EN</a></nav>')
        path = site / relative
        text = path.read_text(encoding='utf-8')
        if english:
            parser = TranslateHTML(translations)
            parser.feed(text)
            parser.close()
            text = ''.join(parser.parts)
        # Use the existing top bar when available; other themes use their header.
        text, count = re.subn(r'(<button\b[^>]*\bid="search-trigger"[^>]*>)',
                              lambda m: button + m[1], text, count=1)
        if count == 0:
            text, count = re.subn(r'(<header\b[^>]*>)', lambda m: m[1] + button, text, count=1)
        if count != 1:
            raise ValueError(f'Cannot place language switch: {relative}')
        head = f'<link rel="stylesheet" href="{html.escape(baseurl, quote=True)}/assets/css/language-switch.css">'
        if paired:
            chinese_path, english_path = (counterpart, relative) if english else (relative, counterpart)
            for language, page in [('zh-CN', chinese_path), ('en', english_path), ('x-default', chinese_path)]:
                head += f'<link rel="alternate" hreflang="{language}" href="{html.escape(url + baseurl + route(page), quote=True)}">'
        # HTML minifiers may omit </head>; the opening tag is always retained.
        text, count = re.subn(r'(<head\b[^>]*>)', lambda m: m[1] + head, text, count=1)
        if count != 1:
            raise ValueError(f'Cannot add language metadata: {relative}')
        path.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('site', type=Path)
    parser.add_argument('--baseurl', default='')
    parser.add_argument('--url', required=True)
    parser.add_argument('--translations', required=True, type=Path)
    args = parser.parse_args()
    localize(args.site, args.baseurl.rstrip('/'), args.url.rstrip('/'),
             json.loads(args.translations.read_text(encoding='utf-8')))
