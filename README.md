# 个人网站工程

两个仓库分工：

- 本仓库：https://github.com/Amateur-debug/Amateur-debug.github.io —— Jekyll、主题、构建和发布。
- 个人资料仓库：https://github.com/Amateur-debug/docs —— 简介、简历、项目、文章、图片和附件，可独立阅读与复用，也为本站提供内容。
- 网站：https://amateur-debug.github.io/

## 写内容

在 `docs` 仓库编辑：

| 内容 | 文件 |
| --- | --- |
| 首页 | pages/index.md |
| 简历 | pages/resume.md |
| 项目 | pages/projects.md |
| 博客 | posts/YYYY-MM-DD-title.md，或 pages/blog.yml 选择的 posts/ 笔记 |
| 个人站点信息 | pages/site.yml |
| 网站联系入口 | pages/data/contact.yml |
| 导航条目及顺序 | pages/data/navigation.yml |
| 图片与 PDF | images/、files/ |
| 学校与公司 Logo | image/logo/ |
| 网站标签图标 | pages/icons/ |

推荐在 `docs/posts/` 的分类目录中维护文章，并在 `docs/pages/blog.yml` 中登记后发布。兼容入口是 `posts/` 根目录下的 `YYYY-MM-DD-title.md`，这类文件带 YAML front matter，无需登记便会发布。
已有技术笔记保存在 `docs/posts/`，通过 `pages/blog.yml` 的 `articles` 列表选择公开文章，配置 `source`、`slug`、`title`、`description`、`math`、`mermaid`。构建只提取选中的正文和相对引用图片，不复制其他笔记；原始 Markdown 保留原文件名、公式和图片链接。
博客无需填写发布日期；清单末尾的文章排在前面。构建后移除页面、搜索与 SEO 元数据中的博客日期，不修改主题模板。Jekyll 所需日期只在临时构建文件中作为排序键；Atom 的更新时间使用订阅文件生成时间。
独立页面放在 `pages/`，网站会生成对应页面；导航入口和顺序由 `pages/data/navigation.yml` 配置，两个主题使用同一份导航数据。
[内容仓库的维护说明](https://github.com/Amateur-debug/docs#日常维护)包含新增博客的完整 YAML 示例、配图规则、撤下文章、添加独立页面与 Git 白名单操作。
网站专用的页面与 YAML 设置集中在 `docs/pages/`；文章、图片和附件分别保存在 `posts/`、`images/`、`files/`，便于独立阅读和复用。

内容更新后，网站约每 15 分钟检查一次更新（GitHub 调度可能延迟）。
需要立即发布时，在本仓库 **Actions → Build and Deploy → Run workflow**。
定时运行会对比已发布网站的 `site-build.json`，未改变的内容不会重新构建部署。
本仓库代码 push 到 main 时立即触发构建；仅修改 README.md 或 LICENSE 不触发 push 构建。

图标由 `docs/pages/icons/` 提供，中英文站共用 XC 头像的 SVG、PNG 和 ICO 版本。构建时覆盖主题默认资源，并为生成页面写入带版本号的图标链接；无需修改主题模板。

## 中英文网站

个人页面分为中文 `docs/pages/` 与英文 `docs/pages/en/`；英文站点信息和导航由 `pages/en/site.yml` 与 `pages/en/data/navigation.yml` 提供。

博客不分语言：`posts/` 和 `pages/blog.yml` 选中的笔记共用 `/blog/` 与 `/posts/`。英文页面的博客链接、最近文章和搜索结果都指向这些统一地址；旧 `/en/blog/`、`/en/posts/` 及相关分类/归档地址保留跳转，英文 sitemap 不重复列出文章。

`tools/localize_site.py` 在生成的 HTML 顶栏添加小号“中/EN”语言切换与 hreflang。独立页面切换到对应译文；没有译文时进入另一语言首页，博客页的 EN 按钮进入英文首页。处理只影响构建产物，不修改 `themes/` 模板。

完整构建会自动包括英文站；排查单一语言可使用 `--locale zh-CN` 或 `--locale en`，单语言构建不添加跨语言按钮。语言切换按钮的样式由构建后处理生成，不依赖特定主题。

## 选择主题

修改 `_config.yml`：

```yaml
selected_theme: chirpy
```

已适配主题：

- `chirpy`：Chirpy 7.6.0，保留个人简介首页、独立博客、搜索、分类和标签。
- `minimal`：轻量主题，支持相同个人内容和博客分页，跟随系统深浅色。

主题目录保存模板与配置，不保存个人正文。添加新主题时需提供 `config.yml`、首页 profile 布局、page/post 布局和 blog/index.html；完成适配后，现有 Markdown 可复用。

## 本地构建

准备 Ruby 3.4、Bundler，将两个仓库克隆到相邻目录：

```sh
bundle install
bundle exec ruby tools/build.rb --content ../docs
python tools/check_site.py .build/output
```

私有内容仓库建议先通过自己的 GitHub 身份克隆到相邻的 docs 目录，再使用 `--content ../docs`。
临时切换主题可添加 `--theme minimal`。
完整验证两套主题和 11 篇文章的分页：`python tools/test_builds.py ../docs`。测试文章只写入 `.build/`。
预览生成结果：

```sh
python -m http.server 4000 --directory .build/output
```

浏览 http://127.0.0.1:4000/ 。生成的网页没有服务器端依赖，静态服务器即可预览。

## 目录结构

```text
_config.yml             站点地址、内容仓库、所选主题
Gemfile / Gemfile.lock   构建依赖
themes/chirpy/          Chirpy 模板适配
themes/minimal/         第二套主题
tools/build.rb          取得内容并组装、构建 Jekyll 站点
tools/check_site.py     检查生成页面和本地链接
tools/localize_site.py  为构建产物添加语言切换和界面翻译
.github/workflows/      GitHub Pages 发布流程
.build/                 临时标准 Jekyll 目录与生成网页，不提交
```

pages/index.md → 临时站点 index.md；其他 pages/*.md → _tabs/；pages/site.yml → 合并进临时站点配置；pages/data/ → _data/；image/logo/ → assets/img/logo/；posts/*.md → _posts/；images/ → assets/img/；files/ → assets/files/。
Jekyll 的标准目录在 `.build/` 内组装，不向工程仓库重复提交正文。

## GitHub Pages

在本仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
内容仓库为私有仓库。Actions 使用仅对 docs 有只读权限的部署密钥读取内容，私钥保存在本站仓库的 `DOCS_KEY` Actions Secret 中。
该密钥无法向 docs 写入；本地编辑和 push 继续使用你自己的 GitHub 身份。
网站和构建后的页面仍然公开。仓库可见性控制源文件的访问，不会使已发布的网页变成私有。

Chirpy 源码：https://github.com/cotes2020/jekyll-theme-chirpy 。保留 MIT 许可；个人正文的授权独立于主题代码。

## 常用维护流程

### 发布内容与确认结果

1. 在 `docs` 修改正文、配图及 `pages/blog.yml`，提交并完成 `git push`。
2. 在本仓库的 **Actions → Build and Deploy → Run workflow** 选择 `main` 并运行。先完成内容推送，避免构建读到旧版本。
3. 等待 build 和 deploy 成功，再查看网站。失败时进入对应步骤查看日志。
4. 如需确认版本，查看网站的 `/site-build.json`，对照其中的 `content_commit`、`site_commit` 和 `built_at`。

常见排查：

| 问题 | 检查位置 |
| --- | --- |
| 新博客不显示 | 确认文章已推送、`pages/blog.yml` 的缩进与 `source` 正确、部署成功。分类目录不会自动全部公开。 |
| 图片缺失或构建提示找不到图片 | 核对文件名大小写、路径是否使用 `/`、文件是否提交；清单文章的相对图片必须在文章目录内。 |
| 私有内容下载失败 | 检查网站仓库 Settings → Secrets and variables → Actions 中的 `DOCS_KEY`，以及 docs 仓库匹配的只读 Deploy key。 |
| 新文件无法提交 | 使用 `git check-ignore -v 路径`，检查 `.gitignore` 白名单。 |
| 中文更新但英文没变 | 英文个人页面需单独维护 `docs/pages/en/`；博客共用，无需复制。 |

### 切换或维护主题

在 `_config.yml` 将 `selected_theme` 改为 `chirpy` 或 `minimal`，按上方“本地构建”验证后提交并推送。正文仍保留在 `docs`，无需复制或改名。

仅修改内容不需要改 `themes/`。调整构建逻辑时，运行 `python tools/test_builds.py ../docs` 检查两套主题；只编辑 README 无需重新构建网站。

### 维护 Git 白名单

`.gitignore` 默认忽略根目录未放行的路径，允许必要配置文件、`themes/`、`tools/`、`.github/workflows/` 和指定的共享编辑器配置。`.build/`、`.content/`、依赖和缓存保持忽略。

在允许的源码目录中新增文件通常无需改规则。如果增加根文件 `new-config.yml`，在放行列表加 `!/new-config.yml`；如果增加根目录 `scripts/`，加 `!/scripts/`。不要为提交构建产物而放行 `.build/` 或 `.content/`。

Git 白名单只控制新文件是否可被 Git 跟踪，不控制网页是否公开，也不会让已经跟踪的文件自动退出版本管理。

### 浏览量统计

每个正文页面底部显示“本页浏览”和“全站浏览”；英文页面显示 Page views / Site views。首页、项目、论文、博客列表、简历以及每篇已发布博客自动接入，之后新增页面和博客也无需单独配置。中英文个人页面按各自 URL 分别累计，博客共用同一个 URL；全站总浏览量汇总同一域名上的访问。

使用 [开源不蒜子公共服务](https://busuanzi.9420.ltd/)（[源码及 API 文档](https://github.com/soxft/busuanzi/wiki/API)），记录的是 PV（访问次数），刷新也会累计，并非独立访客人数。数据从启用起累计，不能补回历史访问；重新部署不会清零，修改页面路径或域名可能改变计数归属。公共服务的可用性与数据保留由服务方负责，浏览器拦截或网络异常时显示 `—`，不显示虚假的 0。

`tools/add_pageviews.py` 在构建及语言合并完成后为 HTML 注入统计栏，`tools/pageviews.js` 调用服务的 POST API，一次请求同时取得本页及全站 PV，未修改 `themes/`。脚本仅在 `_config.yml` 的 `url` 对应正式域名运行，本地与其他域名预览不计数；404 和跳转页不接入，避免跳转重复统计。统计服务会收到访客 IP、浏览器请求信息及页面域名、路径；请求不携带 Cookie，不写 localStorage，不发送 URL 查询参数或章节锚点，`/index.html` 也归一到目录地址。网络失败不自动重试，以免服务端已计数时重复累计。该功能不加载第三方可执行脚本。

关闭统计：把 `_config.yml` 中的 `pageviews` 改为 `false`，提交并部署即可。样式在 `tools/add_pageviews.py` 中维护。验证用 `node tools/test_pageviews.cjs` 和 `python tools/test_builds.py ../docs`；本地显示 `—` 是正常现象，真实数字需在部署后访问正式网站确认。

API 使用服务官方脚本当前配置的 `https://bsz.iirose.cn/api`；不要将其替换成不支持浏览器预检请求的网页代理地址。
