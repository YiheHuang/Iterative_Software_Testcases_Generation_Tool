# LLM-Driven Validator Test Generation

这是一个面向 `validator.js` 的自动化测试生成项目。项目的核心目标，是让大模型像一个“测试 Agent”一样，针对指定校验函数自动生成测试用例、真实执行这些用例、收集覆盖率，并将生成结果与源码仓库中的黄金测试进行语义级比较。

当前项目重点对比两类 Agent：

- `naive`：单轮生成，尽量保守，作为基线方法
- `improved`：在基线之上增强 prompt、引入运行反馈，并在白盒模式下做覆盖率驱动的小规模迭代

项目目前已经支持至少以下函数的实验：

- `isEmail`
- `isFQDN`
- `isURL`

## 这个项目在做什么

传统测试生成往往只做“生成一批测试然后结束”。这个项目希望把过程做得更完整一些：

1. 给 Agent 一个目标函数名，例如 `isEmail`
2. Agent 自动读取 requirement 与源码上下文
3. Agent 生成结构化的测试组
4. 项目把这些测试转成可执行格式并在真实 `validator.js` 代码上运行
5. 收集正确率、失败样例、覆盖率
6. 将生成测试与 `validators.test.js` 中抽取出的黄金测试做语义比较
7. 输出一组可分析的实验结果

换句话说，这不是“只让 LLM 编一点测试代码”，而是一个围绕测试生成、执行、评估、比较搭起来的完整实验框架。

## 项目逻辑

### 1. 输入

一次运行的最小输入通常只有三个维度：

- `--validator`：目标函数名，例如 `isEmail`
- `--mode`：`blackbox` 或 `whitebox`
- `--approach`：`naive` 或 `improved`

其中：

- `blackbox`：只基于 `validator_js/README.md` 中的 requirement 生成测试
- `whitebox`：同时基于 requirement 与 source code 生成测试

这里的 `whitebox` 不是早期那种“只给源码”的定义，而是“需求约束下的白盒测试”。

### 2. 上下文构造

运行时，系统会自动解析目标函数对应的两类上下文：

- requirement：来自 `validator.js` README 中该函数的文档描述
- source code：来自 `source_code/validator_js/src/lib/` 中对应实现

黑盒只看第一类，白盒两类都看。

### 3. Agent 生成

Agent 输出统一 JSON 结构，核心包括两部分：

- `obligations`：它认为应该覆盖的测试义务/规则
- `test_groups`：分组后的测试样例

每个 `test_group` 都是 `validator.js` 风格的结构化测试组，通常包含：

- 组标题
- validator 名称
- 参数 `args`
- `valid` 样例
- `invalid` 样例
- `error` 样例
- 组的 rationale

### 4. 执行与评估

生成完成后，系统会自动：

- 把测试组写入执行输入
- 在真实的 `validator.js` 实现上执行
- 记录每个 case 的实际结果
- 输出正确率相关指标
- 使用 `nyc` 收集覆盖率

目前覆盖率会记录四类主指标：

- `Lines`
- `Statements`
- `Functions`
- `Branches`

同时，项目还会生成带语义描述的覆盖缺口信息，帮助后续白盒补测更贴近真实代码位置。

### 5. 黄金测试比较

项目把 `validator.js` 仓库中的黄金测试视为“参考答案”，但只用于评估，不参与生成反馈。

当前黄金分析采用的是更稳定的双向 category-level 机制：

1. 从 `validators.test.js` 中抽取黄金测试组
2. 将黄金测试组固定分类，形成稳定的 `golden categories`
3. 对 Agent 生成结果按语义聚成 `generated categories`
4. 做双向语义匹配
5. 由程序计算最终汇总指标

这样做的原因是，早期直接让 LLM 输出 overlap/missing 等数字会不稳定。现在的设计把“分类与匹配”交给 LLM，把“统计汇总”交给程序，因而能保证关键量更一致，比如：

- `overlap_golden_categories + missing_golden_categories = total_golden_categories`

## 两个 Agent 的区别

### `naive` Agent

`naive` 是项目里的基线方法，特点是：

- 单轮生成
- 生成失败时会做 JSON repair / completion
- 不做基于运行结果的多轮自我修正
- Prompt 更简单，推理负担更低

它的意义不是“最强”，而是提供一个更朴素、更容易比较的起点。

### `improved` Agent

`improved` 是当前的增强版方法，主要改动有：

