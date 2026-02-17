const NON_RETRYABLE_ERRORS = new Set([
  'InvalidPassword',
  'ChangePasswordNeeded',
  'AccountBlocked',
]);

export function isRetryableError(errorType: string): boolean {
  return !NON_RETRYABLE_ERRORS.has(errorType);
}

export class ScraperError extends Error {
  readonly errorType: string;

  constructor(errorType: string, message: string) {
    super(message);
    this.name = 'ScraperError';
    this.errorType = errorType;
  }
}
