import { describe, it, expect, vi } from 'vitest';
import { retryWithBackoff } from '../retry.js';
import { ScraperError, isRetryableError } from '../errors.js';

/**
 * Integration tests that verify how retryWithBackoff + ScraperError + isRetryableError
 * work together — this mirrors the wiring in scrape.ts's runScraper().
 */

// Simulates what runScraper does: call a scraper, throw ScraperError on failure,
// retry only if the error is retryable
async function simulateRunScraper(
  scrapeFn: () => Promise<{ success: boolean; errorType?: string; errorMessage?: string }>,
) {
  return retryWithBackoff(
    async () => {
      const res = await scrapeFn();
      if (!res.success) {
        const errorType = res.errorType ?? 'Generic';
        throw new ScraperError(
          errorType,
          `Scraper failed: ${errorType} - ${res.errorMessage}`,
        );
      }
      return res;
    },
    {
      baseDelayMs: 1, // tiny delay for test speed
      shouldRetry: (error) =>
        error instanceof ScraperError && isRetryableError(error.errorType),
    },
  );
}

describe('scrape integration: retry + error classification', () => {
  it('succeeds without retry on first successful scrape', async () => {
    const scrapeFn = vi.fn().mockResolvedValue({ success: true });

    const result = await simulateRunScraper(scrapeFn);
    expect(result.success).toBe(true);
    expect(scrapeFn).toHaveBeenCalledTimes(1);
  });

  it('retries on Timeout and succeeds on second attempt', async () => {
    const scrapeFn = vi
      .fn()
      .mockResolvedValueOnce({ success: false, errorType: 'Timeout', errorMessage: 'timed out' })
      .mockResolvedValue({ success: true });

    const result = await simulateRunScraper(scrapeFn);
    expect(result.success).toBe(true);
    expect(scrapeFn).toHaveBeenCalledTimes(2);
  });

  it('retries on NetworkError and succeeds on third attempt', async () => {
    const scrapeFn = vi
      .fn()
      .mockResolvedValueOnce({ success: false, errorType: 'NetworkError', errorMessage: 'net err' })
      .mockResolvedValueOnce({ success: false, errorType: 'NetworkError', errorMessage: 'net err' })
      .mockResolvedValue({ success: true });

    const result = await simulateRunScraper(scrapeFn);
    expect(result.success).toBe(true);
    expect(scrapeFn).toHaveBeenCalledTimes(3);
  });

  it('does NOT retry on InvalidPassword — fails immediately', async () => {
    const scrapeFn = vi
      .fn()
      .mockResolvedValue({ success: false, errorType: 'InvalidPassword', errorMessage: 'bad pw' });

    await expect(simulateRunScraper(scrapeFn)).rejects.toThrow(ScraperError);
    expect(scrapeFn).toHaveBeenCalledTimes(1);
  });

  it('does NOT retry on ChangePasswordNeeded — fails immediately', async () => {
    const scrapeFn = vi
      .fn()
      .mockResolvedValue({ success: false, errorType: 'ChangePasswordNeeded', errorMessage: '' });

    await expect(simulateRunScraper(scrapeFn)).rejects.toThrow(ScraperError);
    expect(scrapeFn).toHaveBeenCalledTimes(1);
  });

  it('does NOT retry on AccountBlocked — fails immediately', async () => {
    const scrapeFn = vi
      .fn()
      .mockResolvedValue({ success: false, errorType: 'AccountBlocked', errorMessage: '' });

    await expect(simulateRunScraper(scrapeFn)).rejects.toThrow(ScraperError);
    expect(scrapeFn).toHaveBeenCalledTimes(1);
  });

  it('retries on Generic error (catch-all)', async () => {
    const scrapeFn = vi
      .fn()
      .mockResolvedValueOnce({ success: false, errorType: 'Generic', errorMessage: 'unknown' })
      .mockResolvedValue({ success: true });

    const result = await simulateRunScraper(scrapeFn);
    expect(result.success).toBe(true);
    expect(scrapeFn).toHaveBeenCalledTimes(2);
  });

  it('defaults to Generic when errorType is missing', async () => {
    const scrapeFn = vi
      .fn()
      .mockResolvedValueOnce({ success: false, errorMessage: 'no type given' })
      .mockResolvedValue({ success: true });

    const result = await simulateRunScraper(scrapeFn);
    expect(result.success).toBe(true);
    expect(scrapeFn).toHaveBeenCalledTimes(2);
  });

  it('thrown ScraperError preserves errorType from the library result', async () => {
    const scrapeFn = vi
      .fn()
      .mockResolvedValue({ success: false, errorType: 'InvalidPassword', errorMessage: 'bad creds' });

    try {
      await simulateRunScraper(scrapeFn);
      expect.fail('should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ScraperError);
      expect((err as ScraperError).errorType).toBe('InvalidPassword');
      expect((err as ScraperError).message).toContain('InvalidPassword');
      expect((err as ScraperError).message).toContain('bad creds');
    }
  });

  it('gives up after maxRetries even for retryable errors', async () => {
    const scrapeFn = vi
      .fn()
      .mockResolvedValue({ success: false, errorType: 'Timeout', errorMessage: 'timed out' });

    // Default maxRetries is 3 → 4 total attempts
    await expect(simulateRunScraper(scrapeFn)).rejects.toThrow(ScraperError);
    expect(scrapeFn).toHaveBeenCalledTimes(4);
  });
});
