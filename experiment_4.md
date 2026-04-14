# Experiment 4

本轮实验基于当前项目的最新实现与最新黄金分析口径重新运行：

- `blackbox`：仅基于 `validator_js/README.md` 中的 requirement 生成测试
- `whitebox`：同时基于 requirement 与 source code 生成测试
- `naive`：单轮生成 + JSON repair/completion
- `improved`：黑盒单轮生成；白盒基于执行结果与覆盖率做小规模 patch

说明：

- 本实验覆盖 `isEmail`、`isFQDN`、`isURL`
- 每个函数都运行 `naive/improved` 两种 agent 的黑盒与白盒测试
- 所有实验均开启黄金测试重合度分析
- 黄金测试字段全部采用最新的 category-level 双向匹配口径
- 本轮额外加入四类覆盖率字段：`Lines / Statements / Functions / Branches`
- 为避免 API 请求过于密集，本轮按 `3` 组一批、共 `4` 批的方式运行

## isEmail

| Agent | Mode | Obligations | Generated Groups | Generated Categories | Total Cases | Correct | Incorrect | Exact Match Rate | Lines % | Statements % | Functions % | Branches % | Total Golden Categories | Overlap Golden Categories | Missing Golden Categories | Matched Generated Categories | Novel Generated Categories | Strong Matches | Partial Matches | Fragmented Matches | Matched Golden Ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 0 | 8 | 4 | 77 | 75 | 2 | 0.9740 | 72.50 | 72.62 | 100.00 | 67.11 | 12 | 7 | 5 | 4 | 0 | 2 | 5 | 0 | 0.5833 |
| naive | whitebox | 0 | 7 | 6 | 48 | 46 | 2 | 0.9583 | 73.75 | 73.81 | 100.00 | 68.42 | 12 | 7 | 5 | 6 | 0 | 5 | 2 | 0 | 0.5833 |
| improved | blackbox | 7 | 7 | 6 | 31 | 30 | 1 | 0.9677 | 71.25 | 70.24 | 100.00 | 60.53 | 12 | 6 | 6 | 5 | 1 | 4 | 2 | 0 | 0.5000 |
| improved | whitebox | 7 | 13 | 7 | 41 | 38 | 3 | 0.9268 | 82.50 | 82.14 | 100.00 | 77.63 | 12 | 10 | 2 | 7 | 0 | 4 | 6 | 0 | 0.8333 |

## isFQDN

| Agent | Mode | Obligations | Generated Groups | Generated Categories | Total Cases | Correct | Incorrect | Exact Match Rate | Lines % | Statements % | Functions % | Branches % | Total Golden Categories | Overlap Golden Categories | Missing Golden Categories | Matched Generated Categories | Novel Generated Categories | Strong Matches | Partial Matches | Fragmented Matches | Matched Golden Ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 0 | 7 | 7 | 74 | 70 | 4 | 0.9459 | 87.88 | 88.24 | 100.00 | 86.84 | 6 | 5 | 1 | 5 | 2 | 4 | 1 | 0 | 0.8333 |
| naive | whitebox | 0 | 7 | 7 | 85 | 81 | 4 | 0.9529 | 87.88 | 88.24 | 100.00 | 86.84 | 6 | 5 | 1 | 5 | 2 | 4 | 1 | 0 | 0.8333 |
| improved | blackbox | 7 | 7 | 3 | 74 | 71 | 3 | 0.9595 | 87.88 | 88.24 | 100.00 | 86.84 | 6 | 6 | 0 | 2 | 1 | 1 | 5 | 0 | 1.0000 |
| improved | whitebox | 7 | 18 | 7 | 102 | 96 | 6 | 0.9412 | 90.91 | 91.18 | 100.00 | 89.47 | 6 | 6 | 0 | 6 | 1 | 4 | 2 | 1 | 1.0000 |

## isURL

| Agent | Mode | Obligations | Generated Groups | Generated Categories | Total Cases | Correct | Incorrect | Exact Match Rate | Lines % | Statements % | Functions % | Branches % | Total Golden Categories | Overlap Golden Categories | Missing Golden Categories | Matched Generated Categories | Novel Generated Categories | Strong Matches | Partial Matches | Fragmented Matches | Matched Golden Ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 0 | 8 | 6 | 42 | 35 | 7 | 0.8333 | 59.65 | 58.47 | 100.00 | 45.38 | 9 | 6 | 3 | 6 | 0 | 5 | 1 | 0 | 0.6667 |
| naive | whitebox | 0 | 7 | 5 | 36 | 33 | 3 | 0.9167 | 64.04 | 62.71 | 100.00 | 47.90 | 9 | 7 | 2 | 5 | 0 | 4 | 3 | 0 | 0.7778 |
| improved | blackbox | 13 | 13 | 5 | 73 | 66 | 7 | 0.9041 | 71.05 | 69.49 | 100.00 | 61.34 | 9 | 8 | 1 | 5 | 0 | 4 | 4 | 0 | 0.8889 |
| improved | whitebox | 3 | 14 | 7 | 79 | 71 | 8 | 0.8987 | 82.46 | 83.05 | 100.00 | 73.11 | 9 | 7 | 2 | 7 | 0 | 5 | 2 | 0 | 0.7778 |

## 简短观察

| 现象 | 观察 |
|---|---|
| `isEmail` | 本轮 `naive` 在 `isEmail` 上反而更稳，黑白盒的正确率都高于 `improved`。不过 `improved whitebox` 仍然明显提升了覆盖率和黄金类别命中，说明它更偏向探索与扩展。 |
| `isFQDN` | `improved` 在 `isFQDN` 上表现出较强的黄金类别覆盖能力，黑盒与白盒都达到了 `6/6` 的黄金类别命中；其中白盒覆盖率也进一步高于 `naive`。 |
| `isURL` | 相比上一轮，`improved blackbox` 不再塌缩成单组，生成规模、覆盖率和黄金类别命中都恢复到了更合理的区间。`improved whitebox` 仍然覆盖率最高，但正确率没有显著优于黑盒。 |
| 总体 | 本轮分批运行后结果整体稳定。结合覆盖率与最新黄金类别指标看，`improved` 依然更擅长扩大探索范围；而 `naive` 在部分函数上会表现出更高的保守正确率。 |

## 结果来源

本文件中的数据来自以下目录下的 `run_summary.json` 与 `coverage/coverage-summary.json`：

- `agent_toolkit/outputs/naive/isEmail/blackbox/`
- `agent_toolkit/outputs/naive/isEmail/whitebox/`
- `agent_toolkit/outputs/improved/isEmail/blackbox/`
- `agent_toolkit/outputs/improved/isEmail/whitebox/`
- `agent_toolkit/outputs/naive/isFQDN/blackbox/`
- `agent_toolkit/outputs/naive/isFQDN/whitebox/`
- `agent_toolkit/outputs/improved/isFQDN/blackbox/`
- `agent_toolkit/outputs/improved/isFQDN/whitebox/`
- `agent_toolkit/outputs/naive/isURL/blackbox/`
- `agent_toolkit/outputs/naive/isURL/whitebox/`
- `agent_toolkit/outputs/improved/isURL/blackbox/`
- `agent_toolkit/outputs/improved/isURL/whitebox/`
