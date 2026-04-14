const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');

const projectRequire = createRequire(path.resolve(process.cwd(), 'package.json'));

async function main() {
  const [, , inputJsonPath, outputJsonPath, coverageDir] = process.argv;
  if (!inputJsonPath || !outputJsonPath) {
    throw new Error('Usage: node run_validator_eval.js <input-json> <output-json> [coverage-dir]');
  }

  const payload = JSON.parse(fs.readFileSync(inputJsonPath, 'utf8'));
  projectRequire('@babel/register');
  const validatorCache = new Map();

  const getValidatorFunction = (validatorName) => {
    if (!validatorCache.has(validatorName)) {
      const modulePath = `./src/lib/${validatorName}.js`;
      const loaded = projectRequire(modulePath);
      validatorCache.set(validatorName, loaded.default || loaded);
    }
    return validatorCache.get(validatorName);
  };

  const results = [];
  let correctCases = 0;
  let incorrectCases = 0;

  for (const testCase of payload.cases) {
    const args = Array.isArray(testCase.args) ? testCase.args : [];
    let actualKind = 'return';
    let actualValue = null;
    let actualErrorName = null;
    let passed = false;

    try {
      const validatorFn = getValidatorFunction(testCase.validator);
      actualValue = validatorFn(testCase.input_value, ...args);
      if (testCase.expected_kind === 'return') {
        passed = actualValue === testCase.expected;
      }
    } catch (error) {
      actualKind = 'throw';
      actualErrorName = error && error.name ? error.name : 'Error';
      if (testCase.expected_kind === 'throw') {
        passed = actualErrorName === testCase.expected;
      }
    }

    if (passed) {
      correctCases += 1;
    } else {
      incorrectCases += 1;
    }

    results.push({
      title: testCase.title,
      validator: testCase.validator,
      args: args,
      input_value: testCase.input_value,
      expected_kind: testCase.expected_kind,
      expected: testCase.expected,
      actual_kind: actualKind,
      actual_value: actualValue,
      actual_error_name: actualErrorName,
      passed: passed,
      obligations: testCase.obligations || [],
    });
  }

  const totalCases = results.length;
  const exactMatchRate = totalCases === 0 ? 0 : correctCases / totalCases;
  const failedResults = results.filter((result) => !result.passed);
  const passedResults = results.filter((result) => result.passed);

  const byExpectedKind = {
    return: results.filter((result) => result.expected_kind === 'return').length,
    throw: results.filter((result) => result.expected_kind === 'throw').length,
  };

  const byTitle = {};
  for (const result of results) {
    const key = result.title || 'untitled';
    if (!byTitle[key]) {
      byTitle[key] = {
        total: 0,
        passed: 0,
        failed: 0,
      };
    }
    byTitle[key].total += 1;
    if (result.passed) {
      byTitle[key].passed += 1;
    } else {
      byTitle[key].failed += 1;
    }
  }

  const byObligation = {};
  for (const result of results) {
    for (const obligation of result.obligations || []) {
      if (!byObligation[obligation]) {
        byObligation[obligation] = {
          total: 0,
          passed: 0,
          failed: 0,
        };
      }
      byObligation[obligation].total += 1;
      if (result.passed) {
        byObligation[obligation].passed += 1;
      } else {
        byObligation[obligation].failed += 1;
      }
    }
  }

  let coverageSummary = null;
  let coverageFiles = {};
  let coverageSummaryPath = null;
  if (coverageDir) {
    coverageSummaryPath = path.join(coverageDir, 'coverage-summary.json');
    if (fs.existsSync(coverageSummaryPath)) {
      coverageSummary = JSON.parse(fs.readFileSync(coverageSummaryPath, 'utf8'));
      coverageFiles = Object.fromEntries(
        Object.entries(coverageSummary).filter(([filePath]) => filePath !== 'total'),
      );
    }
  }

  fs.writeFileSync(
    outputJsonPath,
    JSON.stringify(
      {
        results,
        summary: {
          total_cases: totalCases,
          correct_cases: correctCases,
          incorrect_cases: incorrectCases,
          exact_match_rate: exactMatchRate,
          by_expected_kind: byExpectedKind,
        },
        details: {
          passed_results: passedResults,
          failed_results: failedResults,
          by_title: byTitle,
          by_obligation: byObligation,
          coverage_summary_path: coverageSummaryPath,
          coverage_total: coverageSummary ? coverageSummary.total : null,
          coverage_files: coverageFiles,
        },
      },
      null,
      2,
    ),
    'utf8',
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
