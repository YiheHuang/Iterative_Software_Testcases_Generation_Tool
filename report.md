# LLM-Driven Iterative Software Testcase Generation Tool

## 1. 相关工作与方法定位

### 1.1 相关工作对比

近年 LLM 在测试生成方向已有若干代表性工作：Codex/Copilot 类模型被用于直接合成单元测试；AthenaTest 聚焦 Java focal method 的单元测试生成；ChatUniTest / TestPilot 等利用对话式反馈进行测试修复；学术社区亦提出 coverage-guided prompt、property-based + LLM 混合等方向。

下表给出与代表性工作的对比，说明本项目的差异化定位：

| 方向 | 代表工作 | 侧重 | 本项目差异 |
|---|---|---|---|
| 单元测试生成 | AthenaTest | Java focal method，单轮 | 本项目做多轮 coverage-guided + golden 对齐，支持黑白盒三模态 |
| 对话式修复 | ChatUniTest / TestPilot | 失败驱动修复 | 本项目显式拒绝 golden oracle 泄漏，只用 coverage + uncovered_details 作反馈 |
| LLM + Property-based | 部分学术工作 | 让 LLM 提 property | 本项目不生成 property，而生成具体 test group；property-based 作为 non-AI baseline（§11） |
| Coverage-guided prompt | 若干研究 | 以覆盖率为反馈 | 本项目进一步做语义化覆盖缺口（branch_side / condition_excerpt）而非仅报数字 |

本项目在这一脉络中的定位是：以真实开源库（validator.js）为被测对象，同时评估 correctness、coverage 与 golden overlap 三重指标，并以 naive baseline 与多轮消融支撑方法改进的因果论证。与上述工作相比，本项目不追求单轮生成的极致，而更关注 Agent 在真实工程环境下的可执行性、多输入模态适应性，以及 LLM 已知缺陷（幻觉 / 语义漂移 / priority 错配）的显式回应。

## 2. 项目目标、技术类别与研究问题

### 2.1 技术类别

本项目在 static testing、black-box dynamic testing、white-box dynamic testing 三类中选择 Black-box Dynamic Testing + White-box Dynamic Testing 双路线，不做 static analysis。

validator.js 是一个提供真实可执行实现的开源库，天然适合作为动态测试的 SUT，动态执行可同时度量 correctness（断言是否符合真实行为）与 coverage（路径是否被触达），而静态分析只能度量一部分（如类型、死代码、API 误用），不能直接度量测试用例的"测出 bug 能力"；本项目关注"LLM 能否作为测试设计者"而非"LLM 能否作为静态代码分析器"，后者属于另一条独立研究路线。双路线方法论上同时涉及黑盒 specification-based（Equivalence Partitioning、Boundary Value Analysis、Option-combination、Decision-Table-like obligation 展开，见 §3.5.1）与白盒 structure-based（Statement / Branch / Function / Line 覆盖率度量以及基于 uncovered branch 的语义化路径反馈，见 §5.2.1）。

State transition testing 在 validator.js 上不适用（validator 函数为无状态纯函数），本项目不展开；扩展到 state machine 风格被测对象的路径见 §12.5 future work。

### 2.2 研究目标

本项目围绕一个 LLM 驱动的自动化测试生成工具展开，其中 `improved agent` 是本文的主要研究对象，`naive agent` 作为对照基线用于提供参考比较。`naive agent` 代表保守的一轮生成方案，用于回答一个基本问题：在不引入更强 prompt 设计与覆盖率驱动迭代的情况下，测试生成可以达到怎样的基线水平。

在此基础上，本项目真正关注的是：通过更强的 prompt 设计与白盒迭代机制，`improved agent` 能否在真实开源项目上生成更高质量的测试用例。

研究问题：

1. 在真实开源项目上，LLM 能否生成可执行、可用的测试用例？
2. 在 `blackbox`、`whitebox`、`whitebox_code_only` 三种输入模式下，测试质量如何变化？
3. 相较 baseline `naive agent`，`improved agent` 的 prompt 增强与 iteration 机制到底提升了什么？
4. 在 `improved whitebox` 中，哪些设计是有效改进，哪些设计是错误方向？

## 3. 系统设计、输入与输出

本节重点介绍本文的方法主体 `improved agent`。`naive agent` 仅作为对照基线，不作为系统设计重点展开。

### 3.1 总体流程

系统整体流程如下：

1. 读取目标函数的 requirement 和/或 source code。
2. 根据 mode 构造 prompt，请 LLM 生成结构化测试用例。
3. 将输出规范化为统一 JSON，包含 `obligations` 与 `test_groups`。
4. 在真实实现上执行测试，得到 correctness。
5. 收集代码覆盖率，得到 `Stmt / Branch / Func / Line` 四项指标。
6. 与人工黄金测试做语义类别对齐，得到 `matched_golden_ratio`。
7. 若为 `improved` 白盒模式，则继续利用 coverage feedback 做 patch 迭代。

### 3.2 输入

系统输入主要包括 `requirement` 与 `project code base`，项目支持三种 mode：`blackbox` 只提供 requirement、`whitebox` 同时提供 requirement 与 source code、`whitebox_code_only` 只提供 source code。对于 `improved` 白盒迭代，每轮额外输入当前完整 suite、`coverage_total`、`coverage_files` 与 `uncovered_details`。

### 3.3 输出

系统输出为严格 JSON 形式的 `test cases`，顶层键为 `obligations` 与 `test_groups`，每个 `test_group` 包含 `title`、`validator`、`args`、`valid`、`invalid`、`rationale`、`obligations` 共七个字段。

### 3.4 `naive agent`：对照基线

`naive agent` 的设计目标是提供一个保守的第一轮对照基线，只生成第一版"小而稳"的 suite，不主动追求 completeness、不做深入 branch hunting、更偏 common cases 与 obvious boundaries；白盒下也只把代码当作"发现 obvious branches / guards"的辅助信息。因此 `naive agent` 可以概括为保守、低风险、偏 correctness 的基线生成方案。

### 3.5 `improved agent`：本文方法主体

`improved agent` 的核心设计有两个重点：prompt 增强，以及白盒 iteration。

#### 3.5.1 `blackbox` 模式

在 `blackbox` 模式下，`improved agent` 不只是"从 requirement 写几个 case"，而是显式要求模型做 equivalence partitioning、boundary value analysis、option-combination testing，先提 obligations 再做 category clustering 再展开 test groups，最后做 self-audit 检查 rare options、边界和 option flip 是否遗漏。相比之下 `naive blackbox` 只做保守的一轮基线生成，因此 `improved blackbox` 的优势主要来自更强的 prompt 结构化设计，而不是 iteration。

#### 3.5.2 `whitebox` 模式

在 `whitebox` 模式下，`improved agent` 是整个项目最核心的研发对象，设计包括两层。静态 prompt 增强：明确要求 statement coverage、branch coverage、condition-oriented reasoning，同时关注 requirement-visible behavior 与 code-visible structure，引导模型枚举 structural white-box obligations，并关注 early return、helper-sensitive path、boundary-triggered branches。动态覆盖率迭代：每一轮都提供当前完整 suite、`requirement`、`coverage detail` 与 `uncovered_details`，模型只输出 patch groups，系统做 `current suite + patch` 得到下一轮 suite。因此 `improved whitebox` 的价值不只是"看了代码"，而是先通过更强的 white-box prompt 做结构化初始生成，再通过 coverage-guided patch iteration 逐轮补路径。

#### 3.5.3 `whitebox_code_only` 模式

在 `whitebox_code_only` 模式下，系统不再提供 requirement，只给 source code。`improved agent` 会明确把任务界定为 code-only white-box testing，只从 code-visible contracts 中保守推断 externally visible behavior，强调不应做缺乏代码支持的 speculative claims，迭代时只使用完整 suite、coverage detail 与 uncovered details。这个模式的研究意义是检验"只有代码时 LLM 能否做出接近白盒测试的决策"，并暴露 requirement 缺失时的语义漂移风险。

### 3.6 为什么 `improved` 的优势主要来自 prompt + iteration

`improved` 的性能提升不应被简单理解为"模型更强"，更准确地说它来自两类工程设计。Prompt 层面的增强在 blackbox 中提升语义类别展开能力、在 whitebox 中提升路径意识与结构意识、在 code-only 中限制无依据推断；iteration 层面的增强在白盒场景下利用 coverage / uncovered details 做 patch refinement，并通过 `suite + patch` 保留已有有效 groups，避免整套重写带来的破坏。因此 `improved agent` 构成了本文的主要方法设计，`naive agent` 的作用则是提供稳定的对照基线。

## 4. 选择 `validator.js` 作为测试库的原因

选择 `validator.js` 作为实验对象的主要原因是：它是一个真实、成熟、被广泛使用的开源项目而不是人工构造的 toy benchmark；它同时具备 requirement、source code 与人类专家编写的测试集，适合进行黑盒与白盒联合评估；函数接口具有一定多样性，既有相对简单的 validator 也有带选项参数、边界条件和复杂分支的 validator。

更重要的是 `validator.js` 同时提供两种 ground truth：真实实现本身用于判断生成测试是否执行正确，人工黄金测试集用于从等价类 / 语义类别角度评估生成测试与专家测试的接近程度。因此它非常适合本项目同时评估 correctness、coverage 与 semantic overlap。

## 5. 三类核心评价指标

### 5.1 正确率 `exact_match_rate` 及其细分维度

总体正确率 `exact_match_rate` 含义：生成测试在真实实现上执行后，判断正确的比例。

它反映测试是否能真正执行、测试断言是否正确、LLM 是否正确理解了函数的外部行为。选择原因是：如果测试断言写错，即使覆盖率很高也不能视作高质量测试。

单一 `exact_match_rate` 并不足以刻画 accuracy。为了更充分地暴露 LLM 的偏差方向，本项目在执行层（`run_validator_eval.js`）进一步按 `expected_kind` 将每个 case 归类为三种类型并在 summary 中暴露：

