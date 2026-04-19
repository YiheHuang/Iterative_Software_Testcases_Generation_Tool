# Experiment Final 1

本轮实验在上一轮基础上**删除了 `isUUID`**，只保留 `5` 个 validator：

- `isEmail`
- `isURL`
- `isFQDN`
- `isCurrency`
- `isCreditCard`

因此总实验数为 `5 x 3 x 2 = 30`。  
此外，本轮 `improved whitebox` / `improved whitebox_code_only` 已经恢复为你要求的 **suite + patch 加法式迭代**：

- 每轮输入：当前完整 suite、`requirement`（仅 `whitebox`）、`coverage detail`、`uncovered_details`
- 每轮输出：patch groups
- 下一轮 suite：`current suite + patch`

这使得本轮实验可以回答一个很关键的问题：

**把白盒迭代从“整套重写”改回“完整 suite 输入 + patch 增量输出”之后，整体效果有没有变好？**

## 统计口径说明

当前根目录下的 `experiment_10_batch_summary.json` 仍然是上一轮 `6` 函数版本，所以本报告**不直接使用那个旧 batch summary 作为统计源**。  
本报告直接基于当前最新的：

- `run_experiment_10.py` 默认 `5` 函数列表
- `agent_toolkit/outputs/*/*/*/run_summary.json`
- 各 run 的 `coverage/coverage-summary.json`

重新汇总得到本轮结果。

## 总体结果

- 统计实验数：`30`
- `30` 条实验全部成功
- 总 LLM 请求数：`140`
- 总 token 消耗：`915,473`
- 平均正确率 `exact_match_rate`：`0.8599`
- 平均黄金命中率 `matched_golden_ratio`：`0.7915`
- 平均语句覆盖率：`86.52`
- 平均分支覆盖率：`80.21`
- 平均函数覆盖率：`100.00`
- 平均行覆盖率：`86.55`
- `exact_match_rate >= 0.9` 的实验共有 `13` 条
- `matched_golden_ratio >= 0.9` 的实验共有 `14` 条
- 两项都 `>= 0.9` 的实验共有 `3` 条

相比上一轮 `experiment10` 在相同 `5` 函数口径下的基线，本轮总体表现是**明显改善**的：

- 总 token：`1,069,843 -> 915,473`
- 平均正确率：`0.8497 -> 0.8599`
- 平均黄金命中率：`0.7553 -> 0.7915`
- 平均语句覆盖率：`85.08 -> 86.52`
- 平均分支覆盖率：`76.75 -> 80.21`
- 平均行覆盖率：`84.96 -> 86.55`

也就是说，在删掉 `isUUID` 且恢复 suite+patch 之后，这轮不是单点改善，而是**成本下降，同时 correctness / golden / coverage 都一起改善**。

## 汇总表

下面按 `mode + approach` 汇总平均 token 消耗、正确率、四种覆盖率和黄金命中率：

| Agent | Mode | Avg Tokens | Avg Exact Match | Avg Stmt Cov | Avg Branch Cov | Avg Func Cov | Avg Line Cov | Avg Golden Match |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `naive` | `blackbox` | 11259.80 | 0.8826 | 81.78 | 74.89 | 100.00 | 81.72 | 0.5942 |
| `naive` | `whitebox` | 19494.40 | 0.9167 | 84.27 | 78.74 | 100.00 | 84.33 | 0.7714 |
| `naive` | `whitebox_code_only` | 18603.80 | 0.8855 | 83.71 | 75.11 | 100.00 | 84.49 | 0.5002 |
| `improved` | `blackbox` | 21537.20 | 0.8823 | 83.98 | 78.53 | 100.00 | 84.09 | 0.9667 |
| `improved` | `whitebox` | 58264.80 | 0.8132 | 95.19 | 92.31 | 100.00 | 95.02 | 0.9857 |
| `improved` | `whitebox_code_only` | 53934.60 | 0.7793 | 90.19 | 81.70 | 100.00 | 89.66 | 0.9312 |

这个表里最重要的信号有三条：

