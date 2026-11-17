/* Display shared, server-side PV totals using the original Busuanzi service. */
(() => {
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
  const script = document.createElement('script');
  script.src = 'https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js';
  script.async = true;
  // The official loader also sets this on its JSONP request. The full page
  // path is needed: modern browsers otherwise send only the origin cross-site.
  script.referrerPolicy = 'no-referrer-when-downgrade';
  const unavailable = () => {
    const value = document.getElementById('busuanzi_value_page_pv');
    if (value && value.textContent === '—') {
      counter.title = english ? 'View counts are temporarily unavailable.' : '浏览量暂时无法获取。';
    }
  };
  script.onerror = unavailable;
  window.setTimeout(unavailable, 12000);
  document.head.appendChild(script);
})();
