'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { getSortedStops, getStopRouteCount } from '@/lib/router';

interface StopInputProps {
  label: string;
  placeholder: string;
  value: string;
  onChange: (val: string) => void;
  onSubmit?: () => void;
}

export default function StopInput({ label, placeholder, value, onChange, onSubmit }: StopInputProps) {
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(-1);
  const [items, setItems] = useState<string[]>([]);
  const boxRef = useRef<HTMLDivElement>(null);

  const render = useCallback((q: string) => {
    const sorted = getSortedStops();
    const lq = q.toLowerCase().trim();
    const filtered = lq
      ? sorted.filter(s => s.toLowerCase().includes(lq)).slice(0, 40)
      : sorted.slice(0, 40);
    setItems(filtered);
    setOpen(filtered.length > 0);
    setHi(-1);
  }, []);

  const close = useCallback(() => {
    setOpen(false);
    setHi(-1);
  }, []);

  const handleSelect = useCallback((val: string) => {
    onChange(val);
    close();
  }, [onChange, close]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHi(prev => Math.min(prev + 1, items.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHi(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (hi >= 0 && items[hi]) {
        handleSelect(items[hi]);
      } else {
        close();
        onSubmit?.();
      }
    } else if (e.key === 'Escape') {
      close();
    }
  }, [hi, items, handleSelect, close, onSubmit]);

  useEffect(() => {
    if (hi >= 0 && boxRef.current) {
      const el = boxRef.current.children[hi] as HTMLElement;
      el?.scrollIntoView({ block: 'nearest' });
    }
  }, [hi]);

  return (
    <div className="relative">
      <label className="block mb-2 font-semibold text-[10.5px] uppercase"
        style={{ fontFamily: "'Spline Sans Mono', monospace", color: 'var(--muted)', letterSpacing: '0.16em' }}>
        {label}
      </label>
      <input
        type="text"
        autoComplete="off"
        className="w-full font-semibold"
        style={{
          fontFamily: "'Hanken Grotesque', sans-serif",
          fontSize: '15.5px',
          padding: '12px 14px',
          border: '1.5px solid var(--line)',
          background: 'var(--card)',
          color: 'var(--ink)',
          borderRadius: 'var(--radius-sm)',
          height: '44px',
        }}
        placeholder={placeholder}
        value={value}
        onChange={e => { onChange(e.target.value); render(e.target.value); }}
        onFocus={() => render(value)}
        onBlur={() => setTimeout(close, 150)}
        onKeyDown={handleKeyDown}
      />
      <div ref={boxRef} className={`ac-dropdown ${open ? 'open' : ''}`}>
        {items.map((s, i) => {
          const n = getStopRouteCount(s);
          return (
            <div
              key={s}
              className={`ac-item ${i === hi ? 'hi' : ''}`}
              onMouseDown={e => { e.preventDefault(); handleSelect(s); }}
            >
              {s}
              <span>{n} route{n !== 1 ? 's' : ''}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
