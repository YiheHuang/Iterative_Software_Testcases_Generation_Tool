# Experiment 7

本轮实验是一次完整的 `10 x 3 x 2 = 60` 组批量实验，覆盖 `validator.js` 中的 10 个函数，并记录 `naive` 与 `improved` 两种 agent 在三种输入模式下的表现与 token 消耗：

- `blackbox`：仅基于 `validator_js/README.md` 中的 requirement 生成测试
- `whitebox`：同时基于 requirement 与 source code 生成测试
- `whitebox_code_only`：仅基于 source code 生成测试，不提供 requirement
- `naive`：单轮生成 + JSON repair/completion
- `improved`：黑盒单轮生成；白盒与纯代码白盒基于执行结果与覆盖率做小规模 patch

说明：

- 本轮实验覆盖 `isEmail`、`isURL`、`isFQDN`、`isIP`、`isAlpha`、`isAlphanumeric`、`isISBN`、`isJSON`、`isMobilePhone`、`isSlug`
- 批量脚本使用 `5` 个 worker 并行运行
- 每条实验最多尝试 `4` 次（首次 + `3` 次重试）
- 所有实验都开启了黄金测试比较
- 本轮开始在 `run_summary.json` 中记录单条实验的 `llm_usage`

## 总体结果

- 共提交 `60` 条实验，最终 `54` 条成功、`6` 条失败
- 总批处理耗时 `849.33s`
- 成功落盘的总 LLM 请求数为 `276`
- 成功落盘的总 token 消耗为 `1,660,339`
- 成功实验的平均 `exact_match_rate` 为 `0.6992`
- 成功实验的平均 `matched_golden_ratio` 为 `0.6481`
- 成功实验中共有 `12` 条达到 `exact_match_rate = 1.0`

需要特别注意的是：上面的 `1,660,339` token 只是**下界**。  
原因是 6 条最终失败的实验都在 `golden_analysis` 阶段异常退出，`run_summary.json` 没有成功写出，因此这 6 条 run 的 `llm_usage` 没被汇总进批量 summary。

## Token 观察

按成功实验统计，token 消耗表现出非常清晰的结构差异：

- 按 mode 平均：
  - `blackbox`：`14288.17`
  - `whitebox`：`47822.94`
  - `whitebox_code_only`：`30129.94`
- 按 approach 平均：
  - `naive`：`13120.93`
  - `improved`：`48373.11`
- 按 approach + mode 平均：
  - `naive blackbox`：`13938.67`
  - `naive whitebox`：`11570.44`
  - `naive whitebox_code_only`：`13853.67`
  - `improved blackbox`：`14637.67`
  - `improved whitebox`：`84075.44`
  - `improved whitebox_code_only`：`46406.22`

其中最昂贵的几条 run 分别是：

- `isURL / improved / whitebox`：`253312`
- `isEmail / improved / whitebox`：`211239`
- `isURL / improved / whitebox_code_only`：`172662`
- `isFQDN / improved / whitebox`：`71509`
- `isEmail / improved / whitebox_code_only`：`65656`

这说明本项目当前的主要成本集中在 `improved` 的白盒迭代链路，尤其是 requirement + code + runtime feedback 同时参与时。

## 完整结果矩阵

