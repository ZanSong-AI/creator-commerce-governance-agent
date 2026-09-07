# Creator Commerce Governance Agent 开发日志

这份文件只追加公开、安全、可复用的实施记录。私人求职判断、个人资料和内部材料不进入本文件。

## 2026-08-24 — Week 1 / Session 1：项目边界与全栈骨架

### 本次目标

在实现任何法规抽取或媒体 Agent 之前，先建立独立仓库、服务边界、权威数据库、审计事件、人工状态门和可解释文档。

### 已实现

- 创建与公开仓库分离的私人项目记录；
- 建立独立 public-ready 工程目录；
- 建立 FastAPI API；
- 建立 PostgreSQL 16 migration；
- 建立 Redis + Celery worker；
- 建立 React/TypeScript/Vite Overview；
- 建立 Docker Compose 五服务定义；
- 建立 liveness/readiness；
- 建立 `AuditEvent` 模型和 worker heartbeat；
- 建立 human-only transition guard；
- 建立 backend/frontend tests；
- 建立 README、Architecture、Agent Boundaries、Data Model、Threat Model、Source Policy、Roadmap 和 ADR；
- 建立本中文说明书和公开发布清单。

### 数据流

```text
Browser -> React -> FastAPI -> PostgreSQL
                         -> Redis -> Celery -> PostgreSQL audit event
```

### 关键设计选择

1. PostgreSQL 保存权威状态，Redis 只传输任务。
2. liveness 和 dependency readiness 分开。
3. human-only target 在代码层拒绝非 human actor。
4. UI 只展示 Week 1 真实状态，后续页面保持锁定。
5. cloud flag 固定为 false；Week 1 不调用 Ollama。
6. public repo 与私人项目记录完全分开。

### 遇到的错误

私人项目记录目录不在当前仓库的写入边界内，第一次初始化被工作区权限保护拒绝。

### 诊断与修复

确认脚本本身是工作区要求的官方初始化入口后，针对该脚本申请一次明确的路径写入许可。初始化成功后再用 patch 填写项目文件。没有尝试绕过 sandbox 或改写脚本路径。

### 当前验证状态

- 文件和静态结构：已创建；
- host Python 直接运行：当前环境缺少 FastAPI/SQLAlchemy 等项目依赖，尚未运行；
- Docker Compose：Docker Desktop 当前未安装，尚未运行；
- backend/frontend test：等待容器或依赖环境；
- GitHub：未连接、未创建、未推送。

### Song 需要理解

- public repo 与私人项目记录的区别；
- API、worker、database、queue、web 的职责；
- candidate/approved 权限边界；
- audit event 的 grain 和 correlation ID；
- 为什么 Week 1 不应先写“智能合规判断”。

### 下一阶段前确认项

- 完成 Docker 安装与五服务运行验证；
- 跑通 backend/frontend tests、migration、worker ping；
- Song 完成 Week 1 自测；
- 之后才解锁 Week 2 source/requirement/control。

## 2026-08-24 — Week 1 / Session 2：运行验证与真实故障修复

### 本次目标

把 Session 1 的静态骨架变成真实可运行系统，并验证浏览器、API、数据库、队列、worker 和审计记录之间的完整链路。

### 已实现

- 从 Docker 官方 Apple Silicon 安装包安装并由 Song 启动 Docker Desktop；
- 构建 `api`、`worker` 和 `web` 镜像；
- 拉起 PostgreSQL 16 与 Redis 7；
- 执行 Alembic 空数据库 migration；
- 验证 API liveness 与 readiness；
- 验证 Celery inspect ping；
- 通过本地浏览器检查 React 页面与控制台；
- 投递 heartbeat task，并在 PostgreSQL、API 和 UI 中看到对应 audit event；
- 添加确定性 GitHub CI、Dependabot 和公开发布检查单。

### 实际测试结果

- Backend Pytest：`14 passed`；
- Backend Ruff：通过；
- Alembic empty-database upgrade：通过；
- Frontend ESLint：通过；
- Frontend TypeScript：通过；
- Frontend Vitest：`1 passed`；
- Frontend production build：通过；
- Docker Compose config 和三个镜像 build：通过；
- 五服务 runtime：全部运行，API/PostgreSQL/Redis 健康；
- Worker：`1 node online`，返回 `pong`；
- Web：HTTP 200；
- 浏览器控制台：没有 error/warning；
- Cloud：`false`；
- 外部动作：无。

Pytest 当前有一条来自上游 Starlette TestClient/httpx 兼容层的 deprecation warning；测试未失败。公开 release 前应升级或替换相应测试客户端并消除该 warning。

### 遇到的错误

1. 第一次 Docker build 把宿主机 `node_modules` 带进 web build context，容器内 pnpm 拒绝在无 TTY 时清理不兼容依赖。
2. Vite 启动命令收到多余的 `--`，实际只绑定 localhost，宿主端口得到 empty reply。
3. 第一次 heartbeat 没传必需的 `correlation_id`，worker 明确返回参数缺失，审计表保持为空。
4. Redis 被 Compose 重建时，既有 worker 短暂失联后自动重连。

### 如何诊断和修复

1. 用 `docker compose ps -a` 区分“服务启动过”和“服务仍运行”。
2. 读取限定范围的 web/worker 日志，而不是反复重启。
3. 添加 frontend/backend `.dockerignore`，删除并重建唯一的可再生成 web dependency volume；PostgreSQL volume 未删除。
4. 为容器增加明确的 `vite --host 0.0.0.0` script。
5. 按 task contract 传入 correlation ID，再从 API 查询 audit event。
6. 页面 reload 后确认 `1 recorded` 与 `worker.heartbeat`，完成 UI 端验证。

### Song 需要理解

- `docker compose up` 成功返回不等于每个容器都健康，必须结合 `ps`、health 和日志；
- Redis 是 transport，短暂重建不应改变 PostgreSQL 中的权威审计状态；
- correlation ID 是跨 API、job、worker、test 和 report 串联一次业务处理的线索；
- 一次失败任务也应该在运维日志中可见，但它不能被包装成成功 finding；
- Docker volume 与 Git 文件不同，dependency volume 可重建，PostgreSQL volume 则需要谨慎保护。

### 下一阶段前确认项

- Song 亲自打开 Overview、health 和 API docs；
- Song 完成 Handbook 中 10 个 Week 1 自测题；
- Song 能口述 heartbeat 的完整数据流；
- 收到 Song 明确确认后才进入 Week 2。

## 2026-08-24 — Week 1 / Session 3：依赖与公开树检查

### 本次目标

把“可以运行”扩展为“适合进入 Git history”，补上依赖漏洞、许可证、文档链接和隐私路径检查。

### 实际发现与修复

- `pnpm audit` 发现 Vitest 3.2.4 有一个 critical advisory；升级到已修复的 3.2.6 后重新审计，结果为 `No known vulnerabilities found`。
- `pip-audit` 首次只发现临时测试环境中的旧 pip 自身问题；升级 pip 后重新审计，项目已安装依赖结果为 `No known vulnerabilities found`。本地 editable package 因不在 PyPI 被明确标记为 skipped，而不是假装已审计。
- 生成并检查 Python 与 frontend dependency license 列表；当前包含 MIT、BSD、Apache、MPL、LGPL 等依赖，最终公开前仍需保留第三方许可复核。
- 新增离线 Markdown 本地链接检查，验证 11 条 repository-local links。
- 新增 public-tree 检查，阻止密钥后缀、数据库、`.env`、大文件和个人绝对路径进入公开树。
- 删除并忽略 TypeScript build metadata 和编译出的 Vite config；它们是本地构建产物，不是源代码。

### 为什么重要

测试通过只说明预期行为通过，并不说明依赖没有已知漏洞，也不说明仓库没有隐私材料。CI 将行为测试、dependency audit、license inventory、secret scan 和 public-tree policy 分开，这样失败原因可定位、不可互相替代。

## 2026-08-27 — Week 2：官方来源、Requirement 与 Control

### 本次目标

用截至当天的一手官方资料替换早期计划中的静态假设，并实现 source → snapshot → requirement → review → mapping 的完整安全链。

### 已实现

- 建立九条官方 source registry；
- 核验 FTC Endorsement Guides/FAQ/Disclosures 101；
- 核验 TikTok commercial-content disclosure 与 AIGC support；
- 核验 EU AI Act Article 50 和 2026 年 7 月 Commission guidance；
- 将 C2PA specification 从早期假设的 2.2 更新为当时官方 2.4；
- 将官方 `c2pa-python` 锁定到真实运行的 0.37.7；
- 实现有界 source fetch、visible text、SHA-256、diff、runtime-only immutable snapshot；
- 实现 `registered`、`fixture_only`、`current`、`changed`、`manual_snapshot_required`、`fetch_error`；
- 实现 fixture 与 Ollama requirement candidate；
- 实现 exact quote validator、schema validator、legal-language guard；
- 实现九个 control definition、mapping candidate 和三种人工 review API/UI；
- 增加 PostgreSQL human-only review trigger 和 snapshot immutability trigger。

### 真实来源刷新结果

- fresh runtime snapshot：FTC FAQ、FTC Disclosures 101、EUR-Lex AI Act、European Commission guidance、C2PA 2.4、official c2pa-python repository，共 6 条；
- `manual_snapshot_required`：两个 TikTok dynamic support pages 和 eCFR，共 3 条；
- 没有绕过登录、robots、重定向、验证码或动态页面限制；
- TikTok 未发布版本号，registry 保持 `not_published`。

### 遇到的错误与修复

最初 demo bootstrap 会把 public test fixture 当成 `current`，导致 evaluation 报 source freshness 100%。这违反“最新必须有真实证据”的项目原则。修复后，fixture 只产生 `fixture_only`，没有 snapshot 的来源是 `registered`，只有成功 HTTP 或人工确认 snapshot 才是 `current`。真实 freshness 变为 `6/9 = 0.6667`。

eCFR 返回到自动访问阻断页的 302；TikTok 页面无法让有界客户端取得可验证正文。Source Monitor 最初把它们记为普通 `fetch_error`。修复后，安全 redirect 或 manual fetch mode 的失败统一进入 `manual_snapshot_required`。

### Song 需要理解

- registry metadata verified 不等于 snapshot current；
- source access failure 是产品状态，不是要求工程师绕过网站；
- requirement approval 只授权 mapping 工作，不是法律判断；
- source 更新不会覆盖旧 snapshot 或旧 approved requirement。

## 2026-08-27 — Week 3：真实合成媒体、C2PA 与 Deterministic Rules

### 本次目标