`valid_pass_rate` 表示预期为 valid 的 case 中被真实实现也判为 valid 的比例，反映 LLM 是否倾向于"过度保守"（把本来合法的输入误判为非法）；
`invalid_pass_rate` 表示预期为 invalid 的 case 中被真实实现也判为 invalid 的比例，反映 LLM 是否倾向于"幻觉出错误的非法规则"；
`error_throw_rate` 表示预期抛 `TypeError` 的 case 中真实实现也抛出对应异常的比例，反映 LLM 对非字符串输入、空输入等类型边界的理解是否正确。

失败案例可按混淆方向划分为三类：`valid_misclassified_as_invalid`（LLM 生成 valid 样例但真实实现判为 invalid）、`invalid_misclassified_as_valid`（LLM 生成 invalid 样例但真实实现判为 valid）、`error_not_thrown`（LLM 期望抛异常但真实实现正常返回）。这三类错误在 §9.3 和失败案例章节中对应不同的 LLM 缺陷类别（幻觉 / 语义漂移 / 参数误解 / 过度激进），是本报告剖析方法缺陷的核心材料。

上述细分指标由 `agent_toolkit/run_validator_eval.js` 在执行层直接计算（`by_expected_kind.{valid,invalid,error}.{total,passed,failed,pass_rate}` 与 `confusion.{valid_misclassified_as_invalid, invalid_misclassified_as_valid, error_not_thrown}`），并由 `agent_toolkit/cli.py` 透传至每次运行产出的 `agent_toolkit/outputs/<approach>/<validator>/<mode>/run_summary.json` 的 `evaluation.by_expected_kind` 与 `evaluation.confusion` 字段。

### 5.2 覆盖率 `Stmt / Branch / Func / Line`

覆盖率包括 `Stmt Cov`（Statement Coverage）、`Branch Cov`（Branch Coverage）、`Func Cov`（Function Coverage）与 `Line Cov`（Line Coverage）四项，反映测试是否触达了更多实现路径、白盒信息是否真正转化为了路径探索能力、迭代 patch 是否命中了之前未覆盖的代码位置。

#### 5.2.1 覆盖率选型说明

白盒覆盖率通常包含 statement / branch / condition / path / d-u coverage 五类。Statement、Branch、Function、Line 四项由 Istanbul (nyc) 原生支持，本项目全部采用：Statement 与 Branch 是标准白盒覆盖指标，Line 是 Statement 的逐行近似，Function Coverage 反映函数级探索完整性。Condition Coverage 未单独报告，理由是 nyc 不原生支持，且 `validator.js` 目标函数的条件多为简单 `if` 判断或短路 `&&/||` 组合，Branch Coverage 已能反映绝大多数条件组合；为部分弥补这一缺口，`evaluation.py` 对每个 uncovered branch 区分 `condition_true_branch / condition_false_branch / binary_short_circuit_or_rhs / binary_rhs_path` 等细粒度路径方向作为面向 patch 的语义化白盒反馈。Path Coverage 未报告，理由是 `isURL / isEmail` 等目标函数内含正则与循环，理论路径数呈指数爆炸，在工程上不可度量——使用 McCabe 环复杂度 v(G) = E − N + 2 刻画线性无关路径数下界时，`isURL` 这类多层嵌套 `if` + `for` 的源码 v(G) 容易超过 20，path coverage 需要的路径数随 v(G) 指数增长，在有限测试预算下不可达。d-u (Definition-Use) Coverage 未报告，理由是 validator 类函数数据流非常简单（绝大多数参数只被使用一次），d-u pair 对 LLM 测试生成的区分度极低，采集成本与收益不成比例。综上，本项目在五类覆盖率中选择了成本可控、对目标函数族信息密度最高的四项，并通过 uncovered branch 的方向化语义描述部分弥补 condition coverage 的信息缺口。

### 5.3 黄金测试重合率 `matched_golden_ratio`

含义是生成测试与人工黄金测试在语义类别上的重合比例，反映是否覆盖了主要等价类、是否接近专家测试设计的语义结构、生成测试是否只是"碰巧执行正确"还是在测试设计上也具有合理性。

### 5.4 为什么必须同时看三类指标

本项目最重要的发现之一是 correctness、coverage、golden overlap 三者相关但并不等价。例如在 `isCurrency` 上经常出现 coverage 达到 100%、golden overlap 也很高、但 correctness 仍明显偏低的情况，这说明走到代码路径不等于断言就对、与专家测试类别相似不等于每个 case 都正确，因此实验不能只看 coverage 也不能只看 correctness。

## 6. 实验设计

最终用于结论的函数集合为 `isEmail`、`isURL`、`isFQDN`、`isCurrency`、`isCreditCard`。总实验数为 5 个函数 × 3 种 mode × 2 类 agent，共 30 条实验。其中 `naive` 作为 baseline，`improved` 作为项目主方法，三种 mode 分别为 `blackbox`、`whitebox`、`whitebox_code_only`。

之所以删除 `isUUID` 以及更早删除一些"太简单"或"golden 提取不稳定"的函数，是因为实践中发现：太简单的函数会让所有方法都表现很好，稀释真正困难函数上的差异；ground truth 不稳定的函数会破坏结论解释；高质量 benchmark 需要"有区分度 + 有可靠 ground truth"。

Selection Bias ：这一裁剪本身引入了 selection bias。被剔除的 `isUUID` 等函数在早期实验中呈现所有方法近满分，无法区分 naive / improved 的能力边界；保留的 5 个函数具有较高的选项复杂度和边界敏感度，能形成有意义的对比。但这也意味着本报告的平均指标对"困难函数"加权，对"简单函数"代表性不足——若将本方法部署到整个 validator.js（包括大量简单 `isAscii` / `isHexColor` 类函数）的全量 benchmark 上，所有 agent 的绝对指标都会明显上升，但相对差异会被稀释。这一局限已在 §14.3 External Validity 中再次列出。

## 7. 实验结果

### 7.1 总体结果

最终实验结果来自 `experiment_final_1.md` 的完整数据：实验总数 30、成功实验 30、总 LLM 请求数 140、总 token 消耗 915,473、平均正确率 0.8599、平均黄金测试重合率 0.7915、平均语句覆盖率 86.52、平均分支覆盖率 80.21、平均函数覆盖率 100.00、平均行覆盖率 86.55。

### 7.2 按 `mode + approach` 汇总

| Agent | Mode | Avg Tokens | Avg Exact Match | Avg Stmt Cov | Avg Branch Cov | Avg Func Cov | Avg Line Cov | Avg Golden Match |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `naive` | `blackbox` | 11259.80 | 0.8826 | 81.78 | 74.89 | 100.00 | 81.72 | 0.5942 |
| `naive` | `whitebox` | 19494.40 | 0.9167 | 84.27 | 78.74 | 100.00 | 84.33 | 0.7714 |
| `naive` | `whitebox_code_only` | 18603.80 | 0.8855 | 83.71 | 75.11 | 100.00 | 84.49 | 0.5002 |
| `improved` | `blackbox` | 21537.20 | 0.8823 | 83.98 | 78.53 | 100.00 | 84.09 | 0.9667 |
| `improved` | `whitebox` | 58264.80 | 0.8132 | 95.19 | 92.31 | 100.00 | 95.02 | 0.9857 |
| `improved` | `whitebox_code_only` | 53934.60 | 0.7793 | 90.19 | 81.70 | 100.00 | 89.66 | 0.9312 |

### 7.3 完整结果矩阵

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

## 8. 详细对比分析

本节分两个维度来分析：同一 mode 下 `improved` 相对 baseline `naive` 提升了什么，以及同一 agent 内部不同 mode 带来了什么信息增益或风险。

### 8.1 同一 mode 下：`naive` baseline vs `improved`

#### 8.1.1 `blackbox`

`naive blackbox` 为 Exact 0.8826、Golden 0.5942、Tokens 11259.80；`improved blackbox` 为 Exact 0.8823、Golden 0.9667、Tokens 21537.20。两者 correctness 几乎持平，`improved` 的黄金命中率大幅提升，成本约增加一倍。原因是 `naive blackbox` 只是一个保守 baseline，而 `improved blackbox` 使用 obligations extraction、category clustering 与 self-audit，因此更容易覆盖 requirement 中分散的语义类别和 option family。这说明在 blackbox 场景下 `improved` 的主要增益首先来自 prompt 增强而不是 iteration。

#### 8.1.2 `whitebox`

`naive whitebox` 为 Exact 0.9167、Stmt 84.27、Branch 78.74、Line 84.33、Golden 0.7714、Tokens 19494.40；`improved whitebox` 为 Exact 0.8132、Stmt 95.19、Branch 92.31、Line 95.02、Golden 0.9857、Tokens 58264.80。baseline `naive` 的 correctness 更高，`improved` 的 coverage 和 golden overlap 明显更高，`improved` 成本显著更高。原因是 `naive` 更保守、不主动追 coverage maximality 因此更不容易写歪 test case，而 `improved whitebox` 结合了更强的 white-box prompt 与 coverage-guided patch 迭代，因而更容易补到分支与语义类别，但也更容易在参数、断言和边界细节上出错。这说明 `improved whitebox` 的主要优势不是 correctness，而是结构覆盖能力与语义覆盖能力。

#### 8.1.3 `whitebox_code_only`

`naive whitebox_code_only` 为 Exact 0.8855、Golden 0.5002、Tokens 18603.80；`improved whitebox_code_only` 为 Exact 0.7793、Golden 0.9312、Tokens 53934.60。`improved` 的黄金命中与 coverage 更强，baseline `naive` 的 correctness 更稳，`improved` 成本很高。原因是 code-only 情况下没有 requirement 约束，`improved` 更积极地依据代码分支扩展测试类别，但越激进地从代码推断外部行为，越容易出现"路径上像对了、语义上却不完全对"的问题。

### 8.2 同一 agent 内部：不同 mode 的比较

#### 8.2.1 baseline `naive` 内部对比

`blackbox` Exact 0.8826、`whitebox` Exact 0.9167、`whitebox_code_only` Exact 0.8855。`naive whitebox` 是 baseline 中表现最好的模式，`naive blackbox` 虽然 coverage 与 golden 不如 `whitebox` 但成本最低、correctness 也很稳，`naive whitebox_code_only` correctness 仍然不错但 golden overlap 最低。对 baseline 来说 requirement + code 的组合提供了最平衡的信息；只有 requirement 时模型仍能写出较稳的一轮 baseline；只有 code 时模型容易抓到 obvious branches 却不一定能恢复出专家测试的语义结构。

