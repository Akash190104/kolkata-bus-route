import { readFile } from 'fs/promises';
import path from 'path';
import BusRouter from '@/components/BusRouter';
import type { BusData } from '@/lib/types';

export default async function Home() {
  const raw = await readFile(
    path.join(process.cwd(), 'src/data/busdata.json'),
    'utf-8',
  );
  const data: BusData = JSON.parse(raw);
  return <BusRouter data={data} />;
}