让项目真正处理可播放 MP4，而不是只在 JSON 中假装存在视频证据。

### 已实现

- 固定 seed 生成 50 个 H.264/AAC MP4；
- 使用虚构 NovaGlow 品牌、虚构关系和通用 UI；
- 覆盖 own brand、paid、affiliate、free product、none；
- 覆盖 English/Spanish、视觉/语音/metadata disclosure、AIGC、ambiguous evidence、prompt injection；
- FFprobe 校验 stream；FFmpeg 1 fps 抽帧；Tesseract OCR；Faster-Whisper real local ASR；
- 使用 official c2pa-python 读取 absent/present/invalid/test-signed；
- runtime 生成 7 天 test-only root/leaf certificate，private key 不提交；
- 37 个测试资产写入 manifest，其中 12 个再篡改以产生 invalid 状态；
- evidence 记录 asset hash、frame、timestamp、segment、extractor/version；
- deterministic controls 只查询 approved mappings；没有批准时明确返回 HTTP 409。

### 遇到的错误与修复

第一次 C2PA 签名使用单个 self-signed certificate，official SDK 明确拒绝 `certificate was self-signed`。修复为 runtime test root + leaf chain；仓库只保存签名后的 synthetic assets，不保存 private key，也不声称 public trust。

媒体反复分析早期同时留下了 ASR/C2PA v1 与 normalization-v2 evidence。Audit manifest 保留相同 asset hash 下的 extractor version 历史，避免静默覆盖；evaluation 明确选择当前 provider 和 normalization-v2。

### 真实证据样例

- `case-001`：H.264/AAC 和三帧 OCR 成功；没有批准 mapping，rule run 被阻断；
- `case-002`：Faster-Whisper 实际转写成功；
- `case-003`：签名后篡改，C2PA normalization 为 invalid；
- `case-004`：test chain 内 Valid，但 UI/报告明确不把它解释为真实或合法。

### Song 需要理解

- evidence extraction 和 rule authorization 是两条不同链；
- OCR/ASR 未检测到不代表内容中不存在；
- C2PA 是 provenance evidence，不是 truth oracle；
- deterministic rule 的优势是版本化与复现，不是法律充分性。

## 2026-08-27 — Week 4：100k Events、Evaluation、Audit Pack 与 UI

### 本次目标

完成规模数据、真实指标、四格式报告、八页面 UI 和桌面/手机端验证。

### 100k 数据结果

- seed：`20260827`；
- rows：`100000`；
- logical SHA-256：`c73895e21b86bf7ea57ef9e89899d5a26cc0d30c34347383ee8bb0cf9e48ceb7`；
- jurisdiction：CA 16,666，EU 33,333，US 50,001；
- 五种 event type 各 20,000；
- processing latency field total：46,882,618 ms；
- 第一次 ingestion 100,000，第二次 ingestion 0；
- PostgreSQL control totals 全部一致。

### 第一次 50-case 真实运行

- 50/50 完成，0 silent failure；
- OCR precision/recall：0.8750/1.0000；
- ASR precision/recall：1.0000/0.8571；
- provenance parsing：1.0000；
- p50/p95：1,280.24/4,115.12 ms；
- end-to-end throughput：0.59 case/s。

### 发现的 OCR bug

phrase detector 用普通 substring 查找 `ad`，因此可能在 `generated` 等单词内部误命中。修复为 Unicode word-boundary regex 后：

- OCR precision 从 0.8750 提升到 1.0000；
- OCR recall 真实显示为 0.8571；
- 保留 `case-020`、`case-030` 两个低质量西语 OCR miss；
- 保留 `case-025`、`case-030` 两个 Faster-Whisper 西语 miss；
- finding precision/recall 变为 0.9355/1.0000；
- 没有删除困难 case 或隐藏 metric 下降。

纠错后 evaluation 复用相同 hash 的已验证 evidence，因此 1,711 case/s 只代表 cached validation，不作为媒体吞吐 claim。

### 异步任务故障

API 新增 `evaluation.run_gold` 后，旧 Celery worker 没有自动加载 task，第一次 job 被明确记录为 `unregistered task`。重启 worker 后 task registry 出现 evaluation、media 和 heartbeat 三项，重跑成功。由此新增运维原则：部署新 task code 后必须验证 worker registered-task list，而不能只看 API queued response。

### Audit Pack

- case-004 实际生成 HTML、PDF、JSON、CSV；
- 每个文件有 SHA-256 和数据库 `ReportExport`；
- manifest 包含当前 asset hash evidence 与完整可用 lineage；
- 因 approved mappings 为 0，package status 是 `evidence_only_no_approved_rule_result`；
- HTML 对 untrusted caption 做 escape；
- `legal_conclusion` 与 `external_action` 均为空。

### React 与浏览器验证

- 八页面全部实现；
- desktop 浏览器导航、4 candidate reviews、50 cases、evidence、evaluations 可见；
- 浏览器 console 0 error/warning；
- 390px 手工 viewport 无横向溢出；
- official Playwright Ubuntu image：3 passed，1 desktop 项按 mobile-only 条件跳过。

Playwright 第一次在 Alpine web container 内失败。浏览器文件存在，但它是 glibc build，Alpine 使用 musl，启动显示 ENOENT。没有把它误判为页面错误；改用 official Playwright Ubuntu image 后执行真实规格。

### 测试隔离错误

PostgreSQL trigger integration test 第一个版本把两组 `trigger-test-*` records 提交进开发数据库，使 UI candidate count 从 4 变成 6。诊断后：

1. 精确核验两组 test source/snapshot/requirement；
2. 只清理这个前缀产生的六条测试记录；
3. 把测试改为 outer transaction + savepoint，最终始终 rollback；
4. 重跑后 23 backend tests 通过，UI 恢复 4 candidates；
5. PostgreSQL 仍实际拒绝 model review 和 snapshot UPDATE。

### 最终本地测试结果

- backend Ruff：通过；
- backend Pytest：23 passed（含真实 PostgreSQL trigger tests）；
- frontend ESLint/TypeScript/Vitest：通过，1 component test passed；
- frontend production build：通过；
- Playwright：3 passed，1 intended skip；
- 100k re-ingestion：0 duplicate insert；
- 50-case evaluation：50 results，0 failure；
- source refresh：6 current，3 manual snapshot required；
- report export：四格式成功；
- operational approved requirement/mapping：0/0；
- external action/cloud：none/false。

### 尚未由工程自动完成的人工门

- Song 审阅并决定四个 requirement candidates；
- Song 审阅未来 mapping candidates 和 finding candidates；
- Song 检查 public release checklist、截图、README 和 Git history；
- Song 明确授权后才创建/公开 GitHub repository；
- weekly source schedule 仍关闭。

## 2026-08-27 — 最终发布审计补充

### 最新 SDK 对齐

最终容器重建时，PyPI 官方 registry 发布了 `c2pa-python` 0.37.8（上传时间
2026-08-27T20:39:35Z）。因此运行时依赖下限、source registry、README 和
third-party notice 同步更新为 0.37.8。此前 50-case evaluation 明确保留其
真实运行版本 0.37.7；没有用新依赖版本篡改历史 benchmark provenance。

### PDF 视觉 QA

首个 PDF 虽然结构有效，但视觉上只是单页纯文本，不符合面试展示标准。
改用 ReportLab 5.0.1 生成正式 audit evidence package，加入摘要、资产身份、
evidence inventory、finding lineage、边界声明和页脚。报告仍只渲染同一份
lineage manifest，不新增法律判断或 finding。

### 公开日志隐私清理

发布审计发现早期日志写入了私人 Context 工具名和本地沙箱路径细节。为满足
公开仓库边界，对这些描述做了最小化泛化，只保留“私人项目记录与公开仓库
分离”以及“权限保护拒绝越界写入”两项可公开工程事实；未改变实现结果、
测试结果或时间顺序。

### CI runtime 对齐

通过 GitHub 官方 release API 核验当前稳定 majors：`actions/checkout@v7`、
`actions/setup-python@v7`、`actions/setup-node@v7`、
`pnpm/action-setup@v6`。Node.js 官方 release table 将 Node 24 标为 LTS，
因此 CI 与 web image 从 Node 22 更新到 Node 24；没有采用仍处于 Current 的
Node 26。

官方 npm registry 同时显示 pnpm 11.24.0 为最新稳定版本；`pnpm outdated`
确认 Vite、Vitest、ESLint 与测试工具链已有新稳定 major。依赖声明更新到当日
稳定版本后，必须重新生成 lockfile，并以 lint、typecheck、unit、production
build 与 Playwright E2E 作为兼容性门，不能只凭 registry 的 `latest` 标签判定
升级成功。

第一次升级选择了 registry `latest` 的 TypeScript 7.0.2。typecheck 和 Vite
build 能通过，但 `typescript-eslint` 8.68.0 明确拒绝 TS 7 API，使 lint
失败。项目因此回退到官方 registry 的最新兼容 6.x（6.0.3），并保留这个
失败记录。这里的原则是“最新且被整条工具链支持”，不是机械追随单个包的
`latest` 标签。

升级后的 React Hooks lint 新增 `set-state-in-effect` 检查，发现 Controls 与
Audit Pack 的首次加载函数通过 `async` wrapper 在 effect 内触发 state 更新。
页面本来可工作，但新规则把潜在 cascading render 标为错误。两处 loader
统一改为 promise callback 形式，与其他页面的数据加载模式一致，然后重跑
lint、typecheck、unit、build 和浏览器 E2E。

### 依赖漏洞审计

`pnpm audit --audit-level high` 返回 0 known vulnerabilities，peer check 也
通过。第一次 `pip-audit` 则真实发现基础 Python 3.11 image 内的 `pip 24.0`
和 `setuptools 79.0.1` 命中 2026 年 advisories。PyPI 官方 registry 当日版本
为 pip 26.2.1、setuptools 84.0.0；Docker build 与 CI 先升级到这两个版本，
再安装项目依赖并重跑 audit。构建工具不能因为“不是业务 import”就排除在
镜像安全边界之外。

升级构建工具并重建镜像后，第二次 `pip-audit --local --skip-editable`
返回 `No known vulnerabilities found`；pnpm audit 同样为 0。Python 与 Node
license inventory 均成功生成。Gitleaks 8.30.1 对排除 `.runtime`、包缓存、
build outputs 和测试报告后的实际公开文件集扫描约 2.21 MB，返回
`no leaks found`。第一次误把 `.pnpm-store` 包缓存复制进扫描目录而出现第三方
测试字符串；该次运行被明确作废，修正公开文件集后重新扫描，没有把误报
当作仓库泄漏或把失败写成通过。

