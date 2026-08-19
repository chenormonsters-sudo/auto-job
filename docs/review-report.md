# 本地求职工作台审查报告

审查日期：2026-08-20
审查方式：静态代码审查 + FastAPI 接口实测 + Playwright 页面模拟
审查范围：后端 FastAPI、前端 Next.js、投递流程、安全与验收清单

## 严重级别说明

- P0：会丢失数据、泄露密钥/PII、或导致核心流程不可用
- P1：明显功能错误或安全风险，必须优先修复
- P2：影响使用体验、验收不满足，应尽快修复
- P3：体验细节、可延后

## 一、代码逻辑 Bug

### BUG-01 [P1] 简历上传无大小限制、无内容校验

- 文件：`backend/app/api/resumes.py:17-24`
- 复现：上传任意大小或伪造扩展名文件
- 预期：限制大小、校验文件真实类型、超出返回 4xx
- 实际：`await file.read()` 无上限写入磁盘，仅检查扩展名

### BUG-02 [P1] 非法平台导致 dry-run 500

- 文件：`backend/app/api/jobs.py:13-25`、`backend/app/services/delivery_queue.py:58`
- 复现：创建 `platform="unknown"` 职位，生成投递包后执行 dry-run
- 预期：返回 400/422 并提示平台不支持
- 实际：`get_adapter()` 抛 KeyError，接口返回 500

### BUG-03 [P1] 空投递列表不报错

- 文件：`backend/app/api/deliveries.py:36-48`、`backend/app/services/delivery_queue.py:48-68`
- 复现：`application_ids=[]` 调用 dry-run
- 预期：返回 400 并提示至少选择一项
- 实际：返回 200 且 `results=[]`

### BUG-04 [P1] 投递限流没有按条执行

- 文件：`backend/app/services/delivery_queue.py:16-29,71-117`
- 复现：批量确认多个投递项
- 预期：每两条之间至少间隔 `MIN_DELIVERY_INTERVAL_SECONDS`
- 实际：只在一开始 sleep 一次，之后循环连续执行，无法满足验收清单第 11 条

### BUG-05 [P2] Adapter 返回失败仍标记“已投递”

- 文件：`backend/app/services/delivery_queue.py:92-103`
- 复现：adapter 返回 `{"ok": false}` 或失败状态
- 预期：按结果标记失败
- 实际：只有 `NotImplementedError` 被捕获，其余一律标记 `delivered`

### BUG-06 [P2] LLM 失败被静默吞掉

- 文件：`backend/app/services/greeting_generator.py:13-18`
- 复现：API Key 错误或网络失败
- 预期：接口明确报错
- 实际：静默返回固定模板，用户不知道 AI 失败

### BUG-07 [P2] 投递包响应缺少 application id

- 文件：`backend/app/api/jobs.py:63-68`、`backend/app/schemas.py`
- 复现：前端生成投递包后无法直接拿到投递项 ID
- 预期：返回 `application_id`
- 实际：只返回 job/resume/greeting

### BUG-08 [P2] 投递任务创建时机与日志不完整

- 文件：`backend/app/api/deliveries.py:50-66`、`backend/app/services/delivery_queue.py:32-45`
- 复现：真实投递执行后才创建 DeliveryTask，且 logs 始终为空
- 预期：任务先落库，执行过程写入日志
- 实际：执行失败时无任务记录，审计缺失

### BUG-09 [P3] 真实投递同步 sleep 阻塞事件循环

- 文件：`backend/app/services/delivery_queue.py:71-117`
- 复现：批量真实投递多条时请求其他 API
- 预期：间隔等待不阻塞其他请求，或放入后台任务
- 实际：`time.sleep(minimum)` 在请求线程内同步执行，单用户本地使用可接受，但接口响应会被拖住

## 二、安全风险

### SEC-01 [P1] 简历/Cookie 等敏感数据未加密存储

