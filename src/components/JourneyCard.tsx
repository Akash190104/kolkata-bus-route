'use client';

import { useState } from 'react';
import type { Journey } from '@/lib/types';

interface JourneyCardProps {
  journey: Journey;
  active: boolean;
  onClick: () => void;
}

export default function JourneyCard({ journey, active, onClick }: JourneyCardProps) {
  const [expandedLegs, setExpandedLegs] = useState<Set<number>>(new Set());
  const legs = journey.legs;
  const totalStops = legs.reduce((a, l) => a + l.stops.length - 1, 0) + 1;

  const toggleLeg = (idx: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedLegs(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const changes = legs.slice(0, -1).map(l => l.to);
  const changeTxt = changes.length
    ? <>change at {changes.map((c, i) => (
        <span key={i}>
          {i > 0 && ' & '}
          <b className="font-extrabold" style={{ color: 'var(--accent)' }}>{c}</b>
        </span>
      ))}</>
    : 'no changes';

  return (
    <div
      className={`journey-card ${active ? 'active' : ''}`}
      onClick={onClick}
    >
      {/* Top bar */}
      <div className="card-topbar flex items-center gap-2 flex-wrap border-b"
        style={{ borderColor: 'var(--line-soft)' }}>
        {legs.map((l, i) => (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-xs" style={{ color: 'var(--muted)' }}>›</span>}
            <span className={`bus-badge k${i}`}>
              {l.route}<em>{l.kind === 'government' ? 'GOV' : 'PVT'}</em>
            </span>
          </span>
        ))}
        <span className="text-[12.5px] ml-2" style={{ color: 'var(--soft)' }}>
          {changeTxt}
        </span>
        <span className="ml-auto text-right shrink-0"
          style={{ fontFamily: "'Spline Sans Mono', monospace", fontSize: '10px', color: 'var(--muted)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', lineHeight: 1.4 }}>
          ~{totalStops} stops<br />{legs.length} bus{legs.length > 1 ? 'es' : ''}
        </span>
      </div>

      {/* Legs */}
      <div className="card-legs">
        {legs.map((l, i) => {
          const mid = l.stops.slice(1, -1);
          const isExpanded = expandedLegs.has(i);
          return (
            <div key={i} className={`leg-item k${i}`}>
              <div className="leg-dot" />
              <div className="font-bold text-[13.5px] leading-snug" style={{ color: 'var(--ink)' }}>
                <span style={{ color: 'var(--muted)', fontWeight: 600 }}>Bus </span>
                <span style={{ fontFamily: "'Spline Sans Mono', monospace" }}>{l.route}</span>
                <span className="mx-1.5" style={{ color: 'var(--muted)' }}>—</span>
                {l.from} → {l.to}
              </div>
              <div className="text-[11.5px] mt-1" style={{ color: 'var(--muted)', fontFamily: "'Spline Sans Mono', monospace", letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                {l.stops.length} stops · {l.kind} service
              </div>
              {mid.length > 0 && (
                <>
                  <button
                    className="toggle-stops"
                    onClick={e => toggleLeg(i, e)}
                  >
                    {mid.length} stops between {isExpanded ? '▴' : '▾'}
                  </button>
                  {isExpanded && (
                    <div className="stoplist show">
                      {l.stops.map((s, si) => (
                        <span key={si}>
                          {si > 0 && ' · '}
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