1. `naive whitebox` 仍然是 correctness 最稳的路线，平均正确率达到 `0.9167`。
2. `improved whitebox` 依然保持最强的覆盖率与黄金命中率，但正确率 `0.8132` 仍明显低于 `naive whitebox`。
3. `improved blackbox` 非常值得注意，它的正确率 `0.8823` 几乎与 `naive blackbox` 持平，但黄金命中率高达 `0.9667`，说明这一条路线已经相当平衡。

## 与上一轮同口径对比

为了公平比较本轮修改效果，这里采用和 `experiment10` 同样的 `5` 函数口径：  
即把旧版 `experiment10` 的 `6` 函数矩阵中剔除 `isUUID`，再和本轮比较。

### 1. `improved whitebox` 是本轮最大的正向变化

`improved whitebox` 从旧基线到本轮的变化如下：

- 平均 token：`73750.40 -> 58264.80`
- 平均正确率：`0.7963 -> 0.8132`
- 平均黄金命中率：`0.8746 -> 0.9857`
- 平均语句覆盖率：`93.27 -> 95.19`
- 平均分支覆盖率：`85.61 -> 92.31`
- 平均行覆盖率：`92.88 -> 95.02`

这组结果非常关键，因为它说明：

**恢复 suite+patch 之后，`improved whitebox` 在当前 5 函数集合上不是“只提覆盖不提 correctness”，而是出现了更理想的同步改善：更低成本、更高 correctness、更高 golden、更高 coverage。**

这和上一轮“整套重写式迭代”的结论明显不同，说明你之前对迭代形式的判断是对的。

### 2. `improved whitebox_code_only` 也有改善，但仍然风险更高

`improved whitebox_code_only` 相比旧基线：

- 平均 token：`68101.00 -> 53934.60`
- 平均正确率：`0.7180 -> 0.7793`
- 平均语句覆盖率：`80.98 -> 90.19`
- 平均分支覆盖率：`69.66 -> 81.70`
- 平均行覆盖率：`81.20 -> 89.66`
- 平均黄金命中率：`0.9732 -> 0.9312`

这说明 code-only 模式也因为 patch-merge 受益了，尤其是 correctness 和 coverage 都有明显提升。  
但它依然不是最稳路线，因为平均正确率仍然只有 `0.7793`，且 token 成本依旧很高。

### 3. `naive whitebox` 仍然是 correctness 基线王者

即便 `improved whitebox` 本轮明显回暖，`naive whitebox` 依然以 `0.9167` 的平均正确率领先。  
所以更准确的结论不是“improved 已经全面反超”，而是：

- `naive whitebox`：更稳、更便宜、更偏 correctness
- `improved whitebox`：更强覆盖、更高 golden、更贵，但 correctness 仍未追平

## 完整结果矩阵