- 文件：`backend/app/models.py`、`backend/app/config.py`
- 影响：SQLite 中简历文本、未来 Cookie 均为明文，违反验收清单第 10 条
- 预期：敏感字段加密，密钥本机保存，密钥丢失不可解密
- 实际：当前无任何加密层

### SEC-02 [P1] 云 LLM 会接收完整简历文本

- 文件：`backend/app/services/resume_reviewer.py`、`greeting_generator.py`
- 影响：DeepSeek 等云端会收到姓名、电话、经历等 PII
- 预期：接入云 LLM 前脱敏，或用户显式确认
- 实际：直接把 `raw_text` 截断后发送

### SEC-03 [P2] FastAPI 缺少生产安全基线

- 文件：`backend/app/main.py:10-18`
- 影响：默认开放 `/docs`、无 TrustedHost、无安全响应头
- 预期：生产环境关闭文档、启用 TrustedHost/安全头
- 实际：本地开发可用，但验收未覆盖

### SEC-04 [P2] 前端无 CSP/安全响应头

- 文件：`frontend/next.config.mjs`
- 影响：缺少 XSS 纵深防御
- 预期：至少设置基础安全头
- 实际：无

### SEC-05 [P2] 接口错误会把服务端细节直接返回前端

- 文件：`frontend/lib/api.ts`
- 影响：500 原始响应可能泄露内部信息
- 预期：统一错误提示，细节只进日志
- 实际：直接 `throw new Error(text)`

### SEC-06 [P3] API Key 明文保存在 `.env`

- 文件：`backend/.env`
- 说明：本地单用户可接受，但必须确保永不提交、不打印、不进入日志
- 实际：当前 `.gitignore` 已忽略 `.env`

### SEC-07 [P1] 投递包中的简历快照明文存储

- 文件：`backend/app/api/jobs.py:61-70`、`backend/app/models.py:43`
- 影响：生成投递包后 `Application.resume_version` 以明文写入 SQLite，绕过简历加密
- 预期：与 `Resume.raw_text` 一致使用 Fernet 加密，接口返回时再解密
- 实际：仅 `Resume.raw_text` 加密，`resume_version` 仍明文

## 三、交互 / UI 缺陷

### UI-01 [P1] 子页面没有导航

- 文件：`frontend/app/resumes/page.tsx`、`jobs/page.tsx`、`review/page.tsx`、`delivery/page.tsx`
- 复现：打开 `/jobs` 后无法返回首页或切换到其他页面
- 预期：所有页面统一导航
- 实际：只有首页有导航

### UI-02 [P2] 无加载态

- 文件：所有前端页面
- 复现：首次进入 `/jobs` 时先出现空内容，随后才出现数据
- 预期：显示 loading
- 实际：无任何 loading

### UI-03 [P2] 无空状态

- 文件：`frontend/app/delivery/page.tsx`、`jobs/page.tsx`
- 复现：没有投递项/职位时页面空白
- 预期：显示引导文案
- 实际：空白

### UI-04 [P2] 无禁用态与表单校验

- 文件：`frontend/app/jobs/page.tsx:20-24`、`frontend/app/delivery/page.tsx:31-45`
- 复现：空 JD 可创建职位；未勾选可 dry-run
- 预期：必填校验、按钮禁用
- 实际：均可执行且返回成功

### UI-05 [P2] 关键操作缺少错误捕获

- 文件：`frontend/app/jobs/page.tsx`、`review/page.tsx`、`delivery/page.tsx`
- 复现：接口失败时页面无提示，控制台出现未捕获 Promise
- 预期：统一错误提示
- 实际：多数函数没有 try/catch

### UI-06 [P2] 真实投递没有二次确认弹窗

- 文件：`frontend/app/delivery/page.tsx:39-45`
- 复现：点击“确认投递”立即调用接口
- 预期：弹窗展示数量并二次确认
- 实际：无确认弹窗

### UI-07 [P2] 缺少导出与速率展示

- 文件：`frontend/app/delivery/page.tsx`
- 预期：导出投递包/记录，展示当前投递速率
- 实际：均无

### UI-08 [P2] 缺少风控风险提示

