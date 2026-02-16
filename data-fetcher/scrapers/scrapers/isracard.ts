import { createScraper, CompanyTypes, type ScraperScrapingResult, type ScraperCredentials } from 'israeli-bank-scrapers';

export async function scrapeIsracard(credentials: ScraperCredentials, startDate: Date): Promise<ScraperScrapingResult> {
  const scraper = createScraper({
    companyId: CompanyTypes.isracard,
    startDate,
    showBrowser: true,
  });
  return scraper.scrape(credentials);
}
