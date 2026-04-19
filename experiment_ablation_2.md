# Experiment Ablation 2

本节对应“ `suite` 迭代形式”的版本。  
为与最终实验保持完全一致的统计口径，本报告**只保留最终实验使用的 5 个 validator**：

- `isEmail`
- `isURL`
- `isFQDN`
- `isCurrency`
- `isCreditCard`

因此总实验数为 `5 x 3 x 2 = 30`。

实验模式与 agent 设定保持不变：

- `blackbox`：仅基于 requirement 生成测试
- `whitebox`：同时基于 requirement 与 source code 生成测试
- `whitebox_code_only`：仅基于 source code 生成测试
- `naive`：单轮生成 + repair/completion
- `improved`：黑盒单轮生成；白盒与纯代码白盒结合执行反馈与覆盖率做迭代 patch

四种覆盖率指标统一取自各 run 的 `coverage/coverage-summary.json`：

- `Stmt Cov`：statement coverage
- `Branch Cov`：branch coverage
- `Func Cov`：function coverage
- `Line Cov`：line coverage

## 总体结果

- 统计实验数：`30`
- 总 token 消耗：`1,073,417`
- 平均正确率 `exact_match_rate`：`0.8559`
- 平均黄金命中率 `matched_golden_ratio`：`0.7388`
- 平均语句覆盖率：`84.24`
- 平均分支覆盖率：`77.15`
- 平均函数覆盖率：`98.89`
- 平均行覆盖率：`84.15`
- `exact_match_rate >= 0.9` 的实验共有 `13` 条
- `matched_golden_ratio >= 0.9` 的实验共有 `9` 条
- 两项都 `>= 0.9` 的实验共有 `2` 条

## 汇总表

| Agent | Mode | Avg Tokens | Avg Exact Match | Avg Stmt Cov | Avg Branch Cov | Avg Func Cov | Avg Line Cov | Avg Golden Match |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `naive` | `blackbox` | 11387.20 | 0.8943 | 82.17 | 74.09 | 100.00 | 81.59 | 0.5872 |
| `naive` | `whitebox` | 19478.80 | 0.8983 | 82.53 | 76.76 | 100.00 | 82.48 | 0.5806 |
| `naive` | `whitebox_code_only` | 19127.20 | 0.8836 | 85.13 | 78.62 | 100.00 | 85.21 | 0.6369 |
| `improved` | `blackbox` | 28899.60 | 0.8653 | 86.22 | 80.93 | 100.00 | 86.40 | 0.9238 |
| `improved` | `whitebox` | 68342.80 | 0.8164 | 88.74 | 81.49 | 100.00 | 89.37 | 0.8430 |
| `improved` | `whitebox_code_only` | 67447.80 | 0.7775 | 80.64 | 71.00 | 93.33 | 79.85 | 0.8615 |

从这个表可以看出：

1. 在这一版本中，`improved whitebox` 的 coverage 与 golden 命中仍明显强于 `naive whitebox`。
2. 但 `improved whitebox` 的平均正确率只有 `0.8164`，并未超过 `naive whitebox` 的 `0.8983`。
3. 与最终版本相比，这一阶段的 `improved whitebox` 还没有形成更优的成本-覆盖率平衡。

## 完整结果矩阵

