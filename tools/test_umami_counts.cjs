const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/umami-counts.js', 'utf8');

async function run({ preview = false, failShare = false, wrongSite = false,
  allowFilter = true, page = 7, site = 1200, rejectPage = false } = {}) {
  const values = { page: { textContent: '—' }, site: { textContent: '—' } };
  const calls = [];
  const bar = { dataset: { origin: 'https://example.com', websiteId: 'website',
    apiBase: 'https://stats.example.com/api', shareSlug: 'public-share' }, title: '',
    querySelector: selector => values[selector.includes('"page"') ? 'page' : 'site'] };
  const context = vm.createContext({ URL, AbortController,
    document: { getElementById: () => bar, documentElement: { lang: 'zh-CN' } },
    location: { origin: preview ? 'http://localhost:8000' : 'https://example.com',
      pathname: '/en/projects/', search: '?private=value', hash: '#section' },
    window: { setTimeout, clearTimeout },
    fetch: async (url, options) => {
      calls.push({ url, options });
      if (url.includes('/share/')) {
        if (failShare) throw new Error('Offline');
        return { ok: true, json: async () => ({ websiteId: wrongSite ? 'other' : 'website',
          token: 'public-read-only-token', parameters: { overview: true, allowFilter } }) };
      }
      const isPage = new URL(url).searchParams.has('path');
      if (isPage && rejectPage) throw new Error('Request failed');
      return { ok: true, json: async () => ({ pageviews: isPage ? page : site }) };
    }
  });
  await vm.runInContext(source, context);
  const firstCalls = calls.length;
  await vm.runInContext(source, context);
  assert.equal(calls.length, firstCalls, 'Duplicate initialization must not repeat requests');
  for (const { url, options } of calls) {
    assert.equal(options.method, 'GET', 'Counter must never record visits');
    assert.equal(options.credentials, 'omit');
    assert.equal(options.referrerPolicy, 'no-referrer');
    assert.ok(!url.includes('private') && !url.includes('section'));
    if (!url.includes('/share/')) {
      assert.equal(options.headers['x-umami-share-context'], '1');
      assert.equal(new URL(url).searchParams.get('period'), '6month');
    }
  }
  return { values, calls, bar };
}

(async () => {
  let r = await run();
  assert.equal(r.values.page.textContent, '7');
  assert.equal(r.values.site.textContent, '1,200');
  assert.equal(r.calls.length, 3);
  assert.equal(new URL(r.calls[1].url).searchParams.get('path'), 'eq./en/projects/');
  assert.equal(new URL(r.calls[2].url).searchParams.has('path'), false);
  assert.equal((await run({ preview: true })).calls.length, 0);
  for (const options of [{ failShare: true }, { wrongSite: true }, { allowFilter: false }]) {
    r = await run(options);
    assert.equal(r.calls.length, 1);
    assert.equal(r.values.page.textContent, '—');
    assert.equal(r.values.site.textContent, '—');
  }
  for (const page of [-1, 1.5, '7', null]) {
    r = await run({ page });
    assert.equal(r.values.page.textContent, '—');
    assert.equal(r.values.site.textContent, '1,200');
  }
  assert.equal((await run({ rejectPage: true })).values.site.textContent, '1,200');
  assert.equal((await run({ page: 0 })).values.page.textContent, '0');
  console.log('PASS: public reads only, exact paths, preview exclusion, duplicate initialization, permissions, zero and partial failures.');
})().catch(error => { console.error(error); process.exitCode = 1; });