| Validator | Agent | Mode | Status | Correct/Total | Exact Match Rate | Stmt Cov | Branch Cov | Func Cov | Line Cov | Matched Golden Ratio | Total Tokens | Note |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| isEmail | naive | blackbox | success | 44/46 | 0.9565 | 73.81 | 68.42 | 100.00 | 73.75 | 0.5000 | 12093 | ok |
| isEmail | naive | whitebox | success | 41/42 | 0.9762 | 73.81 | 68.42 | 100.00 | 73.75 | 0.6429 | 13194 | ok |
| isEmail | naive | whitebox_code_only | success | 43/47 | 0.9149 | 66.67 | 52.63 | 100.00 | 67.50 | 0.6429 | 13120 | ok |
| isEmail | improved | blackbox | success | 40/43 | 0.9302 | 79.76 | 75.00 | 100.00 | 80.00 | 1.0000 | 14843 | ok |
| isEmail | improved | whitebox | success | 47/57 | 0.8246 | 94.05 | 90.79 | 100.00 | 93.75 | 0.9286 | 98631 | ok |
| isEmail | improved | whitebox_code_only | success | 36/47 | 0.7660 | 97.62 | 92.11 | 100.00 | 97.50 | 0.9286 | 50120 | ok |
| isURL | naive | blackbox | success | 44/50 | 0.8800 | 64.41 | 52.10 | 100.00 | 65.79 | 0.8182 | 14416 | ok |
| isURL | naive | whitebox | success | 52/64 | 0.8125 | 66.10 | 60.50 | 100.00 | 67.54 | 0.8182 | 18662 | ok |
| isURL | naive | whitebox_code_only | success | 35/41 | 0.8537 | 72.88 | 63.87 | 100.00 | 74.56 | 0.5455 | 15721 | ok |
| isURL | improved | blackbox | success | 34/41 | 0.8293 | 64.41 | 54.62 | 100.00 | 65.79 | 1.0000 | 55039 | ok |
| isURL | improved | whitebox | success | 54/64 | 0.8438 | 96.61 | 86.55 | 100.00 | 96.49 | 1.0000 | 76002 | ok |
| isURL | improved | whitebox_code_only | success | 36/39 | 0.9231 | 78.81 | 66.39 | 100.00 | 78.07 | 0.7273 | 146922 | ok |
| isFQDN | naive | blackbox | success | 43/48 | 0.8958 | 85.29 | 84.21 | 100.00 | 84.85 | 0.8333 | 7897 | ok |
| isFQDN | naive | whitebox | success | 59/60 | 0.9833 | 91.18 | 89.47 | 100.00 | 90.91 | 0.8333 | 40602 | ok |
| isFQDN | naive | whitebox_code_only | success | 13/13 | 1.0000 | 91.18 | 92.11 | 100.00 | 90.91 | 0.1667 | 36714 | ok |
| isFQDN | improved | blackbox | success | 28/30 | 0.9333 | 82.35 | 81.58 | 100.00 | 81.82 | 0.8333 | 8538 | ok |
| isFQDN | improved | whitebox | success | 27/35 | 0.7714 | 85.29 | 84.21 | 100.00 | 84.85 | 1.0000 | 65143 | ok |
| isFQDN | improved | whitebox_code_only | success | 22/26 | 0.8462 | 91.18 | 92.11 | 100.00 | 90.91 | 1.0000 | 26464 | ok |
| isCurrency | naive | blackbox | success | 48/52 | 0.9231 | 85.37 | 75.00 | 100.00 | 84.21 | 0.3750 | 13756 | ok |
| isCurrency | naive | whitebox | success | 74/82 | 0.9024 | 90.24 | 80.56 | 100.00 | 89.47 | 0.5625 | 16352 | ok |
| isCurrency | naive | whitebox_code_only | success | 72/96 | 0.7500 | 87.80 | 72.22 | 100.00 | 89.47 | 0.8125 | 20465 | ok |
| isCurrency | improved | blackbox | success | 52/62 | 0.8387 | 97.56 | 97.22 | 100.00 | 97.37 | 1.0000 | 20067 | ok |
| isCurrency | improved | whitebox | success | 45/67 | 0.6716 | 100.00 | 100.00 | 100.00 | 100.00 | 1.0000 | 39595 | ok |
| isCurrency | improved | whitebox_code_only | success | 35/49 | 0.7143 | 100.00 | 100.00 | 100.00 | 100.00 | 1.0000 | 23228 | ok |
| isCreditCard | naive | blackbox | success | 25/33 | 0.7576 | 100.00 | 94.74 | 100.00 | 100.00 | 0.4444 | 8137 | ok |
| isCreditCard | naive | whitebox | success | 20/22 | 0.9091 | 100.00 | 94.74 | 100.00 | 100.00 | 1.0000 | 8662 | ok |
| isCreditCard | naive | whitebox_code_only | success | 10/11 | 0.9091 | 100.00 | 94.74 | 100.00 | 100.00 | 0.3333 | 6999 | ok |
| isCreditCard | improved | blackbox | success | 22/25 | 0.8800 | 95.83 | 84.21 | 100.00 | 95.45 | 1.0000 | 9199 | ok |
| isCreditCard | improved | whitebox | success | 21/22 | 0.9545 | 100.00 | 100.00 | 100.00 | 100.00 | 1.0000 | 11953 | ok |
| isCreditCard | improved | whitebox_code_only | success | 11/17 | 0.6471 | 83.33 | 57.89 | 100.00 | 81.82 | 1.0000 | 22939 | ok |

