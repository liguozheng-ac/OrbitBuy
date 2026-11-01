# OrbitBuy

跨境电商购物 Agent，基于 AgentScope、FastAPI 和 AG-UI。

提供商品检索与比较、购物需求澄清、订单确认、个人 Skill、长期偏好、会话恢复、自动化任务、模型与 Prompt 管理，以及可复现评测。

商品来自版本化样例目录；订单保存在本地业务账本。尚未接入真实支付、物流或电商供给。此仓库包含 React 前端、Python 后端及必要的部署、样例数据与测试文件；不包含本机桌面程序、定制品牌 LOGO/图标、私人数据、数据库、缓存或运行凭据。通用 UI 图标和商品示意图属于页面运行资源，随前端保留。

## 结构

```text
app/presentation/    FastAPI 接口、AG-UI/SSE、WebSocket
app/application/     Agent、工具、用例、自动化、记忆注入、Harness
app/domain/          商品、订单、偏好、税费、队列的实体与接口
app/infrastructure/  LLM、向量检索、精排、持久化、缓存、限流、监控
scripts/             模型检查、数据生成、评测与维护
tests/               后端测试
frontend/            React + TypeScript + Vite 界面及前端测试
configs/             模型目录配置
knowledge/           品类与跨境购物知识库
data/catalog-*.jsonl  版本化商品样例
eval/                评测集、协议与基线
```

## 本地运行

需要 Python 3.11–3.13、uv、Node.js 22+、npm 和支持工具调用的 OpenAI 兼容模型 API。Windows 可设置 PYTHONUTF8=1，避免系统默认编码影响评测文件读取。

```sh
uv sync --frozen
# 首次运行：从 .env.example 复制为 .env，再在本机填写，已有配置不要覆盖。
uv run uvicorn app.presentation.server:app --host 127.0.0.1 --port 8000
```

至少填写 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`。例如 DeepSeek 使用自己的 API 地址与账户可用模型名；不把凭据写入源码。

访问 `http://127.0.0.1:8000/docs` 查看交互式 API，`/health` 查看依赖健康状态。检索依赖按模式配置：向量检索需提供 Embedding 服务；精排按 `.env.example` 配置。各部署环境都应重新初始化自己的运行数据和 Prompt/模型登记，不复制本机数据库或私有固定版本号。

本地多语种向量服务为可选项：

```sh
uv sync --frozen --extra retrieval
uv run python -m scripts.local_embeddings --port 8001
```

启动前可用 `scripts/model_preflight.py`、`scripts/retrieval_preflight.py` 检查所选服务配置。

## 前端运行

另开终端：

```sh
npm --prefix frontend ci
npm --prefix frontend run dev
```

访问 `http://localhost:5173`；开发服务器将 `/commerce` 请求代理到本机 8000 端口。界面支持中文、日文、英文。

## Docker 全栈编排

```sh
docker compose --env-file .env -f docker/docker-compose.yaml up -d --build
```

包含前端、API、任务 worker、Redis 和 Qdrant。前端默认端口 5173，API 端口 8000。仍需配置可用的 LLM、Embedding 和精排服务。`app.automation_worker` 可按自动化部署需求独立运行。

## 测试与评测

```sh
uv run pytest -q
npm --prefix frontend test
npm --prefix frontend run build
uv run python -m scripts.eval.harness run --profile contracts --output eval/verification/local-contracts
uv run python -m scripts.eval.harness run --profile smoke --output eval/verification/local-smoke
uv run python -m scripts.eval.harness verify eval/verification/local-smoke
```

真实模型评测会消耗 API 配额，需配置自己的凭据；默认不自动在每次推送时发起付费评测。不要把单测通过等同于生产性能或真实购物效果验收。

内部部分 `globex` 配置键、文件名和存储命名保留兼容，产品对外名称为 OrbitBuy。不要直接批量替换已使用的数据库和 Prompt 标识。

## 仓库可见性

初始为私有仓库，不自动邀请协作者、不配置公开部署。面试展示时可由仓库所有者改为公开，之后改回私有；公开期间的下载和公开 fork 无法收回。