- 文件：`frontend/app/delivery/page.tsx`
- 预期：启动/投递前提示自动化账号受限风险、指纹伪装状态
- 实际：无

### UI-09 [P3] favicon 404

- 复现：浏览器请求 `/favicon.ico`
- 实际：404

## 四、业务流程 / 验收清单不满足

### ACC-01 [P1] 平台登录与真实投递未实现

- 验收 5/6：当前平台 Adapter 均为 stub，真实投递返回 NotImplementedError

### ACC-02 [P1] 敏感数据加密未实现

- 验收 10：见 SEC-01

### ACC-03 [P2] 限流未按条执行、无界面展示

- 验收 11：见 BUG-04

### ACC-04 [P2] 指纹伪装与风险提示未实现

- 验收 12：无 UI 开关和提示

### ACC-05 [P2] 投递包导出/记录导出未实现

- 验收 7/8：无导出按钮

### ACC-06 [P2] 页面缺少“生成投递包”入口

- 文件：`frontend/app/jobs/page.tsx`
- 复现：用户无法在界面从职位生成投递包，只能通过 API
- 预期：职位列表提供“生成投递包”操作

## 五、优先行动清单

### 必须优先修复

1. BUG-01 上传大小/内容限制
2. BUG-02 非法平台 500
3. BUG-03 空投递列表 400
4. BUG-04 按条限流
5. SEC-01 敏感数据加密
6. SEC-02 云 LLM 脱敏/用户确认
7. UI-01 子页面导航

### 体验优化

1. UI-02/03/04/05 loading、空状态、校验、错误提示
2. UI-06 二次确认弹窗
3. UI-07 导出与速率展示
4. UI-08 风控提示

### 可延后

1. SEC-06 密钥轮换策略
2. BUG-09 真实投递等待改后台任务
3. 平台真实投递选择器与真实账号回归验证

## 六、修复进度

### 已修复

- BUG-01：上传增加 10MB 限制和 PDF/DOCX 内容头校验
- BUG-02：平台白名单校验，非法平台返回 422
- BUG-03：空投递列表返回 400
- BUG-04：真实投递按条间隔 `>= 20 秒`
- BUG-05：Adapter 返回失败时不再标记已投递
- BUG-06：LLM 失败不再静默回退，接口返回明确错误
- BUG-07：投递包响应新增 `application_id`
- BUG-08：投递任务先落库，执行后写入日志与结果状态
- SEC-01：新增本地 Fernet 加密，新上传简历加密存储
- SEC-03：后端补充安全响应头
- SEC-04：Next.js 增加基础安全响应头
- SEC-05：前端接口错误统一脱敏，不再透传原始响应
- SEC-07：`Application.resume_version` 使用 Fernet 加密存储，接口返回明文快照
- SEC-02：审查/生成打招呼语前增加云端 AI 显式确认开关
- ACC-01：平台账号配置页与 API，Cookie 加密存储；扫码登录窗口会打开本机 Chrome，关闭后保存浏览器用户目录；Playwright 浏览器层试运行/真实投递骨架已可用
- ACC-02：平台 Cookie 使用 Fernet 加密存储，接口不回显 Cookie
- ACC-04：投递页增加指纹伪装开关，开启后注入基础浏览器指纹伪装
- UI-01：所有子页面统一导航
- UI-02/03/04/05：loading、空状态、校验、错误提示
- UI-06：真实投递增加二次确认弹窗
- UI-07：投递速率展示与 CSV 导出
- UI-08：风控风险提示
- UI-09：新增 `icon.svg`，favicon 404 已修复
- ACC-06：职位页新增“生成投递包”入口
- 其他：Next 16 `allowedDevOrigins`、CORS 增加 `127.0.0.1:3000`

### 待后续修复

- 各平台真实投递选择器、扫码登录后的登录态与真实账号回归验证
- 指纹伪装基础注入已实现，仍需真实平台回归验证
- OpenAPI 文档关闭策略、TrustedHost
- BUG-09：真实投递等待改后台任务/异步执行
