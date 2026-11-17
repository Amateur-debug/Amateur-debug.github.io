# frozen_string_literal: true

require 'yaml'
require 'json'
require 'date'
require 'time'
require 'fileutils'
require 'optparse'
require 'tmpdir'
require 'open3'
require 'net/http'
require 'uri'
require 'rbconfig'
require 'digest'

ROOT = File.expand_path('..', __dir__)
BUILD_ROOT = File.join(ROOT, '.build')

def read_yaml(path)
  value = YAML.safe_load(File.read(path, encoding: 'UTF-8'), permitted_classes: [Date, Time], aliases: false)
  raise "Expected a YAML mapping: #{path}" unless value.is_a?(Hash)
  value
end

def merge_config(base, extra)
  base.merge(extra) { |_key, old, value| old.is_a?(Hash) && value.is_a?(Hash) ? merge_config(old, value) : value }
end

def git(*args)
  output, error, status = Open3.capture3('git', *args)
  raise "Git failed: #{error.strip}" unless status.success?
  output.strip
end

def write(path, value)
  FileUtils.mkdir_p(File.dirname(path))
  File.write(path, value, encoding: 'UTF-8')
end

def markdown(path, defaults)
  text = File.read(path, encoding: 'UTF-8')
  match = text.match(/\A---\r?\n(.*?)\r?\n---(?:\r?\n|\z)(.*)\z/m)
  if match
    metadata = YAML.safe_load(match[1], permitted_classes: [Date, Time], aliases: false) || {}
    raise "Invalid front matter: #{path}" unless metadata.is_a?(Hash)
    text = match[2]
  else
    metadata = {}
  end
  # Layout and output URL belong to the site/theme adapter, not to the content repository.
  metadata = defaults.merge(metadata).merge(defaults.select { |key, _| %w[layout permalink].include?(key) })
  text = text.gsub(/\]\((\/(?!\/)[^)\s]+)\)/) { "]({{ '#{Regexp.last_match(1).gsub("'", '%27')}' | relative_url }})" }
  YAML.dump(metadata) + "---\n\n" + text.lstrip
end

options = {}
OptionParser.new do |parser|
  parser.banner = 'bundle exec ruby tools/build.rb [--content ../docs] [--theme chirpy]'
  parser.on('--content PATH', 'Use a local content checkout') { |v| options[:content] = File.expand_path(v) }
  parser.on('--theme NAME', 'Override selected_theme for this build only') { |v| options[:theme] = v }
  parser.on('--locale NAME', 'Build one language (zh-CN or en)') { |v| options[:locale] = v }
  parser.on('--destination PATH', 'Output directory inside .build/') { |v| options[:destination] = File.expand_path(v) }
  parser.on('--check-updates', 'Skip unchanged content on scheduled workflow runs') { options[:check] = true }
  parser.on('--github-output PATH', 'Write the build decision to a GitHub Actions output file') { |v| options[:github_output] = v }
end.parse!

