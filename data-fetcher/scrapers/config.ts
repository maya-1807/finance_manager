import { CompanyTypes } from 'israeli-bank-scrapers';

export type BankKey = 'leumi' | 'isracard' | 'max';

interface BankDefinition {
  companyType: CompanyTypes;
  envVars: Record<string, string>;
  credentialMapper: (env: Record<string, string>) => Record<string, string>;
}

const bankDefinitions: Record<BankKey, BankDefinition> = {
  leumi: {
    companyType: CompanyTypes.leumi,
    envVars: {
      username: 'LEUMI_USERNAME',
      password: 'LEUMI_PASSWORD',
    },
    credentialMapper: (env) => ({
      username: env['LEUMI_USERNAME'],
      password: env['LEUMI_PASSWORD'],
    }),
  },
  isracard: {
    companyType: CompanyTypes.isracard,
    envVars: {
      id: 'ISRACARD_ID',
      password: 'ISRACARD_PASSWORD',
      card6Digits: 'ISRACARD_CARD_6_DIGITS',
    },
    credentialMapper: (env) => ({
      id: env['ISRACARD_ID'],
      password: env['ISRACARD_PASSWORD'],
      card6Digits: env['ISRACARD_CARD_6_DIGITS'],
    }),
  },
  max: {
    companyType: CompanyTypes.max,
    envVars: {
      username: 'MAX_USERNAME',
      password: 'MAX_PASSWORD',
    },
    credentialMapper: (env) => ({
      username: env['MAX_USERNAME'],
      password: env['MAX_PASSWORD'],
    }),
  },
};

export function getBankDefinition(bankKey: BankKey): BankDefinition {
  return bankDefinitions[bankKey];
}

export function getCredentials(bankKey: BankKey): Record<string, string> {
  const definition = bankDefinitions[bankKey];
  const env = process.env as Record<string, string>;

  for (const [field, envVar] of Object.entries(definition.envVars)) {
    if (!env[envVar]) {
      throw new Error(`Missing environment variable ${envVar} (${field}) for ${bankKey}`);
    }
  }

  return definition.credentialMapper(env);
}

export function getStartDate(): Date {
  const envDate = process.env['SCRAPE_START_DATE'];
  if (envDate) {
    const parsed = new Date(envDate);
    if (!isNaN(parsed.getTime())) {
      return parsed;
    }
  }
  const threeMonthsAgo = new Date();
  threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
  return threeMonthsAgo;
}

export const ALL_BANKS: BankKey[] = ['leumi', 'isracard', 'max'];
