import type { BusData, Route, Leg, SearchResult } from './types';

let routes: Route[] = [];
let routeSet: Set<string>[] = [];
let stopRoutes: Record<string, number[]> = {};
let routeAdj: Set<number>[] = [];
let coord: Record<string, [number, number]> = {};
let stopNames: string[] = [];
let sortedStops: string[] = [];
let initialized = false;

export function initRouter(data: BusData) {
  if (initialized) return;
  routes = data.routes;
  routeSet = routes.map(r => new Set(r.stops));
  stopRoutes = {};
  routes.forEach((r, i) => {
    new Set(r.stops).forEach(s => {
      (stopRoutes[s] = stopRoutes[s] || []).push(i);
    });
  });
  routeAdj = routes.map(() => new Set<number>());
  Object.values(stopRoutes).forEach(rs => {
    for (let a = 0; a < rs.length; a++)
      for (let b = a + 1; b < rs.length; b++) {
        routeAdj[rs[a]].add(rs[b]);
        routeAdj[rs[b]].add(rs[a]);
      }
  });
  coord = {};
  data.stops.forEach(s => {
    if (s.lat != null && s.lng != null) coord[s.name] = [s.lat, s.lng];
  });
  stopNames = data.stops.map(s => s.name);
  sortedStops = stopNames.slice().sort();
  initialized = true;
}

export function getRouteCount() {
  return routes.length;
}

export function getStopCount() {
  return stopNames.length;
}

export function getCoord(name: string): [number, number] | undefined {
  return coord[name];
}

export function getSortedStops() {
  return sortedStops;
}

export function getStopRouteCount(name: string): number {
  return stopRoutes[name]?.length ?? 0;
}

function idx(r: number, s: string): number {
  return routes[r].stops.indexOf(s);
}

function seg(r: number, a: string, b: string): string[] {
  const i = idx(r, a), j = idx(r, b), st = routes[r].stops;
  return i <= j ? st.slice(i, j + 1) : st.slice(j, i + 1).reverse();
}

function shared(r1: number, r2: number): string[] {
  const out: string[] = [];
  routeSet[r1].forEach(s => {
    if (routeSet[r2].has(s)) out.push(s);
  });
  return out;
}

function bestTransfer(r1: number, r2: number, o: string, d: string): [string | null, number] {
  let best: string | null = null, bc = 1e9;
  shared(r1, r2).forEach(t => {
    const c = Math.abs(idx(r1, o) - idx(r1, t)) + Math.abs(idx(r2, t) - idx(r2, d));
    if (c < bc) { best = t; bc = c; }
  });
  return [best, bc];
}

function leg(r: number, a: string, b: string): Leg {
  return {
    route: routes[r].code,
    kind: routes[r].kind,
    from: a,
    to: b,
    stops: seg(r, a, b),
  };
}

export function findRoutes(o: string, d: string): SearchResult {
  const res: SearchResult = { origin: o, dest: d, direct: [], one: [], two: [] };
  if (!stopRoutes[o] || !stopRoutes[d]) { res.error = true; return res; }
  const start = stopRoutes[o];
  const end = new Set(stopRoutes[d]);

  // Direct routes
  start.filter(r => end.has(r))
    .sort((a, b) => Math.abs(idx(a, o) - idx(a, d)) - Math.abs(idx(b, o) - idx(b, d)))
    .forEach(r => res.direct.push({ legs: [leg(r, o, d)], cost: Math.abs(idx(r, o) - idx(r, d)) }));

  // One transfer
  const seen = new Set<string>();
  const c1: { cost: number; r1: number; r2: number; t: string }[] = [];
  start.forEach(r1 => {
    routeAdj[r1].forEach(r2 => {
      if (r1 === r2 || !end.has(r2)) return;
      const key = [routes[r1].code, routes[r2].code].sort().join('|');
      if (seen.has(key)) return;
      const [t, cost] = bestTransfer(r1, r2, o, d);
      if (t == null || t === o || t === d) return;
      seen.add(key);
      c1.push({ cost, r1, r2, t });
    });
  });
  c1.sort((a, b) => a.cost - b.cost).slice(0, 10).forEach(x => {
    res.one.push({ legs: [leg(x.r1, o, x.t), leg(x.r2, x.t, d)], cost: x.cost });
  });

  // Two transfers (only when easy options are thin)
  if (res.direct.length + res.one.length < 3) {
    const seen2 = new Set<string>();
    const c2: { cost: number; r1: number; r2: number; r3: number; a: string; b: string }[] = [];
    start.forEach(r1 => {
      stopRoutes[d].forEach(r3 => {
        if (r3 === r1) return;
        routeAdj[r1].forEach(r2 => {
          if (r2 === r1 || r2 === r3 || !routeAdj[r3].has(r2)) return;
          if (end.has(r2) || start.includes(r2)) return;
          const key = routes[r1].code + '|' + routes[r2].code + '|' + routes[r3].code;
          if (seen2.has(key)) return;
          const s12 = shared(r1, r2), s23 = shared(r2, r3);
          let bt: [string, string] | null = null, bc = 1e9;
          s12.forEach(a => s23.forEach(b => {
            if (new Set([o, a, b, d]).size < 4) return;
            const cc = Math.abs(idx(r1, o) - idx(r1, a))
              + Math.abs(idx(r2, a) - idx(r2, b))
              + Math.abs(idx(r3, b) - idx(r3, d));
            if (cc < bc) { bc = cc; bt = [a, b]; }
          }));
          if (!bt) return;
          seen2.add(key);
          c2.push({ cost: bc, r1, r2, r3, a: bt[0], b: bt[1] });
        });
      });
    });
    c2.sort((a, b) => a.cost - b.cost).slice(0, 6).forEach(x => {
      res.two.push({ legs: [leg(x.r1, o, x.a), leg(x.r2, x.a, x.b), leg(x.r3, x.b, d)], cost: x.cost });
    });
  }
  return res;
}