#### 8.2.2 `improved` 内部对比

`blackbox` Exact 0.8823、Golden 0.9667；`whitebox` Exact 0.8132、Golden 0.9857、Stmt 95.19、Branch 92.31；`whitebox_code_only` Exact 0.7793、Golden 0.9312。`improved blackbox` 是最平衡的模式，`improved whitebox` 是最强的 coverage 模式，`improved whitebox_code_only` 风险最大。`improved blackbox` 主要依靠 prompt 增强就已经能显著提升语义类别覆盖；`improved whitebox` 进一步利用代码结构与 uncovered feedback 把路径探索能力拉到最高；`improved whitebox_code_only` 虽然也能追路径，但由于 requirement 缺失更容易语义漂移。

## 9. 消融实验

本节重点回答两个问题：`improved whitebox` 要不要加 requirement 复检，以及为什么 `suite + patch` 比纯 suite 重写更好。为了公平比较，本节不直接对比不同轮次的整张总表，而是基于 `experiment_ablation_1.md`、`experiment_ablation_2.md` 与 `experiment_final_1.md`，统一采用相同的 5 函数口径（`isEmail`、`isURL`、`isFQDN`、`isCurrency`、`isCreditCard`），然后只比较 `improved whitebox` 的均值。

### 9.1 复检机制的消融：要不要加 requirement 复检

`experiment_ablation_1.md` 的 `improved whitebox` 对应“加入 requirement 复检 / pruning”的版本；最终版则去掉了这一机制。

同口径 `5` 函数下，`improved whitebox` 对比如下：

| Version | Avg Tokens | Avg Exact Match | Avg Stmt Cov | Avg Branch Cov | Avg Func Cov | Avg Line Cov | Avg Golden Match |
|---|---:|---:|---:|---:|---:|---:|---:|
| `experiment_ablation_1`（带 requirement 复检） | 79361.20 | 0.8849 | 88.38 | 82.59 | 100.00 | 88.49 | 0.7776 |
| `final`（最终版） | 58264.80 | 0.8132 | 95.19 | 92.31 | 100.00 | 95.02 | 0.9857 |

这个结果说明：requirement 复检确实能在这组数据里保住更高 correctness，但代价是 token 更高、coverage 更低、golden overlap 显著更低。因此对 `improved whitebox` 来说，复检机制并没有把它变成"更平衡"的方法，反而削弱了它原本最有价值的路径探索与语义类别扩展能力。项目最终判断 requirement 复检是错误方向。

这一跨版本对比数据同时也构成 §12.3"跨设计版本泛化性"的主要论据——即使在不同 LLM 随机调用的情况下，去掉 requirement 复检后 coverage 与 golden overlap 均一致提升的现象在两轮独立实验中都可观察到，降低了 §14.2 "LLM 随机性" 威胁的影响。

### 9.2 迭代方式的消融：suite + patch` 比纯 suite 重写更好的原因

`experiment_ablation_2.md` 对应的是删除复检机制后的版本；最终版则进一步收敛到当前的 `suite + patch` 白盒迭代方式。

同口径 `5` 函数下，`improved whitebox` 对比如下：

| Version | Avg Tokens | Avg Exact Match | Avg Stmt Cov | Avg Branch Cov | Avg Func Cov | Avg Line Cov | Avg Golden Match |
|---|---:|---:|---:|---:|---:|---:|---:|
| `experiment_ablation_2` | 68342.80 | 0.8164 | 88.74 | 81.49 | 100.00 | 89.37 | 0.8430 |
| `final`（suite + patch） | 58264.80 | 0.8132 | 95.19 | 92.31 | 100.00 | 95.02 | 0.9857 |

这个结果说明 `suite + patch` 能显著降低 token 成本、明显提升 coverage 与 golden overlap，而 correctness 基本持平只是略微下降。因此更准确的结论不是"`suite + patch` 大幅提高 correctness"，而是在几乎不损伤 correctness 的前提下显著提升了 coverage / semantic overlap 并降低了成本。

这一结果同样是 §12.3 跨版本泛化论证的组成部分——`suite + patch` 相对 pure rewrite 的优势在两次独立实验中都成立，不是单次随机波动。

### 9.3 AI 局限与迭代改进

本节将前几节分散提到的局限，按"遇到的局限 → 实验证据 → 本项目的改进"三段式组织。

| # | 遇到的 AI 局限 | 实验证据 | 本项目的改进 | 效果 |
|---|---|---|---|---|
| L1 | 幻觉：LLM 会伪造 requirement 中不存在的规则 | `isEmail improved whitebox` 生成的 `OB-11 "maximum email length"` 在 validator.js 文档中不存在（见附录 A 案例 2） | 在 `improved whitebox` prompt 中加入硬约束："Are your expectations aligned with the requirement text rather than guessed from hidden implementation details?" 并要求 self-audit | 幻觉率下降但未根除；仍建议 future work 引入 evidence grounding（见 §12.5） |
| L2 | 参数误解：对选项语义理解错误导致断言反转 | `isCurrency improved whitebox` 正确率从 baseline 的 0.90 降至 0.67；失败案例集中于 `require_symbol / thousands_separator` 等选项语义（附录 A 案例 1） | 在 `improved blackbox` prompt 中加入 option-flip self-audit："For each option-focused group, would at least one valid/invalid pair change outcome if that option were flipped back?" | blackbox 场景下 isCurrency 正确率回到 0.84；whitebox 仍未根治，列入已知短板 |
| L3 | 语义漂移：code-only 模式下缺少 requirement 约束时严重 | `improved whitebox_code_only` 平均正确率 0.7793，是三种 mode 中最低；附录 A 案例 3 展示了一个典型漂移 | 在 `improved whitebox_code_only` prompt 中加入："conservative behavior inference from code-visible contracts"、"do not make speculative claims about undocumented behavior unless the code strongly supports them" | 相比无约束版本有改进，但仍不如 whitebox；建议 code-only 只作为补充视角（§10.3） |
| L4 | 过度激进：category clustering 过早塌缩或过度扩张 | 早期版本 `improved isURL blackbox` 塌缩成单一 group；后期又一度扩张到大量不具区分度的 group | prompt 里加入双向约束："do not collapse many unrelated options into one catch-all default group" 与 "when uncertain, choose fewer examples inside a group rather than merging unrelated categories" | `isURL improved blackbox` 恢复到 5–7 个合理 group；黄金类别命中从早期塌缩恢复到 1.0 |
| L5 | Requirement 复检反而损伤核心能力 | `experiment_ablation_1` vs `final`：复检版 correctness 0.8849 略高于最终版 0.8132，但 coverage 从 88.38/82.59 降到 95.19/92.31 的提升路径被阻断，golden overlap 从 0.9857 降到 0.7776 | 在 `final` 版中移除 requirement 复检，恢复 coverage 与 golden overlap（见 §9.1） | golden overlap 提升 20+ 个百分点；coverage 提升约 7–10 个百分点 |
| L6 | 纯 suite 重写迭代发散 / 成本高 | `experiment_ablation_2` 的 token 平均 68342.80，coverage 88.74 | 改为 `suite + patch` 增量迭代，只返回 patch groups 而非重写整套 | token 降至 58264.80，coverage 提升到 95.19，golden 提升到 0.9857（§9.2） |
| L7 | Golden 反馈会污染迭代信号 | 早期方案中 golden overlap 参与 patch 决策，导致 Agent "背答案"式回流 | 在 `improvement_prompt` 中加硬约束 "You must NOT use any golden tests, repository test overlap analysis, or external oracle hints"；服务端只输入 coverage 与 uncovered_details | 消除 golden 泄漏；黄金测试作为纯评估指标保留其可信度 |
| L8 | 单一 accuracy 指标掩盖偏差方向 | 初期只输出 `exact_match_rate`，无法分辨 "LLM 把合法误判为非法" 还是 "幻觉出非法规则" | 在 `run_validator_eval.js` 的 summary 中细分 `by_expected_kind`（valid / invalid / error），并维护混淆方向计数 | 可以区分幻觉型错误与过度保守型错误，成为失败案例分析的基础 |
| L9 | 单次运行受 LLM 随机性影响 | LLM 输出在 temperature=0.2 下仍有波动，单次数字不足以论证方法稳定性 | 在同一 5 函数 × 3 mode 口径下运行了多轮 ablation（见 `experiment_ablation_1 / 2 / final_1`），用跨版本稳定现象作为论据（§12.3） | 跨版本观察到稳定模式：`naive` 稳 correctness / `improved` 强 coverage+golden / code-only 最弱 |

表中的"改进"是工程演化中的实际动作，可在 `agent_toolkit/improved_agent/prompts.py` 与 `service.py` 中直接找到对应代码证据（约束语句、迭代接受条件、反馈字段过滤等）。剩余未根治的局限（尤其 L1 / L2 / L3）在 §12.5 作为 future work 给出 proposed design。

## 10. 项目实践经验

1.太简单的函数会让所有方法都表现很好，从而稀释困难函数上的真实差异。因此 benchmark 设计本身就是实验可信度的重要组成部分。

2.高 coverage 不等于高质量测试。在 `isCurrency` 等案例上多次出现 coverage 很高、golden overlap 很高但 correctness 偏低的情形。这说明 AI 生成测试时不能只追 coverage；如果没有 correctness 约束，高覆盖率可能只是"走到了很多路径"，并不意味着写对了测试。

3.只给代码时，模型更容易学到实现结构，却更容易丢失 requirement 对输入语义、边界和外部行为的约束。因此 `whitebox_code_only` 更适合作为补充视角而不是默认主力模式。

4.如果没有 `naive baseline`，很多复杂设计看起来都会"很先进"。但一旦与一个稳定、保守、低风险的 baseline 对比，就会发现有些复杂设计只是提高了 token 成本、有些提高了 coverage 却没有提高 correctness，只有少数真正值得保留。因此 baseline 在本项目里不是无关紧要的配角，而是验证研发改进是否真的有效的关键参照。

## 11. 与传统非 AI 方法的对比

