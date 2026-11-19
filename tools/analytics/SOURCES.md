# Dashboard assets

- `world.json`: copied unchanged from https://github.com/ttgml/fix-umami-cn-map/blob/5419ae9c58601d7399557cd3e6ac845136981d14/datamaps.world.json, as requested by the site owner. This GeoJSON combines the Taiwan geometry into the CHN feature. The repository does not declare a license. Retain this source reference when updating the file.
- `country-codes.json`: ISO alpha-3 to alpha-2 lookup extracted from Umami's `src/lib/constants.ts` (https://github.com/umami-software/umami), retrieved 2026-11-19. Upstream MIT license is included in `vendor/umami.LICENSE`.
- `vendor/d3.min.js`: D3 7.9.0 from https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js. License: ISC; see `vendor/d3.LICENSE`. Vendored locally to avoid a third-party runtime CDN dependency.

Map rendering uses an Equal Earth projection. Polygon winding is normalized in memory for D3; the original GeoJSON is preserved. Metrics are matched by the original Umami alpha-2 code. No regional counts are merged or reassigned. Locations without a separate polygon remain visible in the table, so a map shape is not an exhaustive statistical grouping.

Only public share endpoints are read. No private credentials are bundled. The share token stays in memory and is discarded on reload; changing or revoking the share may require updating `_config.yml`.
