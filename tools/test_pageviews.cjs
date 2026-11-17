// Loader behavior without making requests that would inflate real statistics.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/pageviews.js', 'utf8');

function fixture(origin = 'https://amateur-debug.github.io', lang = 'zh-CN') {
  const scripts = [], timers = [];
  const counter = { dataset: { origin: 'https://amateur-debug.github.io' }, title: '' };
  const value = { textContent: '—' };
  const context = vm.createContext({
    location: { origin },
    document: {
      documentElement: { lang },
      getElementById: (id) => id === 'site-pageviews' ? counter : value,
      createElement: () => ({}),
      head: { appendChild: (script) => scripts.push(script) }
    },
    window: { setTimeout: (fn) => timers.push(fn) }
  });
  vm.runInContext(source, context);
  return { context, scripts, timers, counter, value };
}
const live = fixture();
assert.equal(live.scripts.length, 1);
assert.equal(live.scripts[0].referrerPolicy, 'no-referrer-when-downgrade');
vm.runInContext(source, live.context);
assert.equal(live.scripts.length, 1, 'Repeated initialization cannot count a view twice');
for (const origin of ['http://localhost:4077', 'http://127.0.0.1:4077', 'https://preview.example.com']) {
  assert.equal(fixture(origin).scripts.length, 0, 'Preview visits must not reach the counter');
}
live.scripts[0].onerror();
assert.equal(live.value.textContent, '—', 'An outage must not invent zero views');
assert.match(live.counter.title, /暂时无法/);
const timeout = fixture(undefined, 'en');
timeout.timers[0]();
assert.match(timeout.counter.title, /unavailable/);
const success = fixture();
success.value.textContent = '123';
success.timers[0]();
assert.equal(success.counter.title, '', 'Late timeout cannot overwrite successful data');
console.log('PASS pageviews: one request, preview isolation, unavailable state and successful response.');
