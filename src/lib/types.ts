export interface Route {
  code: string;
  kind: 'private' | 'government';
  stops: string[];
}

export interface StopInfo {
  name: string;
  routes: number;
  lat: number | null;
  lng: number | null;
}

export interface BusData {
  routes: Route[];
  stops: StopInfo[];
}

export interface Leg {
  route: string;
  kind: 'private' | 'government';
  from: string;
  to: string;
  stops: string[];
}

export interface Journey {
  legs: Leg[];
  cost: number;
}

export interface SearchResult {
  origin: string;
  dest: string;
  direct: Journey[];
  one: Journey[];
  two: Journey[];
  error?: boolean;
}
