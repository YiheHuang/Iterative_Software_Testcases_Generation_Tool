# Experiment 5

本轮实验围绕 `isEmail` 单函数展开，目标是比较两种 agent 在三种输入模式下的表现：

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

## isEmail

| Agent | Mode | Obligations | Generated Groups | Generated Categories | Total Cases | Correct | Incorrect | Exact Match Rate | Lines % | Statements % | Functions % | Branches % | Total Golden Categories | Overlap Golden Categories | Missing Golden Categories | Matched Generated Categories | Novel Generated Categories | Strong Matches | Partial Matches | Fragmented Matches | Matched Golden Ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| naive | blackbox | 0 | 6 | 5 | 39 | 38 | 1 | 0.9744 | 71.25 | 70.24 | 100.00 | 60.53 | 11 | 5 | 6 | 4 | 1 | 3 | 2 | 0 | 0.4545 |
| naive | whitebox | 0 | 7 | 6 | 57 | 55 | 2 | 0.9649 | 73.75 | 73.81 | 100.00 | 67.11 | 11 | 7 | 4 | 6 | 0 | 6 | 1 | 0 | 0.6364 |
| naive | whitebox_code_only | 0 | 9 | 7 | 50 | 46 | 4 | 0.9200 | 85.00 | 85.71 | 100.00 | 78.95 | 11 | 9 | 2 | 7 | 0 | 6 | 3 | 0 | 0.8182 |
| improved | blackbox | 12 | 11 | 4 | 48 | 47 | 1 | 0.9792 | 75.00 | 75.00 | 100.00 | 72.37 | 11 | 11 | 0 | 4 | 0 | 8 | 3 | 0 | 1.0000 |
| improved | whitebox | 10 | 16 | 6 | 53 | 48 | 5 | 0.9057 | 95.00 | 95.24 | 100.00 | 92.11 | 11 | 10 | 1 | 6 | 0 | 7 | 3 | 0 | 0.9091 |
| improved | whitebox_code_only | 9 | 12 | 7 | 36 | 13 | 23 | 0.3611 | 66.25 | 64.29 | 100.00 | 55.26 | 11 | 9 | 2 | 7 | 0 | 3 | 6 | 0 | 0.8182 |

## 简短观察

| 现象 | 观察 |
|---|---|
| `naive` 三种模式 | `naive` 在三种模式下都保持了相对稳定的正确率，其中 `whitebox_code_only` 的正确率略低于另外两种模式，但覆盖率与黄金类别命中反而最高，说明仅代码模式会更激进地追源码路径。 |
| `improved blackbox` | 本轮最稳的一组实际上是 `improved blackbox`。它在只看 requirement 的前提下达到了 `11/11` 的黄金类别命中，同时保持了最高的正确率，说明当前黑盒 prompt 对 `isEmail` 的 requirement 展开已经比较充分。 |
| `improved whitebox` | 修复细粒度覆盖反馈读取后，`improved whitebox` 明显恢复正常，覆盖率提升到本轮最高（`Lines 95.00 / Statements 95.24 / Branches 92.11`），黄金类别命中也达到 `10/11`。虽然正确率仍略低于若干更保守的配置，但已经体现出“覆盖率驱动白盒迭代”应有的效果。 |
| `improved whitebox_code_only` | `improved whitebox_code_only` 仍然是异常组。它的黄金类别命中并不低（`9/11`），但正确率只有 `0.3611`。结合失败样例看，问题不只是“没有 requirement 所以更难”，而是模型在 code-only 模式下经常生成不自然的可执行字面量，例如把整个邮箱额外包一层引号、把字符串 `"12345"` 当成应抛出 `TypeError` 的非字符串输入，从而系统性拉低正确率。 |
| 总体 | 这轮更新后的结果更符合预期：修复覆盖反馈后，`improved whitebox` 已经重新成为项目重点路线中最强的一组；但 `code-only whitebox` 仍显示出一个明显风险，即仅靠源码推断外部行为时，模型很容易写出“结构上像测试、运行上却不对”的样例，因此覆盖和黄金语义命中并不能保证正确率。 |

## 结果来源

本文件中的数据来自以下目录下的 `run_summary.json` 与 `coverage/coverage-summary.json`：

- `agent_toolkit/outputs/naive/isEmail/blackbox/`
- `agent_toolkit/outputs/naive/isEmail/whitebox/`
- `agent_toolkit/outputs/naive/isEmail/whitebox_code_only/`
- `agent_toolkit/outputs/improved/isEmail/blackbox/`
- `agent_toolkit/outputs/improved/isEmail/whitebox/`
- `agent_toolkit/outputs/improved/isEmail/whitebox_code_only/`
