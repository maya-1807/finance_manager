import { createScraper, CompanyTypes, type ScraperScrapingResult, type ScraperCredentials } from 'israeli-bank-scrapers';

export async function scrapeMax(credentials: ScraperCredentials, startDate: Date): Promise<ScraperScrapingResult> {
  const scraper = createScraper({
    companyId: CompanyTypes.max,
    startDate,
  });
  return scraper.scrape(credentials);
}
