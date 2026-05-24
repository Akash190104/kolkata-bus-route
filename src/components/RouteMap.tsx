'use client';

import { useEffect, useRef } from 'react';
import type { Journey } from '@/lib/types';
import { getCoord } from '@/lib/router';

const LEGCOL = ['#1f6f4a', '#0f5c78', '#8a4b12'];

interface RouteMapProps {
  journey: Journey | null;
}

export default function RouteMap({ journey }: RouteMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const noteRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mapRef.current) return;

    // Prevent double-init from React strict mode
    if (mapInstance.current) return;

    let cancelled = false;

    const loadLeaflet = async () => {
      // Dynamically import Leaflet for SSR safety
      const L = (await import('leaflet')).default;
      await import('leaflet/dist/leaflet.css');

      if (cancelled || !mapRef.current || mapInstance.current) return;

      const map = L.map(mapRef.current, { zoomControl: true, attributionControl: false })
        .setView([22.555, 88.37], 11.4);
      L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
        maxZoom: 18, subdomains: 'abcd',
      }).addTo(map);
      L.tileLayer('https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png', {
        maxZoom: 18, subdomains: 'abcd',
      }).addTo(map);
      const layer = L.layerGroup().addTo(map);
      mapInstance.current = map;
      layerRef.current = layer;
    };

    loadLeaflet();

    return () => {
      cancelled = true;
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
        layerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!journey || !mapInstance.current || !layerRef.current) return;

    const drawJourney = async () => {
      const L = (await import('leaflet')).default;
      const map = mapInstance.current!;
      const layer = layerRef.current!;
      layer.clearLayers();

      const allPts: [number, number][] = [];
      let plotted = 0, missing = 0;

      journey.legs.forEach((l, i) => {
        const pts = l.stops.map(s => getCoord(s)).filter((c): c is [number, number] => !!c);
        l.stops.forEach(s => { if (getCoord(s)) plotted++; else missing++; });
        if (pts.length >= 2) {
          L.polyline(pts, { color: LEGCOL[i], weight: 5, opacity: 0.9 }).addTo(layer);
          pts.forEach(p => allPts.push(p));
        } else if (pts.length === 1) {
          allPts.push(pts[0]);
        }
      });

      // Markers
      const marks: { s: string; t: string }[] = [{ s: journey.legs[0].from, t: 'A' }];
      journey.legs.slice(0, -1).forEach(l => marks.push({ s: l.to, t: '~' }));
      marks.push({ s: journey.legs[journey.legs.length - 1].to, t: 'B' });

      marks.forEach(m => {
        const c = getCoord(m.s);
        if (!c) return;
        const big = m.t !== '~';
        L.marker(c, {
          icon: L.divIcon({
            className: '',
            html: `<div style="background:${big ? '#16211a' : '#1f6f4a'};color:#fff;
              width:${big ? 26 : 18}px;height:${big ? 26 : 18}px;border-radius:50%;
              display:flex;align-items:center;justify-content:center;
              border:2.5px solid #f8f4e9;box-shadow:0 1px 4px rgba(0,0,0,.4);
              font:700 ${big ? 12 : 10}px 'Spline Sans Mono',monospace">${m.t === '~' ? '⇅' : m.t}</div>`,
            iconSize: [big ? 26 : 18, big ? 26 : 18],
            iconAnchor: [big ? 13 : 9, big ? 13 : 9],
          }),
        }).addTo(layer).bindPopup(`<b class="pin">${m.s}</b>`);
      });

      if (allPts.length) {
        map.fitBounds(L.latLngBounds(allPts).pad(0.25), { maxZoom: 14 });
      }

      if (noteRef.current) {
        if (missing > 0) {
          noteRef.current.textContent = `Plotted ${plotted} of ${plotted + missing} stops — ${missing} not yet geocoded.`;
        } else {
          noteRef.current.textContent = `Journey plotted · ${plotted} stops mapped.`;
        }
      }
    };

    drawJourney();
  }, [journey]);

  return (
    <div>
      <div
        ref={mapRef}
        className="w-full"
        style={{
          height: '460px',
          border: '1.5px solid var(--line)',
          background: '#e8eee9',
          borderRadius: 'var(--radius)',
          overflow: 'hidden',
        }}
      />
      <div
        ref={noteRef}
        className="mt-3"
        style={{
          color: 'var(--muted)',
          fontFamily: "'Spline Sans Mono', monospace",
          fontSize: '11px',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}
      >
        Pick a journey to plot it.
      </div>
    </div>
  );
}
