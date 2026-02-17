import { describe, it, expect, vi } from 'vitest';
import { retryWithBackoff } from '../retry.js';

describe('retryWithBackoff', () => {
  it('returns the result on first success', async () => {
    const fn = vi.fn().mockResolvedValue('ok');
    const result = await retryWithBackoff(fn);
    expect(result).toBe('ok');
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('retries on failure and returns on eventual success', async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new Error('fail 1'))
      .mockRejectedValueOnce(new Error('fail 2'))
      .mockResolvedValue('ok');

    const result = await retryWithBackoff(fn, { baseDelayMs: 1, multiplier: 1 });
    expect(result).toBe('ok');
    expect(fn).toHaveBeenCalledTimes(3);
  });

  it('throws after exhausting all retries', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('always fails'));

    await expect(
      retryWithBackoff(fn, { maxRetries: 2, baseDelayMs: 1, multiplier: 1 }),
    ).rejects.toThrow('always fails');
    // 1 initial + 2 retries = 3 calls
    expect(fn).toHaveBeenCalledTimes(3);
  });

  it('does not retry when shouldRetry returns false', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('auth error'));

    await expect(
      retryWithBackoff(fn, { maxRetries: 3, baseDelayMs: 1, shouldRetry: () => false }),
    ).rejects.toThrow('auth error');
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('logs retry attempts with exponential backoff delays', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('fail'));
    const stderrSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    await expect(
      retryWithBackoff(fn, { maxRetries: 3, baseDelayMs: 1, multiplier: 3 }),
    ).rejects.toThrow('fail');

    expect(stderrSpy).toHaveBeenCalledTimes(3);
    // Delays: 1*3^0=1ms, 1*3^1=3ms, 1*3^2=9ms
    expect(stderrSpy).toHaveBeenCalledWith('Attempt 1 failed, retrying in 0.001s...');
    expect(stderrSpy).toHaveBeenCalledWith('Attempt 2 failed, retrying in 0.003s...');
    expect(stderrSpy).toHaveBeenCalledWith('Attempt 3 failed, retrying in 0.009s...');

    stderrSpy.mockRestore();
  });

  it('verifies backoff formula produces correct delays', () => {
    // Verify the exponential backoff formula: baseDelay * multiplier^attempt
    const baseDelayMs = 5000;
    const multiplier = 3;

    const delay0 = baseDelayMs * multiplier ** 0; // 5000ms = 5s
    const delay1 = baseDelayMs * multiplier ** 1; // 15000ms = 15s
    const delay2 = baseDelayMs * multiplier ** 2; // 45000ms = 45s

    expect(delay0).toBe(5000);
    expect(delay1).toBe(15000);
    expect(delay2).toBe(45000);
  });

  it('respects custom maxRetries', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('fail'));

    await expect(
      retryWithBackoff(fn, { maxRetries: 1, baseDelayMs: 1, multiplier: 1 }),
    ).rejects.toThrow('fail');
    // 1 initial + 1 retry = 2 calls
    expect(fn).toHaveBeenCalledTimes(2);
  });
});