### Clean-tree 构建

最终把公开文件复制到一个不含 `.git`、`.runtime`、包缓存、build output、
test report 或本地数据库的临时 release tree。在该目录内，API、worker 和
web 三个镜像全部独立构建成功。临时副本在验证后删除；原开发数据库和运行
证据没有被复制或修改。

### 最终自动化结果

- backend Ruff：通过；
- backend Pytest：24 passed，1 个 upstream Starlette deprecation warning；
- frontend lint/typecheck/Vitest/production build：通过；
- Playwright official image：3 passed，1 个 mobile-only assertion 在 desktop intentional skip；
- public-tree：178 files 通过；
- local Markdown links：23 links 通过；
- Docker Compose config：通过；
- clean-tree 三镜像 build：通过；
- Python 与 Node dependency audit：0 known vulnerabilities；
- Gitleaks public-tree scan：no leaks found；
- private project-index refresh/health check：PASS；
- operational approved requirements/mappings/findings：0/0/0；
- GitHub publish、schedule、cloud、external action：均未执行。

## 2026-08-28 — 持续 Goal 启动与 Requirement 审阅准备

### 本次目标

把“持续完成项目”从笼统愿望变成可验收的长期阶段：先让 Song 理解并审阅 requirement，再进入 mapping、finding、demo 和经授权后的发布；同时重新核验会变化的官方资料。

### 本次实现

- 创建持续项目 Goal，但没有设置用户未要求的 token budget；
- 读取当前运行态，确认五个服务正常、四个历史 requirement 仍为 candidate、approved requirement/mapping/finding 仍为 0/0/0；
- 建立 `REQUIREMENT_REVIEW_WORKBOOK.md`，逐条拆分 source fact、Agent interpretation、review question、approval impact 和 Song rationale；
- 将 source registry 的 EU AI Act URL 从 2024 Official Journal 原始版本更新为 2026-07-27 consolidated version；
- 新增 Article 111(4) transition fixture candidate，并只提出 `human_review_required` control；
- bootstrap idempotency payload 改为读取 registry 的真实版本，避免代码内日期漂移；
- 没有自动执行 requirement review、bootstrap、GitHub 操作、schedule、cloud 或外部动作。

### 最新官方对齐发现

- eCFR 16 CFR 255.0 页面显示截至 2026-08-27，multimodal disclosure exact quote 仍存在；
- TikTok 两个官方动态 support 页面索引内容仍支持现有短摘录，但有界直接读取仍无法取得可审计正文，因此状态保持 `manual_snapshot_required`；
- EUR-Lex 显示 Regulation (EU) 2024/1689 已有 2026-07-27 consolidated version；Article 50(2) 文本仍存在，同时 Article 111(4) 为 2026-08-02 前 placed on the market 的相关系统给出到 2026-12-02 的过渡时间；
- 旧 EU candidate 的单一 `effective_date=2026-08-02` 因此不足以表达全部时间适用情况，不能在未补证时静默批准。

### 设计选择

没有直接编辑数据库中的历史 EU candidate，也没有把 transition 文字塞进 Article 50(2) 的 quote。新过渡条款保留独立 locator 和 exact quote，等待受控 bootstrap 产生新 lineage；旧候选如何处置仍由 Song 决定。

### Song 需要理解

- source quote 没变，不代表适用上下文没有新版本；
- 独立过渡条款应该有独立 candidate/lineage；
- `needs_more_evidence` 是安全且可审计的业务结果；
- 更新 public fixture 不等于修改当前数据库状态，更不等于批准 requirement。

### 下一阶段确认项

- Song 按工作簿先审阅 Candidate A；
- Song 决定是否允许一次受控 bootstrap 生成新的 EU consolidated snapshot/candidates；
- 在 requirement review 完成前，不创建 mapping 或 operational finding。

### 本次验证与调试

新增 EU transition regression test 的第一次运行失败：测试根据容器内 `tests/` 路径向上推导 project root，错误得到 `/`，所以尝试读取 `/config/source_registry.json`。这不是 fixture 内容或产品逻辑失败。测试改为使用应用的 `Settings.PROJECT_ROOT`，让本地环境与 Compose 的 `/workspace` 挂载遵循同一配置来源。

修复后的真实结果：

- Ruff：通过；
- Pytest：25 passed，包含两项真实 PostgreSQL trigger tests；
- upstream Starlette/httpx deprecation warning：1，保持可见；
- public-tree：179 files 通过；
- repository-local Markdown links：25 links 通过；
- 当前运行数据库：4 historical candidates，0 approved requirements，0 mappings，0 findings；
- private project-index refresh/health check：PASS。

## 2026-08-28 — Registry 同步、权威刷新与 verified extraction 闭环

### 阶段目标

把“配置文件已经更新”与“运行数据库已经核验”拆成可审计的独立步骤，并用真实官方 snapshot 验证最新 EU 条款。整个流程只能产生候选，不能替 Song 审批。

### 本次实现

新增 `POST /api/v1/sources/sync-registry`。它按 stable source key 同步 publisher、URL、jurisdiction、source type、版本、日期、scope、fetch mode 和 redistribution note。若 URL、版本、日期、scope 等会影响解释的字段发生变化，source 会回到 `registered` 且清空 `last_checked_at`；仅修改 registry metadata 不能继续冒充“fresh”。接口使用 idempotency key，并写 audit event。

新增 `GET /api/v1/sources/{source_id}/snapshots`，让 UI 能显示 snapshot ID、hash、状态、时间和 diff 摘要。新增 `POST /api/v1/source-snapshots/{snapshot_id}/extract-verified-requirements`：它只接受 `current` 或 `manual_snapshot` 的 authoritative snapshot，并只从人工维护的公开 fixture 中选择同 source 的候选；每条 exact quote 必须逐字存在于该 snapshot。成功只写 `candidate`，不创建 review、mapping、test 或 finding。

Sources UI 增加 registry metadata sync、最新 snapshot/diff 展示，以及仅在满足上述条件时出现的 `Create verified candidates` 动作。这样 Song 能看见 `registry → snapshot → diff → exact quote → candidate` 的完整路径。

### 真实运行结果

一次受控 registry sync 处理 9 个来源：0 created、2 updated、2 freshness invalidated。变化来源是 EU consolidated URL/version/scope 与 `c2pa-python` published date/version。

随后真实刷新产生：

- EU snapshot `82b2fff0-d4b6-4f58-be6b-6a45a9ee5b86`，SHA-256 `0dac65251e12c2df4ed7ac9236f8ae78dc04b8a09907c5206bbc2e3f446ab7b6`，diff 为 `changed`；
- `c2pa-python` snapshot `16f4cae3-1c64-4132-a8a0-911863518375`，SHA-256 `6dc1c45ada898e8f232edeadfc701845c7289ab73997277863673a7d4b18a1fc`，版本 0.37.8，diff 为 `changed`。

EU snapshot 中 Article 50(2) 与 Article 111(4) 两段 exact quote 均逐字命中。verified extraction 创建两个新候选：

- Article 50(2)：`231707d5-b6bb-4af7-9fe7-2624b2c70c9b`；
- Article 111(4)：`f7ba95d3-9940-4d87-86dc-478b86fcd785`。

当前数据库共有 6 个 requirement candidates，全部未审批；approved requirements / mappings / findings 仍为 `0 / 0 / 0`。旧 EU candidate 未被覆盖或删除。

### 评估指标错误与诊断

registry sync 后 source 状态是 4 `current`、2 `changed`、3 `manual_snapshot_required`。最初 evaluator 只把 `current` 计为 fresh，错误得到 `4/9 = 0.4444`。代码改为：只要 `current` 或 `changed` 都来自成功的 authoritative refresh，两者都计为 fresh；`changed` 表示与前版有 diff，不表示过期。

第一次修复后重跑仍返回 0.4444。检查发现 Celery worker 仍加载旧 Python 进程代码；重启 worker 并确认 `evaluation.run_gold`、`media.analyze_case` 和 heartbeat task 已注册后，再用新的 idempotency key运行，结果为 `6/9 = 0.6667`。这说明异步系统调试不能只看源文件和 API 容器，还必须核验实际消费任务的 worker 版本。

本次 regression evaluation 使用 fixture ASR 和缓存 evidence，只验证 source freshness、backlog 与边界，不替代真实 Faster-Whisper 50-case benchmark。结果 50/50 completed、0 failures、schema-valid 与 exact-quote validation 均为 1.0、review backlog 为 6、operational rule activation 为 false。

### 公开项目对标

新增 `OPEN_SOURCE_BENCHMARK.md`，仅使用官方仓库核验 OPA、NIST OSCAL、ComplianceAsCode 与 `c2pa-python`：

- 借鉴 OPA 的 data/rule/decision 分离，但当前 9 个小控制不引入第六个 OPA 服务；
- 借鉴 OSCAL 的 control、evidence、assessment result 分层，但不声称 OSCAL conformance；
- 借鉴 ComplianceAsCode 的 single-source rule metadata，但不生成 remediation 或外部执行；
- `c2pa-python` 是真实 runtime dependency，但 valid/absent manifest 都不能被解释为真伪或法律结论。

没有从前三个参考项目复制代码；它们只用于架构比较。任何未来依赖都必须记录官方来源、版本、license、引入成本、失败语义和 approval 影响。

### 本次测试结果

- backend Ruff：通过；
- backend Pytest：28 passed，1 个 upstream Starlette/httpx deprecation warning；
- frontend ESLint、TypeScript、Vitest、Vite production build：通过；
- 新增 registry material-change freshness invalidation test；
- 新增 successful `changed` snapshot 计入 freshness 的 regression test；
- 所有 mutation 继续要求 idempotency key；
- GitHub、schedule、cloud 和 external action：均未执行。

### Song 自测

1. 为什么 registry URL 更新后必须先清空 freshness？
2. 为什么 `changed` 可以是 fresh？
3. 为什么 exact quote 命中仍只能生成 candidate？
4. 为什么旧 EU candidate 和新 EU candidate 应同时保留？
5. 为什么异步 worker 重启属于这次指标修复的一部分？

### Sources UI 并发回归与 N+1 修复

第一次加入 Sources 页面 E2E 后，单独运行 desktop 测试通过，但 desktop/mobile 两个 project 并发时 Requirements 页面偶发在 5 秒内没有渲染候选。trace 显示页面导航成功，API 日志却显示 Sources 在 React StrictMode 下为每个来源逐个请求 snapshot：9 个来源会产生 N+1 请求，两个浏览器 project 和开发模式的重复 effect 又把流量放大。

