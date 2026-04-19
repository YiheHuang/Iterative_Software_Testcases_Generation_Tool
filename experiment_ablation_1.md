# Experiment Ablation 1

本节对应“在 `improved whitebox` 中加入 requirement 复检 / pruning 机制”的版本。  
为与最终版本保持完全一致的统计口径，本报告**只保留最终实验中使用的 5 个 validator**：

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
- 总 token 消耗：`1,048,347`
- 平均正确率 `exact_match_rate`：`0.8430`
- 平均黄金命中率 `matched_golden_ratio`：`0.7454`
- 平均语句覆盖率：`84.07`
- 平均分支覆盖率：`77.13`
- 平均函数覆盖率：`100.00`
- 平均行覆盖率：`84.42`
- `exact_match_rate >= 0.9` 的实验共有 `15` 条
- `matched_golden_ratio >= 0.9` 的实验共有 `9` 条
- 两项都 `>= 0.9` 的实验共有 `4` 条

## 汇总表

| Agent | Mode | Avg Tokens | Avg Exact Match | Avg Stmt Cov | Avg Branch Cov | Avg Func Cov | Avg Line Cov | Avg Golden Match |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `naive` | `blackbox` | 15496.80 | 0.9030 | 81.80 | 75.57 | 100.00 | 82.25 | 0.5809 |
| `naive` | `whitebox` | 22056.20 | 0.8780 | 83.36 | 77.17 | 100.00 | 83.88 | 0.7903 |
| `naive` | `whitebox_code_only` | 14870.20 | 0.8248 | 83.06 | 74.64 | 100.00 | 83.50 | 0.6856 |
| `improved` | `blackbox` | 14450.40 | 0.8719 | 84.74 | 79.89 | 100.00 | 85.39 | 0.8430 |
| `improved` | `whitebox` | 79361.20 | 0.8849 | 88.38 | 82.59 | 100.00 | 88.49 | 0.7776 |
| `improved` | `whitebox_code_only` | 63434.60 | 0.6954 | 83.10 | 72.94 | 100.00 | 82.98 | 0.7947 |

从这个表可以看出：

1. 在这一版本中，`improved whitebox` 的 correctness 仍然较高，达到 `0.8849`。
2. 但它的平均 token 高达 `79361.20`，是所有主路线中最昂贵的一档。
3. requirement 复检机制没有带来与高成本相匹配的黄金命中率与覆盖率优势，这也是后续被继续检验的原因。

## 完整结果矩阵

