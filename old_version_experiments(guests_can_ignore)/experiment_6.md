# Experiment 6

本轮实验继续围绕 `isEmail` 单函数展开，比较两种 agent 在三种输入模式下的表现：

- `blackbox`：仅基于 `validator_js/README.md` 中的 requirement 生成测试
- `whitebox`：同时基于 requirement 与 source code 生成测试
- `whitebox_code_only`：仅基于 source code 生成测试，不提供 requirement
- `naive`：单轮生成 + JSON repair/completion
- `improved`：黑盒单轮生成；白盒与纯代码白盒基于执行结果与覆盖率做小规模 patch

说明：

- 本实验只覆盖 `isEmail`
- 共运行 `2 x 3 = 6` 组实验
- 所有实验均开启黄金测试重合度分析
- 黄金测试字段继续采用最新的 category-level 双向匹配口径
- 继续记录四类覆盖率字段：`Lines / Statements / Functions / Branches`
- 本轮已移除 `error` 分类，仅保留 `valid / invalid`

## isEmail

| Agent | Mode | Obligations | Generated Groups | Generated Categories | Total Cases | Correct | Incorrect | Exact Match Rate | Lines % | Statements % | Functions % | Branches % | Total Golden Categories | Overlap Golden Categories | Missing Golden Categories | Matched Generated Categories | Novel Generated Categories | Strong Matches | Partial Matches | Fragmented Matches | Matched Golden Ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 0 | 8 | 7 | 41 | 40 | 1 | 0.9756 | 73.75 | 73.81 | 100.00 | 67.11 | 11 | 7 | 4 | 6 | 1 | 4 | 3 | 0 | 0.6364 |
| naive | whitebox | 0 | 9 | 8 | 47 | 47 | 0 | 1.0000 | 75.00 | 75.00 | 100.00 | 69.74 | 11 | 8 | 3 | 7 | 1 | 6 | 2 | 0 | 0.7273 |
| naive | whitebox_code_only | 0 | 7 | 7 | 39 | 34 | 5 | 0.8718 | 80.00 | 80.95 | 100.00 | 69.74 | 11 | 7 | 4 | 7 | 0 | 5 | 2 | 0 | 0.6364 |
| improved | blackbox | 12 | 12 | 6 | 46 | 40 | 6 | 0.8696 | 80.00 | 79.76 | 100.00 | 75.00 | 11 | 10 | 1 | 6 | 0 | 2 | 8 | 0 | 0.9091 |
| improved | whitebox | 11 | 22 | 7 | 67 | 56 | 11 | 0.8358 | 95.00 | 95.24 | 100.00 | 92.11 | 11 | 10 | 1 | 7 | 0 | 7 | 3 | 0 | 0.9091 |
| improved | whitebox_code_only | 10 | 15 | 5 | 29 | 15 | 14 | 0.5172 | 67.50 | 65.48 | 100.00 | 57.89 | 11 | 10 | 1 | 5 | 0 | 5 | 5 | 0 | 0.9091 |

## 简短观察

| 现象 | 观察 |
|---|---|
| `naive` 三种模式 | `naive` 在本轮依旧比较稳定，其中 `naive whitebox` 达到了 `47/47` 的完全正确率，说明在 `isEmail` 上，保守的一轮式生成仍然很适合作为强基线。 |
| `improved whitebox` | `improved whitebox` 在覆盖率上仍然显著领先，达到了本轮最高的 `Lines 95.00 / Statements 95.24 / Branches 92.11`，黄金类别命中也达到 `10/11`。这说明覆盖率驱动的白盒迭代确实能持续扩展路径探索。 |
| `improved` 的正确率问题 | 虽然 `improved whitebox` 和 `improved blackbox` 的黄金类别命中都很高，但两者正确率都明显低于对应的 `naive`。这说明当前 `improved` 路线更擅长扩张测试范围，却更容易引入 requirement 不完全支持的预期。 |
| `improved whitebox_code_only` | `code-only` 仍然是最不稳定的一组。它在没有 requirement 约束时仍能达到 `10/11` 的黄金类别命中，但正确率只有 `0.5172`，说明仅靠源码推断外部行为仍然容易写出“结构上合理、语义上不稳”的测试。 |
| 总体 | 本轮结果再次强化了一个核心现象：覆盖率和黄金类别命中可以明显提升，但如果 requirement 约束在多轮白盒迭代里被弱化，正确率就会持续下滑。因此后续更值得做的不是进一步放大覆盖反馈，而是增强 requirement 对 patch 的约束力。 |

## 结果来源

本文件中的数据来自以下目录下的 `run_summary.json` 与 `coverage/coverage-summary.json`：

- `agent_toolkit/outputs/naive/isEmail/blackbox/`
- `agent_toolkit/outputs/naive/isEmail/whitebox/`
- `agent_toolkit/outputs/naive/isEmail/whitebox_code_only/`
- `agent_toolkit/outputs/improved/isEmail/blackbox/`
- `agent_toolkit/outputs/improved/isEmail/whitebox/`
- `agent_toolkit/outputs/improved/isEmail/whitebox_code_only/`