没有通过延长 timeout 隐藏问题，而是新增批量只读端点 `GET /api/v1/source-snapshots/latest`，一次返回每个 source 的最新 immutable snapshot summary。Sources 页面加载从 1 次 sources + 9 次 snapshots 降为 2 个并行请求。保留单来源历史 snapshots endpoint 供详情和审计使用。

修复后并发 Playwright 结果为 3 passed、1 个 desktop project 中的 mobile-only assertion 按设计 skipped。E2E 现在同时验证：9 个官方来源、latest snapshot、6 个候选的 review surface、0 approved requirement 时的 mapping gate、50 个媒体案例、evidence bundle 和未选择 case 时禁用的 audit export。由于 clean CI 只加载 `public_test_fixture`，不会伪造 authoritative snapshot，verified-extraction button 由独立 component test 使用 `current` snapshot mock 验证；这样 CI 不依赖实时网络，也不会把 fixture 当成当前证据。后端另有单元测试证明 batch endpoint 对每个 source 只返回时间最新的 snapshot；最终后端总数为 28 passed。

### 本次镜像重建的外部阻塞

当前代码、运行态、测试和 Compose config 均通过后，尝试重新构建 API、worker、web 三个镜像。第一次本地调用被 Docker Buildx 的 activity metadata 文件权限拦截；经明确权限后重跑，BuildKit 两次都在读取 Docker Hub 的 `python:3.11-slim` 和 `node:24-alpine` metadata 时于约 60 秒超时。主机当前没有这两个带 tag 的 base image cache，因此不能诚实声称“本次最新 tree 的镜像重建通过”。

这次失败没有修改数据库或运行服务。之前成功构建的三个 application images 仍在运行，API/PostgreSQL/Redis 健康，Celery `inspect ping` 返回 1 node online，React UI 和全部本地挂载代码回归仍通过。由于本轮没有修改 Dockerfile 或 dependency lockfile，风险局限在尚未重新证明 clean image build；外部 registry 恢复后必须重跑 `docker compose build api worker web`，再更新发布检查结果。

## 2026-08-28 — Requirement lineage 审阅视图与 authoritative approval gate

### 发现的边界缺口

旧 Requirements 页面只展示 quote 和模型结构化字段，没有同时展示 source type、官方 URL、版本、snapshot hash、抓取状态和历史 review。更严重的是，service 只检查 quote 是否存在与 legal-language guard，理论上允许人工把 `public_test_fixture` parent 的候选批准。fixture 能证明 CI 可重复，不能证明当前官方来源，因此不应授权 operational mapping。

### 本次实现

- 新增 `GET /api/v1/requirements/lineage`，一次返回 requirement、source、immutable snapshot summary、review history 和 `authoritative_for_approval`，避免 UI 再做 N+1 join；
- Requirements UI 直接展示 publisher/source type、official URL、source version、retrieval time、完整 SHA-256、fetch status、exact-quote validation、scope、exception、effective date、uncertainty 和 review history；
- 当 parent 不是 `current` 或 `manual_snapshot` 时，UI 显示明确证据警告并禁用 approve，但保留 `needs_more_evidence` 和 `rejected`；
- service 在 approve 前重新检查 snapshot authority；
- migration `0005` 新增 PostgreSQL trigger：fixture-backed approval review 被拒绝；requirement status 改变若没有 disposition 相同的 human review row 也被拒绝；
- service 先 flush human review，再更新 requirement status，使合法 authoritative transition 能通过数据库 gate。

### 当前真实运行态

6 个候选中，4 个历史候选的 parent 为 `public_test_fixture`，所以不能批准；2 个最新 EU 候选的 parent 为 `current`，具备最低审批证据资格，但仍未被 Song 批准。当前 reviews / approved requirements / mappings / findings 仍为 `0 / 0 / 0 / 0`。

### 验证结果

- Alembic `0004 → 0005`：真实 PostgreSQL upgrade 通过；
- backend Ruff：通过；
- backend Pytest：32 passed，包含非人类 review、fixture approval、direct status bypass 三条拒绝路径，以及 authoritative human transition 成功路径；
- frontend ESLint、TypeScript、3 个 Vitest component tests、production build：通过；
- Playwright：3 passed，1 个 mobile-only assertion 按设计 skipped；
- lineage API 实测：6 records，4 non-authoritative、2 authoritative；
- 本地浏览器视觉 QA：页面正确显示 source authority、完整 snapshot hash、quote、scope 与警告；Approve enabled 状态依次为 `[true, true, false, false, false, false]`，6 个 Needs evidence 均 enabled；console warning/error 为 0；
- empty-database migration：创建独立临时 PostgreSQL database，从空状态依次运行 `0001 → domain model → 0003 → 0004 → 0005`，`alembic current` 返回 `0005 (head)`；验证成功后删除该临时 database，开发数据库未修改；
- 没有对 6 个真实候选写入任何 review 或状态改变。

### Song 自测

1. 为什么 exact quote 在 fixture 中存在，仍不能批准？
2. 为什么 `authoritative_for_approval=true` 仍不等于应该批准？
3. 为什么先写 review row、再改 status？
4. 如果绕过 React 直接更新 requirement status，PostgreSQL 会如何处理？

## 2026-08-28 — Docker base-image transport 诊断与独立镜像重建

### 为什么继续验证

前一轮 `docker compose build api worker web` 在解析 Docker Hub 的 `python:3.11-slim` 和 `node:24-alpine` metadata 时超时。代码测试通过不等于镜像一定能从当前 Dockerfile 重建，因此发布证据必须继续区分应用回归、Dockerfile 构建和本机 Compose/BuildKit 工具链。

### 诊断与处理

- Docker Hub 官方 tag API 与 Google 公共镜像传输端点返回相同 manifest digest：Python 为 `sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6`，Node 为 `sha256:e67514e5d0f6c46656005e1b693b2ec9d52e80b641307de684d4a015ba7a4eaf`；
- 使用不含账号凭据的临时 Docker config 从公共镜像端点拉取这两个 digest-equivalent base，并在本地恢复原始官方 tag；
- 使用当前 backend Dockerfile 从零构建 `ccg-backend-release-verify:20260828`。API 与 worker 共享这个 Dockerfile 和 dependency context，因此这次构建覆盖二者的代码与依赖层；
- 使用当前 frontend Dockerfile 从零构建 `ccg-web-release-verify:20260828`；
- 在新 backend image 内成功导入 `ccg_agent.main` 与 `ccg_agent.worker`，`alembic heads` 返回 `0005 (head)`；
- 在新 frontend image 内重新运行 `pnpm build`，Vite production build 通过；
- 临时无凭据 Docker config 已删除，没有改变项目数据、Git 状态或运行中的五个服务。

### 真实结论与限制

两个不同 Dockerfile 的当前版本已用 digest-verified 官方等价 base 从零构建并完成镜像内 smoke test，因此“当前代码能形成可运行 application images”已有新证据。不能声称本次 `docker compose build` 命令本身通过：正常 Docker config 下的 BuildKit 仍卡在本机 credential/registry metadata 路径；隔离 config 又没有 Compose CLI plugin。托管 GitHub CI 的首次运行也必须等 Song 批准创建并推送仓库后才能获得。

### Song 自测

1. 为什么相同 tag 名称不如相同 manifest digest 有说服力？
2. 为什么 API 与 worker 可以共享一次 backend Dockerfile 构建证据？
3. “Dockerfile 可以构建”和“本机 `docker compose build` 命令成功”有什么区别？
4. 为什么仍不能把尚未运行的 GitHub CI 写成已通过？

## 2026-08-28 — 发布前只读总审计

### 审计范围

本次没有创建 review、批准 requirement、创建 mapping/finding、运行 cloud、启用 schedule、创建 GitHub 仓库或执行外部动作。只读取公开树、服务和 API 状态，并把尚未发生的 hosted CI 留为未勾选发布门。

### 实际结果

- public-tree checker：181 files，PASS；
- repository-local Markdown links：26 links，PASS；
- personal path、项目私有系统名和 email 模式扫描：PASS；
- `git diff --check`：PASS；
- API、PostgreSQL、Redis：healthy；web 与 worker 运行；Celery ping 返回 1 node online；
- requirement lineage：6 candidates，4 个 non-authoritative fixture lineage，2 个 authoritative current EU lineage；
- review / approved requirement / mapping / finding：`0 / 0 / 0 / 0`；
- source 状态：4 `current`、2 `changed`、3 `manual_snapshot_required`；
- `PUBLIC_RELEASE_CHECKLIST.md` 新增未完成的 hosted GitHub Actions 首次运行门；它只能在 Song 批准 initial push 后验证。

### 结论

本地工程与公开树仍处于 release-candidate 状态，不等于已经发布。下一条会改变治理状态的动作必须是 Song 对具体候选作出明确 disposition；下一条会改变外部状态的动作必须是 Song 单独批准 GitHub 创建与公开。

## 2026-08-28 — ASR provider 隔离与可重复面试演示

### 演示核对发现的问题

同一 media hash 先保存真实 Faster-Whisper evidence，后续 CI/regression 又保存 fixture ASR evidence。旧 evaluator 读取全部 ASR rows 后使用最后一条；因此后来创建的 fixture transcript 可能污染标记为 Faster-Whisper 的重评结果。历史真实 run 本身仍保留正确结果，但选择算法没有把 provider provenance 变成硬约束。

### 修复

- evaluator 只选择 `evidence_type=asr` 且 `extractor == settings.asr_provider` 的 rows；
- metrics 新增 `evidence_selector=extractor_matches_provider`；
- 单元测试构造先写 real、后写 fixture 的顺序，并证明 Faster-Whisper 选择不会改变；
- 新增只读 `scripts/rehearse_demo.py` 和 `make demo-rehearsal`；
- preflight 核对 9 sources、6 candidates、0 mappings/findings、50 analyzed cases、case-003/004 evidence、provider-isolated evaluation 和 case-004 四种 report；
- Evaluations UI 改成摘要 metric cards，明确区分 Faster-Whisper evidence 与 fixture evidence，同时用折叠区保留完整 JSON 和 retained errors；
- `ROADMAP.md` 修正为工程项已完成、Song 学习/审批/GitHub 项仍待完成，不再用未勾选工程项制造错误状态。

### 真实回归