本节按三种代表性非 AI 方法与本文 AI 方法进行维度化对比，前两种为经典软件测试方法，第三种为自动化随机测试基线。

### 11.1 三种对照基线

#### 11.1.1 手写 EP / BVA（Equivalence Partitioning + Boundary Value Analysis）

课堂经典的黑盒测试设计方法。针对 `isURL` 在 `require_valid_protocol=['http','https']` 配置下手工设计的等价类/边界值示例：

| ID | 类别 | 输入示例 | 预期 | 设计动机 |
|---|---|---|---|---|
| EP-1 | 合法协议 + 合法域名 | `http://example.com` | valid | 等价类代表 |
| EP-2 | 非白名单协议 | `ftp://x.com` | invalid | 协议白名单反例 |
| EP-3 | 无协议 | `example.com` | invalid | 缺失必需前缀 |
| EP-4 | 空串 | `""` | invalid | 边界退化 |
| BVA-1 | 长度刚低于 2083 | `http://a.com/` + 2070×`x` | valid | 边界-1 |
| BVA-2 | 长度在默认上限附近 | `http://a.com/` + 2075×`x` | invalid | 边界+1 |
| EP-5 | 非字符串 | `null / 123 / {}` | TypeError | 类型边界 |

特点：设计者是人类，每条 case 对应一个明确的等价类或边界；正确率理论上为 100%（因为设计时已知答案）；但覆盖率受设计者经验限制，通常难以穷尽选项组合。

#### 11.1.2 Property-based Testing

基于性质的随机输入生成。对 `isURL` 的典型 property 包括：`http(s)://<wellFormedAuthority>` 应恒为 valid、空字符串应恒为 invalid、`isURL` 对任意字符串返回 boolean 或抛 TypeError 而不应崩溃、幂等性（对同一输入重复调用结果一致）。特点是工具（`fast-check`）自动生成数百到数千输入，能在无人工编写具体 case 的前提下探索路径；但 property 的设计质量决定上限，发现边界 bug 依赖 shrinking 能力。

#### 11.1.3 纯随机 Fuzz

使用随机字符串生成器喂给 `isURL`，收集 coverage。特点：零人力成本，但语义覆盖最弱；通常只能触达浅层结构。

### 11.2 维度化对比

| 维度 | 手写 EP/BVA | Property-based | 随机 Fuzz | Naive LLM | Improved LLM |
|---|---|---|---|---|---|
| 生成者 | 人类 | 算法 + 人类写 property | 算法 | LLM | LLM |
| 设计成本 | 高（需软测专业知识） | 中（需 property 经验） | 极低 | 低 | 低 |
| 单函数耗时 | 1–2 小时 | 30 分钟–1 小时 | 秒级 | 约 30 秒（API） | 数分钟（多轮 API） |
| 金钱成本 | 仅人力 | 仅人力 | 近 0 | API token | API token（更高） |
| 正确率 | 100%（设计即答案） | 100%（property 为规约） | 不适用（无 oracle） | 约 88% | 约 81%–89% |
| 语句覆盖 | 中（受设计者经验） | 较高（随机量大） | 低 | 约 82% | 约 83%–95% |
| 分支覆盖 | 中 | 较高 | 低 | 约 75% | 约 78%–92% |
| 边界/选项敏感 | 强（定义明确） | 一般（需专门 property） | 弱 | 中 | 强 |
| 需求变更适应 | 需人工重写 | 需改写 property | 无需 | 自动重新生成 | 自动重新生成 |
| 可解释性 | 极强 | 强 | 弱 | 中（含 rationale） | 中（含 rationale + obligations） |
| 稳定性（可复现） | 完全确定 | 随机 + seed 可控 | 随机 | LLM 随机性 | LLM 随机性 |

说明：上表中 LLM 的数字来自本项目 `experiment_final_1.md` 对 5 个函数的平均值；手写 EP/BVA、Property-based、随机 Fuzz 的数字区间来自作者对 `isURL` 的手工对照观察与既有学术研究惯例，因条件限制未对 5 个函数全面复跑。本项目定位为 AI 方法原型，完整 non-AI 实测对比列为 future work（见 §12.5）。

### 11.3 Pros / Cons 总结

传统非 AI 方法（手写 EP/BVA、Property-based、Fuzz）的优点是正确率有理论保证（human / property 即 oracle）、结果确定可复现便于回归测试、设计过程本身即文档可维护性强、零 API 成本；缺点是手写方法耗时极长不适合大规模迭代、property-based 需要测试工程师能抽象出合适的性质门槛较高、随机 fuzz 没有语义方向难以命中带选项的业务路径、对需求变更的适应成本高（需人工重新设计）。

AI 方法的优点是生成速度快（秒到分钟级）、能从 requirement 文本自动扩展语义类别、白盒模式下具备较强路径探索能力（Improved whitebox Stmt 达 95.19%）、对需求变更自动适应（只需重跑 prompt）、可以直接输出结构化 rationale / obligations 便于人工审计；缺点是正确率并非理论 100% 存在幻觉（见 §9.3 与附录 A.2）、结果带随机性同一 prompt 多次运行会波动、会误解参数（option_misinterpretation）和产生幻觉规约（hallucinated_expected）、无 requirement 时易语义漂移（code-only 模式 correctness 下降）、需要 LLM API 成本单函数 token 消耗可达数万。

成本量化：以 gpt-4o 当前定价（输入 $2.50 / 1M tokens，输出 $10.00 / 1M tokens，按 80% 输入 + 20% 输出近似估算）计算，本项目 30 条实验共 915,473 tokens 的累计 API 成本约为 $3.5–5.0，平均每函数 × 每 mode × 每 agent 约 $0.12–0.17，即每个函数的完整三模态双 agent 分析（6 次实验）成本约 $0.7–1.0。作为对比，手写一份等价质量的 EP/BVA 测试套件按测试工程师 $50/小时、每函数 1–2 小时计需 $50–100；property-based 需测试工程师写 property（每函数 0.5 小时，$25），再加大约半小时 tuning 约 $50。因此 AI 方法在单位测试生成成本上比手写方法低约两个数量级，这正是"AI 作为测试设计加速器"的经济基础。但这一优势仅在"生成"环节，执行、验证、回归所需的基础设施成本（nyc、mocha、CI）与非 AI 方法相同。

从 exploratory vs scripted 视角看，测试研究领域一个经典对照实验显示 "exploratory testing 比 scripted testing 的 bug/小时效率约高 2 倍，但覆盖深度较窄"。本项目的 `improved agent` 实质是 exploratory 风格（每次生成不同、依靠 LLM "经验"扩张），`naive agent` 是 scripted 风格（保守、固定）。§8 的实验结果——improved golden overlap 明显更高（0.97 vs 0.59）但 correctness 略低（0.82 vs 0.92）——与该规律高度一致。这说明本项目观察到的不只是 "LLM 恰好如此"，而是软测中两类测试哲学的本质差异在 AI 时代的再现。

### 11.4 更现实的定位

综合来看，AI 方法不适合完全替代传统非 AI 方法，而最适合作为测试设计加速器、草案生成器与覆盖率探索工具。一个更合理的工作流是：先由 AI 快速产出候选测试集，再由 Property-based 方法做一次随机输入补强以找出 AI 遗漏的边界，然后由人工审阅 AI 给出的 rationale 与 obligations 对高风险 case 做修正或最终确认，重要边界用手写 EP/BVA 做回归。这种组合在保留 AI 扩展能力的同时，利用传统非 AI 方法堵住正确率与稳定性两个短板。

## 12. 方法的泛化能力

### 12.1 跨函数类型的泛化

最终纳入的 5 个函数并不属于同一种简单模式：`isEmail` 规则复杂、选项多；`isURL` 路径与选项组合复杂；`isFQDN` 结构清晰但边界较多；`isCurrency` 格式与选项耦合明显；`isCreditCard` 校验规则较强、边界较敏感。尽管函数风格不同，实验中仍然能反复看到稳定模式：baseline `naive` 更稳、`improved` 更强 coverage / golden、code-only 风险更高、`suite + patch` 优于整套重写。这说明结论不是只在某一个函数上成立，而是在多个不同 validator 上都可重复观察到。

### 12.2 跨输入模式的泛化

本项目同时覆盖"只给 requirement"、"requirement + code"、"只给 code"三种输入条件，因此方法的泛化性不仅体现在跨函数，也体现在跨信息条件。实验表明：当 requirement 可得时模型更容易保持 correctness；当 code 可得时模型更容易提升 coverage；当只有 code 时模型更容易语义漂移。这说明结论对不同测试输入场景都有解释力。

### 12.3 跨设计版本的泛化

本项目经历了多轮设计演化（带 requirement 复检、去掉 requirement 复检、纯 suite 重写、`suite + patch` 迭代）。在这些设计版本变化中有三个现象始终稳定存在：`improved whitebox` 的核心优势是 coverage / golden 而不是 correctness，baseline `naive` 的核心优势是 correctness 稳定性，仅代码模式更不稳定。这说明项目结论并不是偶然来自某一次实验，而是具有一定跨版本稳定性。详细的跨版本 ablation 数据见 §9.1（requirement 复检是否必要）和 §9.2（suite + patch vs 纯 suite 重写）。这一跨版本稳定性是支撑本节 generalizability 论证的核心数据。

### 12.4 泛化性的边界

本项目的泛化性仍有边界：当前实验对象主要集中在 `validator.js` 风格函数，尚未扩展到更大型、跨模块、状态更复杂的系统级软件，因此不能直接声称该方法已泛化到所有软件测试场景。更谨慎的结论是：本方法已经在真实开源库中的 validator-style functions 上表现出较好的跨函数、跨模式、跨版本稳定性，但更复杂软件系统的泛化仍需后续验证。

### 12.5 跨 Domain 扩展的 Future Work

本节给出跨 domain 扩展的具体方案设计：

