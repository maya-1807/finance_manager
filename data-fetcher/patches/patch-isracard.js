/**
 * Patches israeli-bank-scrapers to work around Isracard bot detection.
 * Based on PR #1027: https://github.com/eshaham/israeli-bank-scrapers/pull/1027
 *
 * Run automatically via npm postinstall, or manually: node patches/patch-isracard.js
 */

const fs = require('fs');
const path = require('path');

const LIB_DIR = path.join(__dirname, '..', 'node_modules', 'israeli-bank-scrapers', 'lib');
const PATCH_MARKER = '/* PATCHED:isracard-anti-bot */';

function patchFile(relPath, patchFn) {
  const filePath = path.join(LIB_DIR, relPath);
  if (!fs.existsSync(filePath)) {
    console.warn(`[patch] File not found, skipping: ${relPath}`);
    return;
  }
  let content = fs.readFileSync(filePath, 'utf-8');
  if (content.includes(PATCH_MARKER)) {
    console.log(`[patch] Already patched: ${relPath}`);
    return;
  }
  content = PATCH_MARKER + '\n' + patchFn(content);
  fs.writeFileSync(filePath, content);
  console.log(`[patch] Patched: ${relPath}`);
}

// 1. Add randomDelay to waiting.js
patchFile('helpers/waiting.js', (content) => {
  content = content.replace(
    'exports.sleep = sleep;',
    'exports.randomDelay = randomDelay;\nexports.sleep = sleep;',
  );
  content = content.replace(
    `function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}`,
    `function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
function randomDelay(min = 500, max = 2000) {
  const delay = Math.floor(Math.random() * (max - min + 1)) + min;
  return new Promise(resolve => setTimeout(resolve, delay));
}`,
  );
  return content;
});

// 2. Patch fetchPostWithinPage to return [text, status] and detect automation blocking
patchFile('helpers/fetch.js', (content) => {
  content = content.replace(
    `    if (response.status === 204) {
      return null;
    }
    return response.text();
  }, url, data, extraHeaders);
  try {
    if (result !== null) {
      return JSON.parse(result);
    }
  } catch (e) {
    if (!ignoreErrors) {
      throw new Error(\`fetchPostWithinPage parse error: \${e instanceof Error ? \`\${e.message}\\n\${e.stack}\` : String(e)}, url: \${url}, data: \${JSON.stringify(data)}, extraHeaders: \${JSON.stringify(extraHeaders)}, result: \${result}\`);
    }
  }`,
    `    if (response.status === 204) {
      return [null, response.status];
    }
    return [await response.text(), response.status];
  }, url, data, extraHeaders);
  const [resultText, status] = result;
  if (!ignoreErrors) {
    if (status === 429 || (resultText && /block automation|bot detection/i.test(resultText))) {
      throw new Error(\`Automation detected and blocked by server. Status: \${status}, URL: \${url}.\`);
    }
  }
  try {
    if (resultText !== null) {
      return JSON.parse(resultText);
    }
  } catch (e) {
    if (!ignoreErrors) {
      throw new Error(\`fetchPostWithinPage parse error: \${e instanceof Error ? \`\${e.message}\\n\${e.stack}\` : String(e)}, url: \${url}, data: \${JSON.stringify(data)}, extraHeaders: \${JSON.stringify(extraHeaders)}, result: \${resultText}\`);
    }
  }`,
  );
  return content;
});

// 3. Patch base-isracard-amex.js: increase delay and use randomDelay
patchFile('scrapers/base-isracard-amex.js', (content) => {
  content = content.replace(
    'SLEEP_BETWEEN: 1000,',
    'SLEEP_BETWEEN: 2500,',
  );
  // Replace all sleep calls with randomDelay
  content = content.replaceAll(
    'await (0, _waiting.sleep)(RATE_LIMIT.SLEEP_BETWEEN)',
    'await (0, _waiting.randomDelay)(RATE_LIMIT.SLEEP_BETWEEN, RATE_LIMIT.SLEEP_BETWEEN + 500)',
  );
  // Add delay before fetchAccounts
  content = content.replace(
    `debug(\`fetching accounts from \${dataUrl}\`);
  const dataResult = await (0, _fetch.fetchGetWithinPage)(page, dataUrl);`,
    `debug(\`fetching accounts from \${dataUrl}\`);
  await (0, _waiting.randomDelay)(RATE_LIMIT.SLEEP_BETWEEN, RATE_LIMIT.SLEEP_BETWEEN + 500);
  const dataResult = await (0, _fetch.fetchGetWithinPage)(page, dataUrl);`,
  );
  return content;
});

console.log('[patch] Done.');