- backend Ruff：PASS；
- backend Pytest：33 passed，1 个 upstream Starlette/httpx deprecation warning；
- fixture evaluation：50/50、ASR provider `fixture`、selector `extractor_matches_provider`；
- Faster-Whisper evaluation `93def3e2-49fd-4de9-aae3-2140a1607056`：50/50、0 failures、ASR precision/recall `1.0000 / 0.8571`，仍保留 case-025 与 case-030 两个西语 miss；
- frontend ESLint、TypeScript、4 component tests、production build：PASS；
- local browser visual QA：第一个 card 正确显示 50/50、OCR/ASR `1.0000 / 0.8571`、freshness `0.6667`、provider selector 和 0 failures；fixture card 有不同标签；
- Playwright：3 passed，1 个 desktop 中的 mobile-only assertion 按设计 skipped；
- `make demo-rehearsal`：`ready`；没有创建 review、mapping、finding 或任何外部动作。
- 最新 tree 独立镜像重建：backend `ca7dd56d2138`、frontend
  `b629bcc050bb`；backend import 与 Alembic `0005 (head)`、frontend 镜像内
  production build 均通过。正常 Docker config 首次仍因本机凭据路径卡住，
  使用已记录的无凭据临时 config 后成功；临时 config 随后删除。

### Song 自测

1. 为什么同一个 asset hash 可以同时存在 real ASR 和 fixture ASR？
2. 为什么 `created_at` 不能决定 evaluation 使用哪个 provider？
3. 为什么 fixture ASR 的 1.0000 recall 不能替代 Faster-Whisper 的 0.8571？
4. 为什么 Song 一旦批准 requirement，当前 evidence-only rehearsal 应主动失败？

## 2026-08-28 — Meaningful human review 与 Mapping/Finding lineage

### 发现的治理缺口

Requirement 页面已经要求 Song 输入 rationale，但 Mapping 和 Finding 页面仍把固定英文模板直接提交给 API。它能证明请求携带 `X-Reviewer-Id: Song`，却不能证明 Song 实际比较了 requirement、control、test、evidence 和 uncertainty。审批后 UI 也没有显示 mapping/finding review history。

### 实现

- 新增通用 `HumanDecisionBox`：所有 disposition 在输入至少 20 个 trimmed characters 前保持 disabled；
- 删除 Mapping/Finding 的 canned rationale；每个 card 单独保存 Song 输入并展示字符下限；
- Pydantic `HumanReviewRequest` 去除首尾空白并拒绝少于 20 字符；`MappingCreate` 使用同一下限；
- SQLAlchemy model 与 Alembic `0006` 为 requirement review、mapping candidate、mapping review、finding review 添加独立 check constraints；
- 新增 `GET /api/v1/mappings/lineage`，批量返回 mapping、requirement、control 和 review history；
- 新增 `GET /api/v1/findings/lineage`，批量返回 finding、test run、requirement、control、linked evidence 和 review history；
- Controls 与 Review Queue 改用 lineage endpoint，不再依赖孤立 ID 或一键模板；
- 20 字符只作为 anti-empty engineering floor，文档明确它不证明 review 的实质质量。

### 验证

- 迁移前真实表均为 0 rows，没有旧短 rationale 需要修复；
- dev PostgreSQL `0005 → 0006`：PASS；
- 独立临时空数据库从 `0001` 迁移到 `0006 (head)`：PASS，随后删除；
- short rationale API 请求返回 HTTP 422；复核后真实数据库仍是 0 reviews、6 candidates；
- backend Ruff：PASS；Pytest：36 passed，包含 Pydantic whitespace、PostgreSQL 四约束、mapping/finding lineage join；
- frontend ESLint、TypeScript、5 component tests、production build：PASS；
- component test 证明 fixture requirement 即使输入 rationale 也不能 approve，而 finding disposition 必须先输入 rationale；
- Playwright：3 passed，1 intentional desktop skip；
- 本地浏览器只读 QA：6 个 review forms 显示 `0 / 20`，所有 approve 和 needs-evidence buttons 在未输入时均 disabled；
- 包含本轮代码和 migration `0006` 的发布验证镜像重新构建成功：backend `42a1cf28389d`、frontend `e885dfb4fb03`；backend 镜像内 API/worker import 与 `alembic heads = 0006 (head)` 通过，frontend 镜像内 production build 通过；
- 镜像构建使用不含账号凭据的临时 Docker config；验证后已删除该 config，没有改动运行数据或 Git 状态；
- 没有创建 requirement review、mapping、finding 或外部动作。

### Song 自测

1. 为什么 `reviewer_type=human` 不足以证明 meaningful review？
2. 为什么 20 字符下限仍不能自动证明 rationale 正确？
3. Mapping review 应同时检查 requirement 与 control 的哪些字段？
4. Finding disposition 为什么必须看 test result 和 evidence IDs，而不能只看模型 explanation？

## 2026-08-28 — Meaningful review 改动后的只读发布门

### 本次目的

确认 `0006`、typed rationale 和 mapping/finding lineage 合入后，发布候选没有产生回归，也没有越过 Song 的人工权限。

### 实际结果

- `make demo-rehearsal`：`ready`；50 个案例、四种 report、Faster-Whisper evaluation 与 provider selector 均可读取；
- public-tree checker：184 files，PASS；repository-local Markdown links：27，PASS；
- personal path、私人项目名与 email 模式扫描：无命中；`git diff --check`：PASS；
- API、PostgreSQL、Redis healthy；web 与 worker 运行；Celery ping：1 node online；
- requirement lineage：6 candidates，其中 2 个 authoritative current EU candidates、4 个 non-authoritative fixtures；reviews 仍为 0；
- mapping lineage：0；finding lineage：0；
- source 状态保持 4 `current`、2 `changed`、3 `manual_snapshot_required`；
- 没有创建 GitHub 仓库、commit、push、release，没有启用 schedule、cloud 或外部动作。

### 结论

工程发布候选在新人工审批约束下仍可重复运行，但治理工作流故意停在第一个 Song disposition 之前。下一步不是让 Agent 自行批准，而是 Song 对 authoritative candidate 写下具体判断和 rationale。

## 2026-08-28 — eCFR 官方 API adapter 与北美 FTC authoritative lineage

### 阶段目标

消除 FTC 主线长期依赖 `public_test_fixture` 的证据缺口，同时遵守 eCFR reader page 的自动访问限制，不绕过 CAPTCHA、redirect 或访问控制。

### 公开事实核验

- eCFR 的访问阻断页明确要求 programmatic clients 使用 developer APIs；
- 官方 `titles.json` metadata 在本次运行返回 Title 16 `up_to_date_as_of=2026-08-27`；
- 官方 dated Versioner endpoint 成功返回 `2026-08-27/title-16.xml?part=255` 的完整 XML；
- XML 包含 16 CFR 255.0(f) exact quote 及 clear-and-conspicuous 的完整相邻上下文；
- canonical reader URL 仍保留为 source URL，API URL 只作为 snapshot retrieval locator。

### 实现

- registry 的 FTC fetch mode 改为 `ecfr_api`，版本字段改成长期策略说明；exact as-of date 留在每个 snapshot；
- registry item 新增 title/part retrieval metadata；registry sync 会忽略非数据库配置字段，保持 clean bootstrap；
- monitor 先读官方 Title metadata，再构造 exact-date XML URL；
- XML parser 按 HEAD/P/FP/PSPACE 保留段落 grain，避免把整部 Part 压成单行；
- completeness gate 同时检查最小长度和已审阅 exact-quote marker；
- snapshot locator 保存 canonical URL、retrieval URL、retrieval mode、as-of date、latest-amended date、title、part 与 content type；
- 新增 MockTransport 单元测试，验证 metadata date 决定 retrieval URL、locator 完整性和 XML paragraph normalization。

### 运行结果

- 第一次 refresh 请求因官方 API 的短暂 HTTP failure 返回 502；系统没有把 fixture 或缓存升级为 current；
- 使用新 idempotency key 重试成功，创建 snapshot `b32f9720-9671-47ef-886c-c70bf792f689`，SHA-256 `6db6d50b8abfc85b79ffb569fa6ab9e868ff4e30d8003d4ce9303a66a60e9125`；
- exact-quote validator 创建新的未审批 Candidate G `21864f25-ab46-4212-bee8-78e877c3e7c0`；历史 fixture Candidate A 未覆盖、未删除；
- 运行态变为 5 current、2 changed、2 manual；freshness `7/9 = 0.7778`；
- 新 Faster-Whisper evaluation `bbe98b81-b177-4139-83a0-0269b7c5ea3a`：50/50、0 failures、OCR/ASR precision/recall `1.0000 / 0.8571`、7 candidates、0 approved requirements、0 mappings、operational activation false；
- backend Ruff PASS；Pytest 39 passed，1 个 upstream Starlette/httpx warning；其中新增 clean-registry sync 测试，证明带 retrieval adapter metadata 的 registry 可从空数据库初始化，而不会把非模型字段传给 SQLAlchemy；
- `make demo-rehearsal` 已更新并返回 `ready`；
- Sources UI 显示 `official_ecfr_versioner_api · as of 2026-08-27`；Requirements UI 显示 7 个 card、7 个独立 rationale form，未输入时 7 个 approve 与 7 个 needs-evidence 按钮全部 disabled；
- 前端首次并行执行四个 Compose one-off checks 时，三个命令在启动前发生依赖 API 容器命名竞争；没有删除数据或业务容器。改用 `--no-deps` 串行重跑后 ESLint、TypeScript、5 Vitest tests 和 production build 全部通过；
- Playwright 真实运行：3 passed、1 个 desktop 的 mobile-only assertion 按设计 skipped；
- 最终 eCFR tree 发布验证镜像：backend `5ba08b7ff158`、frontend `61cb2c5156ec`；backend 镜像内 API 与 eCFR adapter import、Alembic `0006 (head)` 通过，frontend 镜像内 production build 通过；
- runtime backend image 按 Dockerfile 只复制 `src`、migrations 和运行依赖，不包含 `tests/`，因此镜像内裸跑 `pytest` 正确返回 “no tests collected”；39-test 证据来自带 bind-mounted test tree 的隔离 Compose test container，不能把这两种 artifact grain 混为一谈；
- 不含凭据的临时 Docker config 已在验证后删除；
- 最终只读发布门：184 public files、27 Markdown links、privacy pattern 无命中、`git diff --check` PASS、五服务运行、API/PostgreSQL/Redis healthy、worker pong、dev migration `0006 (head)`；
- 最终治理状态复核：7 candidates、0 reviews、3 authoritative candidates、0 mappings、0 findings；FTC current candidate 仍为未审批 `candidate`；
- 没有 requirement review、mapping、finding、GitHub、schedule、cloud 或外部动作。

### Song 自测

