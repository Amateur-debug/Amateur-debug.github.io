# 个人网站工程

两个仓库分工：

- 本仓库：https://github.com/Amateur-debug/Amateur-debug.github.io —— Jekyll、主题、构建和发布。
- 内容仓库：https://github.com/Amateur-debug/docs —— 简介、简历、项目、博客、图片和附件。
- 网站：https://amateur-debug.github.io/

## 写内容

在 `docs` 仓库编辑：

| 内容 | 文件 |
| --- | --- |
| 首页 | pages/index.md |
| 简历 | pages/resume.md |
| 项目 | pages/projects.md |
| 博客 | posts/YYYY-MM-DD-title.md |
| 个人站点信息 | site.yml |
| 图片与 PDF | images/、files/ |

博客示例在 `docs/examples/` 中，将其复制到 `posts/` 后修改内容即可发布。
论文页示例复制到 `pages/publications.md` 后会自动增加页面与导航。

内容更新后，网站约每 15 分钟检查一次更新（GitHub 调度可能延迟）。
需要立即发布时，在本仓库 **Actions → Build and Deploy → Run workflow**。
定时运行会对比已发布网站的 `site-build.json`，未改变的内容不会重新构建部署。
本仓库代码 push 到 main 时立即触发构建。

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
.github/workflows/      GitHub Pages 发布流程
.build/                 临时标准 Jekyll 目录与生成网页，不提交
```

pages/index.md → 临时站点 index.md；其他 pages/*.md → _tabs/；posts/*.md → _posts/；images/ → assets/img/；files/ → assets/files/。
Jekyll 的标准目录在 `.build/` 内组装，不向工程仓库重复提交正文。

## GitHub Pages

在本仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
内容仓库为私有仓库。Actions 使用仅对 docs 有只读权限的部署密钥读取内容，私钥保存在本站仓库的 `DOCS_KEY` Actions Secret 中。
该密钥无法向 docs 写入；本地编辑和 push 继续使用你自己的 GitHub 身份。
网站和构建后的页面仍然公开。仓库可见性控制源文件的访问，不会使已发布的网页变成私有。

Chirpy 源码：https://github.com/cotes2020/jekyll-theme-chirpy 。保留 MIT 许可；个人正文的授权独立于主题代码。
