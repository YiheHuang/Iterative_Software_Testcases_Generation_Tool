# LLM-Driven Validator Test Generation

本仓库的 `README` 只保留最基本的复现实验说明。更完整的项目说明、实验分析与结论见 `report.md`。

## 1. 环境准备

建议环境：

- Python `3.11+`
- Node.js `18+`

先在仓库根目录安装 Python 依赖：

```bash
pip install -r requirements.txt
```

再安装 `validator.js` 的 Node 依赖：

```bash
cd source_code/validator_js
npm install --legacy-peer-deps
cd ../..
```

## 2. 配置 LLM API

在 `agent_toolkit/.env` 中至少配置：

```env
AGENT_API_KEY=your_key_here
AGENT_API_URL=https://yunwu.ai/v1/chat/completions
AGENT_MODEL=gpt-4o
```

## 3. 运行单条实验

统一入口：

```bash
python -m agent_toolkit.cli --approach <naive|improved> --mode <blackbox|whitebox|whitebox_code_only> --validator <function_name> --analyze-golden
```

参数说明：

- `--approach`：`naive` 或 `improved`
- `--mode`：`blackbox`、`whitebox` 或 `whitebox_code_only`
- `--validator`：例如 `isEmail`
- `--analyze-golden`：执行黄金测试对比

示例：

```bash
python -m agent_toolkit.cli --approach naive --mode blackbox --validator isEmail --analyze-golden
python -m agent_toolkit.cli --approach improved --mode whitebox --validator isURL --analyze-golden
python -m agent_toolkit.cli --approach improved --mode whitebox_code_only --validator isFQDN --analyze-golden
```

## 4. 批量运行最终 5 函数实验

默认批量脚本会运行最终实验使用的 5 个函数：

- `isEmail`
- `isURL`
- `isFQDN`
- `isCurrency`
- `isCreditCard`

脚本会默认执行：

- `2` 个 agent：`naive`、`improved`
- `3` 个 mode：`blackbox`、`whitebox`、`whitebox_code_only`
- 总计 `30` 条实验
- 并行数默认 `5`
- 失败自动重试，默认 `3` 次

直接运行：

```bash
python run_experiment.py
```

常用写法：

```bash
python run_experiment.py --workers 5 --max-retries 3
python run_experiment.py --validators isEmail isURL
python run_experiment.py --skip-golden
```

## 5. 结果位置

单条实验输出默认写到：

```text
agent_toolkit/outputs/<approach>/<validator>/<mode>/
```

最常看的文件是：

- `run_summary.json`
- `coverage/coverage-summary.json`
- `golden_comparison.json`

实验分析可参考仓库中的 `experiment_*.md` 与 `report.md`。