1. 为什么读取 eCFR 官方 developer API 不等于绕过 reader-page CAPTCHA？
2. 为什么 `eCFR-daily` 版本策略仍必须配合 snapshot 的 exact as-of date？
3. 为什么 Candidate A 和 Candidate G 的 quote 相同，只有 G 才具备 authority gate 的最低资格？
4. 为什么 Candidate G 的证据合格仍不代表它的 trigger 解释一定足够精确？

## 2026-08-28 — Bounded source context 审阅投影

### 发现的缺口

Requirements 页面已有 exact quote、source type、authority、snapshot hash 和结构化解释，但 Song 仍需跳出系统才能看到 quote 的相邻条件。对 Candidate G 来说，关键短语 `representation necessitating a disclosure` 正好位于 exact quote 前面；只看被抽取的句子，难以判断 trigger 是否被写宽。

### 实现

- lineage API 从 immutable snapshot 计算 review-only context，不建立新的 source-of-truth 表；
- matcher 只为定位折叠 whitespace，再把位置映射回原始文本；
- 返回 exact-match state、原始 line range、excerpt SHA-256、truncation flag 和 plain-text excerpt；
- excerpt 包含前后相邻行且最多 6,000 characters，不向每张 card 发送整份 snapshot；
- React 只用普通 `<pre>` 渲染 untrusted text，不使用 raw HTML；
- 找不到 quote 时 UI 显示错误并禁用 approve，Song 仍可选择 needs-evidence 或 reject；
- ADR 0003 记录为什么采用 bounded projection 而不是 full-snapshot payload。

### 验证

- whitespace 跨行 quote 的 unit test 与 missing-quote test：PASS；
- lineage join test 验证 context 与 snapshot 同源：PASS；
- backend Ruff：PASS；完整 PostgreSQL Pytest：40 passed，1 upstream warning；
- frontend ESLint、TypeScript、5 Vitest tests、production build：PASS；
- Playwright：3 passed、1 intentional desktop skip；
- 运行态 7/7 candidate context 均找到 exact quote，最大 excerpt 1,793 characters；
- FTC Candidate G context 为 lines 10–13、SHA-256 `a6716e7d8e3143b2b9a2031be740d92e86a07acdbe0862076e421395f173b2ed`、未截断，并包含 `necessitating a disclosure`；
- 浏览器 QA 显示 7 个 bounded-context cards 和 7 个 rationale forms；未输入时所有 approve buttons disabled；
- 最终 context-tree 镜像：backend `462644c613bd`、frontend `6cfef3d4da89`；backend 镜像内 OpenAPI 明确把 `review_context` 列为 RequirementLineageOut required property，Alembic `0006 (head)` 通过，frontend 镜像内 production build 通过；
- 临时无凭据 Docker config 已删除；
- post-context 发布门：185 public files、28 Markdown links、privacy pattern 无命中、`git diff --check` PASS、API healthy、worker pong、demo rehearsal ready；
- reviews / mappings / findings 仍为 `0 / 0 / 0`。

### Song 自测

1. 为什么 exact quote 存在仍不代表 actor/trigger/action 的解释正确？
2. excerpt hash 能证明什么，不能证明什么？
3. 为什么 review context 不应成为第二份可独立修改的 source table？
4. 为什么 source text 即使来自官方，也必须在 UI 中按 untrusted plain text 处理？

## 2026-08-28 — TikTok 官方 FAQ adapter、9/9 freshness 与当前 candidates

### 阶段目标

消除最后两个 `manual_snapshot_required`，但只在能证明来源是 TikTok 官方、请求不依赖登录或 Cookie、内容可重复抓取并能做 identity/completeness validation 时升级；否则继续保留 manual 状态。

### 公开事实核验

- legacy commercial support URL 302 到 `www.tiktok.com/support/faq_detail?id=7636670088170904085`；
- legacy AIGC support URL 302 到 `www.tiktok.com/support/faq_detail?id=7636670084747893268`；
- 未登录浏览器完整渲染 commercial article，并显示当前 disclosure setting、Promotional content、Paid partnership、TikTok One、Content Suite 等正文；
- TikTok 当前官方 frontend bundle 调用 `/feedback/1/faq_detail_by_id/`，参数包括 FAQ ID、English locale、US country、`app_id=1284` 与 `app_key=tiktok-web`；
- 使用新的 credential-free HTTP client（不携带 Cookie、token、账号或 session）可重复得到 `status_code=200`、`status_message=success` 和相同 FAQ identity；
- 该 endpoint 是 TikTok 当前公开 web client 使用的一方基础设施，不是已文档化的 developer API 或稳定性承诺；任何 URL、schema 或 identity drift 都必须 fail closed；
- commercial article 当前名称是 `Promoting a brand, product, or service`；AIGC article 当前名称是 `About AI-generated content`；两页仍未公开 version、published date 或 effective date。

浏览器只用于核对 visible text 与发现公开请求形态。最终 snapshot 来自直接、无凭据、可重复的官方 JSON endpoint，而不是浏览器 DOM、搜索摘要或第三方镜像。

### 实现

- registry version 升到 `2026-08-28.4`；两个 source title 与当前 API article title 对齐；
- fetch mode 改为 `tiktok_faq_api`；registry 固定 FAQ ID、expected title、expected marker、locale `en`、country `US`；
- adapter 只接受 `support.tiktok.com` canonical URL，并把 retrieval host 固定为 `www.tiktok.com`；
- API response 必须同时通过 HTTP status、JSON status、FAQ ID、exact title、article HTML type、minimum length 和 reviewed marker；任何 drift 都进入显式 fetch failure，不创建 snapshot；
- HTML 转 plain text 后折叠 inline-link whitespace，并清除标点前的异常空白；locator 保存 canonical URL、exact retrieval URL、FAQ ID、title、locale/country、default-language/AI-translation flag、style version 和 content type；
- 新增两个参数化 happy-path tests 和一个 title-drift rejection test；MockTransport 同时断言 host、path、FAQ ID、country、language；
- open-source benchmark 重新核对 OPA、NIST OSCAL、ComplianceAsCode 与官方 `c2pa-python`；只采用 rule/data separation、lineage、single-source rule metadata 和 provenance evidence 模式，不新增 OPA service，不声称 OSCAL conformance，也不复制上游代码。

### 遇到的错误与诊断

commercial 第一次真实 refresh 返回 502，而 AIGC 成功。原始 HTML 把 `turn on the content disclosure setting` 放在 `<a>` 中，句号在 `</a>` 之后；通用 parser 因此生成 `setting\n.`。最初 expected marker 使用正常的 `setting.`，严格 substring check 失败。

修复不是降低或删除 completeness gate，而是在 marker comparison 和 stored plain text 上执行确定性的 whitespace/punctuation normalization。测试 fixture 特意把 marker 拆到 inline anchor 内，并断言 snapshot 不再包含 `\n.`。重试后两页均成功。

### 真实运行结果

- commercial authoritative snapshot：`95e1af51-02f7-4641-b139-706d12a78934`，SHA-256 `065d922d7a6947d8f3f6a0414cfb693188b54ff4bdd060cec5570728384fefe7`；
- AIGC authoritative snapshot：`e4d70c39-8c36-40ed-b44f-0c7903cb9083`，SHA-256 `d200f43571e9a092e4027f8a350d3562372b390d74bb864ed2f5accb2378de27`；
- commercial current candidate：`d41e4d99-3407-454e-8af0-ab1bc48b8873`；AIGC current candidate：`8935556c-68c5-46c2-8c16-f207fa2c929b`；两者 exact quote validator、legal-language guard 与 authoritative approval gate 均通过，但 status 仍为 `candidate`；
- bounded context：commercial lines 15–19、SHA-256 `6e2420cec3c01c8e690a91679bd5b17b7f3984a384944b71366a08e70ee5a944`；AIGC lines 26–30、SHA-256 `4779f1ad981f5af8b7869ccdca4017ec4360a349044c35379e46a0cbd3a8cf35`；
- source state：5 `current` + 4 `changed`，freshness `9/9 = 1.0000`；`changed` 表示当前 authoritative snapshot 与前版不同，不表示 stale；
- requirement backlog：9 candidates，其中 5 authoritative、4 historical fixture；reviews、mappings、findings 仍为 `0 / 0 / 0`；
- Faster-Whisper evaluation `80f1763e-c2bf-4d02-8941-3d544d0d8b84`：50/50、0 failures、OCR/ASR precision/recall `1.0000 / 0.8571`、source freshness `1.0000`、provider selector `extractor_matches_provider`、operational activation false；50 份媒体 evidence 被复用，因此 cached latency 不作为新 throughput claim；
- backend Ruff PASS；完整 PostgreSQL Pytest `43 passed`，1 个 upstream Starlette/httpx warning；
- frontend ESLint、TypeScript、5 Vitest tests、production build PASS；Playwright 3 passed、1 intentional desktop skip；
- 浏览器 Sources QA 显示两个 `tiktok_faq_api` source、两个 FAQ ID、`en-US` 和 exact article identity；Requirements QA 显示 9 cards、2 个 FAQ retrieval identities、9 个 rationale forms，空 rationale 时 9 个 approve buttons 全部 disabled；
- public-tree checker：185 files PASS；repository-local Markdown links：28 PASS；`git diff --check` PASS；demo rehearsal `ready`；worker ping 1 node online；
- final release-check images 从当前 public tree 重新构建成功：backend manifest-list SHA-256 `b77aa655dd4a6cd38076bd2a2e6ae0a088491a49f0197b3ab42ee91769b8277d`，frontend manifest-list SHA-256 `08de7840f2ac10e305c0ca151fb030733cb8f983f668e3eea507de838d24d00a`；backend image import 到 `_fetch_tiktok_faq_api` 且 Alembic `0006 (head)`，frontend image 内 production build PASS；
- 没有 requirement review、mapping、finding、GitHub、schedule、cloud 或外部动作。

### Song 需要理解

1. “官方页面能在浏览器打开”与“后台拿到了可审计 snapshot”不是同一件事；后者需要稳定 retrieval、identity validation、hash 和 diff。
2. FAQ ID 是内容 identity 的强信号，但不是公开 version number；文章内容仍必须每次 hash 和 diff。
3. `changed` 是成功刷新后的差异状态，所以 freshness 仍计入；失败才不能把旧内容叫 current。
4. exact quote 通过只说明字符串来自当前 snapshot；actor、trigger、exception 与 control mapping 仍需要 Song 判断。

### Song 自测

1. 为什么不能把浏览器 `innerText` 直接当成后台 source snapshot？
2. 为什么 adapter 必须同时校验 FAQ ID 和 article title？
3. 为什么 TikTok AIGC 的 auto label/C2PA 更像独立 evidence path，而不是对所有 creator labeling requirement 的普遍例外？
4. 为什么 9/9 freshness 仍不意味着系统已经“判断合规”？