settings = read_yaml(File.join(ROOT, '_config.yml'))
selected = options[:theme] || settings.fetch('selected_theme')
raise 'Invalid theme name' unless selected.match?(/\A[a-z0-9][a-z0-9-]*\z/)
theme_root = File.join(ROOT, 'themes', selected)
raise "Unknown theme: #{selected}" unless File.file?(File.join(theme_root, 'config.yml'))
repository = settings.fetch('content_repository')
raise 'Invalid content repository' unless repository.match?(%r{\A[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\z})
ref = settings.fetch('content_ref', 'main')
raise 'Invalid content branch or tag' unless ref.match?(%r{\A[A-Za-z0-9][A-Za-z0-9_./-]*\z}) && !ref.include?('..')
site_commit = ENV['GITHUB_SHA'] || git('-C', ROOT, 'rev-parse', 'HEAD')

if options[:check]
  changed = true
  if ENV['GITHUB_EVENT_NAME'] == 'schedule'
    begin
      revision = if options[:content]
                   git('-C', options[:content], 'rev-parse', 'HEAD')
                 else
                   git('ls-remote', '--exit-code', "https://github.com/#{repository}.git", "refs/heads/#{ref}").split.first
                 end
      url = settings.fetch('url').sub(%r{/+\z}, '') + settings.fetch('baseurl', '') + '/site-build.json'
      uri = URI(url)
      response = Net::HTTP.start(uri.host, uri.port, use_ssl: uri.scheme == 'https', open_timeout: 10, read_timeout: 10) do |http|
        http.get(uri.request_uri, { 'Cache-Control' => 'no-cache' })
      end
      previous = JSON.parse(response.body) if response.is_a?(Net::HTTPSuccess)
      changed = !(revision && previous && previous['content_commit'] == revision && previous['site_commit'] == site_commit && previous['theme'] == selected)
    rescue StandardError => error
      warn "Update comparison unavailable; attempt a fresh build (#{error.class})."
    end
  end
  decision = "build=#{changed}\n"
  File.open(options[:github_output], 'a') { |file| file.write(decision) } if options[:github_output]
  puts decision
  exit
end

FileUtils.mkdir_p(BUILD_ROOT)
source = Dir.mktmpdir('source-', BUILD_ROOT)
destination = options[:destination] || File.join(BUILD_ROOT, 'output')
# Jekyll cleans its destination. Keep all generated output inside this project's .build/.
destination = File.expand_path(destination)
raise 'Destination must be inside the site .build directory' unless destination.start_with?(BUILD_ROOT + File::SEPARATOR) || destination.start_with?(BUILD_ROOT + '/')
raise 'Destination must not be a symlink' if File.symlink?(destination)

content_root = options[:content]
unless content_root
  content_root = File.join(Dir.mktmpdir('content-', BUILD_ROOT), 'checkout')
  git('clone', '--quiet', '--depth', '1', '--branch', ref, "https://github.com/#{repository}.git", content_root)
end
locale = options.fetch(:locale, 'zh-CN')
raise 'Unsupported locale' unless %w[zh-CN en].include?(locale)
pages_root = File.join(content_root, locale == 'en' ? 'pages/en' : 'pages')
raise 'Content checkout must contain pages/index.md and pages/site.yml' unless File.file?(File.join(pages_root, 'index.md')) && File.file?(File.join(pages_root, 'site.yml'))
[theme_root, content_root].each do |directory|
  Dir.glob(File.join(directory, '**', '*'), File::FNM_DOTMATCH).each do |path|
    next if path.include?('/.git/') || path.end_with?('/.git')
    raise "Symlink is not supported in site inputs: #{path}" if File.symlink?(path)
  end
end

%w[_layouts _includes _sass _data _tabs assets blog].each do |directory|
  path = File.join(theme_root, directory)
  FileUtils.cp_r(path, source) if File.directory?(path)
end
%w[feed.xml sitemap.xml 404.html robots.txt].each do |name|
  path = File.join(theme_root, name)
  FileUtils.cp(path, source) if File.file?(path)
end
profile = read_yaml(File.join(pages_root, 'site.yml'))
allowed_profile_keys = %w[title tagline description avatar github twitter social]
raise 'pages/site.yml contains unsupported settings' unless (profile.keys - allowed_profile_keys).empty?
configuration = merge_config(read_yaml(File.join(theme_root, 'config.yml')), settings)
configuration = merge_config(configuration, profile)
configuration['lang'] = locale
if locale == 'en'
  configuration['baseurl'] = settings.fetch('baseurl', '').sub(%r{/+\z}, '') + '/en'
end
configuration['exclude'] = (Array(configuration['exclude']) + %w[Gemfile Gemfile.lock README.md LICENSE tools themes]).uniq
write(File.join(source, '_config.yml'), YAML.dump(configuration))

page_icons = { 'projects' => 'fas fa-code', 'resume' => 'fas fa-file-alt', 'publications' => 'fas fa-book-open' }
page_order = { 'projects' => 0, 'resume' => 1, 'publications' => 2 }
Dir.glob(File.join(pages_root, '*.md')).sort.each do |page|
  name = File.basename(page, '.md')
  raise "Invalid page filename: #{name}" unless name.match?(/\A[a-z0-9][a-z0-9-]*\z/)
  if name == 'index'
    write(File.join(source, 'index.md'), markdown(page, { 'layout' => 'profile', 'permalink' => '/', 'toc' => false }))
  else
    write(File.join(source, '_tabs', name + '.md'), markdown(page, {
      'layout' => 'page', 'permalink' => "/#{name}/", 'icon' => page_icons.fetch(name, 'fas fa-file'),
      'order' => page_order.fetch(name, 10), 'toc' => false
    }))
  end
end
FileUtils.mkdir_p(File.join(source, '_posts'))
posts_root = File.join(content_root, 'posts')
Dir.glob(File.join(posts_root, '*.md')).sort.each do |post|
  name = File.basename(post)
  next if name == 'README.md'
  raise "Blog filename must use YYYY-MM-DD-title.md: #{name}" unless name.match?(/\A\d{4}-\d{2}-\d{2}-.+\.md\z/)
  write(File.join(source, '_posts', name), markdown(post, { 'layout' => 'post' }))
end

# Publish selected notes without copying the private knowledge library into Jekyll.
# The manifest is website-specific; each article has a single source in posts/.
blog_manifest = File.join(content_root, 'pages', 'blog.yml')
if File.file?(blog_manifest)
  entries = read_yaml(blog_manifest).fetch('articles')
  raise 'blog.yml articles must be a list' unless entries.is_a?(Array)
  entries.each do |entry|
    slug = entry.fetch('slug')
    raise 'Invalid blog slug' unless slug.match?(/\A[a-z0-9]+(?:-[a-z0-9]+)*\z/)
    note = File.expand_path(entry.fetch('source'), content_root)
    raise 'Published articles must be inside posts/' unless note.start_with?(File.join(content_root, 'posts') + '/')
    text = File.read(note, encoding: 'UTF-8')
    text = text.sub(/\A# [^\n]+\r?\n+/, '')
    # Kramdown uses $$ for inline math as well; leave fenced and inline code intact.
    text = text.split(/(^```.*?^```[^\n]*|`[^`\n]+`)/m).map.with_index do |part, i|
      next part if i.odd?
      part.gsub(/^(\#{1,5}) /, '\\1# ').gsub(/(?<![\\$])\$(?!\$)([^\n$]+)(?<!\\)\$(?!\$)/) { "$$#{Regexp.last_match(1)}$$" }
    end.join
    text = text.gsub(/!\[([^\]]*)\]\(([^)]+)\)/) do |image|
      alt, reference = Regexp.last_match(1), Regexp.last_match(2)
      next image if reference.match?(%r{\A(?:[a-zA-Z][\w+.-]*:|/)})
      asset = File.expand_path(reference, File.dirname(note))
      raise 'Blog image must stay beside its source note' unless asset.start_with?(File.dirname(note) + '/')
      raise "Missing blog image: #{asset}" unless File.file?(asset)
      relative = "assets/blog/#{slug}/#{reference}"
      FileUtils.mkdir_p(File.dirname(File.join(source, relative)))
      FileUtils.cp(asset, File.join(source, relative))
      "![#{alt}]({{ '/#{relative}' | relative_url }})"
    end
    date = Date.iso8601(entry.fetch('date').to_s)
    name = "#{date}-#{slug}.md"
    raise "Duplicate blog article: #{name}" if File.exist?(File.join(source, '_posts', name))
    metadata = entry.reject { |key, _| %w[source slug].include?(key) }
    metadata.merge!('layout' => 'post', 'permalink' => "/posts/#{slug}/")
    write(File.join(source, '_posts', name), YAML.dump(metadata) + "---\n\n" + text)
  end
end

{ 'images' => 'assets/img', 'files' => 'assets/files', 'image/logo' => 'assets/img/logo', 'pages/data' => '_data',
  'pages/icons' => 'assets/img/favicons' }.each do |from, to|
  directory = File.join(content_root, from)
  next unless File.directory?(directory)
  FileUtils.mkdir_p(File.join(source, to))
  Dir.children(directory).each do |name|
    next if name.start_with?('.')
    # Chirpy generates its own manifest page; replace the output after rendering.
    next if from == 'pages/icons' && name == 'site.webmanifest'
    FileUtils.cp_r(File.join(directory, name), File.join(source, to))
  end
end

# Localized data and page metadata are content inputs. Theme files stay untouched.
ui = {}
if locale == 'en'
  data_root = File.join(pages_root, 'data')
  Dir.glob(File.join(data_root, '*.yml')).each do |path|
    next if File.basename(path) == 'ui.yml'
    FileUtils.cp(path, File.join(source, '_data', File.basename(path)))
  end
  ui_path = File.join(data_root, 'ui.yml')
  ui = read_yaml(ui_path) if File.file?(ui_path)
  (Dir.glob(File.join(source, '_tabs', '*.md')) +
    [File.join(source, 'blog', 'index.html'), File.join(source, '404.html')]).each do |path|
    next unless File.file?(path)
    text = File.read(path, encoding: 'UTF-8')
    match = text.match(/\A---\r?\n(.*?)\r?\n---(?:\r?\n|\z)(.*)\z/m)
    next unless match
    metadata = YAML.safe_load(match[1], permitted_classes: [Date, Time], aliases: false) || {}
    %w[title description].each { |key| metadata[key] = ui.fetch(metadata[key], metadata[key]) if metadata[key] }
    write(path, YAML.dump(metadata) + "---\n" + match[2])
  end
end

ENV['JEKYLL_ENV'] ||= 'production'
require 'jekyll'
Jekyll::PluginManager.require_from_bundler
Jekyll::Commands::Build.process('source' => source, 'destination' => destination, 'trace' => true)

# Apply personal icons to rendered pages without editing theme templates.
icons = File.join(destination, 'assets', 'img', 'favicons')
if File.file?(File.join(content_root, 'pages', 'icons', 'favicon.svg'))
  version = Digest::SHA256.file(File.join(icons, 'favicon.svg')).hexdigest[0, 12]
  icon_url = configuration.fetch('baseurl', '') + '/assets/img/favicons'
  links = [
    %(<link rel="icon" type="image/png" sizes="96x96" href="#{icon_url}/favicon-96x96.png?v=#{version}">),
    %(<link rel="icon" type="image/svg+xml" href="#{icon_url}/favicon.svg?v=#{version}">),
    %(<link rel="shortcut icon" href="#{icon_url}/favicon.ico?v=#{version}">),
    %(<link rel="apple-touch-icon" sizes="180x180" href="#{icon_url}/apple-touch-icon.png?v=#{version}">)
  ].join
  Dir.glob(File.join(destination, '**', '*.html')).each do |path|
    text = File.read(path, encoding: 'UTF-8')
    text = text.gsub(/<link\b[^>]*\brel=["'](?:icon|shortcut icon|apple-touch-icon|mask-icon)["'][^>]*>/i, '')
    text = text.sub(/<head\b[^>]*>/i) { |tag| tag + links }
    write(path, text)
  end
  FileUtils.cp(File.join(icons, 'favicon.ico'), File.join(destination, 'favicon.ico'))
  manifest_path = File.join(content_root, 'pages', 'icons', 'site.webmanifest')
  FileUtils.cp(manifest_path, icons) if File.file?(manifest_path)
end
content_commit = begin
  top = git('-C', content_root, 'rev-parse', '--show-toplevel')
  raise 'Content is not a separate checkout' unless File.expand_path(top).casecmp?(File.expand_path(content_root))
  git('-C', content_root, 'rev-parse', 'HEAD')
rescue StandardError
  'local-uncommitted'
end
write(File.join(destination, 'site-build.json'), JSON.pretty_generate({
  'theme' => selected, 'content_repository' => repository, 'content_commit' => content_commit,
  'site_commit' => site_commit, 'built_at' => Time.now.utc.iso8601
}) + "\n")

if !options[:locale] && File.file?(File.join(content_root, 'pages', 'en', 'index.md'))
  english_output = Dir.mktmpdir('english-', BUILD_ROOT)
  success = system(RbConfig.ruby, __FILE__, '--content', content_root, '--theme', selected,
                   '--locale', 'en', '--destination', english_output)
  raise 'English build failed' unless success
  FileUtils.cp_r(english_output, File.join(destination, 'en'))
  translations = read_yaml(File.join(content_root, 'pages', 'en', 'data', 'ui.yml'))
  translations_path = File.join(source, 'ui-translations.json')
  write(translations_path, JSON.generate(translations))
  success = system('python', File.join(ROOT, 'tools', 'localize_site.py'), destination,
                   '--baseurl', settings.fetch('baseurl', ''), '--url', settings.fetch('url'),
                   '--translations', translations_path)
  raise 'Language switch generation failed' unless success
end
# Run after language redirects are created, once for the complete public site.
if !options[:locale] && settings.fetch('pageviews', true)
  success = system('python', File.join(ROOT, 'tools', 'add_pageviews.py'), destination,
                   '--url', settings.fetch('url'), '--baseurl', settings.fetch('baseurl', ''))
  raise 'Page view counter generation failed' unless success
end
puts "Built theme=#{selected}, content=#{content_commit[0, 12]}, output=#{destination}"
