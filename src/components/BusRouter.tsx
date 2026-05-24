'use client';

import { useState, useCallback, useRef } from 'react';
import { initRouter, findRoutes, getRouteCount, getStopCount } from '@/lib/router';
import type { BusData, Journey, SearchResult } from '@/lib/types';
import StopInput from './StopInput';
import JourneyCard from './JourneyCard';
import AddToHomeScreenButton from './AddToHomeScreenButton';
import dynamic from 'next/dynamic';

const RouteMap = dynamic(() => import('./RouteMap'), { ssr: false });

interface BusRouterProps {
  data: BusData;
}

const GH_URL = 'https://github.com/Akash190104/kolkata-bus-route';

export default function BusRouter({ data }: BusRouterProps) {
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [result, setResult] = useState<SearchResult | null>(null);
  const [activeIdx, setActiveIdx] = useState<number>(0);
  const [flat, setFlat] = useState<Journey[]>([]);
  const resultsRef = useRef<HTMLDivElement>(null);

  initRouter(data);

  const handleSwap = useCallback(() => {
    setFrom(prev => {
      const oldTo = to;
      setTo(prev);
      return oldTo;
    });
  }, [to]);

  const handleSearch = useCallback(() => {
    const f = from.trim();
    const t = to.trim();
    if (!f || !t) return;
    const res = findRoutes(f, t);
    setResult(res);
    const all = [...res.direct, ...res.one, ...res.two];
    setFlat(all);
    setActiveIdx(0);
    setTimeout(() => {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
  }, [from, to]);

  const rcount = getRouteCount();
  const scount = getStopCount();

  const renderResults = () => {
    if (!result) {
      return (
        <div className="empty-state">
          <b>No search yet.</b>
          <span>Choose two stands above. Try <i>Behala Chowrasta → Saltlake</i>.</span>
        </div>
      );
    }

    if (result.error) {
      return (
        <div className="empty-state">
          <b>Stop not recognised.</b>
          <span>Please choose both stands from the suggestions list.</span>
        </div>
      );
    }

    const none = !result.direct.length && !result.one.length && !result.two.length;
    if (none) {
      return (
        <div className="empty-state">
          <b>No route found in this dataset.</b>
          <span>These two stands aren&apos;t connected within two changes in the loaded routes.</span>
        </div>
      );
    }

    const renderGroup = (title: string, sub: string, cls: string, list: Journey[], offset: number) => {
      if (!list.length) return null;
      return (
        <div className="result-group" key={cls}>
          <div className={`group-tag ${cls}`}>
            {title}<small>{sub}</small>
          </div>
          {list.map((j, i) => (
            <JourneyCard
              key={offset + i}
              journey={j}
              active={activeIdx === offset + i}
              onClick={() => setActiveIdx(offset + i)}
            />
          ))}
        </div>
      );
    };

    return (
      <>
        {renderGroup('Direct', 'one bus', 't0', result.direct, 0)}
        {renderGroup('One change', 'two buses', 't1', result.one, result.direct.length)}
        {renderGroup('Two changes', 'three buses', 't2', result.two, result.direct.length + result.one.length)}
      </>
    );
  };

  return (
    <div className="page-shell">
      {/* Masthead — newspaper-style metadata strip */}
      <div className="masthead">
        <span className="masthead-tag">Fragmented data, made navigable</span>
        <span className="masthead-meta">
          <span><b>{rcount || '—'}</b> routes</span>
          <span className="dot">·</span>
          <span><b>{scount || '—'}</b> stops</span>
          <span className="dot">·</span>
          <span>src · kolbusopedia</span>
        </span>
      </div>

      {/* Hero */}
      <header className="hero">
        <h1 className="hero-title">
          Kolkata <em>Bus</em> Router
        </h1>
        <p className="hero-lead">
          Pick where you are and where you&apos;re going. It finds direct buses,
          one-change routes, and two-change routes across the private &amp; government
          network — then draws the journey on the map.
        </p>

        <div className="hero-actions">
          <AddToHomeScreenButton />
          <a className="btn-ink" href={GH_URL} target="_blank" rel="noopener noreferrer">
            <svg viewBox="0 0 16 16" className="w-4 h-4 fill-current shrink-0">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82A7.65 7.65 0 0 1 8 3.86c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
            </svg>
            Star on GitHub
          </a>
          <span className="hits-chip">
            <span>People checked routes</span>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="https://hits.sh/kolkata-bus-route.vercel.app.svg?label=&color=1f6f4a&labelColor=ffffff" alt="Visitor count" />
          </span>
        </div>
      </header>

      {/* Why this exists — quieter sidebar block */}
      <section className="why-row">
        <div className="why-label">Why this exists</div>
        <p className="why-body">
          <b>Kolkata moves by bus, but the route data is scattered.</b> People rely
          on memory, local advice, and half-complete route lists to figure out how to
          get across the city. I built this as a small attempt to make that fragmented
          knowledge searchable — normalise the stop names, connect the routes, and
          let anyone see possible journeys in one place.
        </p>
      </section>

      {/* Search panel */}
      <section className="search-panel" aria-label="Route search">
        <div className="search-grid">
          <StopInput
            label="From — starting stand"
            placeholder="e.g. Garia Metro"
            value={from}
            onChange={setFrom}
            onSubmit={handleSearch}
          />
          <button
            onClick={handleSwap}
            className="swap-btn"
            title="Swap start and destination"
            aria-label="Swap stands"
          >
            <span aria-hidden>⇅</span>
          </button>
          <StopInput
            label="To — destination stand"
            placeholder="e.g. Howrah Station"
            value={to}
            onChange={setTo}
            onSubmit={handleSearch}
          />
        </div>
        <div className="search-cta-row">
          <span className="search-hint">
            Hit <kbd>Enter</kbd> in either field, or
          </span>
          <button className="go-btn" onClick={handleSearch}>
            Find routes
          </button>
        </div>
      </section>

      {/* Results + Map */}
      <div className="results-grid" ref={resultsRef}>
        <div className="results-col">
          <div className="section-head">
            <span>Journeys</span>
            <span className="rule" />
          </div>
          {renderResults()}
        </div>

        <div className="map-col">
          <div className="section-head">
            <span>Route map</span>
            <span className="rule" />
          </div>
          <RouteMap journey={flat[activeIdx] || null} />
        </div>
      </div>

      {/* Footer */}
      <footer className="page-foot">
        <span className="foot-credit">
          Built as a routing graph over{' '}
          <code>kolbusopedia</code> route data. Stop names normalised through a single{' '}
          <code>canon()</code> layer.
        </span>
        <span className="foot-author">Made with love by Akash and Vedanta</span>
      </footer>
    </div>
  );
}