## 2026-08-28 — GitHub 展示截图与公开资产 QA

### 阶段目标

发布前总审计发现代码、手册、架构图和 10 分钟 demo 都已存在，但公开仓库没有实际产品截图。这会削弱招聘方在不启动 Docker 时理解系统的能力，也不满足原计划的 Week 4 screenshot 交付。

### 本次实现

- 使用本地运行中的 React UI 和现有合成数据生成 5 张 `1280 × 720` 截图：Overview、TikTok Sources、Requirement Review、Media Evidence、Evaluation；
- README 只展示三张最能说明边界和 lineage 的图片，另外两张放入独立 `docs/SCREENSHOTS.md` inventory，避免 README 变成长图集；
- inventory 记录 capture date、approval state、数据性质、每张图证明什么和不能证明什么；
- evaluation 图片明确标注 Faster-Whisper evidence、50/50 cases、保留的 recall 缺口、operational rules false；文档同时说明 cached-evidence run 不是新的媒体吞吐 benchmark；
- requirement 图片保留 `candidate`、source type、FAQ identity、snapshot hash、exact quote 与 bounded untrusted context，不能误读为已批准规则；
- media 图片使用虚构 `NovaGlow`、虚构 case 和合成 transcript，没有真实 creator、merchant 或 post。

### 遇到的错误与修复

浏览器截图接口最初返回 JPEG bytes，但文件名使用 `.png`。仅看扩展名会让 GitHub、内容类型检测和后续资产工具产生不一致。没有把这个结果直接提交，而是用本地图片转换工具重新编码，并逐个用 `file` 验证为真实的 `PNG image data, 1280 x 720`。

### 验证

- 5 张图片逐张人工视觉检查：导航状态、主要证据和免责声明可见，没有浏览器地址栏或个人账号；
- OCR privacy scan：个人路径、邮箱、Cookie、token、password、secret、session、私人项目名、真实 creator/merchant indicators 均无命中；
- 截图只进行了本地只读导航和 case selection，没有创建 review、mapping、finding、report、GitHub、schedule、cloud 或外部动作；
- Song 对截图、README、简历措辞和 Git history 的最终人工审阅仍保持未勾选。

### Song 需要理解

1. Screenshot 是方便招聘方快速理解的展示证据，不是自动测试或最新来源证明。
2. `changed` badge 只证明当前 authoritative representation 与前一 snapshot 有 diff，不能单凭图片声称 TikTok 改了政策。
3. `candidate`、`operational rules false` 和 synthetic-data 说明必须在截图及口头 demo 中保留，不能为了“好看”隐藏。

### Song 自测

1. 如果面试官问为什么没有绿色 `Compliant`，你如何用系统边界回答？
2. 为什么 README 只放三张图，而详细 evidence 和 evaluation 放 inventory？
3. 截图中的 50/50、precision/recall 和 freshness 分别证明什么，不能证明什么？

## 2026-08-28 — Ollama 固定 Schema、Authority Guard 与真实无写入回归

### 阶段目标

完成度审计发现：仓库已有 Ollama adapter 和 deterministic quote guard，但公开可引用的成功候选主要来自 verified fixtures；旧 adapter 只请求普通 JSON，再手工检查部分字段，无法证明无效日期、错误类型、额外字段和 authority conflation 都能 fail closed。

### 官方实现依据

Ollama 官方 structured-output 文档说明 `format` 可以直接接收 JSON Schema，并建议用 Pydantic `model_json_schema()` 生成 schema、再用 Pydantic 验证 response。项目采用该模式，但没有把 Ollama 的 schema generation 当作最终安全边界。

### 本次实现

- 新增严格 `RequirementExtractionPayload`：11 个字段全部有类型、长度或范围限制，`exception` 和 `effective_date` 虽可为 null 仍必须存在，额外字段 forbidden；
- `/api/generate` 的 `format` 改为完整 Pydantic JSON Schema，temperature 为 0、thinking 关闭、generation 上限 800 tokens；
- prompt 要求 exact quote 逐字来自 untrusted source，并要求 jurisdiction 与 source metadata 完全相同；
- 应用层在 JSON Schema 之后再次运行 Pydantic；无效日期、confidence 超界、额外字段和 string/list drift 都以显式 `ValidationError` fail closed；
- deterministic validator 扫描 actor、trigger、action、exception、jurisdiction、scope 和 uncertainties，而不再只扫四个字段；
- 新增 `jurisdiction_matches_source`，模型不能把 TikTok platform policy 和 FTC guidance 合并到 jurisdiction；
- 新增完全无数据库写入的 `make verify-local-model`；它从 API 读取当前 source/snapshot，通过 API 容器调用 Mac host Ollama，只打印 candidate preview、guards、model digest 和 latency；
- 新增 `docs/IMPLEMENTATION_AUDIT.md`，把原四周计划逐项分成 `VERIFIED_LOCAL`、`PENDING_SONG`、`PENDING_HOSTED`、`ONGOING_ALIGNMENT`。

### 真实失败链

1. 直接用 Mac system Python 运行时缺少 `httpx`，在 inference 前 `ModuleNotFoundError`；正式命令改在项目 API 容器中执行。
2. 第一次 full-snapshot run 超过 response wait，返回 `ReadTimeout`；没有计为通过。
3. 关闭 thinking、限制输出后，full-snapshot 很快返回 JSON，但 `required_action` 是 list 而 schema 要求 string；Pydantic 正确拒绝。
4. 第一次 bounded run 的程序用 literal string 搜 anchor，而 current snapshot 中存在换行差异；改成 whitespace-tolerant anchor matching。
5. 接着的 bounded output schema 和 exact quote 都通过，但 jurisdiction 写成 `GLOBAL_PLATFORM including FTC guidance`。这暴露 validator 漏扫 authority 字段；该次“结构通过”被撤销，不能作为最终成功证据。
6. 加入 exact source-jurisdiction binding 后重新运行，模型返回 `GLOBAL_PLATFORM`，所有 guards 通过。

### 最终真实结果

- source：current TikTok commercial-content snapshot `95e1af51-02f7-4641-b139-706d12a78934`；
- snapshot SHA-256：`065d922d7a6947d8f3f6a0414cfb693188b54ff4bdd060cec5570728384fefe7`；
- model：`song-local:latest`，digest `537ba19b64712ce02edf7b25f457746e772f65df9fe95fdcbaa89fa227685ae3`；
- context：5,773-character full snapshot 中、以已复核 exact quote 为 anchor 的 4,000-character bounded window；不是 autonomous discovery；
- schema valid、exact quote、quote guard、interpretation guard、jurisdiction match：全部 PASS；
- total duration 6,306.473 ms，prompt 1,662 tokens，output 214 tokens；单次 warm run，不是 throughput SLA；
- 正式 `make verify-local-model` 再次 PASS：5,371.352 ms、相同 1,662 prompt tokens、226 output tokens；scope/uncertainties 有轻微变化，因此公开报告同时保留两次结果；
- persistence：database write false、candidate false、review false、external action false；
- 公开报告：`reports/LOCAL_MODEL_EXTRACTION_REPORT.md`。

### Song 需要理解

1. Ollama 接受 JSON Schema 不等于模型一定遵守；Pydantic 必须再次验证。
2. exact quote 正确也不能阻止模型在 jurisdiction、scope 或 uncertainty 中混淆不同 authority。
3. bounded anchor-assisted interpretation 与 autonomous discovery 是两种不同能力，简历和面试必须说清楚。
4. 失败结果不是项目污点；能复现、拦截、修复并保留限制，才是 AI Backend/FDE 的核心证据。

### Song 自测

1. 为什么第一次 schema-valid output 仍然不能进入 candidate state？
2. 为什么不能把 model jurisdiction 静默改写成 registry jurisdiction 后假装成功？
3. `make verify-local-model` 为什么没有数据库写入路径？
4. 面试官问“这是 agent 还是规则系统”时，你如何解释 LLM 与 deterministic validation 的分工？

## 2026-08-28 — API Contract 与恶意媒体 Admission Gates

### 阶段目标

继续用原计划的明确不变量审计当前实现，而不是因为 demo 绿色就停止。重点检查：所有 mutation 是否真的要求 idempotency、review 是否真的要求人工 identity/rationale、SSRF/redirect 是否有 fail-closed tests，以及 Threat Model 中的媒体限制是否已经从“planned”变成代码。

### 审计发现

- 当前 OpenAPI 有 16 个 mutation operations，全部声明 `Idempotency-Key`；三个 `/review` endpoints 还声明 `X-Reviewer-Id` 和 `HumanReviewRequest`；
- 这项事实以前只有函数签名和个别 idempotency tests，没有一个能在未来新增 endpoint 时自动失败的全 OpenAPI contract test；
- Source Monitor 已实现 credential-free HTTPS、registry-host allowlist 和 `follow_redirects=False`，但缺少 localhost/link-local/userinfo/redirect 的直接回归；
- Media Worker 只执行 path、size、extension、guessed MIME 和 hash；Threat Model 仍把 magic bytes、duration、resolution 和 frame count 写成 planned controls，属于真实实现缺口。

### 本次实现

- 新增全 OpenAPI contract test：任何 POST/PUT/PATCH/DELETE 缺 `Idempotency-Key` 都失败；任何 `/review` 缺 reviewer header、rationale required 或 20-character minimum 都失败；
- 新增 SSRF tests：HTTP、userinfo、`127.0.0.1`、`169.254.169.254` 在 network client 构造前被拒绝；302 不跟随、不创建 snapshot，并把 source 设为 `manual_snapshot_required`；
- Media admission 增加数据库 declared MIME、`.mp4`、ISO BMFF `ftyp` signature、project-root confinement、size、SHA-256；
- FFprobe 增加 duration、width、height、`nb_frames`、`r_frame_rate`；默认上限为 180 seconds、3840×3840、10,800 video frames；缺失/无效 metadata 返回 415，超限返回 413；
- admission 在 OCR/ASR/C2PA 前执行，所有 subprocess 保留 timeout；backend image 已使用 UID 10001 的非 root user；
- 新增 `make verify-media-fixtures`，逐个对 50 个 public MP4 调用 production `_asset_path`、`_probe`、`_validate_probe`；
- deterministic GitHub E2E 在 Playwright 前运行同一 verifier，不调用 OCR/ASR、不下载 Whisper。

### 真实验证

- unsafe URL/redirect tests：5 passed；
- media admission unit tests：3 passed；
- 50-fixture production validation：50/50 PASS；
- observed maxima：38,977 bytes、2.625 seconds、320×180、63 video frames；
- configured limits：25,000,000 bytes、180 seconds、3840×3840、10,800 frames；
- verifier persistence：false。

