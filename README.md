# Kolkata Travel Router

A simple, static route finder for Kolkata buses and metro connections.

Kolkata moves by bus and metro, but route information is scattered across memory, local advice, and fragmented lists. This project turns that route data into a searchable graph so people can find direct, one-change, and two-change journeys between stops.

Live site: https://kolkata-travel-router.vercel.app

Old link: https://kolkata-bus-route.vercel.app redirects to the new site after the Vercel project/domain change is deployed.

## Features

- Search by starting stop and destination stop
- Autocomplete for known bus stops and familiar local aliases
- Direct, one-change, and two-change route suggestions
- Direction-aware bus routing using separate up/down route records
- Metro-first recommendations when a useful metro route is available
- Route cards showing buses, metro legs, transfers, and stop counts
- Map plotting for geocoded stops
- Vercel Web Analytics support
- Public visitor badge on the site

## Project Structure

- `kolkata-bus-router.html` - the static web app
- `index.html` - redirects the root URL to the app page
- `build.py` - parses and normalizes raw route data
- `busdata.json` - generated route dataset
- `raw_busrepo_routes1.js` - local Kolkata/Howrah route source data from Bus Repository
- `raw_busrepo_routes2.js` - NBSTC/intercity route source data from Bus Repository
- `raw_busrepo_routes3.js` - SBSTC/intercity route source data from Bus Repository
- `raw_busrepo_routes4.js` - additional regional route source data from Bus Repository
- `route_intermediate_hints.json` - bounded A-B-C intermediate stop hints from older matched route data
- `Kolkata_Metro_Bus_Connections.txt` - metro lines and nearest bus-stop connections
- `vercel.json` - Vercel static hosting configuration

## Recent Data Changes

- Replaced the older `raw_private.txt` and `raw_govt.txt` inputs with Bus Repository route files.
- Imported all four Bus Repository source files: `routes1.js`, `routes2.js`, `routes3.js`, and `routes4.js`.
- Preserved bus direction instead of treating every bus route as reversible, so separate up/down entries are respected.
- Kept regional/intercity routes in the data, but ranked local city routes ahead of them for normal Kolkata searches.
- Removed supplemental gap-fill routes so routing only uses stops present in the Bus Repository sources and metro file.
- Added search-only aliases for well-known names that are absent from the source stop list, such as Bidhannagar Station resolving to Ultadanga.
- Matched Bus Repository's own `replaceLocAlias()` search aliases, including Dharmatala, Sector V, Exide More, and Biswa Bangla Gate.
- Restored bounded intermediate stops only when an older matching route proves an A-B-C gap in the current Bus Repository route.
- Kept metro data from `Kolkata_Metro_Bus_Connections.txt` unchanged.

## Run Locally

Because the app is static, you can open `kolkata-bus-router.html` directly in a browser.

For a local server:

```bash
python3 -m http.server 8080
```

Then visit:

```text
http://localhost:8080/kolkata-travel-router
```

## Rebuild Data

After editing route sources:

```bash
python3 build.py
```

This regenerates `busdata.json` and refreshes the embedded app data in
`kolkata-bus-router.html`, `kolkata-travel-router.html`, and `index.html`.

## Deploy

The site is deployed on Vercel as a static project. Use `kolkata-travel-router`
as the new project name, and keep the old `kolkata-bus-route.vercel.app`
deployment configured with the redirect in `vercel.json`.

```bash
vercel deploy --prod
```

## Analytics

The app includes Vercel Web Analytics:

```html
<script defer src="/_vercel/insights/script.js"></script>
```

Enable Web Analytics in the Vercel project dashboard to see detailed visitor data. The public visitor count shown on the page uses a lightweight external badge.

## Contributing

If this helped you, please star the repo:

https://github.com/Akash190104/kolkata-bus-route

Route corrections, stop-name fixes, and geocoding improvements are welcome.
