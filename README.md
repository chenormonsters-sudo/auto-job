# Resume Job Workbench

免费、本地优先、个人自用的国内多平台求职工作台。

## 当前进度

- 后端：FastAPI + SQLite，已实现简历上传、JD 管理、匹配评分、投递包生成、确认队列、dry-run。
- 前端：Next.js 工作台，已实现简历、职位、审查、投递、平台账号五个页面。
- 平台适配：Boss直聘、猎聘、智联、前程无忧已接入 Playwright 浏览器层骨架，支持扫码登录窗口、用户目录/Cookie 登录态和试运行。
- 安全约束：投递最小间隔默认 40 秒，可调大到 60 秒；试运行不真实投递；指纹伪装配置预留；云端 AI 调用前需用户显式确认。
- 简历解析：DOCX 支持文本框内容提取，并自动去重 Choice/Fallback 导致的重复段落。

## 目录

```text
resume-job-workbench/
  backend/       FastAPI 后端
  frontend/      Next.js 前端
  prompts/       AI 提示词模板
  data/          本地数据（SQLite、上传文件）
  docker-compose.yml
```

## 本地启动

后端：

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

前端：

```powershell
cd frontend
npm run dev
```

打开 http://localhost:3000 。

## 环境变量

复制 `backend/.env.example` 为 `backend/.env` 并填写：

```text
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=deepseek-chat
MIN_DELIVERY_INTERVAL_SECONDS=40
FINGERPRINT_SPOOFING_ENABLED=false
BROWSER_HEADLESS=true
```

本地 Ollama 只需设置 `LLM_BASE_URL=http://127.0.0.1:11434/v1`。

浏览器投递依赖 Python Playwright，并复用本机 Chrome：

```powershell
python -m pip install playwright
```

## 主要 API

- `POST /api/resumes/upload` 上传简历
- `POST /api/resumes/{id}/confirm` 标记最终确认版
- `POST /api/reviews/resumes/{id}` AI 审查简历
- `POST /api/jobs` 创建职位/JD
- `POST /api/jobs/{id}/match` 计算匹配分
- `POST /api/jobs/{id}/packet` 生成打招呼语并创建投递项（需 `allow_llm=true`）
- `POST /api/applications/select` 勾选确认投递项
- `POST /api/deliveries/dry-run` 试运行
- `POST /api/deliveries/confirm` 二次确认后真实投递
- `GET/PUT/DELETE /api/platforms/{platform}/account` 平台账号配置
- `POST /api/platforms/{platform}/qr-login` 打开扫码登录窗口
- `GET /api/platforms/{platform}/qr-status` 查询扫码登录状态

## 安全边界

- 只做浏览器层 Playwright 页面交互，不做接口逆向和抓包。
- 投递间隔默认 40 秒，只能调大，不能低于该值；建议控制在 40-60 秒。
- 试运行不产生真实打招呼/简历投递。
- 指纹伪装默认关闭，可在投递页一键切换；开启时 UI 必须提示账号受限风险。
- 简历文本、投递包快照、平台 Cookie 使用 Fernet 加密存储，密钥不离开本机。
