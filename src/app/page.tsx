import { readFile } from 'fs/promises';
import path from 'path';
import BusRouter from '@/components/BusRouter';
import type { BusData } from '@/lib/types';

async function readBusData() {
  const candidates = [
    path.join(process.cwd(), 'src/data/busdata.json'),
    path.join(process.cwd(), 'busdata.json'),
  ];

  for (const filePath of candidates) {
    try {
      return await readFile(filePath, 'utf-8');
    } catch (error) {
      const code = (error as NodeJS.ErrnoException).code;
      if (code !== 'ENOENT') {
        throw error;
      }
    }
  }

  throw new Error(`Missing bus route data. Checked: ${candidates.join(', ')}`);
}

export default async function Home() {
  const raw = await readBusData();
  const data: BusData = JSON.parse(raw);
  return <BusRouter data={data} />;
}
