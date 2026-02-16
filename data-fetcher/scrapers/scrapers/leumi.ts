import { createScraper, CompanyTypes, type ScraperScrapingResult, type ScraperCredentials } from 'israeli-bank-scrapers';

export async function scrapeLeumi(credentials: ScraperCredentials, startDate: Date): Promise<ScraperScrapingResult> {
  const scraper = createScraper({
    companyId: CompanyTypes.leumi,
    startDate,
  });
  return scraper.scrape(credentials);
}
