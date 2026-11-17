# frozen_string_literal: true

# Assemble a content-owned index while leaving all theme templates untouched.
def group_blog(manifest, source, configuration)
  sections = manifest['sections']
  return unless sections
  raise 'blog.yml sections must be a nonempty list' unless sections.is_a?(Array) && !sections.empty?
  ids = sections.map { |section| section.fetch('id') }
  raise 'Invalid or duplicate blog section ID' unless ids.uniq == ids && ids.all? { |id| id.match?(/\A[a-z0-9-]+\z/) }
  entries = manifest.fetch('articles').reverse
  raise 'Every article needs a known section' unless entries.all? { |entry| ids.include?(entry['section']) }
  escape = ->(value) { CGI.escapeHTML(value.to_s) }
  body = <<~HTML
    <style>
    .blog-sections-nav { display:flex; flex-wrap:wrap; gap:.6rem 1.4rem; margin:0 0 2rem; }
    .blog-section { margin:2.5rem 0; scroll-margin-top:5rem; }
    .blog-section h2 { font-size:1.4rem; margin:0 0 .8rem; }
    .blog-section h2 small { font-size:.8rem; font-weight:400; color:var(--text-muted-color,#757575); margin-left:.6rem; }
    .blog-entry { padding:1rem 0; border-bottom:1px solid var(--main-border-color,#eee); }
    .blog-entry h3 { margin:0 0 .4rem; font-size:1.1rem; line-height:1.5; }
    .blog-entry p { margin:0; color:var(--text-muted-color,#757575); font-size:.95rem; line-height:1.7; }
    </style>
    <nav class="blog-sections-nav" aria-label="博客板块">
  HTML
  sections.each { |section| body += %(<a href="##{section['id']}">#{escape.call(section.fetch('title'))}</a>\n) }
  body += "</nav>\n"
  sections.each do |section|
    articles = entries.select { |entry| entry['section'] == section['id'] }
    body += %(<section class="blog-section" aria-labelledby="#{section['id']}"><h2 id="#{section['id']}">#{escape.call(section['title'])}<small>#{articles.size} 篇</small></h2>\n)
    articles.each do |entry|
      body += %(<article class="blog-entry"><h3><a href="{{ '/posts/#{entry.fetch('slug')}/' | relative_url }}">#{escape.call(entry.fetch('title'))}</a></h3><p>#{escape.call(entry['description'])}</p></article>\n)
    end
    body += "</section>\n"
  end
  # Preserve the legacy root-post publishing entry point if it is used.
  body += <<~LIQUID
    {% assign other_posts = site.posts | where_exp: 'post', 'post.section == nil' %}
    {% if other_posts.size > 0 %}<section class="blog-section"><h2>其他文章</h2>
    {% for post in other_posts %}<article class="blog-entry"><h3><a href="{{ post.url | relative_url }}">{{ post.title | escape }}</a></h3></article>{% endfor %}
    </section>{% endif %}
  LIQUID
  write(File.join(source, 'blog', 'index.html'), YAML.dump({ 'layout' => 'page', 'title' => '博客', 'toc' => false }) + "---\n" + body)
  configuration.delete('paginate')
  write(File.join(source, '_config.yml'), YAML.dump(configuration))
  # Old pagination bookmarks still reach the complete index.
  pages = [(entries.size.to_f / 10).ceil, 2].max
  (2..pages).each do |number|
    write(File.join(source, 'blog', "page#{number}", 'index.html'), "---\nlayout: null\n---\n" +
      %(<html><head><meta name="shared-blog-redirect" content="true"><meta http-equiv="refresh" content="0;url={{ '/blog/' | relative_url }}"><link rel="canonical" href="{{ '/blog/' | absolute_url }}"></head><body><a href="{{ '/blog/' | relative_url }}">博客</a></body></html>))
  end
end