| Validator | Agent | Mode | Status | Correct/Total | Exact Match Rate | Stmt Cov | Branch Cov | Func Cov | Line Cov | Matched Golden Ratio | Total Tokens | Attempts | Note |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| isEmail | naive | blackbox | success | 43/45 | 0.9556 | 73.81 | 68.42 | 100.00 | 73.75 | 0.5000 | 11991 | 1 | ok |
| isEmail | naive | whitebox | success | 47/49 | 0.9592 | 75.00 | 71.05 | 100.00 | 75.00 | 0.5714 | 14168 | 1 | ok |
| isEmail | naive | whitebox_code_only | success | 34/40 | 0.8500 | 73.81 | 67.11 | 100.00 | 73.75 | 0.4286 | 46352 | 1 | ok |
| isEmail | improved | blackbox | success | 31/32 | 0.9688 | 75.00 | 69.74 | 100.00 | 75.00 | 0.7857 | 50074 | 2 | ok |
| isEmail | improved | whitebox | success | 33/38 | 0.8684 | 95.24 | 88.16 | 100.00 | 95.00 | 0.8571 | 55393 | 1 | ok |
| isEmail | improved | whitebox_code_only | success | 29/35 | 0.8286 | 94.05 | 89.47 | 100.00 | 93.75 | 0.9286 | 146586 | 1 | ok |
| isURL | naive | blackbox | success | 31/41 | 0.7561 | 62.71 | 50.42 | 100.00 | 61.40 | 0.8182 | 14479 | 1 | ok |
| isURL | naive | whitebox | success | 34/46 | 0.7391 | 63.56 | 56.30 | 100.00 | 64.91 | 0.7273 | 18202 | 1 | ok |
| isURL | naive | whitebox_code_only | success | 45/50 | 0.9000 | 72.88 | 63.87 | 100.00 | 74.56 | 0.8182 | 16392 | 1 | ok |
| isURL | improved | blackbox | success | 42/47 | 0.8936 | 72.03 | 63.87 | 100.00 | 73.68 | 1.0000 | 54520 | 1 | ok |
| isURL | improved | whitebox | success | 24/31 | 0.7742 | 56.78 | 43.70 | 100.00 | 57.89 | 0.5455 | 217109 | 2 | ok |
| isURL | improved | whitebox_code_only | success | 34/39 | 0.8718 | 74.58 | 65.55 | 100.00 | 73.68 | 0.5455 | 105139 | 1 | ok |
| isFQDN | naive | blackbox | success | 47/50 | 0.9400 | 88.24 | 86.84 | 100.00 | 87.88 | 0.8333 | 7287 | 3 | ok |
| isFQDN | naive | whitebox | success | 43/44 | 0.9773 | 91.18 | 89.47 | 100.00 | 90.91 | 0.8333 | 40142 | 1 | ok |
| isFQDN | naive | whitebox_code_only | success | 30/34 | 0.8824 | 91.18 | 86.84 | 100.00 | 90.91 | 0.6667 | 7606 | 1 | ok |
| isFQDN | improved | blackbox | success | 38/39 | 0.9744 | 88.24 | 86.84 | 100.00 | 87.88 | 0.8333 | 8325 | 1 | ok |
| isFQDN | improved | whitebox | success | 27/32 | 0.8438 | 94.12 | 94.74 | 100.00 | 93.94 | 1.0000 | 32866 | 1 | ok |
| isFQDN | improved | whitebox_code_only | success | 14/28 | 0.5000 | 47.06 | 36.84 | 66.67 | 45.45 | 0.8333 | 42861 | 1 | ok |
| isCurrency | naive | blackbox | success | 76/85 | 0.8941 | 90.24 | 80.56 | 100.00 | 89.47 | 0.5625 | 15889 | 1 | ok |
| isCurrency | naive | whitebox | success | 93/103 | 0.9029 | 82.93 | 72.22 | 100.00 | 81.58 | 0.4375 | 16804 | 1 | ok |
| isCurrency | naive | whitebox_code_only | success | 74/84 | 0.8810 | 87.80 | 80.56 | 100.00 | 86.84 | 0.9375 | 17245 | 1 | ok |
| isCurrency | improved | blackbox | success | 47/66 | 0.7121 | 100.00 | 100.00 | 100.00 | 100.00 | 1.0000 | 21735 | 1 | ok |
| isCurrency | improved | whitebox | success | 31/48 | 0.6458 | 97.56 | 86.11 | 100.00 | 100.00 | 0.8125 | 19819 | 1 | ok |
| isCurrency | improved | whitebox_code_only | success | 28/36 | 0.7778 | 100.00 | 100.00 | 100.00 | 100.00 | 1.0000 | 18992 | 1 | ok |
| isCreditCard | naive | blackbox | success | 25/27 | 0.9259 | 95.83 | 84.21 | 100.00 | 95.45 | 0.2222 | 7290 | 1 | ok |
| isCreditCard | naive | whitebox | success | 21/23 | 0.9130 | 100.00 | 94.74 | 100.00 | 100.00 | 0.3333 | 8078 | 1 | ok |
| isCreditCard | naive | whitebox_code_only | success | 19/21 | 0.9048 | 100.00 | 94.74 | 100.00 | 100.00 | 0.3333 | 8041 | 1 | ok |
| isCreditCard | improved | blackbox | success | 14/18 | 0.7778 | 95.83 | 84.21 | 100.00 | 95.45 | 1.0000 | 9844 | 1 | ok |
| isCreditCard | improved | whitebox | success | 19/20 | 0.9500 | 100.00 | 94.74 | 100.00 | 100.00 | 1.0000 | 16527 | 1 | ok |
| isCreditCard | improved | whitebox_code_only | success | 10/11 | 0.9091 | 87.50 | 63.16 | 100.00 | 86.36 | 1.0000 | 23661 | 1 | ok |

## 结果来源

本文件中的数据主要来自：

- `agent_toolkit/outputs/*/*/*/run_summary.json`
- 各 run 的 `coverage/coverage-summary.json`
