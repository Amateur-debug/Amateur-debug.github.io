"""Remove publication dates; Jekyll's temporary sorting dates are not public dates."""
import json
from pathlib import Path
import re
import sys


def clean_schema(value):
    if isinstance(value, dict):
        return {key: clean_schema(item) for key, item in value.items()
                if key not in ('datePublished', 'dateModified')}
    if isinstance(value, list):
        return [clean_schema(item) for item in value]
    return value


site = Path(sys.argv[1])
for path in site.rglob('*.html'):
    text = path.read_text(encoding='utf-8')
    # Chirpy article metadata: remove the label together with its date.
    text = re.sub(r'<span\b[^>]*>\s*[^<]*<time\b[^>]*data-ts=[^>]*>.*?</time>\s*</span>',
                  '', text, flags=re.S)
    text = re.sub(r'<time\b[^>]*data-ts=[^>]*>.*?</time>', '', text, flags=re.S)
    text = re.sub(r'<span\b[^>]*class="date [^"]*"[^>]*>.*?</span>', '', text, flags=re.S)
    text = re.sub(r'<time\b[^>]*class="year [^"]*"[^>]*>.*?</time>', '', text, flags=re.S)
    text = re.sub(r'<i\b[^>]*class="[^"]*\bfa-calendar\b[^"]*"[^>]*>\s*</i>', '', text)
    # Drop the now-empty card footer without disturbing categories or pinned badges.
    text = re.sub(r'<div class="post-meta[^"]*">\s*<div class="me-auto">\s*</div>\s*</div>', '', text)
    # The bundled minimal theme renders dates without datetime attributes.
    text = re.sub(r'<time>\d{4}-\d{2}-\d{2}</time>', '', text)
    if path.parent.name == 'archives':
        text = re.sub(r'(<li>)\s*\d{4}-\d{2}-\d{2}\s*·\s*', r'\1', text)
    text = re.sub(r'(<p class="eyebrow">.*?</a>)\s*·\s*\d{4}-\d{2}-\d{2}(</p>)',
                  r'\1\2', text, flags=re.S)
    text = re.sub(r'<meta\b[^>]*property="article:(?:published|modified)_time"[^>]*>', '', text)
    text = re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',
                  lambda m: m[1] + json.dumps(clean_schema(json.loads(m[2])), ensure_ascii=False) + m[3],
                  text, flags=re.S)
    path.write_text(text, encoding='utf-8')

for path in site.rglob('search.json'):
    entries = json.loads(path.read_text(encoding='utf-8'))
    for entry in entries:
        entry.pop('date', None)
    path.write_text(json.dumps(entries, ensure_ascii=False), encoding='utf-8')

for path in site.rglob('*.xml'):
    text = path.read_text(encoding='utf-8')
    if path.name == 'sitemap.xml':
        # Do not advertise an internal ordering date as a last-modified timestamp.
        text = re.sub(r'<url>.*?</url>', lambda m: re.sub(r'<lastmod>.*?</lastmod>', '', m[0])
                      if '/posts/' in m[0] else m[0], text, flags=re.S)
    elif path.name == 'feed.xml':
        text = re.sub(r'<published>.*?</published>', '', text)
        # Atom requires updated. Use the feed generation time, never a fake date.
        updated = re.search(r'<updated>(.*?)</updated>', text)
        if updated:
            text = re.sub(r'<entry>.*?</entry>', lambda m: re.sub(
                r'<updated>.*?</updated>', '<updated>' + updated[1] + '</updated>', m[0]), text, flags=re.S)
    path.write_text(text, encoding='utf-8')