## 结果解读

本轮结果最值得强调的，不是某个单点最好看，而是**suite+patch 形式确实把 `improved whitebox` 从“方向有点跑偏”拉回来了**。

### 1. `improved whitebox` 明显回暖，但还没赢下 correctness

这是本轮最关键的主结论。

一方面，`improved whitebox` 的覆盖率和黄金命中依旧非常强：

- 平均 `Stmt Cov = 95.19`
- 平均 `Branch Cov = 92.31`
- 平均 `Line Cov = 95.02`
- 平均 `Golden Match = 0.9857`

另一方面，它的 correctness 仍然只有 `0.8132`，还没有追平 `naive whitebox` 的 `0.9167`。

所以更准确的结论是：

**suite+patch 修复了“整套重写”带来的明显副作用，但 `improved whitebox` 仍然更像一条 coverage / semantic overlap 更强的路线，而不是 correctness 最稳的路线。**

### 2. `improved blackbox` 其实已经很有竞争力

本轮有一个很容易被忽略的现象：`improved blackbox` 非常平衡。

- 平均正确率 `0.8823`
- 平均黄金命中率 `0.9667`
- 平均 token `21537.20`

它没有 `improved whitebox` 那么极端昂贵，也没有 `whitebox_code_only` 那么不稳，反而是一条相对均衡的路线。  
如果后续希望优先追求“综合质量/成本比”，`improved blackbox` 值得持续关注。

### 3. `isCurrency` 继续说明 coverage / golden / correctness 并不等价

本轮最典型的反例仍然是 `isCurrency`：

- `improved whitebox`：`Stmt/Branch/Func/Line` 全 `100`
- `matched_golden_ratio = 1.0000`
- 但 `exact_match_rate = 0.6716`

这说明：

- case 类别和黄金测试的语义类别可以高度对齐
- 代码路径也可以基本打满
- 但最终具体断言、参数组合、边界细节仍可能出错

所以这组实验再次验证：  
**coverage 高、golden overlap 高，并不自动意味着 executable correctness 高。**

### 4. `whitebox_code_only` 仍然不是最稳妥的主线

虽然本轮 `improved whitebox_code_only` 已比上一轮明显改善，但它整体上仍有两个问题：

- 平均正确率仍然偏低：`0.7793`
- token 成本仍然偏高：`53934.60`

而且异常点也依然明显：

- `isCreditCard / improved / whitebox_code_only`：`0.6471`
- `isCurrency / improved / whitebox_code_only`：`0.7143`
- `isURL / improved / whitebox_code_only`：虽然 `0.9231`，但 token 高达 `146922`

所以从当前结果看，code-only 模式更像一个“可用但高风险”的补充模式，而不是主力模式。

## 本轮最重要的结论

1. 在剔除 `isUUID` 后，这一轮 `5` 函数实验整体表现比 `experiment10` 的同口径基线更好：成本更低，correctness / golden / coverage 全部提升。
2. `improved whitebox` 是本轮变化最大的受益者，说明你要求恢复的 **suite+patch 加法式迭代** 是有效的。
3. 但即便如此，`improved whitebox` 依然没有在 correctness 上追平 `naive whitebox`，所以它的优势仍主要体现在 coverage 与 golden overlap。
4. `improved blackbox` 的综合平衡性比之前更值得重视，它已经接近一条“性价比最好”的路线。
5. `isCurrency` 继续证明：覆盖率、黄金命中率、最终正确率是三个相关但不等价的指标，后续优化时不能只盯 coverage。

## 结果来源

本文件中的数据主要来自：

- `run_experiment_10.py`
- `agent_toolkit/outputs/*/*/*/run_summary.json`
- 各 run 的 `coverage/coverage-summary.json`
- `experiment10.md`（仅用于构造上一轮的同口径 5 函数比较基线）