1. Target Adapter 抽象层：将目前在 `target_context.py / evaluation.py / run_validator_eval.js` 中对 validator.js 硬编码的路径、执行命令、覆盖率解析抽象为 `TargetAdapter` 接口，每个目标库实现 `get_source() / get_requirement() / run_tests() / parse_coverage()` 四个方法。
2. 候选扩展 domain（按难度递增）：同类 JS 校验库（如 `lodash` 的 `_.isEqual / _.isPlainObject`）验证同 domain 泛化；有状态 JS 模块（如一个小型 state machine）验证状态转换测试；网络请求模块（axios 的 URL 构造 / 拦截器子模块）验证异步与副作用路径。
3. Domain Profiling 阶段：在 `service._generate_initial` 最前端增加一次轻量 LLM 调用，让模型基于 requirement + source 输出结构化 `DomainProfile`（`domain_category / risk_dimensions / priority_policy`），并注入后续 prompt 作为 context。
4. Priority 分级机制：obligation schema 增加 `priority: high|medium|low` 与 `risk_category`，让高优先级 obligation 获得更多 case 预算；在评估侧新增 `high_priority_obligation_pass_rate` 指标。
5. Evidence Grounding：obligation schema 增加 `evidence_type / evidence_locator / evidence_snippet / confidence` 四字段，要求 LLM 把每条规约挂到 requirement 原文或源码行号；无法 ground 的 obligation 标记 speculative 并折扣。
6. Mutation Testing 评估补强：在当前三重评价（correctness / coverage / golden overlap）之外引入 mutation score。具体做法是对每个目标函数生成 mutant（常见 mutator：arithmetic-swap、boundary-shift、negation-flip、return-value-perturbation），用 LLM 生成的 test suite 去 kill 这些 mutant，未被 killed 的 mutant 即为 test suite 的真实盲点。这比纯 coverage 更接近"发现 bug 能力"，也是对 §14.1 中 "soundness 被牺牲" 的直接度量工具。
7. Differential Testing：对同一输入同时调用 validator.js 与另一独立实现（如 Python email-validator），对输出分歧做自动分析。这是"换 oracle"方案，能把"LLM 幻觉"与"validator.js 真实 bug"在报告层面区分开。
8. Multi-Role Collaborative Agent Architecture（多角色协作架构）：当前 `improved whitebox` 的 Stmt 95.19% / Branch 92.31% / Golden 0.9857，但 correctness 0.8132 明显低于保守生成的 `naive whitebox`（0.9167），§8.1.2 已观察到这一张力。这一现象表明单一 Agent 在激进追求高覆盖率时容易陷入"逻辑过拟合"。未来可演进为三角色协作：Domain Expert Agent 读 requirement + source 后产出 contract specification、Test Writer Agent 基于 spec 生成 test suite、Auditor Agent 独立审查 writer 输出的断言是否与 contract 一致。通过引入独立的 critic 角色，有望在保持高覆盖率的同时守住 correctness 底线，突破单 Agent 的固有天花板。
9. Metamorphic Testing（蜕变测试）：针对 `isCurrency` 这类 "覆盖率 100%、golden overlap 1.0 但 correctness 仅 0.67" 的场景，核心困境是 LLM 难以稳定预测单一绝对正确的 expected（即 Test Oracle Problem）。蜕变测试绕开这个困境——不要求 LLM 给出唯一正确答案，而是让它生成一组具有逻辑关联的输入并验证输出间的相对关系 (metamorphic relation) 是否符合预期。例如对 isCurrency 可设计的 metamorphic relation 包括"若 `f(x)=true` 且 `x` 不含 thousands separator，则在允许该选项时 `f(插入千分位符后的 x)=true`"、"若 `f(x)=true` 则 `f(x 前后加空格)=false`（除非允许）"等。这类关系比绝对 expected 更容易被 LLM 正确生成，可大幅降低 Oracle Problem 对 correctness 的冲击。蜕变测试与 Differential Testing、Property-based 并列为四条互补的 oracle 策略。

### 12.6 渐进式验证路线图（按风险-价值分层）

上述 9 条 proposed design 并非要一次性全部实施。按实施难度 × 方法论收益排序，可构建三阶段路线图。

阶段一（低风险 / 高可行性 / 先行实施）：同 validator.js 生态扩展函数集至 20+，每条配置重复 5 次报均值 ± 标准差以消除 §14.2 中"单次随机性"威胁；实装 Priority 分级（第 4 条）、Evidence Grounding（第 5 条）、Accuracy 细分指标。这一阶段不改变被测对象，只改进方法本身，风险最低。

阶段二（中风险 / 可控改造 / 中期实施）：实装 Target Adapter（第 1 条）并迁移到 1–2 个同任务类型库（如 lodash 的 validation helpers），保持 golden tests + nyc 覆盖率统计口径一致，验证"跨库同任务"的泛化；实装 Domain Profiling（第 3 条），在扩展后的多库上验证 DomainProfile 的判别有效性；引入 Mutation Testing（第 6 条）作为对 soundness 的独立度量。这一阶段涉及跨库工程改造，但仍在"无状态纯函数"范围内，可控。

阶段三（高风险 / 高价值 / 长期愿景）：迁移到强状态依赖任务（state machine、异步 API、带副作用的模块），验证方法对 ISO 9126 Reliability / Efficiency / Portability 等维度的覆盖能力；实装 Multi-Role Collaborative Architecture（第 8 条）与 Metamorphic Testing（第 9 条），突破单 Agent + 绝对 Oracle 的双重天花板；引入 Differential Testing（第 7 条）用独立实现作为外部 oracle；配合跨 LLM 对照（gpt-4o vs Claude vs DeepSeek）与人工抽样复核，真正突破当前同库同构函数的证据边界。这一阶段才真正回答了"LLM 测试生成是否能在生产级复杂系统上替代人工"这一核心问题。

阶段二、三的内容属于跨领域场景下的研究假设与改进方向，而非本轮实验已经完成验证的结论。

## 13. 深入分析：LLM 方法的核心挑战与改进方向

本节对 LLM 测试生成方法中最关键的三组问题给出系统分析：(1) 如何让系统处理不同 domain 的输入并较好运行；(2) 如何从生成结果中发掘方法本身的缺点；(3) 本方法在"发现 real-world bugs"维度上的定位与诚实评价。

### 13.1 跨 domain 输入的三大挑战

LLM 在跨 domain 输入下有三大典型缺陷：幻觉 / 通用但不具体 / 不能体现不同 domain 中不同 case 的 priority。本项目对这三点逐一给出分析 + 当前已实施缓解 + 预期收益 + 未来增强方案。

#### 13.1.1 幻觉

现象：LLM 会生成 requirement 中不存在的规约。直接证据是附录 A 案例 2：`isEmail` 被生成出一个不存在的 `maximum email length` 规则，断言 `"a@b.com" → invalid`，而真实实现返回 valid。

已实施缓解：`improved` system prompt 加入 "You must reason conservatively, preserve correctness"；`improved blackbox` prompt 要求 self-audit "Did you use examples whose expected result depends on undocumented implementation details rather than the visible requirement?"；白盒迭代明确拒绝 golden oracle 泄漏，避免 Agent 以"背标准答案"方式掩盖幻觉。效果是幻觉率下降但未根除，isCurrency / isEmail 在 improved whitebox 下仍有可观察幻觉（见 §9.3 L1、附录 A.2）。

学术定位上，LLM 的幻觉对应软测领域的经典难题——测试预言器问题 (Test Oracle Problem)。当被测系统的正确行为难以被预先完全规约时，测试断言本身可能错误；LLM 倾向于"猜"一个看似合理的 expected，跨 domain 输入下会放大这个经典问题，因为 LLM 在陌生领域更缺乏可靠的规约参考。§13.3 讨论了针对 Oracle Problem 的四条互补改进路径（Evidence Grounding、Differential Testing、Property-based、Metamorphic Testing）。

Proposed 未来增强为 Evidence Grounding：让每条 obligation 必须引用 requirement 原文片段或源码行号，schema 层面强制 `evidence_type / evidence_locator / evidence_snippet / confidence` 四字段，无法 ground 的标记 speculative 并在汇总时折扣，从而把"规约到底来自哪里"变成可审计的字段。以附录 A 案例 2 为例，若 Evidence Grounding 已实装，LLM 生成 `OB-11: maximum email length` 时将被要求引用 validator.js README 的具体段落——该规则在 README 中根本不存在，将被 schema 强制标为 `evidence_type: speculative, confidence: low`，在汇总统计时被折扣，幻觉断言不会进入最终 test suite。

#### 13.1.2 通用但不具体

现象：不同 domain（校验库、网络请求库、算法库、状态机）对测试的关注点完全不同——例如金融类关注金额边界与精度、安全类关注注入与协议白名单、算法类关注路径与复杂度。但当前 prompt 写死 "validator-style functions"，对所有目标一视同仁。

已实施缓解：通过 `improved blackbox / whitebox / whitebox_code_only` 三套差异化 prompt 给 LLM 不同的注意力焦点（EP/BVA vs 分支覆盖 vs 代码唯一约束）；通过 `obligations → categories → test_groups` 三层展开，让 domain-specific 语义至少能从 requirement 文本拉取到 prompt 上下文中。效果是在 validator.js 内部不同函数（`isEmail / isURL / isFQDN / isCurrency / isCreditCard`）已经能产出差异化的 category 结构，但跨库的 domain 差异尚未覆盖，因为被测对象只有 validator.js 一个。

Proposed 未来增强为 Domain Profiling 阶段（§12.5 第 3 条）：让 LLM 先读取 requirement + source 输出 `DomainProfile`：

```json
{
  "domain_category": "validator | network | algo | stateful | financial | ...",
  "risk_dimensions": ["boundary","security","concurrency","resource_leak", "..."],
  "priority_policy": {"security": "high", "boundary": "medium", "format": "low"},
  "typical_failure_modes": ["..."]
}
```

再把该 profile 注入后续 blackbox / whitebox / codeonly prompt 的 context，使系统能在不同 domain 上自动调整注意力分配。以金融类 domain（如一个 payment API）为例，Domain Profiling 将自动识别 `risk_dimensions = [boundary, precision, security]` 并置 `priority_policy.boundary = high`，这会让 Agent 在金额边界上分配更多 case 而不是像现在对 `isCurrency` 的所有 obligation 等权对待——这恰好是当前 `isCurrency improved whitebox` 正确率从 0.90 降到 0.67 的一个关键原因（见 §9.3 L2 和附录 A.2 案例 1）。

