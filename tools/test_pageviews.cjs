// Exercise the client without inflating real statistics.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/pageviews.js', 'utf8');

async function fixture({ href = 'https://amateur-debug.github.io/projects/index.html?q=private#heading',
  lang = 'zh-CN', failure = false, data = { page_pv: 12, site_pv: 1234 } } = {}) {
  const calls = [];
  const counter = { dataset: { origin: 'https://amateur-debug.github.io' }, title: '' };
  const values = { page_pv: { textContent: '—' }, site_pv: { textContent: '—' } };
  const context = vm.createContext({
    URL, AbortController, location: new URL(href),
    document: {
      documentElement: { lang },
      getElementById: id => id === 'site-pageviews' ? counter : values[id.replace('busuanzi_value_', '')]
    },
    window: { setTimeout: () => 1, clearTimeout: () => {} },
    fetch: async (url, options) => {
      calls.push({ url, options });
      if (failure) throw new Error('Network offline');
      return { ok: true, json: async () => ({ success: true, data }) };
    }
  });
  await vm.runInContext(source, context);
  return { context, calls, counter, values };
}
(async () => {
  const live = await fixture();
  assert.equal(live.calls.length, 1);
  assert.equal(live.calls[0].options.method, 'POST');
  assert.equal(live.calls[0].options.credentials, 'omit');
  assert.equal(live.calls[0].options.headers['x-bsz-referer'], 'https://amateur-debug.github.io/projects/');
  assert.equal(live.values.page_pv.textContent, '12');
  assert.equal(live.values.site_pv.textContent, '1,234');
  await vm.runInContext(source, live.context);
  assert.equal(live.calls.length, 1, 'Repeated initialization must not count twice');
  for (const href of ['http://localhost:4077/', 'http://127.0.0.1:4077/', 'https://preview.example.com/']) {
    assert.equal((await fixture({ href })).calls.length, 0);
  }
  const en = await fixture({ href: 'https://amateur-debug.github.io/en/', lang: 'en' });
  assert.equal(en.calls[0].options.headers['x-bsz-referer'], 'https://amateur-debug.github.io/en/');
  for (const options of [{ failure: true }, { data: { page_pv: -1, site_pv: 10 } }, { data: {} }]) {
    const failed = await fixture(options);
    assert.equal(failed.values.page_pv.textContent, '—');
    assert.equal(failed.values.site_pv.textContent, '—');
    assert.match(failed.counter.title, /暂时无法/);
    assert.equal(failed.calls.length, 1, 'Failures must not retry and double-count');
  }
  console.log('PASS pageviews: real response handling, URL normalization, one request, preview isolation and failure states.');
})().catch(error => { console.error(error); process.exitCode = 1; });