### Song 需要理解

1. `.mp4` 扩展名和 `video/mp4` 字符串都不是文件真实性证明，至少还要检查 container signature 和 FFprobe metadata。
2. Hash 一致只证明文件与注册资产一致，不证明文件安全；资源上限必须在重工具运行前执行。
3. SSRF allowlist 与 redirect 禁止解决的是“系统能访问哪里”，不是“那个网页的解释一定正确”。
4. Idempotency 是全 API contract；只测试一个 endpoint 不能证明所有 future mutations 都安全。

### Song 自测

1. 为什么 path resolve check 必须在 `is_file()` 之前？
2. 为什么 302 要进入 manual review，而不是自动跟随到新 host？
3. 为什么 CI 只运行 admission verifier，而不是下载 Whisper 做 50-case 实时 ASR？
4. 413 和 415 在本项目中分别表达什么失败？

## 2026-08-28 — Celery Worker 重投、重试与业务幂等证明

### 阶段目标

原手册写过“worker 崩溃后根据幂等键重试”，但当时只有 API idempotency 和服务层查询，没有证明 Celery delivery 设置真的允许 worker-loss redelivery，也没有直接执行过自动 retry。把架构意图当实现结果会误导面试官，因此这一轮核对 transport、task 和 PostgreSQL 三层。

### 官方依据与设计判断

Celery 5.6 官方文档说明：late acknowledgement 会让消息在 task 执行后才 ack，因此 worker 中途崩溃时任务可能重复执行；`task_reject_on_worker_lost` 可以让丢失 worker 的消息重新入队，但官方同时警告必须保证任务幂等并防止循环。官方也建议长任务配合 prefetch multiplier 1。项目依赖范围仍是 `celery>=5.4,<6`，当前容器加载的 task 属性按该合同验证。

没有把设置全局打开。heartbeat 每次本来就代表一个独立事件；evaluation 每次先创建新 `EvaluationRun`，尚未具有稳定 run key。若对它们全局 late-ack/autoretry，会把不同事实错误地混为一次“exactly once”运行。

### 本次实现

- `media.analyze_case` 增加 `acks_late=True`、`reject_on_worker_lost=True`；只对 `RuntimeError` 自动退避重试，最多两次；
- Celery app 使用 `worker_prefetch_multiplier=1`，本地 Compose worker 使用 `--concurrency=1`，适配 FFmpeg/OCR/ASR 的资源特征；
- media completion audit event 记录 task ID、retry count 和 broker redelivery flag；
- 保留 evaluation early ack、无 autoretry，并在文档说明失败后显式创建新 evaluation 的 provenance 语义；
- 扩展 deterministic rule regression：同一 case/mapping/rule 再跑返回相同 TestRun/Finding ID，表计数仍为 1；
- 新增 Celery task contract test和真实 eager retry test：第一次 synthetic `RuntimeError`，第二次成功，执行次数严格等于 2。

### 真实验证

- worker/retry/idempotency 定向测试：5 passed；
- worker 容器按新 Compose config 重建后，`inspect ping`：1 node online；
- registered tasks：`evaluation.run_gold`、`media.analyze_case`、`system.record_worker_heartbeat`；
- live pool max concurrency：1；live prefetch count：1；
- 容器内 task inspection：media late ack true、reject-on-worker-lost true、max retries 2、autoretry only RuntimeError；evaluation late ack false；
- 以上只证明单 worker 本地 topology。没有做 kill-in-flight chaos test，也没有实现多 worker 对同一 case 的并发 claim，因此不声称水平扩展 exactly-once。

### Song 需要理解

1. API idempotency key 防止同一个 mutation request 重复入队；它不等于 broker 只投递一次。
2. Celery late ack 提高崩溃可恢复性，同时必然要求 task 可以被重复执行。
3. 项目把 exactly-once 目标改写为更可实现的组合：at-least-once delivery + PostgreSQL unique business grain + auditable attempt metadata。
4. evaluation 的“再次运行”是新的 benchmark provenance，不应该偷偷复用旧 run ID。

### Song 自测

1. 为什么不能全局打开 `task_acks_late` 和 autoretry？
2. task ID、EvidenceItem ID 和 TestRun ID 分别属于哪一种 grain？
3. worker 在写完 Finding、但 ack 前崩溃，重新执行时为什么不会再创建第二个 Finding？
4. 若要扩展到四个 worker 并允许同一 case 并发提交，还缺哪个 case-scoped 控制？

## 2026-08-28 — 九来源再刷新、Latest-Snapshot 审批门与依赖锁

### 阶段目标

长期 goal 要求持续与最新公开信息对齐。已有 9/9 freshness 指标，但各来源的 `last_checked_at` 并不在同一运行窗口；同时旧审批门只判断 parent snapshot 的 `fetch_status`，没有证明它仍是该 source 最新权威版本。依赖范围也会在不同构建日解析出不同 transitive versions。

### 来源刷新与真实 diff

- 第一次 zsh 批处理把多行 source IDs 保留在一个 scalar 中，curl 报 `Malformed input to a URL function`；循环末尾的 `echo` 又让 shell 返回 0。该次没有访问来源，也没有计为 refresh；
- 改为 `while read` 并使用 `set -e` 后，九个 allowlisted source 全部刷新成功；没有登录、Cookie、token、redirect bypass、cloud model 或 external action；
- 最新状态为 7 `current` + 2 `changed`，九条 `last_checked_at` 都进入同一刷新窗口；
- 两条 changed 是 FTC Disclosures 101 与 Endorsement FAQ。逐行比较 parent/current immutable snapshot 后，全部 27 added、4 removed lines 都属于 global navigation/footer；文章正文没有观察到变化；
- 因此 `changed` 仍保留为 representation hash 事实，但文档不把它升级成“FTC 政策变化”。

### 审批门缺口与修复

历史 `current/manual_snapshot` 仍可能在新 snapshot 创建或下一次 refresh 失败后被 API 接受。这会让“immutable history”错误地继续拥有新授权能力。

本轮新增 `source_approval_evidence`，同时检查：parent evidence type、source 当前 freshness state、以及 parent 是否等于该 source 按 retrieved/created/id 排序的 newest authoritative snapshot。Lineage 返回 `latest_authoritative_snapshot_id` 与具体 blockers；React 显示原因并禁用 approve；review service 返回 409；PostgreSQL migration `0007` 用独立 trigger 复核同一不变量。

当前运行态验证：五个 EU/eCFR/TikTok 候选的 parent ID 与 latest authoritative ID 相同，仍只是可审候选；四个历史 fixture 候选显示 fixture + superseded blockers。没有创建 review、mapping 或 finding。

### 依赖与 CI 对齐

- npm registry 只显示两个兼容 patch：`@vitejs/plugin-react 6.1.1`、`@testing-library/react 16.3.3`；升级后 lint、typecheck、5 component tests 与 production build 通过；
- TypeScript 7.0.2 虽是 registry latest，但仍不满足 current `typescript-eslint 8.68.0` 已验证组合，保留 TypeScript 6.0.3；
- pnpm frozen lock 的 supply-chain policy PASS；production audit 为 0 vulnerabilities；
- Python direct packages 按 PyPI JSON registry 核验，容器当前主版本与 allowed ranges 一致；`pip-audit` 对已安装环境和新 constraints lock 均为 0 known vulnerabilities，本地 project package 因不在 PyPI 被明确 skipped；license inventory 成功输出；
- 新增 Python 3.11 `backend/requirements.lock`，覆盖 runtime/dev/media extras；Dockerfile 与 CI 通过它约束解析并执行 `pip check`，dependency job 对 lock 运行 audit；
- 第一次 `pip-audit` 因 appuser 的 local bin 不在 PATH 没有执行，改用 `python -m pip_audit` 后才算真实 PASS；
- 第一次 YAML parser 使用 Mac system Python，缺少 PyYAML；第二次 API 容器没有挂载 `.github`；最终使用 Ruby stdlib 直接读取工作树，6 CI jobs parse PASS；
- 第一次 Docker build 被 sandbox 拒绝写 Buildx activity metadata；授权同一明确 build 后，正常 `docker compose build api worker web` 成功。

### 镜像与定向验证

- migration `0006 -> 0007`：PASS；
- stale/fresh source、lineage 与 approval targeted tests：11 passed；
- new API image manifest-list：`60b3b0f5c219f190c574b2e6cea0710899337f9f52453c9c23c8359ae9fda21a`；
- new worker image manifest-list：`ab0cace9a3beb9198fdd53c2229a3406e5d73d107156e6e2bacebb7897fbc1dc`；
- new web image manifest-list：`88d26c977431f37ab31d74b26f965571c24c3e142b8527f5a07f3056f175c1f7`；
- backend build 从 lock 安装并在 image 内 `pip check` PASS；web build 从 frozen pnpm lock 安装成功。

### Song 需要理解

1. Immutable 表示旧证据不能被改，不表示旧证据永久拥有授权能力。
2. `changed` 是 representation diff，不是 semantic-policy-change classifier。
3. `pyproject.toml` 的 range 负责允许什么，constraints lock 负责本次构建解析成什么，`pip-audit` 负责当前已知漏洞；三者不是同一件事。
4. “registry latest”仍需经过 compatibility 和项目回归，TypeScript 7 是当前反例。

### Song 自测

1. 为什么 source refresh 失败时，即使旧 snapshot 的 `fetch_status=current` 也不能批准新 requirement？
2. 为什么不删除只包含导航变化的 FTC snapshot？
3. Python constraints lock 为什么仍不能取代 vulnerability scan？
4. 面试官问“你如何避免 stale compliance rule activation”时，你如何从 source → snapshot → candidate → DB trigger 讲完整路径？
### 2026-08-28：GitHub Actions 官方版本复核

- 通过各项目的 GitHub Releases API 核验：`actions/checkout@v7.0.1`、`actions/setup-python@v7.0.0`、`actions/setup-node@v7.0.0`、`pnpm/action-setup@v6.0.10` 和 `gitleaks/gitleaks-action@v3.0.0`。
- 发现 CI 仍使用 `gitleaks/gitleaks-action@v2`。官方 v3 迁移说明明确写明它只把运行时从 Node 20 升到 Node 24，inputs、outputs 和行为不变，因此把工作流升级为 `@v3`。
- 这次升级是对 GitHub Actions 运行环境的兼容性修复；仍需在 Song 批准首次推送后，以 hosted GitHub Actions 的真实运行结果完成最终验证。