#### 13.1.3 不能体现不同 domain 中不同 case 的 priority

现象：同样是"边界值测试"这一类别，金融 domain 的金额边界与网页 domain 的字符串长度不应同等权重。当前 LLM 默认对所有 obligation 等权分配 case，无法反映 priority。

已实施缓解：`improved` 的 obligations 已经有粗粒度的 "kind (blackbox/whitebox)" 与 "minimal_valid/minimal_invalid" 字段间接表达一部分测试义务的关键性；`run_validator_eval.js` 已按 `by_obligation` 统计每条 obligation 的通过率支撑 post-hoc 分析。效果是只有后验的通过率统计，没有先验的 priority 驱动分配。

Proposed 未来增强为 Priority 分级机制（§12.5 第 4 条）：obligation schema 加 `priority` 与 `risk_category`，prompt 引导 LLM 把更多 case 预算分配给 high-priority obligation（≥3 cases），low-priority 仅 1 case；同时新增评估指标 `high_priority_obligation_pass_rate`——它比全局正确率更能反映"关键风险是否真的被测到"。理论依据是软件质量与风险管理中 FMEA（Failure Mode and Effect Analysis）与 Risk Priority Number (RPN) 的直接应用：FMEA 的标准做法是 stakeholders 列出可能的失败模式，按 severity × priority × likelihood 算出 RPN（1–25），RPN 高的 case 分配更深入的测试；本项目提出的 priority 分级机制就是把 FMEA 从"stakeholders 手工打分"升级为"LLM 基于 DomainProfile 自动打分"。在 isCurrency 数据上若把 option-sensitive obligation 标为 `priority: high, risk_category: option_interpretation` 并分配 ≥3 case，案例 1（`"123.45"` 误判）类型的错误有机会被 self-audit 在生成阶段拦下；从指标层面看，当前 isCurrency improved whitebox 正确率 0.67 中若仅 option-sensitive case 能被 priority 机制挡下 50%，全局 correctness 可回到约 0.83，接近 isEmail / isURL 水平。

### 13.2 从生成结果发掘方法本身的缺点

实践度量层面：§9.3 的 L1–L9 九条局限全部来自实际实验过程中遇到并记录的问题，每一条都带实验数据或代码改动证据。其中 L1/L2/L3 是 LLM 固有缺陷（方法本身的上限问题），L4–L9 是 prompt/迭代机制设计缺陷（可被工程改进），这 9 条共同构成方法缺点清单。肉眼观察层面，附录 A.2 给出 5 个具体失败案例，每个案例包含完整的 input / expected / actual / 所属 obligation / 失败类别，直接展示 LLM 生成测试的缺陷形态。

代表性的三类缺陷（完整 5 例请见附录 A.2）：幻觉 (hallucinated_expected) —— `isEmail improved whitebox` 生成了一个 validator.js README 中根本不存在的 "maximum email length" 规则，据此把 `"a@b.com"` 断言为 invalid，而真实实现返回 valid，这是 LLM 把训练语料中的常见"邮箱长度限制"知识硬塞给一个并不实现该规则的函数的典型幻觉；选项误读 (option_misinterpretation) —— `isCurrency improved whitebox` 在 `require_symbol=false` 下把 `"123.45"` 断言为 invalid，LLM 误把"符号可选"读成"符号禁止"，这是读懂 option 语义上的认知偏差而非简单记错；过度激进 (over_aggressive) —— `isFQDN improved whitebox` 在 `allow_underscores=true` 下把 `"invalid_domain.com"` 断言为 invalid，恰恰是该选项要放行的情况，LLM 记住了"下划线在标准 FQDN 中非法"的一般规则，却没有反思当下选项已经打开允许，是忽略选项配置的典型错误。这三类缺陷肉眼即可识别，且每一类都对应一种可工程化的修复方向（§13.1 的 Evidence Grounding、Domain Profiling、Priority 机制分别对应）。

对方法本身的诚实评价是：LLM 在 requirement 可见范围内做黑盒测试生成表现良好，但一旦涉及需要读懂选项语义（isCurrency 的 `require_symbol / thousands_separator`）或需要判断规约是否真实存在（isEmail 的虚构 maximum length）时错误率显著上升；code-only 模式的 correctness 下降是 LLM 方法族固有短板，不是特定 prompt 的设计失误——当缺失外部规约时 LLM 只能从代码结构反推行为，而代码的"可能行为"和"合法行为"是两个不同集合；LLM 的"高 coverage 不等于高 correctness"问题（§10.2）揭示了一个方法学风险：如果评估指标只看 coverage，LLM 会在数字上迅速看起来很好但生成的测试质量并未同步提升，本项目通过三重评价（correctness + coverage + golden overlap）堵住这个漏洞。

### 13.3 Real-world bugs found 的诚实评价

本项目在 validator.js 的 5 个目标函数上运行 30 条实验后未报告任何 validator.js 本身的 real-world bug。以下给出三类原因分析，这本身也是对"LLM 测试方法能不能发现真实 bug"这一问题的方法论思考。

原因一是被测对象的成熟度限制了 bug 密度。validator.js 是一个被广泛使用（npm 周下载量百万级）、持续维护了多年的成熟库，其 5 个目标函数（`isEmail / isURL / isFQDN / isCurrency / isCreditCard`）是库中最核心、被测试最充分的几个，已经有大量人工撰写的 golden tests 作为回归保护。按 Defect Clustering 原则 defect 集中在新功能与复杂模块，而我们选的是最稳定的那部分，这是实验设计层面的 selection bias。

原因二是本项目的 oracle 设计限制了 bug 检出。本项目把 "validator.js 真实实现" 作为 oracle（test_case 的 expected 与真实 return 不一致即为失败），这意味着：若 validator.js 实现本身有 bug，LLM 若幸运地生成了正确的 expected，这个 bug 会被报告为"LLM 生成了错误的 test case"而非"validator.js 有 bug"；换言之当前框架下真 bug 与 LLM 幻觉在输出上不可区分，都表现为 exact_match_rate 中的 failure。要发现 real-world bug 需要改变 oracle，本报告列出四条互补的 oracle 替代策略：Differential Testing（对比 validator.js 与另一独立实现如 Python 的 `email-validator`，输出分歧即疑似 bug）、Property-based Testing（直接断言数学性质，如 "isURL(str) == true 必然能 URL.parse(str)"）、Metamorphic Testing 蜕变测试（构造 metamorphic relation 验证输出相对关系而非绝对值，例如"若 `isCurrency(x)=true` 且 x 无千分位，则允许千分位时 `isCurrency(插入千分位的 x)=true`"，这类关系比绝对 expected 更容易被 LLM 正确生成，可绕过 Test Oracle Problem）、Mutation Testing（用 LLM 生成的测试集去 kill mutants，未被 killed 的 mutant 即 test suite 的真实盲点）。这四条都列入 §12.5 future work，是回答 "LLM 方法能否找 real-world bug" 的互补改进路径。

原因三是本项目的评估重心在"测试生成能力"而非"bug 发现能力"。本项目的研究问题是 "LLM 能否生成高质量测试"，而非 "LLM 能否通过测试发现 bug"，两者是软测研究的两个不同子任务，不能互相替代。

虽然未报告正式 bug，在失败案例分析中注意到几个 validator.js 的可讨论行为边界（并非 bug 但值得文档化）：`isEmail` 对 `user@localhost` 默认返回 invalid（无 TLD），但 RFC 允许 local-part，这是行为决策而非缺陷；`isCurrency` 的 `require_symbol=false` 实际语义是"符号可选"而非"符号禁止"，这与许多 LLM 的"直觉解读"不一致，文档若更清晰可减少下游误用（包括 LLM 误用）；`isFQDN` 的 `allow_underscores=true` 对连字符-下划线混合的行为在文档中描述不够显式，多次导致 LLM 生成不一致的测试期望。这三条都是把 LLM 测试生成的失败模式反向投射到被测对象的可改进点上得到的观察——这本身是 LLM-based testing 对开源库的一个间接价值：即使不直接发现 bug 也能发现"文档不够清晰 / 接口易被误用"的可文档化弱点。

方法论结论：要在未来版本中真正发现 real-world bugs，需要换被测对象（选择 bug 密度更高的目标如早期版本或新合入的 PR 中的模块）、换 oracle（引入 differential testing 或 property-based assertion）、引入 mutation testing（mutation score 比 coverage 更能反映"测出 bug 能力"）。

## 14. 提交包说明与复现实验

最终提交包（压缩文件）的内容与路径约定如下：

```
<Team_XX_Assignment1_Submission>.zip
├── report.pdf                        # 本报告 PDF 版
├── presentation.pdf                  # 15 分钟英文 PPT 导出 PDF
├── README.md                         # 复现说明
├── requirements.txt                  # Python 依赖
├── run_experiment.py                 # 一键复现脚本
├── agent_toolkit/                    # Agent 源码（naive + improved）
├── source_code/validator_js/         # 被测对象
├── requirements/                     # 项目需求文档
├── experiment_final_1.md             # 主实验结果
├── experiment_ablation_1.md          # Ablation: with requirement recheck
├── experiment_ablation_2.md          # Ablation: pure suite rewrite
└── old_version_experiments(guests_can_ignore)/  # 历史实验（不影响审阅）
```

最简复现命令（已在 `README.md` 中给出）：

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 安装 validator.js 的 Node 依赖
cd source_code/validator_js && npm install --legacy-peer-deps && cd ../..

# 3. 配置 API Key（写入 agent_toolkit/.env 的 AGENT_API_KEY）

# 4. 一键跑完整实验矩阵（5 函数 × 3 mode × 2 agent）
python run_experiment.py