| Validator | Agent | Mode | Status | Correct/Total | Exact Match Rate | Matched Golden Ratio | Total Tokens | Attempts | Note |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| isEmail | naive | blackbox | success | 41/43 | 0.9535 | 0.5000 | 16905 | 1 | ok |
| isEmail | naive | whitebox | success | 49/51 | 0.9608 | 0.6667 | 14255 | 1 | ok |
| isEmail | naive | whitebox_code_only | success | 25/25 | 1.0000 | 0.2857 | 43810 | 1 | ok |
| isEmail | improved | blackbox | success | 38/40 | 0.9500 | 0.7857 | 44850 | 1 | ok |
| isEmail | improved | whitebox | success | 36/38 | 0.9474 | 0.5714 | 211239 | 1 | ok |
| isEmail | improved | whitebox_code_only | success | 12/23 | 0.5217 | 0.8571 | 65656 | 1 | ok |
| isURL | naive | blackbox | success | 29/32 | 0.9063 | 0.4000 | 18880 | 1 | ok |
| isURL | naive | whitebox | success | 38/49 | 0.7755 | 0.6000 | 17210 | 1 | ok |
| isURL | naive | whitebox_code_only | success | 36/38 | 0.9474 | 0.5000 | 14695 | 1 | ok |
| isURL | improved | blackbox | success | 34/39 | 0.8718 | 0.8000 | 16907 | 1 | ok |
| isURL | improved | whitebox | success | 44/48 | 0.9167 | 1.0000 | 253312 | 2 | retried x2 |
| isURL | improved | whitebox_code_only | success | 26/30 | 0.8667 | 0.7000 | 172662 | 1 | ok |
| isFQDN | naive | blackbox | success | 34/37 | 0.9189 | 0.8333 | 8607 | 1 | ok |
| isFQDN | naive | whitebox | success | 42/47 | 0.8936 | 0.8333 | 8339 | 1 | ok |
| isFQDN | naive | whitebox_code_only | success | 30/33 | 0.9091 | 0.5000 | 6692 | 1 | ok |
| isFQDN | improved | blackbox | success | 33/36 | 0.9167 | 0.8333 | 8651 | 1 | ok |
| isFQDN | improved | whitebox | success | 45/46 | 0.9783 | 1.0000 | 71509 | 1 | ok |
| isFQDN | improved | whitebox_code_only | success | 13/23 | 0.5652 | 0.8333 | 30331 | 1 | ok |
| isIP | naive | blackbox | success | 30/30 | 1.0000 | 0.0000 | 4566 | 1 | ok |
| isIP | naive | whitebox | success | 48/48 | 1.0000 | 0.0000 | 5916 | 1 | ok |
| isIP | naive | whitebox_code_only | success | 34/34 | 1.0000 | 0.0000 | 5154 | 1 | ok |
| isIP | improved | blackbox | success | 22/22 | 1.0000 | 0.0000 | 5152 | 1 | ok |
| isIP | improved | whitebox | success | 22/23 | 0.9565 | 0.0000 | 33481 | 1 | ok |
| isIP | improved | whitebox_code_only | success | 20/22 | 0.9091 | 0.0000 | 19712 | 1 | ok |
| isAlpha | naive | blackbox | success | 30/41 | 0.7317 | 1.0000 | 31523 | 1 | ok |
| isAlpha | naive | whitebox | success | 0/37 | 0.0000 | 1.0000 | 21843 | 1 | ok |
| isAlpha | naive | whitebox_code_only | success | 0/34 | 0.0000 | 0.7500 | 21045 | 1 | ok |
| isAlpha | improved | blackbox | success | 0/28 | 0.0000 | 0.7500 | 21426 | 1 | ok |
| isAlpha | improved | whitebox | success | 0/28 | 0.0000 | 1.0000 | 54605 | 1 | ok |
| isAlpha | improved | whitebox_code_only | success | 0/17 | 0.0000 | 1.0000 | 35189 | 1 | ok |
| isAlphanumeric | naive | blackbox | success | 0/36 | 0.0000 | 0.6000 | 30472 | 1 | ok |
| isAlphanumeric | naive | whitebox | success | 0/45 | 0.0000 | 1.0000 | 21980 | 1 | ok |
| isAlphanumeric | naive | whitebox_code_only | success | 0/29 | 0.0000 | 0.6000 | 18741 | 1 | ok |
| isAlphanumeric | improved | blackbox | success | 0/22 | 0.0000 | 0.8000 | 19010 | 1 | ok |
| isAlphanumeric | improved | whitebox | success | 0/32 | 0.0000 | 1.0000 | 54190 | 1 | ok |
| isAlphanumeric | improved | whitebox_code_only | success | 0/32 | 0.0000 | 1.0000 | 42383 | 1 | ok |
| isISBN | naive | blackbox | success | 26/31 | 0.8387 | 0.0000 | 4701 | 1 | ok |
| isISBN | naive | whitebox | success | 31/36 | 0.8611 | 0.0000 | 5104 | 1 | ok |
| isISBN | naive | whitebox_code_only | success | 32/40 | 0.8000 | 0.0000 | 6160 | 1 | ok |
| isISBN | improved | blackbox | success | 14/16 | 0.8750 | 0.0000 | 5216 | 1 | ok |
| isISBN | improved | whitebox | success | 8/14 | 0.5714 | 0.0000 | 41792 | 1 | ok |
| isISBN | improved | whitebox_code_only | success | 8/15 | 0.5333 | 0.0000 | 31768 | 1 | ok |
| isJSON | naive | blackbox | success | 47/47 | 1.0000 | 1.0000 | 5773 | 1 | ok |
| isJSON | naive | whitebox | success | 47/47 | 1.0000 | 1.0000 | 5309 | 1 | ok |
| isJSON | naive | whitebox_code_only | success | 38/38 | 1.0000 | 1.0000 | 4722 | 1 | ok |
| isJSON | improved | blackbox | success | 24/26 | 0.9231 | 1.0000 | 5821 | 1 | ok |
| isJSON | improved | whitebox | success | 48/48 | 1.0000 | 1.0000 | 30806 | 1 | ok |
| isJSON | improved | whitebox_code_only | success | 4/6 | 0.6667 | 1.0000 | 15144 | 1 | ok |
| isMobilePhone | naive | blackbox | failed | 39/39 | 1.0000 | N/A | N/A | 4 | golden extraction failed |
| isMobilePhone | naive | whitebox | failed | 0/39 | 0.0000 | N/A | N/A | 4 | golden extraction failed |
| isMobilePhone | naive | whitebox_code_only | failed | 0/29 | 0.0000 | N/A | N/A | 4 | golden extraction failed |
| isMobilePhone | improved | blackbox | failed | 3/23 | 0.1304 | N/A | N/A | 4 | golden extraction failed |
| isMobilePhone | improved | whitebox | failed | 0/16 | 0.0000 | N/A | N/A | 4 | golden extraction failed |
| isMobilePhone | improved | whitebox_code_only | failed | 0/10 | 0.0000 | N/A | N/A | 4 | golden extraction failed |
| isSlug | naive | blackbox | success | 25/27 | 0.9259 | 1.0000 | 4021 | 1 | ok |
| isSlug | naive | whitebox | success | 32/32 | 1.0000 | 1.0000 | 4178 | 1 | ok |
| isSlug | naive | whitebox_code_only | success | 22/24 | 0.9167 | 1.0000 | 3664 | 1 | ok |
| isSlug | improved | blackbox | success | 19/19 | 1.0000 | 1.0000 | 4706 | 1 | ok |
| isSlug | improved | whitebox | success | 21/21 | 1.0000 | 1.0000 | 5745 | 1 | ok |
| isSlug | improved | whitebox_code_only | success | 9/20 | 0.4500 | 1.0000 | 4811 | 1 | ok |

