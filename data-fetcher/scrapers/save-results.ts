import { writeFile, mkdir } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { ScraperScrapingResult } from 'israeli-bank-scrapers';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT_DIR = join(__dirname, '..', 'output');

export async function saveResults(bankName: string, result: ScraperScrapingResult): Promise<string> {
  const date = new Date().toISOString().split('T')[0];
  const dir = join(OUTPUT_DIR, bankName);
  await mkdir(dir, { recursive: true });

  const filePath = join(dir, `${bankName}_${date}.json`);

  const output = {
    bank: bankName,
    scrapedAt: new Date().toISOString(),
    accounts: result.accounts ?? [],
  };

  await writeFile(filePath, JSON.stringify(output, null, 2));
  return filePath;
}