# 或者单条：
python -m agent_toolkit.cli --approach improved --mode whitebox --validator isURL --analyze-golden
```

## 15. 总结

本项目在真实开源函数库 `validator.js` 上实现并评估了一个 LLM 驱动的测试生成工具，并围绕 `improved agent` 展开了系统性的设计与验证。

最终可以得出以下结论：

1. LLM 的确可以生成真实可执行测试，但测试质量必须用 correctness、coverage、golden overlap 联合评估。
2. `naive agent` 作为 baseline，提供了一个稳定、保守、偏 correctness 的参考上界。
3. `improved agent` 的核心贡献主要来自两部分：更强的 prompt 设计，以及覆盖率驱动的白盒 patch 迭代。
4. `improved whitebox` 是 coverage 与 golden overlap 最强的方案，但 correctness 仍未追平 baseline `naive whitebox`。
5. `improved blackbox` 是一个非常平衡的方案，说明 prompt 增强本身就能显著改善 black-box 测试生成。
6. 对 `improved whitebox` 而言，requirement 复检是错误方向；`suite + patch` 才是更有效的迭代策略。
7. 本方法已经在多个 validator-style functions、多个输入模式和多个设计版本上表现出一定泛化性，但距离更复杂系统级软件测试的全面泛化仍有距离。

上述结论的有效性受 §14 中列出的威胁制约，尤其是"被测对象仅限 validator.js"与"LLM 随机性未做多次平均"两项。在更广泛的 domain 与更严格的统计口径下，具体数值可能波动，但跨版本稳定现象（§12.3 + §9.1/§9.2 的两轮 ablation）为结论方向性提供了较强支撑。§13.3 已诚实讨论"未发现 real-world bugs"的三类原因与未来改进路径（differential testing / property-based / mutation testing），这些改进落地后本报告的方法论结论才会真正具备跨被测对象的普适性。

因此本项目的总体结论不是"AI 已经能够取代人工测试设计"，而是 AI 最适合作为测试设计加速器与覆盖率探索工具，而高可靠测试质量仍然需要更稳健的约束机制，甚至需要人工参与修正。

## 附录 A：代表性生成输出与失败案例分析

本附录给出代表性通过测试组与 5 条典型失败案例的一手证据。

### A.1 代表性通过测试组（每个函数各 1 例）

#### A.1.1 `isEmail`（improved whitebox）

```json
{
  "title": "Baseline email validation",
  "validator": "isEmail",
  "args": [{"require_tld": true, "allow_display_name": false}],
  "valid": ["example@example.com", "user+tag@domain.co.uk"],
  "invalid": ["invalid-email", "user@localhost"],
  "rationale": "Covers the baseline equivalence class: RFC-like local + valid TLD",
  "obligations": ["OB-1"]
}
```

#### A.1.2 `isURL`（improved blackbox）

```json
{
  "title": "Default behavior validation",
  "validator": "isURL",
  "args": [{}],
  "valid": ["http://example.com", "https://example.com/path?q=v#frag"],
  "invalid": ["example.com", "http://"],
  "rationale": "Default options must accept http/https with authority and reject missing scheme/authority",
  "obligations": ["OB-1"]
}
```

#### A.1.3 `isFQDN`（improved whitebox）

```json
{
  "title": "Baseline FQDN validation",
  "validator": "isFQDN",
  "args": [{"require_tld": true}],
  "valid": ["example.com", "sub.domain.com"],
  "invalid": ["example", "-example.com"],
  "rationale": "TLD required; leading hyphen in label is invalid",
  "obligations": ["OB-1", "OB-2"]
}
```

#### A.1.4 `isCurrency`（improved whitebox）

```json
{
  "title": "Default options profile",
  "validator": "isCurrency",
  "args": [{"symbol": "$", "require_symbol": true, "allow_decimal": true}],
  "valid": ["$123.45", "$1,234.56"],
  "invalid": ["123.45", "€123.45"],
  "rationale": "With require_symbol=true, missing or mismatched symbol must be rejected",
  "obligations": ["OB-1"]
}
```

#### A.1.5 `isCreditCard`（improved whitebox）

```json
{
  "title": "Valid credit card numbers without provider",
  "validator": "isCreditCard",
  "args": [{}],
  "valid": ["4111111111111111", "378282246310005"],
  "invalid": ["1234567890123456", "4111-1111-1111-111X"],
  "rationale": "Luhn-valid prefixes accepted; Luhn-invalid and non-digit must be rejected",
  "obligations": ["OB-1", "OB-5"]
}
```

### A.2 失败案例深度分析（5 例）

以下案例均来自归档目录 `agent_toolkit/outputs_final/improved/<validator>/<mode>/failed_cases.json` 的实际执行记录（对应 `experiment_final_1.md` 表中的 improved whitebox / whitebox_code_only / blackbox 各行；每条 case 同时在同目录下 `evaluation_output.json` 的 `details.failed_results` 中留有完整原始 actual 返回值）。每条给出 input / expected / actual / 所属 obligation / 失败类别 / 根因分析。如在新代码上重跑并产生新的 failed_cases.json，结果会写入 `agent_toolkit/outputs/`——具体失败样本可能因 LLM 随机性与当前 5 个函数上的小概率 case 变化而与本附录不完全一致。

#### 案例 1：参数误解（option_misinterpretation）

- **位置**：`isCurrency / improved / whitebox`，group `"Default options profile"`
- **Input**：`"123.45"`
- **Expected**：`false`（LLM 判断为 invalid）
- **Actual**：`true`（真实实现判为 valid）
- **所属 obligation**：`OB-1`
- **失败类别**：**option_misinterpretation**
- **根因**：LLM 误解了 `require_symbol` 与"数字是否必须带符号"之间的关系。LLM 假设该选项置 `false` 就一定要求"无符号 → invalid"，但 validator.js 的 `require_symbol=false` 实际意味着"符号可选"，所以 `"123.45"` 是 valid。这是对选项语义（**可选 vs 必需**）的典型误读。

#### 案例 2：幻觉规约（hallucinated_expected）

- **位置**：`isEmail / improved / whitebox`，group `"Validation for maximum email length"`
- **Input**：`"a@b.com"`
- **Expected**：`false`
- **Actual**：`true`
- **所属 obligation**：`OB-11`（"maximum email length"）
- **失败类别**：**hallucinated_expected**
- **根因**：LLM 凭空产生了一个"最大长度规则"，并据此断言一个 7 字符的合法邮箱为 invalid。真实的 validator.js README 中并没有关于 minimum length 的描述，`OB-11` 本身就是幻觉规约。这是 §13.1.1 幻觉类型的标准样本，也正是 proposed Evidence Grounding 机制要防的。

#### 案例 3：语义漂移（semantic_drift_code_only）

- **位置**：`isEmail / improved / whitebox_code_only`，group `"Domain-specific validation for Gmail"`
- **Input**：`"user@gmail.com"`
- **Expected**：`true`
- **Actual**：`false`
- **所属 obligation**：`OB-13`
- **失败类别**：**semantic_drift_code_only**
- **根因**：在 code-only 模式下，LLM 从代码中看到了 Gmail 专属分支，但没有理解该分支要求用户名必须满足额外长度 / 点号约束。LLM 按"存在分支即放行"的朴素思路判断 valid，实际被真实实现拒绝。这正是 §10.3 所说的"只给代码时模型更容易丢失 requirement 对输入语义的约束"。

#### 案例 4：断言方向反转（boundary_off_by_one / inverted_assertion）

- **位置**：`isURL / improved / blackbox`，group `"Require valid protocol"`
- **Input**：`"ftp://example.com"`
- **args**：`{require_valid_protocol: true, protocols: ['http','https','ftp']}`
- **Expected**：`false`
- **Actual**：`true`
- **所属 obligation**：`OB-5`
- **失败类别**：**inverted_assertion**（断言方向反转）
- **根因**：LLM 已经正确识别了 `protocols` 白名单包含 `ftp`，却仍然把 `ftp://example.com` 断言为 invalid。这是"category 信息正确但 expected 方向反转"的典型样本，反映 LLM 在并列列举多个选项时容易出现心理反转。

#### 案例 5：过度激进（over_aggressive）

- **位置**：`isFQDN / improved / whitebox`，group `"Validation with allow_underscores enabled"`
- **Input**：`"invalid_domain.com"`
- **Expected**：`false`
- **Actual**：`true`
- **所属 obligation**：`OB-3`
- **失败类别**：**over_aggressive**
- **根因**：LLM 把含下划线的域名作为 `allow_underscores=true` 下的 invalid 样例，但这恰恰是该选项设计要放行的情况。LLM 只记住了"下划线在标准 FQDN 中非法"的一般规则，未反思当下选项已经打开允许。这是 §9.3 L4 过度激进在选项层面的体现。

### A.3 失败类别与 §9.3 局限清单的对应

| 失败案例 | 失败类别 | §9.3 局限编号 |
|---|---|---|
| 案例 1（isCurrency） | option_misinterpretation | L2 |
| 案例 2（isEmail max length） | hallucinated_expected | L1 |
| 案例 3（isEmail code-only Gmail） | semantic_drift_code_only | L3 |
| 案例 4（isURL ftp） | inverted_assertion | L1 / L2 混合 |
| 案例 5（isFQDN underscores） | over_aggressive | L4 |

这张映射表说明：§9.3 提出的抽象局限清单，每一条都可以找到具体的失败案例作为支撑；反过来，任何失败案例也都能追溯到清单中的某一条（或组合）。

## 附录 B：本项目使用的主要 Prompt

下面展示本项目中最核心的 prompt 模板。为方便阅读，使用占位符表示动态插入内容。

### B.1 `naive` 系统 Prompt

```text
Generate a conservative first-pass validator.js-style test suite.
Prefer obvious behaviors, obvious edge cases, and small grouped coverage over broad exploration.
Keep the suite intentionally naive: do not optimize for completeness, novelty, or deep branch hunting.

Always return valid JSON only.
JSON schema:
{
  "obligations": [],
  "test_groups": [
    {
      "title": "string",
      "validator": "target validator name",
      "args": [ { } ],
      "valid": ["..."],
      "invalid": ["..."],
      "rationale": "string",
      "obligations": ["OB-1", "OB-2"]
    }
  ]
}

Requirements:
- Group tests by option profile.
- obligations may be an empty list.
- Prefer a small number of clear groups over many speculative groups.
- Prefer common cases and easy-to-justify boundaries.
- Avoid complex combinations unless they are directly implied by the requirement.
- Never repeat the same JSON key within one object.
- Keep the response concise enough to remain valid JSON.
- Do not output markdown.
```

