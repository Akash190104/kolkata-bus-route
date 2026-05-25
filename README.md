# Kolkata Bus + Metro Route

A simple, static route finder for Kolkata buses and metro connections.

Kolkata moves by bus and metro, but route information is scattered across memory, local advice, and fragmented lists. This project turns that route data into a searchable graph so people can find direct, one-change, and two-change journeys between stops.

Live site: https://kolkata-bus-route.vercel.app

## Features

- Search by starting stop and destination stop
- Autocomplete for known bus stops
- Direct, one-change, and two-change route suggestions
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
- `raw_private.txt` - raw private bus route source data
- `raw_govt.txt` - raw government bus route source data
- `Kolkata_Metro_Bus_Connections.txt` - metro lines and nearest bus-stop connections
- `vercel.json` - Vercel static hosting configuration

## Run Locally

Because the app is static, you can open `kolkata-bus-router.html` directly in a browser.

For a local server:

```bash
python3 -m http.server 8080
```

Then visit:

```text
http://localhost:8080/kolkata-bus-router.html
```

## Rebuild Data

After editing route sources:

```bash
python3 build.py
```

This regenerates `busdata.json`. If you change the dataset, make sure the app's embedded `DATA` object is refreshed before deploying.

## Deploy

The site is deployed on Vercel as a static project.

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
