import { describe, it, expect } from 'vitest';
import { isRetryableError, ScraperError } from '../errors.js';

describe('isRetryableError', () => {
  it.each(['InvalidPassword', 'ChangePasswordNeeded', 'AccountBlocked'])(
    'returns false for non-retryable error: %s',
    (errorType) => {
      expect(isRetryableError(errorType)).toBe(false);
    },
  );

  it.each(['Timeout', 'NetworkError', 'Generic', 'UnknownFutureError'])(
    'returns true for retryable error: %s',
    (errorType) => {
      expect(isRetryableError(errorType)).toBe(true);
    },
  );
});

describe('ScraperError', () => {
  it('preserves errorType and message', () => {
    const err = new ScraperError('Timeout', 'connection timed out');
    expect(err.errorType).toBe('Timeout');
    expect(err.message).toBe('connection timed out');
    expect(err.name).toBe('ScraperError');
  });

  it('is an instance of Error', () => {
    const err = new ScraperError('Generic', 'something broke');
    expect(err).toBeInstanceOf(Error);
  });
});
