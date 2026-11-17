/* Read public analytics only. The official Umami tracker records each visit. */
(async () => {
  'use strict';
  const bar = document.getElementById('umami-counts');
  if (!bar || window.umamiCountsStarted) return;
  const english = document.documentElement.lang.startsWith('en');
  if (location.origin !== bar.dataset.origin) {
    bar.title = english ? 'Counts are disabled in previews.' : '本地预览不读取统计。';
    return;
  }
  window.umamiCountsStarted = true;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 12000);
  const options = { method: 'GET', credentials: 'omit', cache: 'no-store',
    referrerPolicy: 'no-referrer', signal: controller.signal };
  const unavailable = () => {
    bar.title = english ? 'Some view counts are temporarily unavailable.' : '部分浏览量暂时无法获取。';
  };
  async function json(url, headers = {}) {
    const response = await fetch(url, { ...options, headers });
    if (!response.ok) throw new Error('Statistics unavailable');
    return response.json();
  }
  try {
    const share = await json(bar.dataset.apiBase + '/share/' + encodeURIComponent(bar.dataset.shareSlug));
    if (share.websiteId !== bar.dataset.websiteId || !share.token ||
        !share.parameters?.overview || !share.parameters?.allowFilter) {
      throw new Error('Public share does not permit these statistics');
    }
    const headers = { 'x-umami-share-token': share.token, 'x-umami-share-context': '1' };
    const siteUrl = new URL(bar.dataset.apiBase + '/websites/' + encodeURIComponent(share.websiteId) + '/stats');
    siteUrl.searchParams.set('period', '6month');
    siteUrl.searchParams.set('timezone', 'Asia/Shanghai');
    const pageUrl = new URL(siteUrl);
    pageUrl.searchParams.set('path', 'eq.' + location.pathname);
    const results = await Promise.allSettled([json(pageUrl.href, headers), json(siteUrl.href, headers)]);
    results.forEach((result, index) => {
      const count = result.status === 'fulfilled' ? result.value.pageviews : undefined;
      if (!Number.isSafeInteger(count) || count < 0) {
        unavailable();
        return;
      }
      bar.querySelector('[data-count="' + (index === 0 ? 'page' : 'site') + '"]').textContent =
        count.toLocaleString(english ? 'en-US' : 'zh-CN');
    });
  } catch {
    unavailable();
  } finally {
    window.clearTimeout(timeout);
  }
})();
