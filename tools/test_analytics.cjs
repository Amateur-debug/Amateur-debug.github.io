const assert = require('node:assert/strict');
const fs = require('node:fs');
const { dateRange, rows, daily, validPath, apiUrl } = require('./analytics/dashboard.js');
const now = Date.parse('2026-11-18T17:00:00Z'); // Nov 19 in Shanghai.
const range = dateRange('7', now);
assert.equal(range.days[0], '2026-11-13');
assert.equal(range.days.at(-1), '2026-11-19');
assert.equal(range.startAt, Date.parse('2026-11-12T16:00:00Z'));
assert.equal(range.endAt, now);
assert.equal(range.days.length, 7);
assert.equal(dateRange('6month', Date.parse('2026-08-31T12:00:00Z')).days[0], '2026-02-28');
assert.equal(dateRange('6month', Date.parse('2024-08-31T12:00:00Z')).days[0], '2024-02-29');
assert.throws(() => dateRange('invalid'));
const normalized = daily({ pageviews: [{ x: '2026-11-19T00:00:00Z', y: 12 }], sessions: [{ x: '2026-11-19T00:00:00Z', y: 2 }] }, range.days);
assert.deepEqual(normalized[0], { day: '2026-11-13', views: 0, visitors: 0 });
assert.deepEqual(normalized.at(-1), { day: '2026-11-19', views: 12, visitors: 2 });
assert.throws(() => daily({ error: true }, range.days)); // Failure must not become zeros.
assert.throws(() => daily({ pageviews: [{ x: null, y: 3 }], sessions: [] }, range.days));
assert.deepEqual(rows([{ x: null, y: 2 }]), [{ x: '', y: 2 }]); // Unknown region remains counted.
for (const bad of [null, {}, [{ x: '/', y: -1 }], [{ x: '/', y: '4' }]]) assert.throws(() => rows(bad));
for (const value of ['', '/', '/en/projects/', '/posts/中文/']) assert.equal(validPath(value), true);
for (const value of ['https://example.com/', '//example.com', '/?secret=1', '/#x', '/x\ny']) assert.equal(validPath(value), false);
const url = apiUrl('https://cloud.umami.is/analytics/us/api', 'website-id', 'metrics', range, '/posts/中文/', 'path');
assert.equal(url.searchParams.get('path'), 'eq./posts/中文/');
assert.equal(url.searchParams.get('timezone'), 'Asia/Shanghai');
assert.equal(url.searchParams.get('startAt'), String(range.startAt));
assert.equal(url.searchParams.get('type'), 'path');
assert.equal(url.searchParams.has('token'), false);
const d3 = require('./analytics/vendor/d3.min.js');
const geo = JSON.parse(fs.readFileSync(__dirname + '/analytics/world.json'));
const china = geo.features.find(f => f.id === 'CHN');
assert(china && !geo.features.some(f => f.id === 'TWN'));
const smallPolygons = china.geometry.coordinates.map(coordinates => {
  const polygon = { type: 'Polygon', coordinates };
  if (d3.geoArea(polygon) > 2 * Math.PI) coordinates.forEach(ring => ring.reverse());
  return polygon;
});
assert(smallPolygons.some(p => d3.geoContains(p, [121, 24]))); // Taiwan geometry remains in CHN.
assert(smallPolygons.some(p => d3.geoContains(p, [116.4, 39.9])));
assert(!smallPolygons.some(p => d3.geoContains(p, [-74, 40.7])));
console.log('PASS: Shanghai ranges, leap months, zero days, invalid data, path encoding, and map geometry.');
