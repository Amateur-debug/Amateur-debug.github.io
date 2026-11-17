/* Server-side PV totals via the open-source Busuanzi HTTP API. */
(async () => {
  'use strict';
  const counter = document.getElementById('site-pageviews');
  if (!counter || window.sitePageviewsStarted) return;
  const english = document.documentElement.lang.startsWith('en');
  // Preview builds must never pollute live statistics (or localhost totals).
  if (location.origin !== counter.dataset.origin) {
    counter.title = english ? 'View counting is disabled in previews.' : '本地预览不计入浏览量。';
    return;
  }
  window.sitePageviewsStarted = true;
  // Query parameters, heading anchors and index.html aliases share one count.
  const page = new URL(location.href);
  page.search = '';
  page.hash = '';
  page.pathname = page.pathname.replace(/\/index\.html$/, '/');
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 12000);
  try {
    // Endpoint used by the service's official https://busuanzi.9420.ltd/js loader.
    const response = await fetch('https://bsz.iirose.cn/api', {
      method: 'POST',
      headers: { 'x-bsz-referer': page.href },
      credentials: 'omit',
      referrerPolicy: 'no-referrer',
      cache: 'no-store',
      signal: controller.signal
    });
    if (!response.ok) throw new Error('Counter unavailable');
    const result = await response.json();
    if (!result.success || !['page_pv', 'site_pv'].every(key =>
      Number.isSafeInteger(result.data?.[key]) && result.data[key] >= 0)) {
      throw new Error('Invalid view counts');
    }
    for (const key of ['page_pv', 'site_pv']) {
      document.getElementById('busuanzi_value_' + key).textContent =
        result.data[key].toLocaleString(english ? 'en-US' : 'zh-CN');
    }
  } catch {
    // Do not retry automatically: the server may already have counted the visit.
    counter.title = english ? 'View counts are temporarily unavailable.' : '浏览量暂时无法获取。';
  } finally {
    window.clearTimeout(timeout);
  }
})();
