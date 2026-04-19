const fs = require('fs');
const path = require('path');
const vm = require('vm');

const EXTRACTOR_VERSION = 3;

function skipString(source, start, quote) {
  let i = start + 1;
  while (i < source.length) {
    const ch = source[i];
    if (ch === '\\') {
      i += 2;
      continue;
    }
    if (quote === '`' && ch === '$' && source[i + 1] === '{') {
      i = skipTemplateExpression(source, i + 2);
      continue;
    }
    if (ch === quote) {
      return i + 1;
    }
    i += 1;
  }
  return source.length;
}

function skipTemplateExpression(source, start) {
  let depth = 1;
  let i = start;
  while (i < source.length && depth > 0) {
    const ch = source[i];
    if (ch === '\'' || ch === '"' || ch === '`') {
      i = skipString(source, i, ch);
      continue;
    }
    if (ch === '{') {
      depth += 1;
    } else if (ch === '}') {
      depth -= 1;
    }
    i += 1;
  }
  return i;
}

function skipLineComment(source, start) {
  let i = start;
  while (i < source.length && source[i] !== '\n') {
    i += 1;
  }
  return i;
}

function skipBlockComment(source, start) {
  let i = start + 2;
  while (i < source.length - 1) {
    if (source[i] === '*' && source[i + 1] === '/') {
      return i + 2;
    }
    i += 1;
  }
  return source.length;
}

function extractBalanced(source, start, openChar, closeChar) {
  let depth = 0;
  let i = start;
  while (i < source.length) {
    const ch = source[i];
    const next = source[i + 1];
    if (ch === '\'' || ch === '"' || ch === '`') {
      i = skipString(source, i, ch);
      continue;
    }
    if (ch === '/' && next === '/') {
      i = skipLineComment(source, i + 2);
      continue;
    }
    if (ch === '/' && next === '*') {
      i = skipBlockComment(source, i);
      continue;
    }
    if (ch === openChar) {
      depth += 1;
    } else if (ch === closeChar) {
      depth -= 1;
      if (depth === 0) {
        return {
          end: i,
          text: source.slice(start, i + 1),
        };
      }
    }
    i += 1;
  }
  throw new Error(`Unbalanced segment starting at ${start}`);
}

function parseTitleLiteral(argText) {
  const match = argText.match(/^\s*(['"`])([\s\S]*?)\1/);
  return match ? match[2] : 'unknown';
}

function serializeValue(value) {
  if (Object.prototype.toString.call(value) === '[object RegExp]') {
    return {
      __type__: 'RegExp',
      source: value.source,
      flags: value.flags,
      literal: value.toString(),
    };
  }
  if (Array.isArray(value)) {
    return value.map(serializeValue);
  }
  if (value && typeof value === 'object') {
    const result = {};
    for (const [key, inner] of Object.entries(value)) {
      result[key] = serializeValue(inner);
    }
    return result;
  }
  return value;
}

function normalizeArgs(args) {
  if (!Array.isArray(args) || args.length === 0) {
    return [];
  }
  if (args.length === 1 && args[0] && typeof args[0] === 'object' && !Array.isArray(args[0])) {
    if (Object.keys(args[0]).length === 0) {
      return [];
    }
  }
  return serializeValue(args);
}

function evaluateObjectLiteral(objectText) {
  return vm.runInNewContext(`(${objectText})`, {}, { timeout: 1000 });
}

function extractLocalConstContext(blockText, objectStartInBlock) {
  const prefix = blockText.slice(0, objectStartInBlock);
  const declarationPattern = /\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*/g;
  const declarations = [];
  let match = declarationPattern.exec(prefix);

  while (match) {
    const start = match.index;
    const valueStart = declarationPattern.lastIndex;
    let cursor = valueStart;
    let depthParen = 0;
    let depthBracket = 0;
    let depthBrace = 0;

    while (cursor < prefix.length) {
      const ch = prefix[cursor];
      const next = prefix[cursor + 1];
      if (ch === '\'' || ch === '"' || ch === '`') {
        cursor = skipString(prefix, cursor, ch);
        continue;
      }
      if (ch === '/' && next === '/') {
        cursor = skipLineComment(prefix, cursor + 2);
        continue;
      }
      if (ch === '/' && next === '*') {
        cursor = skipBlockComment(prefix, cursor);
        continue;
      }
      if (ch === '(') {
        depthParen += 1;
      } else if (ch === ')') {
        depthParen -= 1;
      } else if (ch === '[') {
        depthBracket += 1;
      } else if (ch === ']') {
        depthBracket -= 1;
      } else if (ch === '{') {
        depthBrace += 1;
      } else if (ch === '}') {
        depthBrace -= 1;
      } else if (ch === ';' && depthParen === 0 && depthBracket === 0 && depthBrace === 0) {
        declarations.push(prefix.slice(start, cursor + 1));
        break;
      }
      cursor += 1;
    }

    match = declarationPattern.exec(prefix);
  }

  return declarations.join('\n');
}

function evaluateObjectLiteralWithContext(objectText, contextSource) {
  const sandbox = {};
  if (contextSource && contextSource.trim()) {
    vm.runInNewContext(contextSource, sandbox, { timeout: 1000 });
  }
  return vm.runInNewContext(`(${objectText})`, sandbox, { timeout: 1000 });
}

function extractGoldenTests(source, validatorName) {
  const results = [];
  const seen = new Set();
  const markerPattern = new RegExp(`validator\\s*:\\s*['"]${validatorName}['"]`, 'g');
  let searchMatch = markerPattern.exec(source);

  while (searchMatch) {
    const validatorIndex = searchMatch.index;

    const testIndex = source.lastIndexOf('test(', validatorIndex);
    const itIndex = source.lastIndexOf('it(', validatorIndex);
    if (testIndex === -1 || itIndex === -1) {
      searchMatch = markerPattern.exec(source);
      continue;
    }

    const titleArgs = extractBalanced(source, itIndex + 2, '(', ')');
    const title = parseTitleLiteral(titleArgs.text.slice(1, -1));
    const itBlockStart = source.indexOf('{', itIndex);
    const itBlock = extractBalanced(source, itBlockStart, '{', '}');
    const objectStart = source.indexOf('{', testIndex);
    const objectLiteral = extractBalanced(source, objectStart, '{', '}');
    if (seen.has(objectLiteral.text)) {
      searchMatch = markerPattern.exec(source);
      continue;
    }
    seen.add(objectLiteral.text);

    const objectStartInBlock = objectStart - itBlockStart;
    const contextSource = extractLocalConstContext(itBlock.text, objectStartInBlock);
    const evaluated = evaluateObjectLiteralWithContext(objectLiteral.text, contextSource);
    if (evaluated.validator === validatorName) {
      results.push({
        title,
        validator: evaluated.validator,
        args: normalizeArgs(evaluated.args || []),
        valid: serializeValue(evaluated.valid || []),
        invalid: serializeValue(evaluated.invalid || []),
      });
    }

    searchMatch = markerPattern.exec(source);
  }

  return results;
}

function main() {
  const [, , inputPath, validatorName, outputPath] = process.argv;
  if (!inputPath || !validatorName || !outputPath) {
    throw new Error('Usage: node extract_golden_tests.js <validators.test.js> <validator-name> <output.json>');
  }
  const source = fs.readFileSync(path.resolve(inputPath), 'utf8');
  const tests = extractGoldenTests(source, validatorName);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(
    outputPath,
    JSON.stringify({ extractor_version: EXTRACTOR_VERSION, test_groups: tests }, null, 2),
    'utf8',
  );
}

main();
