# 项目说明文档

## 概览

- 名称：Analyze（FastAPI + Web 前端）
- 目标：围绕足球/篮球比赛进行数据分析、聊天与在线搜索整合，输出结构化结果
- 组成：后端服务（FastAPI/SQLAlchemy）+ 前端静态页面（Vanilla JS）+ 模型客户端（Volcengine）

## 目录结构

- `server/` 后端 API 与数据库
  - `main.py` 定义 FastAPI 应用与所有接口
  - `db.py` 数据库连接、会话管理（MySQL）
  - `models.py` 三张表：`conversations`、`football_analyses`、`basketball_analyses`
- `controller/` 业务逻辑
  - `chat_controller.py` 聊天与时间线查询
  - `analysis_controller.py` 比赛分析（足球/篮球），持久化结果
  - `search_controller.py` 在线搜索与模型信息提炼
  - `llm_client.py` Volcengine 通用对话客户端
- `web/` 前端静态站点
  - `index.html` 首页；`football.html`/`basketball.html`/`history.html`/`search.html`
  - `assets/` 样式与脚本，其中 `api.js` 为前端 API 客户端、`search.js` 为搜索页逻辑
- `run.py` 作为 uvicorn 的入口模块（动态加载 `server/main.py` 的 `app`）
- `main.py` 命令行入口：`serve` 启动服务；`test-model` 测试模型

## 环境准备

- Python 3.12+
- MySQL 8.x（或兼容版本）
- 虚拟环境建议：`python -m venv .venv && .venv/Script/activate`（Windows）
- 安装依赖：请根据部署环境安装 `fastapi`, `uvicorn`, `sqlalchemy`, `pymysql`, `python-dotenv`, `requests` 等

## 环境变量（`.env`）

- 数据库（二选一）
  - `DATABASE_URL` 如：`mysql+pymysql://user:pass@host:3306/analyze?charset=utf8mb4`
  - 或分散配置：`DB_HOST`/`DB_USER`/`DB_PASSWORD`/`DB_DATABASE`/`DB_PORT`
- 模型（Volcengine / ARK）
  - `VOLC_API_KEY` 或 `ARK_API_KEY`
  - `VOLC_API_BASE` 或 `ARK_API_BASE`（默认为 `https://ark.cn-beijing.volces.com/api/v3`）
  - `VOLC_MODEL` 或 `ARK_MODEL`（如 `ep-xxxx`）
  - `VOLC_TEMPERATURE`、`VOLC_MAX_TOKENS` 可选
- 可选的分析提示覆盖（足球/篮球）
  - `ANALYSIS_PROMPT_FOOTBALL_FILE` / `ANALYSIS_PROMPT_FOOTBALL_TEXT`
  - `ANALYSIS_PROMPT_BASKETBALL_FILE` / `ANALYSIS_PROMPT_BASKETBALL_TEXT`

## 启动后端服务

- 命令：`python main.py serve --host 127.0.0.1 --port 5173`
- 默认无参也会启动服务（端口 5173）；如端口占用，可换 `--port 5174`
- 健康检查：`GET /healthz` → `{"status":"ok"}`

## 前端访问

- 开发模式：直接打开 `http://127.0.0.1:5173/`（或改用 5174）
- 搜索页：`/search.html`；参数 `?mock=0` 强制走后端接口；默认 `api.js` 走后端
- 搜索页脚本：`web/assets/search.js`
  - 解析 `summary` 的 JSON，按“摘要/要点/风险”展示
  - 在“相关网页”区域列出搜索到的标题与链接

## API 文档

- `POST /api/chat`
  - 请求：`{ text, history?: [{role, content}], sessionId?: string }`
  - 响应：`{ reply, createdAt }`
- `GET /api/conversations`
  - 参数：`sessionId? page? pageSize? order?`
  - 返回：时间线列表
- `GET /api/conversation-sessions`
  - 返回：按会话分组的摘要信息
- `POST /api/analyze`
  - 请求：`{ sport: 'football'|'basketball', modelId?: string, temperature?: number, dataText: string }`
  - 响应：结构化分析结果，含持久化标识 `id`
- `GET /api/results`
  - 参数：`sport?`，返回最近分析结果列表
- `GET /api/results/{rid}`
  - 返回：指定分析结果详情
- `POST /api/search`
  - 请求：`{ query: string, temperature?: number }`
  - 响应：`{ ok, query, createdAt, summary, hits }`
    - `hits`: 5–10 条网页 `{ title, url, snippet }`
    - `summary`: JSON 字符串，包含 `summary`（200 字内摘要）、`bullets`（3–8 条关键信息，带来源索引）、`risks`

## 搜索功能说明

- 检索：`controller/search_controller.py:40` 调用 DuckDuckGo/Bing，解析并去重，产出 `hits`
- 正文片段：对前 5 条结果抓取页面正文（去除 HTML），限制 600 字
- 提炼：`search_and_analyze` 构造包含标题/摘要/正文片段的上下文，调用模型生成仅包含 JSON 的结构化结果
- 失败兜底：当模型不可用时返回标题聚合 JSON，前端依旧可展示（不会返回站点入口型列表）
- 来源索引：[1]…[n] 与 `hits` 顺序一致，用于溯源

## 数据库模型

- `conversations`：聊天记录（`session_id`、`role`、`content`、`created_at`）
- `football_analyses`/`basketball_analyses`：分析结果（`query_text`、`result_json`、`created_at`）

## 开发与调试

- 模型连通性测试：`python main.py test-model "你好，我有点焦虑"`
- 常见问题：
  - 端口占用：改 `--port`
  - 数据库未配置：按 `.env` 说明提供 MySQL 连接；支持 `DATABASE_URL`
  - 模型失败：检查 `VOLC_API_KEY`、`VOLC_MODEL`、网关地址；`llm_client.py` 自动在 v3 与 openai/v1 路径间回退

## 安全与合规

- 不要将任何密钥（API Key、数据库密码）提交到仓库
- 前端仅展示后端处理后的信息；实际检索由后端执行，便于统一审计与日志