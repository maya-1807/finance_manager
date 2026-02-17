import 'dotenv/config';
import { type BankKey, ALL_BANKS, getCredentials, getStartDate, getBankDefinition } from './config.js';
import { saveResults } from './save-results.js';
import { scrapeLeumi } from './scrapers/leumi.js';
import { scrapeIsracard } from './scrapers/isracard.js';
import { scrapeMax } from './scrapers/max.js';
import { retryWithBackoff } from './retry.js';
import { ScraperError, isRetryableError } from './errors.js';
import type { ScraperCredentials, ScraperScrapingResult } from 'israeli-bank-scrapers';

const scraperFunctions: Record<BankKey, (credentials: ScraperCredentials, startDate: Date) => Promise<ScraperScrapingResult>> = {
  leumi: scrapeLeumi,
  isracard: scrapeIsracard,
  max: scrapeMax,
};

async function runScraper(bankKey: BankKey): Promise<void> {
  console.log(`\n--- Scraping ${bankKey} ---`);

  const credentials = getCredentials(bankKey);
  const startDate = getStartDate();
  console.log(`Start date: ${startDate.toISOString().split('T')[0]}`);

  const scrapeFn = scraperFunctions[bankKey];

  const result = await retryWithBackoff(
    async () => {
      const res = await scrapeFn(credentials as ScraperCredentials, startDate);
      if (!res.success) {
        const errorType = res.errorType ?? 'Generic';
        throw new ScraperError(
          errorType,
          `Scraper failed for ${bankKey}: ${errorType} - ${res.errorMessage}`,
        );
      }
      return res;
    },
    {
      shouldRetry: (error) =>
        error instanceof ScraperError && isRetryableError(error.errorType),
    },
  );

  const accounts = result.accounts ?? [];
  const totalTxns = accounts.reduce((sum, acc) => sum + acc.txns.length, 0);

  const filePath = await saveResults(bankKey, result);
  console.log(`Accounts: ${accounts.length}`);
  console.log(`Transactions: ${totalTxns}`);
  console.log(`Saved to: ${filePath}`);
}

async function main(): Promise<void> {
  const arg = process.argv[2];

  if (!arg) {
    console.error('Usage: tsx scrapers/scrape.ts [leumi|isracard|max|all]');
    process.exit(1);
  }

  const banksToScrape: BankKey[] = arg === 'all' ? ALL_BANKS : [arg as BankKey];

  if (arg !== 'all' && !ALL_BANKS.includes(arg as BankKey)) {
    console.error(`Unknown bank: ${arg}. Valid options: ${ALL_BANKS.join(', ')}, all`);
    process.exit(1);
  }

  let hasError = false;

  for (const bankKey of banksToScrape) {
    try {
      await runScraper(bankKey);
    } catch (error) {
      hasError = true;
      const message = error instanceof Error ? error.message : String(error);
      console.error(`\nError scraping ${bankKey}: ${message}`);
    }
  }

  if (hasError) {
    process.exit(1);
  }

  console.log('\nDone.');
}

main();