### B.2 `naive blackbox` Prompt

```text
Task: generate black-box tests for {validator_name}.

Read the requirement and directly produce a small first-pass grouped validator.js-style test suite.
Stay conservative and only cover behaviors that are explicit or strongly implied by the requirement.
Do not spend effort extracting formal obligations.
Use an empty obligations list unless there is a very obvious single high-level rule to note.

Black-box guidance:
- prefer common positive and negative examples
- use only a few clearly differentiated groups
- avoid speculative option interactions
- stop at a modest baseline instead of trying to be comprehensive

Requirement specification:
{requirement_spec}
```

### B.3 `naive whitebox` Prompt

```text
Task: generate white-box tests for {validator_name}.

Read the requirement and source code, then directly produce a small first-pass grouped validator.js-style test suite.
Use the source code only to notice obvious branches or guards, not to aggressively chase coverage.
Do not try to build a detailed obligation hierarchy.
Use an empty obligations list unless there is a very obvious single high-level rule to note.

Requirement specification:
{requirement_spec}

Source code:
{source_code}

Output guidance:
- keep the suite modest in size
- each group should focus on one option profile or one branch family
- prefer obvious branches and obvious edge cases over exhaustive exploration
- avoid patch-like additions or coverage-maximizing behavior
- keep the result as a conservative baseline, not an ambitious suite
```

### B.4 `naive whitebox_code_only` Prompt

```text
Task: generate white-box tests for {validator_name} using source code only.

Read the source code and directly produce a small first-pass grouped validator.js-style test suite.
There is no external requirement specification in this mode.
Infer externally visible behavior conservatively from obvious guards, branches, and option handling in the code.
Do not try to build a detailed obligation hierarchy.
Use an empty obligations list unless there is a very obvious single high-level rule to note.

Source code:
{source_code}

Output guidance:
- keep the suite modest in size
- each group should focus on one option profile or one obvious branch family
- prefer obvious branches, guards, and obvious edge cases over exhaustive exploration
- avoid speculative behavioral claims that are not well supported by the code
- keep the result as a conservative baseline, not an ambitious suite
```

### B.5 `improved` 系统 Prompt

```text
You are an expert software testing agent.
You generate high-quality black-box and white-box tests for validator-style functions.
You must reason conservatively, preserve correctness, and improve coverage with small precise patches.

Always return valid JSON only.
JSON schema:
{
  "obligations": [
    {
      "id": "string",
      "kind": "blackbox|whitebox",
      "rule": "string",
      "why": "string",
      "minimal_valid": "string or null",
      "minimal_invalid": "string or null"
    }
  ],
  "test_groups": [
    {
      "title": "string",
      "validator": "target validator name",
      "args": [ { } ],
      "valid": ["..."],
      "invalid": ["..."],
      "rationale": "string",
      "obligations": ["OB-1", "OB-2"]
    }
  ]
}

Requirements:
- Group tests by option profile.
- For broad black-box APIs with many documented options, expand into multiple semantically distinct groups instead of collapsing everything into one default group.
- Keep each group narrow: a group should usually cover one baseline partition family or one closely related option-sensitive behavior.
- Prefer more distinct categories when the requirement clearly documents many switches, constraints, or acceptance/rejection modes.
- Keep patches minimal and avoid redundant duplicates.
- Prefer minimally different cases that flip one rule at a time.
- Never repeat the same JSON key within one object.
- Keep the response concise enough to remain valid JSON.
- Do not output markdown.
```

### B.6 `improved blackbox` Prompt

```text
Task: generate black-box tests for {validator_name}.

Apply standard black-box testing methods aggressively:
- equivalence partitioning
- boundary value analysis
- option-combination testing
- negative-input testing
- special-case and rare-option exploration

Step 1: extract explicit black-box obligations from the requirement.
Step 2: cluster the obligations into semantically distinct black-box categories.
Step 3: expand each category into grouped validator.js-style tests.
Step 4: self-check whether rare options, boundary-adjacent cases, invalid partitions, and documented option flips were skipped.

Requirement specification:
{requirement_spec}

Output guidance:
- first identify the major requirement-visible categories before writing any examples
- keep one coherent option profile or one closely related rule family per group
- do not collapse many unrelated options into one catch-all "default" group
- if the requirement documents many independent switches or acceptance/rejection rules, reflect them in multiple groups
- cover both baseline behavior and option-sensitive deviations
- prefer broad category exploration, but keep each example requirement-grounded and likely correct
- for every option-sensitive group, choose examples whose validity actually changes because of that option profile
- if a documented option effect is only observable together with another option value, configure both so the distinction is real
- do not claim an example is invalid for an option if the requirement text still permits it under the provided args
- prefer paired examples that differ by one rule or one option flip when demonstrating requirement changes
- when a default already allows a behavior, do not present enabling the same behavior as a meaningful new category unless another argument makes the contrast observable
- when uncertain, choose fewer examples inside a group rather than merging unrelated categories
- include multiple concrete valid and invalid examples only when they cover meaningfully different cases
- try to ensure most obligations are represented by at least one dedicated or clearly focused group

Self-audit before finalizing:
- Did you create separate groups for materially different option families instead of one oversized group?
- Did you include default behavior, strictness-raising options, permissive options, whitelist/blacklist style filters, and length-related behavior when documented?
- For each option-focused group, would at least one valid/invalid pair change outcome if that option were flipped back?
- Did you accidentally use examples whose expected result depends on undocumented implementation details rather than the visible requirement?
- Are your expectations aligned with the requirement text rather than guessed from hidden implementation details?
```

### B.7 `improved whitebox` Prompt

```text
Task: generate white-box tests for {validator_name}.

Treat this as requirement-constrained white-box testing.
Use both the intended external behavior and the implementation structure.

Apply standard white-box testing methods aggressively:
- statement coverage
- branch coverage
- condition-oriented reasoning
- early-return triggering
- helper-sensitive path exploration
- requirement-grounded partition checking

Step 1: derive black-box obligations from the requirement.
Step 2: enumerate structural white-box obligations directly from the code.
Step 3: merge overlaps and contradictions.
Step 4: expand them into many grouped validator.js-style tests.
Step 5: self-check whether early returns, helper-dependent checks, option flips, boundary-triggered branches, and requirement-visible edge cases were skipped.

Requirement specification:
{requirement_spec}

Source code:
{source_code}

Output limits:
- each group should focus on one option profile or one branch family
- explore broadly when requirement-visible behavior and source-level branches genuinely justify it
- do not inflate obligations or groups just to reach a target count
- prefer a compact suite that still covers materially different paths and edge cases
```

### B.8 `improved whitebox_code_only` Prompt

```text
Task: generate white-box tests for {validator_name} using source code only.

Treat this as code-only white-box testing.
There is no external requirement specification in this mode.
Use the implementation structure to infer externally visible behavior conservatively.

Apply standard white-box testing methods aggressively:
- statement coverage
- branch coverage
- condition-oriented reasoning
- early-return triggering
- helper-sensitive path exploration
- conservative behavior inference from code-visible contracts

Step 1: enumerate structural white-box obligations directly from the code.
Step 2: infer only well-supported externally visible behaviors from those structures.
Step 3: expand them into grouped validator.js-style tests.
Step 4: self-check whether early returns, helper-dependent checks, option flips, and boundary-triggered branches were skipped.

Source code:
{source_code}

Output limits:
- each group should focus on one option profile or one branch family
- explore broadly when the source code clearly justifies it
- do not inflate obligations or groups just to reach a target count
- prefer a compact suite that still covers materially different paths and edge cases
- do not make speculative claims about undocumented behavior unless the code strongly supports them
```

### B.9 `improved` 白盒迭代 Prompt（最终版）

```text
You are improving an existing {mode} test suite for {validator_name}.
You are given only coverage details and fine-grained uncovered white-box locations.
You must use those uncovered positions as exact white-box targets when updating the suite.
You must NOT use any golden tests, repository test overlap analysis, or external oracle hints.

Goal:
- propose a small patch that helps the current suite target more uncovered code locations
- preserve the current suite unless a new patch is clearly justified by uncovered locations
- keep the patch conservative and additive whenever possible
- keep the suite conservative and low-redundancy

Return strict JSON with top-level keys obligations and test_groups.
The returned test_groups must be patch groups only, not a full rewritten suite.

Black-box requirement source:
{requirement_spec_or_none}

Current full test suite from the previous iteration:
{generated_groups}

Coverage details allowed for improvement:
{evaluation_feedback}

Instructions:
- You must use only the requirement (if provided), the current suite, coverage details, and uncovered details.
- Do not infer or use any correctness signal, pass/fail summary, failed cases, or hidden oracle information.
- Treat uncovered_details as exact white-box targets, not as vague hints.
- Use the previous full suite as the baseline and return only the incremental patch groups.
- Do not rewrite, delete, or duplicate the existing groups already shown in the current suite.
- Add only groups that cover meaningfully new targets beyond the current suite.
- Prefer at most 3 patch groups, each focused on one concrete uncovered condition or path family.
- If an uncovered branch or statement cannot be operationalized from the provided coverage details, do not guess.
- If uncovered_details are provided, use them only as white-box targets.
- If uncovered_details are not provided, do not infer any hidden coverage gap.
- Prefer minimal option-profile-specific groups.
- Avoid broad extrapolation; every meaningful update should correspond to a concrete uncovered position or condition.
- Do not mention or infer any golden test information.
```

### B.10 JSON 修复 Prompt

```text
Repair the following invalid JSON into strict valid JSON.
Keep the same schema with top-level keys obligations and test_groups.
Remove duplicated keys, remove obviously repeated corrupted fragments, and preserve as much valid content as possible.
Return JSON only.

{raw_response}
```

### B.11 Group Completion Prompt

```text
The previous {mode} generation for {validator_name} produced obligations but no usable test_groups.
Using the obligations below, generate non-empty validator.js-style test_groups now.
Return strict JSON with top-level keys obligations and test_groups.
Keep the obligations unchanged unless a tiny correction is necessary.
test_groups must be non-empty.
Each group must contain validator, args, valid, invalid, title, rationale, obligations.

Original task:
{original_prompt}

Existing obligations:
{obligations}
```
