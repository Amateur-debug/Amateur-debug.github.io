/* Public, read-only Umami data. Tracking is handled separately by the official script. */
(() => {
  'use strict';
  const DAY = 86400000;
  function dateRange(period, now = Date.now()) {
    if (!['7', '30', '90', '6month'].includes(period)) throw new Error('Invalid period');
    const shanghai = new Date(now + 8 * 3600000);
    const endDay = Date.UTC(shanghai.getUTCFullYear(), shanghai.getUTCMonth(), shanghai.getUTCDate());
    let startDay = endDay - (Number(period) - 1) * DAY;
    if (period === '6month') {
      const d = new Date(endDay);
      const day = d.getUTCDate();
      d.setUTCDate(1);
      d.setUTCMonth(d.getUTCMonth() - 6);
      const last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
      d.setUTCDate(Math.min(day, last));
      startDay = +d;
    }
    const days = [];
    for (let d = startDay; d <= endDay; d += DAY) days.push(new Date(d).toISOString().slice(0, 10));
    return { startAt: startDay - 8 * 3600000, endAt: now, days };
  }
  function rows(value) {
    if (!Array.isArray(value) || value.some(r => !r || (typeof r.x !== 'string' && r.x !== null) || !Number.isSafeInteger(r.y) || r.y < 0)) throw new Error('Invalid metrics');
    return value.map(r => ({ x: r.x ?? '', y: r.y }));
  }
  function daily(value, days) {
    const dated = data => rows(data).map(r => {
      if (!/^\d{4}-\d{2}-\d{2}T/.test(r.x)) throw new Error('Invalid daily bucket');
      return [r.x.slice(0, 10), r.y];
    });
    const views = new Map(dated(value.pageviews));
    const visitors = new Map(dated(value.sessions));
    return days.map(day => ({ day, views: views.get(day) || 0, visitors: visitors.get(day) || 0 }));
  }
  function validPath(value) {
    return value === '' || (value.startsWith('/') && !value.startsWith('//') && !/[?#\s\u0000-\u001f]/u.test(value));
  }
  function apiUrl(base, websiteId, endpoint, range, path = '', type = '') {
    const url = new URL(base.replace(/\/$/, '') + '/websites/' + encodeURIComponent(websiteId) + '/' + endpoint);
    url.search = new URLSearchParams({ startAt: range.startAt, endAt: range.endAt, timezone: 'Asia/Shanghai' });
    if (path) url.searchParams.set('path', 'eq.' + path);
    if (type) { url.searchParams.set('type', type); url.searchParams.set('limit', type === 'country' ? '300' : '100'); }
    if (endpoint === 'pageviews') url.searchParams.set('unit', 'day');
    return url;
  }
  // Export pure functions for boundary and API-contract checks without running a browser.
  if (typeof module !== 'undefined' && module.exports) { module.exports = { dateRange, rows, daily, validPath, apiUrl }; return; }
  const root = document.getElementById('site-analytics');
  if (!root || root.dataset.started) return;
  root.dataset.started = 'true';
  const en = document.documentElement.lang.startsWith('en');
  const t = (zh, english) => en ? english : zh;
  const fmt = n => n.toLocaleString(en ? 'en-US' : 'zh-CN');
  const $ = selector => root.querySelector(selector);
  const form = $('form');
  const status = $('.analytics-status');
  const names = new Intl.DisplayNames([en ? 'en' : 'zh-CN'], { type: 'region' });
  const countryName = code => {
    if (!code) return t('未知地区', 'Unknown location');
    try { return names.of(code) || code; } catch { return code; }
  };
  const element = (tag, text, parent) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (parent) parent.append(node);
    return node;
  };
  const svgNode = (tag, attributes, parent, text) => {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    parent.append(node);
    return node;
  };
  function message(node, text, error = false) {
    node.replaceChildren();
    const p = element('p', text, node);
    p.className = 'analytics-empty';
    p.dataset.error = String(error);
  }
  function table(node, headers, data) {
    node.replaceChildren();
    const wrap = element('div', undefined, node);
    wrap.className = 'analytics-table-wrap';
    const table = element('table', undefined, wrap);
    const head = element('tr', undefined, element('thead', undefined, table));
    for (const h of headers) element('th', h, head).scope = 'col';
    const body = element('tbody', undefined, table);
    for (const row of data) {
      const tr = element('tr', undefined, body);
      for (const value of row) element('td', String(value), tr);
    }
  }
  function renderList(type, value) {
    const data = rows(value);
    const node = $(`[data-list="${type}"]`);
    if (!data.length) { message(node, t('该范围内暂无数据', 'No data in this range')); return; }
    const label = x => type === 'country' ? countryName(x) : (x || t('未知', 'Unknown'));
    const heading = { path: t('页面', 'Page'), referrer: t('来源', 'Source'), country: t('国家 / 地区', 'Country / region'), browser: t('浏览器', 'Browser'), device: t('设备', 'Device') };
    table(node, [heading[type], t('访客数', 'Visitors')], data.map(r => [label(r.x), fmt(r.y)]));
    if (type === 'path') {
      const list = $('#analytics-paths');
      list.replaceChildren();
      for (const row of data) if (validPath(row.x) && row.x) { const option = element('option', undefined, list); option.value = row.x; }
    }
  }
  function renderChart(value, range) {
    const data = daily(value, range.days);
    const node = $('[data-chart]');
    node.replaceChildren();
    table($('[data-daily]'), [t('日期', 'Date'), t('浏览量', 'Page views'), t('访客数', 'Visitors')], data.map(r => [r.day, fmt(r.views), fmt(r.visitors)]));
    if (!data.some(r => r.views || r.visitors)) { message(node, t('该范围内暂无访问记录', 'No traffic in this range')); return; }
    const svg = svgNode('svg', { viewBox: '0 0 720 210', role: 'img', 'aria-label': t('每日浏览量柱状图；详细数值见下方每日数据', 'Daily page views; values are listed in the daily data table below') }, node);
    const max = Math.max(1, ...data.map(r => r.views));
    const width = 640 / data.length;
    for (let tick = 0; tick <= 2; tick++) {
      const y = 170 - tick * 70;
      svgNode('line', { x1: 45, x2: 700, y1: y, y2: y, stroke: 'currentColor', opacity: '.12' }, svg);
      svgNode('text', { x: 36, y: y + 4, 'text-anchor': 'end', fill: 'currentColor', 'font-size': 11 }, svg, fmt(Math.round(max * tick / 2)));
    }
    data.forEach((r, i) => {
      const height = 140 * r.views / max;
      const bar = svgNode('rect', { x: 48 + i * width, y: 170 - height, width: Math.max(1, width * .72), height, rx: Math.min(2, width / 5), fill: 'var(--analytics-accent)' }, svg);
      svgNode('title', {}, bar, `${r.day} · ${t('浏览量', 'Views')} ${fmt(r.views)} · ${t('访客数', 'Visitors')} ${fmt(r.visitors)}`);
    });
    for (const i of new Set([0, Math.floor((data.length - 1) / 2), data.length - 1])) {
      svgNode('text', { x: 48 + i * width + width / 2, y: 194, 'text-anchor': 'middle', fill: 'currentColor', 'font-size': 11 }, svg, data[i].day.slice(5));
    }
  }
  let mapAssets;
  async function renderMap(value) {
    const metrics = rows(value);
    if (!window.d3) throw new Error('Map renderer unavailable');
    if (!mapAssets) mapAssets = Promise.all(['world.json', 'country-codes.json'].map(name => read(root.dataset.assets + '/' + name))).catch(error => { mapAssets = undefined; throw error; });
    const [geo, codes] = await mapAssets;
    if (!geo.features || !codes.CHN) throw new Error('Invalid map data');
    // GeoJSON files may use RFC 7946 winding; d3 expects the smaller spherical polygon.
    const features = geo.features.filter(f => f.id !== 'ATA').map(f => {
      const copy = JSON.parse(JSON.stringify(f));
      const polygons = copy.geometry.type === 'Polygon' ? [copy.geometry.coordinates] : copy.geometry.coordinates;
      for (const coordinates of polygons) {
        if (d3.geoArea({ type: 'Polygon', coordinates }) > 2 * Math.PI) coordinates.forEach(ring => ring.reverse());
      }
      return copy;
    });
    return () => {
      const node = $('[data-map]');
      node.replaceChildren();
      const collection = { type: 'FeatureCollection', features };
      const projection = d3.geoEqualEarth().fitExtent([[3, 3], [697, 352]], collection);
      const path = d3.geoPath(projection);
      const counts = new Map(metrics.map(r => [r.x, r.y]));
      const max = Math.max(1, ...metrics.map(r => r.y));
      const svg = svgNode('svg', { viewBox: '0 0 700 360', role: 'img', 'aria-label': t('访客地区地图；完整地区计数见旁边列表', 'Visitor location map; full counts appear in the adjacent list') }, node);
      features.forEach(feature => {
        const code = codes[feature.id];
        const count = counts.get(code) || 0;
        const label = `${countryName(code || feature.id)} · ${t('访客数', 'Visitors')} ${fmt(count)}`;
        const shape = svgNode('path', { d: path(feature), class: 'map-shape', 'data-country': code || feature.id, fill: count ? d3.interpolateRgb('#cce9f1', '#167c9b')(Math.sqrt(count / max)) : 'var(--main-border-color, #e5e7eb)' }, svg);
        if (count) { shape.setAttribute('tabindex', '0'); shape.setAttribute('aria-label', label); }
        svgNode('title', {}, shape, label);
        for (const event of ['pointerenter', 'focus']) shape.addEventListener(event, () => { $('.analytics-map-label').textContent = label; });
      });
    };
  }
  async function read(url, signal, headers = {}) {
    const controller = new AbortController();
    const abort = () => controller.abort();
    if (signal?.aborted) controller.abort();
    signal?.addEventListener('abort', abort, { once: true });
    const timeout = setTimeout(abort, 15000);
    try {
      const response = await fetch(url, { method: 'GET', credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', signal: controller.signal, headers });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } finally { clearTimeout(timeout); signal?.removeEventListener('abort', abort); }
  }
  let active, generation = 0;
  async function load() {
    const page = form.elements.path.value.trim();
    if (!validPath(page)) { status.textContent = t('请输入以 / 开头的页面路径，不包含域名、查询参数或 #。', 'Enter a path starting with /, without a domain, query, or #.'); status.dataset.error = 'true'; return; }
    active?.abort();
    active = new AbortController();
    const signal = active.signal;
    const current = ++generation;
    const range = dateRange(form.elements.period.value);
    root.setAttribute('aria-busy', 'true');
    status.dataset.error = 'false';
    status.textContent = t('正在读取访问数据…', 'Loading traffic data…');
    for (const card of root.querySelectorAll('[data-stat]')) card.textContent = '—';
    for (const panel of root.querySelectorAll('[data-list], [data-chart], [data-map]')) message(panel, t('加载中…', 'Loading…'));
    $('[data-daily]').replaceChildren();
    $('.analytics-map-label').textContent = t('将鼠标移到地图上查看访客数', 'Hover over the map to see visitor counts');
    try {
      const share = await read(root.dataset.apiBase + '/share/' + encodeURIComponent(root.dataset.shareSlug), signal);
      if (share.websiteId !== root.dataset.websiteId || !share.token || !share.parameters?.overview || !share.parameters?.allowFilter) throw new Error('Share unavailable');
      const headers = { 'x-umami-share-token': share.token, 'x-umami-share-context': '1' };
      const get = (endpoint, type) => read(apiUrl(root.dataset.apiBase, share.websiteId, endpoint, range, page, type), signal, headers);
      const jobs = [
        ['stats', get('stats')], ['trend', get('pageviews')],
        ...['country', 'path', 'referrer', 'browser', 'device'].map(type => [type, get('metrics', type)])
      ];
      let failed = 0;
      await Promise.all(jobs.map(async ([type, promise]) => {
        try {
          const data = await promise;
          if (current !== generation) return;
          if (type === 'stats') {
            for (const key of ['pageviews', 'visitors', 'visits']) if (!Number.isSafeInteger(data[key]) || data[key] < 0) throw new Error('Invalid totals');
            for (const key of ['pageviews', 'visitors', 'visits']) $(`[data-stat="${key}"]`).textContent = fmt(data[key]);
          } else if (type === 'trend') renderChart(data, range);
          else {
            renderList(type, data);
            if (type === 'country') {
              try { const draw = await renderMap(data); if (current === generation) draw(); }
              catch { if (current === generation) { failed++; message($('[data-map]'), t('地图暂不可用，地区数据见列表。', 'Map unavailable; location counts are listed alongside.'), true); } }
            }
          }
        } catch {
          if (current !== generation) return;
          failed++;
          const target = type === 'trend' ? $('[data-chart]') : $(`[data-list="${type}"]`);
          if (target) message(target, t('暂时无法读取，请重试。', 'Temporarily unavailable. Please retry.'), true);
          if (type === 'country') message($('[data-map]'), t('地区数据暂不可用', 'Location data unavailable'), true);
        }
      }));
      if (current !== generation) return;
      status.dataset.error = String(failed > 0);
      status.textContent = `${range.days[0]} – ${range.days.at(-1)} · ${page || t('所有页面', 'All pages')} · ` + (failed ? t('部分数据暂不可用，请点击“查看”重试。', 'Some data is unavailable. Select Apply to retry.') : t('已更新', 'Updated'));
    } catch {
      if (current !== generation) return;
      status.dataset.error = 'true';
      status.textContent = t('无法读取公开统计，请稍后重试。', 'Public statistics are unavailable. Please retry later.');
      for (const panel of root.querySelectorAll('[data-list], [data-chart], [data-map]')) message(panel, t('暂不可用', 'Unavailable'), true);
    } finally { if (current === generation) root.setAttribute('aria-busy', 'false'); }
  }
  form.addEventListener('submit', event => { event.preventDefault(); load(); });
  form.elements.period.addEventListener('change', load);
  $('[data-reset]').addEventListener('click', () => { form.reset(); load(); });
  load();
})();
