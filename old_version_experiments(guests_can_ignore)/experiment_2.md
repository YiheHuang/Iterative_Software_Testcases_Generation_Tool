# Experiment 2

本轮实验基于当前项目的最新定义重新运行：

- `blackbox`：仅基于 `validator_js/README.md` 中的 requirement 生成测试
- `whitebox`：同时基于 requirement 与 source code 生成测试
- `naive`：单轮生成 + JSON repair/completion
- `improved`：更强 prompt；黑盒不迭代，白盒基于覆盖率做小规模 patch

说明：

- 本实验覆盖 `isEmail`、`isFQDN`、`isURL`
- 每个函数都运行 `naive/improved` 两种 agent 的黑盒与白盒测试
- 所有实验均开启黄金测试重合度分析
- `exact_match_rate` 来自真实执行结果
- 黄金测试相关指标来自 `golden_comparison.json`
- 本轮黄金分析采用新的稳定口径：固定 `golden groups`，并由程序计算 `overlap/missing/total`

## isEmail

| Agent | Mode | Obligations | Total Generated Groups | Total Cases | Correct | Incorrect | Exact Match Rate | Total Golden Groups | Overlap Golden Groups | Missing Golden Groups | Novel Valid Groups |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 14 | 9 | 32 | 29 | 3 | 0.9063 | 15 | 7 | 8 | 2 |
| naive | whitebox | 4 | 5 | 44 | 42 | 2 | 0.9545 | 15 | 4 | 11 | 1 |
| improved | blackbox | 10 | 9 | 43 | 43 | 0 | 1.0000 | 15 | 8 | 7 | 1 |
| improved | whitebox | 10 | 16 | 57 | 53 | 4 | 0.9298 | 15 | 7 | 8 | 6 |

## isFQDN

| Agent | Mode | Obligations | Total Generated Groups | Total Cases | Correct | Incorrect | Exact Match Rate | Total Golden Groups | Overlap Golden Groups | Missing Golden Groups | Novel Valid Groups |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 7 | 7 | 68 | 67 | 1 | 0.9853 | 6 | 3 | 3 | 4 |
| naive | whitebox | 5 | 6 | 68 | 65 | 3 | 0.9559 | 6 | 4 | 2 | 2 |
| improved | blackbox | 7 | 7 | 61 | 60 | 1 | 0.9836 | 6 | 5 | 1 | 2 |
| improved | whitebox | 14 | 7 | 38 | 34 | 4 | 0.8947 | 6 | 4 | 2 | 3 |

## isURL

| Agent | Mode | Obligations | Total Generated Groups | Total Cases | Correct | Incorrect | Exact Match Rate | Total Golden Groups | Overlap Golden Groups | Missing Golden Groups | Novel Valid Groups |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 12 | 12 | 37 | 32 | 5 | 0.8649 | 31 | 12 | 19 | 3 |
| naive | whitebox | 3 | 5 | 38 | 35 | 3 | 0.9211 | 31 | 5 | 26 | 2 |
| improved | blackbox | 11 | 10 | 34 | 28 | 6 | 0.8235 | 31 | 10 | 21 | 1 |
| improved | whitebox | 10 | 19 | 70 | 65 | 5 | 0.9286 | 31 | 8 | 23 | 9 |

## 简短观察

| 现象 | 观察 |
|---|---|
| `isEmail` | 本轮 `improved blackbox` 表现非常好，达到了 `1.0000` 的精确匹配率，并且比 `naive blackbox` 多覆盖了 1 个固定 golden group。白盒上 `naive` 更稳，但 `improved whitebox` 带来了更多 generated match groups 和更多 novel categories。 |
| `isFQDN` | `improved blackbox` 在固定 golden group 覆盖上明显优于 `naive blackbox`。白盒上 `naive` 的正确率更高，而 `improved whitebox` 更偏探索型，novel categories 更多。 |
| `isURL` | `isURL` 的 fixed golden groups 总数较大，黑盒和白盒都只覆盖其中一部分。`improved whitebox` 生成规模最大，novel categories 也最多，但正确率并没有显著领先于 `naive whitebox`。 |
| 总体 | 在新的 prompt 口径下，`improved` 仍然更有探索性，但已经不再被固定数量目标直接驱动。黄金指标现在也更稳定，因为 `overlap + missing = total golden groups` 由程序保证。 |

## 结果来源

本文件中的数据来自以下目录下的 `run_summary.json`：

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