## 结果解读

从整体上看，本轮 10 个函数可以大致分成四类：

1. `稳定强势型`
   - `isJSON` 和 `isSlug` 是最稳定的两组。
   - `isJSON` 几乎全线保持高正确率，其中 `naive` 三种模式都是 `1.0`，`improved whitebox` 也是 `1.0`。
   - `isSlug` 的黑盒/白盒也整体很稳，只有 `improved whitebox_code_only` 明显回落到 `0.45`。

2. `白盒增强有效型`
   - `isURL` 与 `isFQDN` 上，`improved whitebox` 的表现是最有代表性的。
   - `isURL / improved / whitebox` 达到了 `0.9167` 的正确率和 `1.0` 的黄金类别命中，但代价是本轮最高的 `253312` token。
   - `isFQDN / improved / whitebox` 同样表现很强，正确率 `0.9783`，黄金类别命中 `1.0`。

3. `仅代码模式风险较高型`
   - `isEmail`、`isFQDN`、`isISBN`、`isSlug` 在 `whitebox_code_only` 下都有明显不稳定现象。
   - 特别是 `isEmail / improved / whitebox_code_only`，虽然黄金类别命中高达 `0.8571`，但正确率只有 `0.5217`。
   - 这再次说明“只看源码”容易让模型产出在结构上像测试、但在外部语义上并不稳的样例。

