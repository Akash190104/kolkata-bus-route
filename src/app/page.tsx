import BusRouter from '@/components/BusRouter';
import busData from '@/data/busdata.json';
import type { BusData } from '@/lib/types';

export default function Home() {
  return <BusRouter data={busData as BusData} />;
}