- 更强调测试类别展开和义务提取
- 黑盒 prompt 更强调 requirement-visible 分类扩展
- 白盒 prompt 同时利用 requirement 与源码结构
- 白盒模式会根据真实覆盖率做小规模 patch 迭代
- 只接受覆盖率严格变好的 patch
- 连续回退达到阈值后停止，避免越修越差

目前的设计原则是：

- 黑盒不使用覆盖率反馈
- 黄金测试结果绝不反馈给生成过程
- 白盒只根据真实执行结果与覆盖率缺口迭代

## 目前的创新点

这个项目目前比较有价值的部分主要在下面几点。

### 1. 把“测试生成”做成了完整闭环

不是只生成文本，而是形成了：

- 生成
- 执行
- 覆盖率收集
- 黄金测试比较
- 结果归档

这使得 Agent 的好坏可以被真实度量，而不是只看 prompt 输出是否“像测试”。

### 2. `naive` / `improved` 双路线对比

项目没有把所有改进都堆在一个 Agent 上，而是明确保留了两个相互独立的包：

- `agent_toolkit/naive_agent`
- `agent_toolkit/improved_agent`

这使得实验对比更干净，也更适合课程项目或论文式报告。

### 3. requirement-constrained whitebox

当前白盒不是“只看代码瞎补路径”，而是同时要求：

- 从 requirement 出发保持语义正确
- 从 source code 出发补路径和分支

这比纯路径覆盖更贴近真实测试设计。

### 4. 语义化覆盖缺口

覆盖率输出不只给一个数字，还会尽量把缺失位置描述成更可读的语义缺口，例如：

- 哪一段条件未覆盖
- 哪个分支侧没有被触发
- 哪类 early return 没被命中

这对后续做 whitebox patch 很重要。

### 5. 稳定化的黄金测试评估

当前黄金分析不再直接依赖 LLM 随机输出总结数字，而是：

- 固定黄金分类
- 运行时生成生成分类
- 双向匹配
- 程序聚合 summary

这显著提高了实验统计口径的一致性。

## 当前效果如何

以最新的 `experiment_4.md` 为代表，目前可以看到几个比较明确的现象。

### `isEmail`

- `naive` 在 `isEmail` 上非常稳，黑盒和白盒正确率都较高
- `improved whitebox` 明显提高了覆盖率和黄金类别命中
- 这说明 `improved` 在 `isEmail` 上更像“扩大探索范围”，但不总能保持和 `naive` 一样保守

### `isFQDN`

- `improved` 在 `isFQDN` 上表现较好
- 黑盒和白盒都达到了 `6/6` 的黄金类别命中
- 白盒覆盖率也高于 `naive`

这是当前 `improved` 表现最稳定的一类函数。

### `isURL`

- `isURL` 是当前最难的函数之一，因为选项多、组合多、边界多
- 早期 `improved blackbox` 曾出现塌缩成单个测试组的问题
- 在最新 prompt 调整后，这个问题已经明显缓解，`improved blackbox` 的测试组数、覆盖率、黄金类别命中都恢复到了更合理区间
- 但 `isURL` 的正确率仍然不算特别稳，说明“多发散”和“贴需求”之间还需要进一步平衡

### 总体判断

当前项目已经能够比较清楚地复现一个常见现象：

- `naive` 更保守，局部函数上正确率更稳
- `improved` 更激进，更擅长扩大测试范围、提升覆盖率和黄金命中
- 但更激进也更容易在复杂函数上引入错误预期

因此，这个项目现在最有意思的地方，不是“谁绝对更强”，而是它比较清楚地展示了：

- 覆盖率驱动的 Agent 为什么会更激进
- 为什么更高覆盖率不一定等于更高正确率
- 如何用实验把这种 trade-off 量化出来

## 目录结构

核心目录可以这样理解：

```text
.
├─ agent_toolkit/
│  ├─ cli.py
│  ├─ .env
│  ├─ naive_agent/
│  ├─ improved_agent/
│  └─ outputs/
├─ source_code/
│  └─ validator_js/
├─ experiment_1.md
├─ experiment_2.md
├─ experiment_3.md
└─ experiment_4.md
```

其中：

- `agent_toolkit/cli.py`：统一命令入口
- `agent_toolkit/naive_agent/`：基线 Agent
- `agent_toolkit/improved_agent/`：增强 Agent
- `agent_toolkit/outputs/`：所有实验输出
- `source_code/validator_js/`：被测源码与原始测试仓库
- `experiment_*.md`：阶段性实验结果总结