4. `语义对齐但执行错误型`
   - `isAlpha` 与 `isAlphanumeric` 是本轮最值得警惕的异常组。
   - 它们很多 run 的 `matched_golden_ratio` 达到了 `0.75` 甚至 `1.0`，但 `exact_match_rate` 却是 `0.0`。
   - 这不是传统意义上的“完全没学到语义”，而是“语义大方向对了，但最终构造出的调用格式不可执行”。

## 异常情况重点分析

### 1. `isMobilePhone` 的 6 条失败不是模型失败，而是黄金测试提取器失败

本轮 6 条永久失败全部集中在 `isMobilePhone`：

- `naive blackbox`
- `naive whitebox`
- `naive whitebox_code_only`
- `improved blackbox`
- `improved whitebox`
- `improved whitebox_code_only`

从 `Experiment_Log.txt` 看，这 6 条 run 的共同报错是：

- `RuntimeError: Golden test extraction failed`
- Node 侧报错为 `ReferenceError: fixture is not defined`

根因并不在 LLM 生成阶段，而在 `validators.test.js` 中 `isMobilePhone` 的黄金测试写法与当前提取器不兼容。  
`isMobilePhone` 的测试不是直接写静态对象字面量，而是在 `fixtures.forEach((fixture) => { ... test({ valid: fixture.valid, invalid: fixture.invalid, args: [fixture.locale] }) })` 这种循环里动态展开的。当前 `extract_golden_tests.js` 能处理很多对象字面量场景，但这里在 `vm` 中单独求值时拿不到外层 `fixture` 绑定，于是直接抛出 `ReferenceError`。

这意味着：

- 这 6 条 run 并不是“实验从头跑挂了”
- 生成阶段和执行评估阶段其实大多已经完成
- 真正失败的是 `--analyze-golden` 这一最后阶段

这一点非常关键，因为它决定了这 6 条结果应被理解为“benchmark infrastructure failure”，而不是“agent generation failure”。

更具体地说：

- `naive / isMobilePhone / blackbox` 的中间评估其实已经做到 `39/39` 全对
- 只是还没来得及写最终 `run_summary.json`，就被黄金提取阶段中断

所以如果只看批量 summary 里的 `failed_runs = 6`，会低估这轮实验里已经成功完成的有效工作量。

### 2. 重试对“随机格式噪声”有效，但对“系统性提取 bug”无效

本轮脚本支持失败后自动重跑，效果可以分成两类：

1. `可恢复异常`
   - 典型例子是 `isURL / improved / whitebox`
   - 第一次尝试因模型返回 JSON 格式损坏而失败
   - 第二次重跑后成功，最终得到 `0.9167` 正确率和 `1.0` 黄金类别命中

2. `不可恢复异常`
   - 典型例子就是 `isMobilePhone`
   - 这类问题不是随机网络波动，也不是一次性模型格式噪声
   - 它是一个稳定可复现的 extractor 兼容性问题，因此 4 次重试全部失败

这说明“自动重试”适合作为对抗 LLM 随机性和偶发格式错误的保险机制，但它不能替代对 benchmark pipeline 本身的修复。

