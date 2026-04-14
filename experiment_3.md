# Experiment 3

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
- `improved isFQDN blackbox` 首次运行时因生成阶段返回坏 JSON 失败，随后重跑成功；表中记录的是成功重跑后的结果

## isEmail

| Agent | Mode | Obligations | Generated Groups | Generated Categories | Total Cases | Correct | Incorrect | Exact Match Rate | Lines % | Statements % | Functions % | Branches % | Total Golden Categories | Overlap Golden Categories | Missing Golden Categories | Matched Generated Categories | Novel Generated Categories | Strong Matches | Partial Matches | Fragmented Matches | Matched Golden Ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 0 | 8 | 7 | 86 | 80 | 6 | 0.9302 | 73.75 | 72.62 | 100.00 | 65.79 | 12 | 7 | 5 | 6 | 1 | 4 | 3 | 0 | 0.5833 |
| naive | whitebox | 0 | 8 | 6 | 43 | 39 | 4 | 0.9070 | 73.75 | 73.81 | 100.00 | 68.42 | 12 | 8 | 4 | 6 | 0 | 4 | 4 | 0 | 0.6667 |
| improved | blackbox | 11 | 9 | 7 | 39 | 39 | 0 | 1.0000 | 75.00 | 75.00 | 100.00 | 69.74 | 12 | 8 | 4 | 6 | 1 | 4 | 4 | 0 | 0.6667 |
| improved | whitebox | 10 | 19 | 7 | 70 | 65 | 5 | 0.9286 | 95.00 | 95.24 | 100.00 | 89.47 | 12 | 11 | 1 | 7 | 0 | 5 | 6 | 0 | 0.9167 |

## isFQDN

| Agent | Mode | Obligations | Generated Groups | Generated Categories | Total Cases | Correct | Incorrect | Exact Match Rate | Lines % | Statements % | Functions % | Branches % | Total Golden Categories | Overlap Golden Categories | Missing Golden Categories | Matched Generated Categories | Novel Generated Categories | Strong Matches | Partial Matches | Fragmented Matches | Matched Golden Ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 0 | 7 | 7 | 74 | 72 | 2 | 0.9730 | 84.85 | 85.29 | 100.00 | 84.21 | 6 | 5 | 1 | 5 | 2 | 4 | 1 | 0 | 0.8333 |
| naive | whitebox | 0 | 7 | 4 | 68 | 64 | 4 | 0.9412 | 87.88 | 88.24 | 100.00 | 86.84 | 6 | 6 | 0 | 3 | 1 | 1 | 5 | 0 | 1.0000 |
| improved | blackbox | 8 | 7 | 7 | 37 | 36 | 1 | 0.9730 | 87.88 | 88.24 | 100.00 | 86.84 | 6 | 5 | 1 | 5 | 2 | 5 | 0 | 0 | 0.8333 |
| improved | whitebox | 10 | 10 | 6 | 40 | 37 | 3 | 0.9250 | 93.94 | 94.12 | 100.00 | 92.11 | 6 | 4 | 2 | 4 | 2 | 3 | 1 | 0 | 0.6667 |

## isURL

| Agent | Mode | Obligations | Generated Groups | Generated Categories | Total Cases | Correct | Incorrect | Exact Match Rate | Lines % | Statements % | Functions % | Branches % | Total Golden Categories | Overlap Golden Categories | Missing Golden Categories | Matched Generated Categories | Novel Generated Categories | Strong Matches | Partial Matches | Fragmented Matches | Matched Golden Ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 0 | 11 | 5 | 51 | 48 | 3 | 0.9412 | 60.53 | 59.32 | 100.00 | 48.74 | 9 | 6 | 3 | 5 | 0 | 3 | 3 | 0 | 0.6667 |
| naive | whitebox | 0 | 6 | 6 | 33 | 30 | 3 | 0.9091 | 64.04 | 62.71 | 100.00 | 47.90 | 9 | 4 | 5 | 6 | 0 | 3 | 1 | 0 | 0.4444 |
| improved | blackbox | 16 | 1 | 1 | 16 | 13 | 3 | 0.8125 | 64.04 | 65.25 | 100.00 | 52.94 | 9 | 1 | 8 | 1 | 0 | 0 | 1 | 0 | 0.1111 |
| improved | whitebox | 9 | 14 | 7 | 72 | 67 | 5 | 0.9306 | 73.68 | 72.03 | 100.00 | 62.18 | 9 | 8 | 1 | 7 | 0 | 5 | 3 | 0 | 0.8889 |

## 简短观察

| 现象 | 观察 |
|---|---|
| `isEmail` | `improved whitebox` 在本轮最强，覆盖率四项都明显拉高，黄金分类命中也达到 `11/12`。`improved blackbox` 的正确率最稳，但覆盖率仍明显低于白盒。 |
| `isFQDN` | `naive whitebox` 在黄金分类上实现了 `6/6` 全命中，但 `improved whitebox` 的代码覆盖率更高，说明它更偏向“覆盖驱动”而不是“黄金对齐驱动”。黑盒下两者黄金命中相同。 |
| `isURL` | `isURL` 仍然最难。`improved blackbox` 本轮明显退化，只保留了 `1` 个 generated category，导致黄金命中和正确率都偏低；相对地，`improved whitebox` 把覆盖率和黄金分类命中都显著拉了上来。 |
| 总体 | 最新黄金字段已经完全切到 category-level：现在更关注“命中了多少黄金类别”，而不是旧口径下不稳定的 group 粒度数字。结合覆盖率一起看，会更容易区分“语义对齐能力”和“代码路径探索能力”。 |

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