## 输出目录里有什么

单次运行的主要输出目录形如：

`agent_toolkit/outputs/<approach>/<validator>/<mode>/`

例如：

`agent_toolkit/outputs/improved/isURL/blackbox/`

该目录下通常会看到：

- `prompt.txt`
- `response.json`
- `normalized_generation.json`
- `evaluation_output.json`
- `coverage/coverage-summary.json`
- `golden_comparison.json`
- `run_summary.json`

另外，固定黄金分类会缓存到：

`agent_toolkit/outputs/golden/<validator>/`

## 环境配置

### Python

当前 Python 侧只使用标准库，没有额外第三方依赖。为了便于统一安装入口，仓库根目录提供了 `requirements.txt`。

建议使用 Python 3.11 及以上版本。

### Node.js

测试执行依赖 `validator.js` 仓库自己的开发依赖，包括：

- `mocha`
- `nyc`
- `@babel/register`

因此第一次运行前，需要先安装 `source_code/validator_js` 下的 Node 依赖。

### LLM API

当前默认从 `agent_toolkit/.env` 读取配置。常用字段如下：

```env
AGENT_API_URL=https://yunwu.ai/v1/chat/completions
AGENT_API_KEY=your_key_here
AGENT_MODEL=gpt-4o
```

如果没有配置 `AGENT_API_URL` 和 `AGENT_MODEL`，系统会分别默认使用：

- API URL: `https://yunwu.ai/v1/chat/completions`
- Model: `gpt-4o`

## 如何安装

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 Node.js 依赖

```bash
cd source_code/validator_js
npm install
```

### 3. 配置 `agent_toolkit/.env`

```env
AGENT_API_KEY=your_key_here
AGENT_API_URL=https://yunwu.ai/v1/chat/completions
AGENT_MODEL=gpt-4o
```

## 如何运行实验

统一入口是：

```bash
python -m agent_toolkit.cli --approach <naive|improved> --mode <blackbox|whitebox> --validator <function_name> --analyze-golden
```

例如：

```bash
python -m agent_toolkit.cli --approach naive --mode blackbox --validator isEmail --analyze-golden
python -m agent_toolkit.cli --approach improved --mode whitebox --validator isURL --analyze-golden
```

常用参数说明：

- `--approach`：`naive` 或 `improved`
- `--mode`：`blackbox` 或 `whitebox`
- `--validator`：目标函数，例如 `isEmail`
- `--analyze-golden`：开启黄金测试比较
- `--skip-eval`：只生成，不执行
- `--timeout-seconds`：设置 LLM 请求超时

## 如何复现实验表

如果你希望自己重跑一组实验，最简单的方式是按函数分别运行 4 条命令：

```bash
python -m agent_toolkit.cli --approach naive --mode blackbox --validator isEmail --analyze-golden
python -m agent_toolkit.cli --approach naive --mode whitebox --validator isEmail --analyze-golden
python -m agent_toolkit.cli --approach improved --mode blackbox --validator isEmail --analyze-golden
python -m agent_toolkit.cli --approach improved --mode whitebox --validator isEmail --analyze-golden
```

如果使用的中转 API 对频率比较敏感，建议像 `experiment_4.md` 那样分批运行，例如每次只跑 3 组，再继续下一批。

## 当前局限

项目已经能稳定产出有分析价值的结果，但还有一些明显局限：

- `improved` 的黑盒扩展能力和需求贴合度仍然需要继续平衡
- `isURL` 这类高选项复杂度函数仍然容易出现误判
- 白盒迭代当前只使用覆盖率反馈，没有更细粒度的自动“失败归因修正”
- 黄金分析虽然已经比早期稳定，但仍然包含 LLM 参与的语义分类和匹配过程

## 适合怎样理解这个项目

如果把这个项目当成一个课程实验或研究原型来看，它回答的是这样一个问题：

“在软件测试任务中，LLM 到底能不能不仅生成测试，还能被放进一个真实评估闭环里，比较不同 Agent 策略的优劣？”

当前答案是：可以，而且已经能看出比较清晰的趋势。

这个仓库最有价值的地方，不只是生成了一些测试，而是已经具备了：

- 可复现的运行方式
- 明确的基线与增强版对比
- 稳定化的黄金评估口径
- 能够支持继续迭代的实验基础设施