### 3. `isAlpha / isAlphanumeric` 说明“黄金语义命中”不能替代“可执行正确率”

这是本轮最有代表性的非崩溃型异常。

从结果表看，以下几组都出现了“正确率 0，但黄金命中很高”的现象：

- `isAlpha / naive / whitebox`
- `isAlpha / improved / whitebox`
- `isAlpha / improved / whitebox_code_only`
- `isAlphanumeric / naive / whitebox`
- `isAlphanumeric / improved / whitebox`
- `isAlphanumeric / improved / whitebox_code_only`

抽样查看 `failed_cases.json` 后，问题模式很一致：

- 模型生成的组标题和案例语义其实是合理的
- 但 `args` 的组织方式错了
- 最终不是“返回 true/false”，而是运行时直接 `throw Error`

例如：

- `isAlpha` 的失败样例中大量出现 `args: [{}]` 或 `args: [{"locale": "fr-FR"}]`
- `isAlphanumeric` 的失败样例中大量出现 `args: [{"str": "abc123"}]`

这说明模型抓住了“默认行为 / locale 行为 / 严格模式 / 多 locale”等语义类别，因此 category-level 黄金比较仍然会给出高分；但真正执行时，调用接口签名被写坏了，整个 suite 在运行层面几乎全部失效。

因此，本轮一个非常重要的认识是：

- `matched_golden_ratio` 更像“语义类别对齐度”
- `exact_match_rate` 才反映“这些测试能不能真的正确调用目标函数”

在参数接口比较微妙的 validator 上，前者不能替代后者。

### 4. `isIP` 的黄金命中率为 0，不代表测试质量差

`isIP` 是另一个指标层面的异常：

- 多条 `isIP` 实验正确率接近或达到 `1.0`
- 但 `matched_golden_ratio` 始终是 `0.0`

进一步看 `run_summary.json` 会发现，这里的真实原因是：

- `total_golden_categories = 0`
- `total_golden_groups = 0`

也就是说，对 `isIP` 而言，本轮黄金比较阶段根本没有抽取到可比较的黄金类别。  
因此 `matched_golden_ratio = 0.0` 不是“全部没对上”，而是“当前黄金基线为空，指标没有信息量”。

这类情况和 `isMobilePhone` 不一样：  
`isMobilePhone` 是黄金提取直接崩溃；`isIP` 是黄金提取没崩，但最终得到的黄金集合为空。

## 本轮最重要的结论

1. 从系统层面看，当前批量实验链路已经能稳定支撑 `54/60` 条实验成功落盘，并能较好吸收一次性 JSON 格式噪声。
2. 从成本层面看，`improved whitebox` 是最昂贵、但也是最能扩展覆盖与黄金语义命中的路线。
3. 从异常层面看，本轮最大的“硬异常”不是 LLM，而是 benchmark pipeline 本身：
   - `isMobilePhone` 的黄金提取器不兼容
   - `isIP` 的黄金集合为空
4. 从评估层面看，本轮最重要的“软异常”是：
   - 高黄金命中并不保证高运行正确率
   - `isAlpha / isAlphanumeric` 充分说明 category-level semantic overlap 只能衡量“测了什么”，不能保证“怎么调函数”是对的
5. 从 token 统计层面看，当前总 token 已经可以稳定记录成功 run，但对失败 run 仍然缺失，因此批量总消耗目前只能视为下界。

## 结果来源

本文件中的数据主要来自：

- `experiment_10_batch_summary.json`
- `Experiment_Log.txt`
- `agent_toolkit/outputs/*/*/*/run_summary.json`
- 对于 `isMobilePhone` 这 6 条未成功写出 `run_summary.json` 的失败实验，额外参考了：
  - `normalized_generation.json`
  - `evaluation_output.json`
  - `failed_cases.json`
  - `coverage/coverage-summary.json`
