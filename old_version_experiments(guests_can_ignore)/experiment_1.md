# Experiment 1

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

## isEmail

| Agent | Mode | Obligations | Total Generated Groups | Total Cases | Correct | Incorrect | Exact Match Rate | Total Golden Groups | Overlap Golden Groups | Missing Golden Groups | Novel Valid Groups |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 15 | 9 | 20 | 19 | 1 | 0.9500 | 12 | 7 | 5 | 2 |
| naive | whitebox | 8 | 8 | 60 | 57 | 3 | 0.9500 | 13 | 6 | 7 | 1 |
| improved | blackbox | 7 | 7 | 41 | 31 | 10 | 0.7561 | 9 | 3 | 6 | 2 |
| improved | whitebox | 13 | 21 | 71 | 61 | 10 | 0.8592 | 11 | 5 | 6 | 4 |

## isFQDN

| Agent | Mode | Obligations | Total Generated Groups | Total Cases | Correct | Incorrect | Exact Match Rate | Total Golden Groups | Overlap Golden Groups | Missing Golden Groups | Novel Valid Groups |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 6 | 7 | 72 | 71 | 1 | 0.9861 | 5 | 4 | 1 | 1 |
| naive | whitebox | 4 | 6 | 48 | 47 | 1 | 0.9792 | 4 | 2 | 2 | 2 |
| improved | blackbox | 5 | 7 | 72 | 70 | 2 | 0.9722 | 5 | 4 | 1 | 1 |
| improved | whitebox | 15 | 14 | 62 | 58 | 4 | 0.9355 | 5 | 4 | 1 | 2 |

## isURL

| Agent | Mode | Obligations | Total Generated Groups | Total Cases | Correct | Incorrect | Exact Match Rate | Total Golden Groups | Overlap Golden Groups | Missing Golden Groups | Novel Valid Groups |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 12 | 4 | 19 | 18 | 1 | 0.9474 | 24 | 2 | 22 | 1 |
| naive | whitebox | 4 | 4 | 22 | 21 | 1 | 0.9545 | 5 | 1 | 4 | 2 |
| improved | blackbox | 13 | 12 | 36 | 32 | 4 | 0.8889 | 21 | 5 | 16 | 0 |
| improved | whitebox | 3 | 12 | 80 | 76 | 4 | 0.9500 | 8 | 5 | 3 | 2 |

## 简短观察


| 现象        | 观察                                                                                                                         |
| --------- | -------------------------------------------------------------------------------------------------------------------------- |
| `isEmail` | 当前结果里，`naive` 在黑盒和白盒上都比 `improved` 更稳；`improved` 更激进，生成了更多 case 和更多 novel valid groups，但错误数明显更高。                           |
| `isFQDN`  | `naive` 与 `improved` 都表现较好，但 `naive` 的正确率略高；`improved whitebox` 生成更多 obligations 和 generated groups，不过并没有换来更好的最终精确率。       |
| `isURL`   | `whitebox` 明显优于 `blackbox`，尤其对 `improved` 更明显；`improved whitebox` 在保持高正确率的同时，missing golden groups 也显著少于 `naive blackbox`。 |
| 总体        | 当前版本下，`improved` 并不是在所有函数和模式上都优于 `naive`。它的优势更体现在更强发散与更多 novel valid groups，而劣势通常体现在更高的错误风险。                               |


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