| Validator | Agent | Mode | Status | Correct/Total | Exact Match Rate | Stmt Cov | Branch Cov | Func Cov | Line Cov | Matched Golden Ratio | Total Tokens | Attempts | Note |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| isEmail | naive | blackbox | success | 37/38 | 0.9737 | 73.81 | 68.42 | 100.00 | 73.75 | 0.5714 | 16600 | 1 | ok |
| isEmail | naive | whitebox | success | 44/49 | 0.8980 | 75.00 | 69.74 | 100.00 | 75.00 | 0.8000 | 18534 | 1 | ok |
| isEmail | naive | whitebox_code_only | success | 45/47 | 0.9574 | 75.00 | 69.74 | 100.00 | 75.00 | 0.7500 | 17796 | 1 | ok |
| isEmail | improved | blackbox | success | 44/47 | 0.9362 | 79.76 | 75.00 | 100.00 | 80.00 | 1.0000 | 14641 | 1 | ok |
| isEmail | improved | whitebox | success | 25/27 | 0.9259 | 95.24 | 88.16 | 100.00 | 95.00 | 0.9286 | 122284 | 1 | ok |
| isEmail | improved | whitebox_code_only | success | 16/32 | 0.5000 | 64.29 | 55.26 | 100.00 | 66.25 | 0.8571 | 71140 | 1 | ok |
| isURL | naive | blackbox | success | 35/41 | 0.8537 | 66.95 | 55.46 | 100.00 | 68.42 | 0.5556 | 20072 | 1 | ok |
| isURL | naive | whitebox | success | 43/59 | 0.7288 | 65.25 | 59.66 | 100.00 | 66.67 | 0.8182 | 25859 | 1 | ok |
| isURL | naive | whitebox_code_only | success | 31/39 | 0.7949 | 70.34 | 60.50 | 100.00 | 71.93 | 0.6364 | 22320 | 1 | ok |
| isURL | improved | blackbox | success | 37/47 | 0.7872 | 65.25 | 58.82 | 100.00 | 66.67 | 1.0000 | 19224 | 1 | ok |
| isURL | improved | whitebox | success | 11/13 | 0.8462 | 52.54 | 35.29 | 100.00 | 53.51 | 0.1818 | 165678 | 3 | retried x2 |
| isURL | improved | whitebox_code_only | success | 40/44 | 0.9091 | 79.66 | 64.71 | 100.00 | 78.95 | 0.7273 | 158837 | 1 | ok |
| isFQDN | naive | blackbox | success | 36/43 | 0.8372 | 85.29 | 84.21 | 100.00 | 84.85 | 0.8333 | 9736 | 1 | ok |
| isFQDN | naive | whitebox | success | 59/60 | 0.9833 | 91.18 | 89.47 | 100.00 | 90.91 | 0.8333 | 40521 | 1 | ok |
| isFQDN | naive | whitebox_code_only | success | 69/72 | 0.9583 | 91.18 | 86.84 | 100.00 | 90.91 | 0.6667 | 8039 | 1 | ok |
| isFQDN | improved | blackbox | success | 28/29 | 0.9655 | 85.29 | 84.21 | 100.00 | 84.85 | 0.8333 | 8306 | 1 | ok |
| isFQDN | improved | whitebox | success | 69/71 | 0.9718 | 94.12 | 94.74 | 100.00 | 93.94 | 1.0000 | 55842 | 1 | ok |
| isFQDN | improved | whitebox_code_only | success | 26/27 | 0.9630 | 88.24 | 86.84 | 100.00 | 87.88 | 0.8333 | 31021 | 1 | ok |
| isCurrency | naive | blackbox | success | 94/96 | 0.9792 | 82.93 | 75.00 | 100.00 | 84.21 | 0.5000 | 20317 | 1 | ok |
| isCurrency | naive | whitebox | success | 71/86 | 0.8256 | 85.37 | 72.22 | 100.00 | 86.84 | 0.5000 | 17275 | 1 | ok |
| isCurrency | naive | whitebox_code_only | success | 70/73 | 0.9589 | 82.93 | 66.67 | 100.00 | 84.21 | 0.3750 | 13864 | 1 | ok |
| isCurrency | improved | blackbox | success | 47/65 | 0.7231 | 97.56 | 97.22 | 100.00 | 100.00 | 0.9375 | 21695 | 1 | ok |
| isCurrency | improved | whitebox | success | 55/72 | 0.7639 | 100.00 | 100.00 | 100.00 | 100.00 | 1.0000 | 22756 | 1 | ok |
| isCurrency | improved | whitebox_code_only | success | 33/59 | 0.5593 | 100.00 | 100.00 | 100.00 | 100.00 | 1.0000 | 32739 | 1 | ok |
| isCreditCard | naive | blackbox | success | 27/31 | 0.8710 | 100.00 | 94.74 | 100.00 | 100.00 | 0.4444 | 10759 | 1 | ok |
| isCreditCard | naive | whitebox | success | 21/22 | 0.9545 | 100.00 | 94.74 | 100.00 | 100.00 | 1.0000 | 8092 | 1 | ok |
| isCreditCard | naive | whitebox_code_only | success | 25/55 | 0.4545 | 95.83 | 89.47 | 100.00 | 95.45 | 1.0000 | 12332 | 1 | ok |
| isCreditCard | improved | blackbox | success | 18/19 | 0.9474 | 95.83 | 84.21 | 100.00 | 95.45 | 0.4444 | 8386 | 1 | ok |
| isCreditCard | improved | whitebox | success | 11/12 | 0.9167 | 100.00 | 94.74 | 100.00 | 100.00 | 0.7778 | 30246 | 1 | ok |
| isCreditCard | improved | whitebox_code_only | success | 6/11 | 0.5455 | 83.33 | 57.89 | 100.00 | 81.82 | 0.5556 | 23436 | 1 | ok |

## 结果来源

本文件中的数据主要来自：

- `agent_toolkit/outputs/*/*/*/run_summary.json`
- 各 run 的 `coverage/coverage-summary.json`
