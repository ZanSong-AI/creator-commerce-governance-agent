# Requirement 人工审阅与学习工作簿

版本：2026-08-28 九来源同窗口刷新与 migration 0007 复核版
对象：当前数据库中的 9 个未审批 `requirement_candidate`，按 7 组学习练习组织：4 个历史 fixture 候选，以及 5 个 latest-authoritative EU/eCFR/TikTok 候选
审批者：Song
边界：本文件是工程审阅材料，不是法律意见，也不会替 Song 写入审批结果。

当前 authority gate：四个历史记录的 parent 是 `public_test_fixture`，且都已有更新的 authoritative snapshot，因此 UI、API 和 PostgreSQL migration `0007` 会同时显示 fixture/superseded blockers 并拒绝 `approved`；Song 只能选择 `needs_more_evidence` 或 `rejected`。五个当前候选分别指向两个 TikTok、两个 EU 和一个 eCFR latest-authoritative snapshot，技术上可以进入审批，但是否批准仍完全由 Song 判断。未来如果来源刷新失败或出现更新的 authoritative snapshot，这五个候选也会立即失去新审批资格，而历史记录保持不变。

## 1. 这一步到底在做什么

现在系统里有九条“候选 requirement”，工作簿把相同主题的历史/当前版本合并成七组练习。它们不是九条已经生效的产品规则，更不是九个违法判断。每条候选只是把一段公开来源拆成结构化字段：谁在什么情况下需要做什么、有什么例外、适用什么地区和范围。

Song 的审阅不是判断某条真实视频是否合法，而是在回答更窄的工程问题：

> 这段来源原文是否真实存在？Agent 的结构化解释是否忠实、范围是否足够窄，能否授权下一步提出 product-control mapping candidate？

批准 requirement 后也不会自动运行控制。系统仍需第二次人工审批 mapping，之后 deterministic test 才可能产生 `control_issue_candidate`；finding 还需要第三次人工 disposition。

## 2. 审阅前必须区分的四层

| 层 | 它是什么 | 它不是什么 |
|---|---|---|
| Source text | 官方来源里的原文和上下文 | Agent 的总结 |
| Requirement candidate | Agent 对 actor、trigger、action、exception、scope 的结构化解释 | 已批准规则或法律结论 |
| Control mapping candidate | requirement 与可测试产品控制之间的候选连接 | 自动生效的执法规则 |
| Finding candidate | 已批准控制对一份证据运行后的候选问题 | 违法、欺骗或不合规认定 |

## 3. Song 每次审阅的标准动作

对每一条候选都按相同顺序：

1. 打开官方 URL，确认 publisher 和 source type；
2. 在来源中定位 exact quote；
3. 阅读 quote 前后至少一段，避免断章取义；
4. 对照 actor、trigger、required action、exception；
5. 检查 jurisdiction、effective date、scope；
6. 确认没有把平台政策写成法律，也没有把 guidance 写成正式法规；
7. 先检查 UI 的 source authorization blockers；只有 parent 是 `current/manual_snapshot`、source 最新 refresh 仍 fresh、parent ID 等于 latest authoritative snapshot ID 时，`approved` 才可能可用，否则选择 `rejected` 或 `needs_more_evidence`；
8. 用自己的话写 rationale，至少说明“核对了什么”和“为什么这个 disposition 合适”。

一个合格 rationale 示例：

> I verified the exact quote and surrounding context in the named official source. I am approving this narrow requirement interpretation only for creating a synthetic product-control mapping candidate; this is not a legal conclusion about any real content.

如果来源当前无法重新取得、适用主体不清楚、过渡日期被简化或例外不完整，选择 `needs_more_evidence` 比勉强批准更正确。

## 4. Candidate A — FTC 多模态披露

### 身份

- stable key：`ftc-clear-conspicuous-multimodal`
- 当前数据库 ID：`5131b2a5-3761-49b2-8cad-f93a42bf4967`
- source type：`administrative_guide`
- jurisdiction：`US`
- locator：`16 CFR 255.0(f)`
- 官方来源：[eCFR 16 CFR 255.0](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-B/part-255/section-255.0)

### 原文与 Agent 解释

Exact quote：

> if the representation is made through both visual and audible means, the disclosure should be made in the communication's visual and audible portions.

候选结构：

- actor：advertiser or endorser；
- trigger：需要披露的 endorsement representation 同时通过 visual 和 audible means 表达；
- action：在 visual 和 audible portions 都提供 disclosure；
- exception：当前候选未记录；
- scope：synthetic social-media promotional video。

### 2026-08-28 复核事实

- eCFR 页面显示 Title 16 内容截至 2026-08-27；
- exact quote 仍存在于 16 CFR 255.0(f)；
- 同一段还要求 disclosure 容易注意和理解，并讨论视觉尺寸、对比度、位置、持续时间以及音频音量、速度和节奏；
- 255.0(a) 明确把 Part 255 定义为 FTC 对其执法法律的 administrative interpretations，不能把本项目 source type 简化成“statute”。

### 需要 Song 判断

- 当前 trigger 是否清楚表达“representation necessitating a disclosure”，而不是误写成所有带声音和画面的视频？
- 只映射 `visual_disclosure_detected` 和 `audio_disclosure_detected` 是否过窄？是否还应提出 `disclosure_prominence_review_required`？
- 当前 scope 是否明确限定在合成演示案例，而不是对真实内容作结论？

### 审批影响

如果批准：只解锁下一步 mapping candidate，不证明某个视频满足 FTC 要求。
如果需要更多证据：可以要求把 255.0(f) 的完整 clear-and-conspicuous 上下文加入本地 runtime snapshot 后再审。
如果拒绝：应说明是 quote、结构化解释还是 scope 有问题。

当前 Candidate A 还会显示 `public_test_fixture` 与 superseded blockers；即使 quote 在最新 eCFR 中仍存在，也不能用这条历史 fixture record 授权 mapping。应与 Candidate G 分开 disposition。

### Song 的决定

- historical fixture disposition（只能 rejected / needs_more_evidence）：`__________`
- rationale：`____________________________________________________________`
- 复核日期：`__________`

## 5. Candidate B — TikTok commercial-content disclosure setting

### 身份

- stable key：`tiktok-commercial-disclosure-setting`
- 当前 authoritative candidate ID：`d41e4d99-3407-454e-8af0-ab1bc48b8873`
- 历史 fixture candidate ID：`e2b42a6f-bced-41b7-a50d-cb9ccbffcb1e`（不可审批，只保留 lineage）
- source type：`platform_policy_help`
- jurisdiction：`GLOBAL_PLATFORM`
- locator：`Requirements for promoting a brand, product, or service`
- 官方来源：[TikTok Promoting a brand, product, or service](https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/promoting-a-brand-product-or-service)

### 原文与 Agent 解释

Exact quote：

> When posting content that promotes a brand, product, or service on TikTok, you must turn on the content disclosure setting.

候选结构：

- actor：TikTok creator；
- trigger：在 TikTok 发布推广 brand、product 或 service 的内容；
- action：打开平台 content disclosure setting；
- exception：当前候选未记录；
- scope：synthetic TikTok-like creator commerce post；platform policy, not law。

### 2026-08-28 复核事实与限制

- TikTok 当前官方 FAQ JSON snapshot 逐字包含相同 exact quote；
- 页面上下文同时包括 own business 和为第三方品牌换取 payment 或 other incentive 的内容；
- 页面说明平台标签会区分 `Promotional content` 与 `Paid partnership`；
- TikTok 页面没有公开版本号，registry 必须保留 `not_published`；
- canonical support URL 当前重定向到 FAQ ID `7636670088170904085`；专用 adapter 已在无登录、无 Cookie 条件下取得并校验官方 JSON 正文；
- 当前 snapshot ID `95e1af51-02f7-4641-b139-706d12a78934`，SHA-256 `065d922d7a6947d8f3f6a0414cfb693188b54ff4bdd060cec5570728384fefe7`；bounded review context 为 lines 15–19，exact quote 已找到；
- TikTok 未发布版本号，因此 `version` 仍是 `not_published`；不能把抓取日期伪装成政策生效或发布日。

### 需要 Song 判断

- actor 写作 `TikTok creator` 是否足够，还是应强调 own-brand 与 third-party branded content 两类？
- trigger 是否忠实覆盖“promotes a brand, product, or service”，而没有缩窄成只有 paid partnership？
- own-brand 与 third-party branded content 是否应拆成两个更窄的 trigger，还是当前统一 requirement 足够？
- 未来 mapping 是否只测试 synthetic metadata flag，且明确不把 flag 等同于 FTC 的 clear-and-conspicuous 判断？

### 审批影响

如果批准：下一步可以提出 `platform_disclosure_flag_present` mapping candidate。
这项批准只授权平台产品控制建模，不把 TikTok policy 变成美国法律，也不说明真实 TikTok 帖子有问题。

### Song 的决定

- 当前 authoritative candidate disposition：`__________`
- 当前 authoritative candidate rationale：`____________________________________________________________`
- 历史 fixture candidate disposition（只能 rejected / needs_more_evidence）：`__________`
- 历史 fixture candidate rationale：`____________________________________________________________`
- 复核日期：`__________`

## 6. Candidate C — TikTok realistic AIGC label

### 身份

- stable key：`tiktok-realistic-aigc-label`
- 当前 authoritative candidate ID：`8935556c-68c5-46c2-8c16-f207fa2c929b`
- 历史 fixture candidate ID：`d7bba957-e928-449a-ba96-a81a4dd41f99`（不可审批，只保留 lineage）
- source type：`platform_policy_help`
- jurisdiction：`GLOBAL_PLATFORM`
- locator：`AI-generated content overview`
- 官方来源：[TikTok AI-generated content](https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content)

### 原文与 Agent 解释

Exact quote：

> We also require creators to label all AI-generated content that contains realistic images, audio, and video, as explained in our Community Guidelines.

候选结构：

- actor：TikTok creator；
- trigger：发布含 realistic images、audio 或 video 的 AIGC；
- action：应用 AI-generated content label；
- exception：仅使用符合条件的 TikTok AI effects 时，TikTok 可能自动标注；
- scope：synthetic TikTok-like AIGC promotional post；platform policy, not law。

### 2026-08-28 复核事实与限制

- TikTok 当前官方 FAQ JSON snapshot 逐字包含 exact quote；
- 同页区分“鼓励标注 completely generated 或 significantly edited content”与“要求标注 realistic AIGC”；
- creator 可以通过平台 label、文字、hashtag sticker 或 description 提供披露；平台也可能依据 TikTok AI effects 或 C2PA Content Credentials 自动加标；
- 有效 C2PA 只说明 provenance manifest 的验证状态，不证明画面真实、合法或没有误导；
- canonical support URL 当前对应 FAQ ID `7636670084747893268`；专用 adapter 已在无登录、无 Cookie 条件下取得并校验官方 JSON 正文；
- 当前 snapshot ID `e4d70c39-8c36-40ed-b44f-0c7903cb9083`，SHA-256 `d200f43571e9a092e4027f8a350d3562372b390d74bb864ed2f5accb2378de27`；bounded review context 为 lines 26–30，exact quote 已找到；
- TikTok 未发布版本号，仍记录 `not_published`；当前页面同时保留 creator label、auto label、TikTok effects 和 C2PA Content Credentials 四条不同证据路径。

### 需要 Song 判断

- 当前 trigger 的英文用了 `and`，是否可能被误读为必须同时含 image、audio、video？产品逻辑更安全的表达应是“one or more realistic image/audio/video modalities”，但改写必须由人确认；
- exception 是否准确？自动标注更像 alternate labeling path，不一定是对披露责任的普遍例外；
- mapping 是否应优先用 `aigc_visible_label_present`，而把 C2PA 只作为独立 evidence，不作为唯一 pass/fail 条件？

### 工程审阅提示

这条候选存在语义精度问题：来源列举 modalities 的自然语言和当前 trigger 的结构化表达可能被下游规则误读。Song 在确认前可选择 `needs_more_evidence`，要求重新抽取 trigger/exception；这比直接批准后再补丁更可审计。

### Song 的决定

- 当前 authoritative candidate disposition：`__________`
- 当前 authoritative candidate rationale：`____________________________________________________________`
- 历史 fixture candidate disposition（只能 rejected / needs_more_evidence）：`__________`
- 历史 fixture candidate rationale：`____________________________________________________________`
- 复核日期：`__________`

## 7. Candidate D — EU AI Act Article 50(2)

### 身份

- stable key：`eu-provider-machine-readable-aigc`
- 当前数据库 ID：`cd826b35-334b-4fe9-a18b-33060c322ede`
- source type：`regulation`
- jurisdiction：`EU`
- locator：`Article 50(2)`
- 当前官方来源：[EUR-Lex consolidated version 27 July 2026](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02024R1689-20260727)

### 原文与 Agent 解释

Exact quote：

> Providers of AI systems, including general-purpose AI systems, generating synthetic audio, image, video or text content, shall ensure that the outputs of the AI system are marked in a machine-readable format and detectable as artificially generated or manipulated.

候选结构：

- actor：provider of an AI system generating synthetic content；
- trigger：系统生成 synthetic audio、image、video 或 text；
- action：让输出带有 machine-readable marking，并可被检测为 artificially generated/manipulated；
- exception：standard editing assistive function、未实质改变输入或语义，以及特定执法用途；
- effective date：候选当前写为 2026-08-02；
- scope：provider-side synthetic content output；actor applicability requires human review。

### 2026-08-28 复核发现：原候选需要补充过渡条款

- Article 50(2) exact quote 在 2026-07-27 consolidated version 中仍存在；
- consolidated Article 111(4) 另行规定：对 2026-08-02 前已经 placed on the market 的相关系统，provider 采取 Article 50(2) 必要措施的期限是 2026-12-02；
- 因此单一字段 `effective_date=2026-08-02` 不能完整表达所有系统的时间适用性；
- Article 50(2) 要求 machine-readable 和 detectable marking，但没有把 C2PA 写成唯一法定技术；C2PA 可以作为作品集中的合成 control/evidence implementation，不能声称“有 C2PA 就满足 Article 50”。
- migration `0007` 现在还会明确阻止这条 historical fixture candidate 的 approval，因为 Candidate E/F 的 authoritative parent 已是该 source 的 latest snapshot。

### 需要 Song 判断

- 这条旧 candidate 是否应先标为 `needs_more_evidence`，然后从 consolidated snapshot 产生新 candidate？
- 数据模型是否需要把单一 `effective_date` 扩展为 `application_rule` 或 transition notes？
- mapping 到 `c2pa_manifest_present` 是否只能描述“一种技术候选”，并强制附加 `human_review_required`？
- 项目是否应把 actor applicability 与“output used in the Union”等 Article 2 scope 条件保留给人工，而不是让 rule engine推断？

### 工程建议（不是审批）

不要按当前结构直接批准 Candidate D。更可审计的下一步是：Song 选择 `needs_more_evidence`，系统保存 consolidated snapshot，并生成带 Article 111(4) transition uncertainty 的新候选。最终 disposition 仍由 Song 决定。

### Song 的决定

- disposition：`__________`
- rationale：`____________________________________________________________`
- 复核日期：`__________`

## 8. Candidate E — EU AI Act Article 50(2)（最新 consolidated snapshot）

### 为什么和 Candidate D 并存

Candidate D 指向旧 snapshot，是历史记录；Candidate E 指向 2026-07-27 consolidated version 的新 immutable snapshot。系统没有修改或删除 Candidate D，而是在新证据 lineage 下重新验证相同 Article 50(2) quote。两条候选并存，正好展示 source version 变化时“保留历史、创建新候选”的审计原则。

### 身份

- stable key：`eu-provider-machine-readable-aigc`
- 当前数据库 ID：`231707d5-b6bb-4af7-9fe7-2624b2c70c9b`
- source snapshot ID：`82b2fff0-d4b6-4f58-be6b-6a45a9ee5b86`
- snapshot SHA-256：`0dac65251e12c2df4ed7ac9236f8ae78dc04b8a09907c5206bbc2e3f446ab7b6`
- quote validation：通过
- status：`candidate`

### 与 Candidate D 的关键差异

- quote 内容相同，但 parent snapshot、source version 和 audit correlation 不同；
- 新 snapshot 同时保存 Article 111(4) 的 transition context；
- Candidate E 仍保留 `effective_date=2026-08-02`，因此 Song 仍需结合 Candidate F 判断时间适用性，不能因为 quote validator 通过就直接推断所有系统的同一期限；
- extraction endpoint 只创建 candidate，没有创建 review、mapping、test 或 finding。

### 需要 Song 判断

- Candidate D 应选择 `superseded`、`needs_more_evidence`，还是保留待审？
- Candidate E 的 `uncertainties` 是否充分提示 Article 111(4) transition 与 Article 2 scope？
- 是否需要在数据模型后续加入结构化 `application_rule`，而不只依赖单一日期字段？

### Song 的决定

- disposition：`__________`
- rationale：`____________________________________________________________`
- 复核日期：`__________`

## 9. Candidate F — EU Article 111(4) transition（已创建，未审批）

### 为什么独立成一条候选

Article 50(2) 的 machine-readable marking 要求和 Article 111(4) 的过渡时间是两个不同 locator。把二者压进一条 `exact_quote` 会破坏 quote lineage，因此系统从同一 authoritative snapshot 创建了独立候选，同时保留历史数据库记录不变。

### 身份与原文

- stable key：`eu-provider-machine-readable-aigc-transition`
- 当前数据库 ID：`f7ba95d3-9940-4d87-86dc-478b86fcd785`
- source snapshot ID：`82b2fff0-d4b6-4f58-be6b-6a45a9ee5b86`
- locator：`Article 111(4)`
- source type：`regulation`
- jurisdiction：`EU`
- proposed control：`human_review_required`

Exact quote：

> Providers of AI systems, including general-purpose AI systems, generating synthetic audio, image, video or text content, that have been placed on the market before 2 August 2026 shall take the necessary steps in order to comply with Article 50(2) by 2 December 2026.

### 需要 Song 判断

- 是否同意保留为独立 requirement candidate，而不是修改 Article 50(2) 的原文？
- trigger 是否准确限定为 2026-08-02 前 placed on the market 的 covered system？
- 首版是否只映射 `human_review_required`，避免系统根据媒体证据推断产品投放时间或法律适用性？

### 当前状态

2026-08-28 的受控流程已经完成 registry sync、官方 EU refresh、exact-quote validation 和 candidate extraction。Candidate F 当前仍为 `candidate`；0 个 requirement 已批准，0 个 mapping 已创建，0 个 finding 已创建。这不是发布，也没有启用任何规则。

### Song 的决定

- disposition：`__________`
- rationale：`____________________________________________________________`
- 复核日期：`__________`

## 10. Candidate G — FTC 16 CFR 255.0(f)（官方 eCFR API snapshot）

### 为什么和 Candidate A 并存

Candidate A 来自用于 CI 的最小公开 fixture，不能授权 operational mapping。eCFR 的 reader page 会把自动客户端引导到 developer API；Source Monitor 因此读取官方 Title metadata，再抓取带明确日期的 Versioner XML，而没有绕过 CAPTCHA 或访问控制。Candidate G 指向这份新的 immutable snapshot，Candidate A 继续保留为历史测试 lineage。

### 身份

- 当前数据库 ID：`21864f25-ab46-4212-bee8-78e877c3e7c0`
- source snapshot ID：`b32f9720-9671-47ef-886c-c70bf792f689`
- snapshot SHA-256：`6db6d50b8abfc85b79ffb569fa6ab9e868ff4e30d8003d4ce9303a66a60e9125`
- locator：`16 CFR 255.0(f)`
- eCFR Title 16 as-of：`2026-08-27`
- source type：`administrative_guide`
- status：`candidate`
- quote validation：通过

### 需要 Song 判断

- exact quote 前一句限定的是“representation necessitating a disclosure”；当前 trigger 写成 `an endorsement representation is communicated through both visual and audible means`，是否仍可能把适用范围写得过宽？
- 当前 action 只保留 visual/audio 双通道，是否必须把同段中的 easily noticeable、easily understandable、duration、contrast、volume、speed、cadence 与 unavoidable 另建 `disclosure_prominence_review_required` mapping candidate？
- scope 是否足够明确地限定在 synthetic social-media promotional video，且不把 administrative guide 写成 statute？

### 工程建议（不是审批）

这是北美 creator-commerce 主线最值得先审的一条，因为证据已 authoritative，但结构化 trigger 仍有可讨论的语义风险。保守 disposition 是 `needs_more_evidence`，rationale 可以明确要求重新抽取 “necessitating a disclosure” 条件；如果 Song 认为当前 trigger 已足够忠实，也可以批准它只用于提出 mapping candidate。两者都必须由 Song 自己写理由。

### Song 的决定

- disposition：`__________`
- rationale：`____________________________________________________________`
- 复核日期：`__________`

## 11. 推荐的审阅顺序

1. Candidate G：先用 authoritative FTC snapshot 练习 exact-quote/context 与 extraction-quality 核对；
2. Candidate A：和 G 比较 fixture lineage 为什么不能授权；
3. Candidate B：练习区分 platform policy 与法律；
4. Candidate C：练习发现自然语言到结构化 trigger 的语义风险；
5. Candidate D：练习发现旧 candidate 的版本/适用时间缺口；
6. Candidate E：比较历史 snapshot 与最新 consolidated snapshot 的 lineage；
7. Candidate F：练习以独立 quote 保存 transition provision。

这七组练习覆盖九条数据库 candidate，故意不追求“一次全批”。一个成熟的 governance workflow 应允许部分批准、部分退回补证，并保留理由和版本 lineage。

## 12. 完成本阶段的验收问题

Song 应能不用看答案解释：

1. 为什么 exact quote 验证通过，仍不足以批准 requirement？
2. 为什么 TikTok disclosure flag 不能代替 FTC clear-and-conspicuous 分析？
3. 为什么 C2PA manifest absence 不能证明内容虚假？
4. 为什么 Article 50(2) 的 quote 没变，candidate 仍可能因为过渡条款而需要更新？
5. requirement approval、mapping approval 和 finding disposition 分别授权了什么？
6. 为什么 `needs_more_evidence` 是成功的安全输出，而不是系统失败？

只有 Song 对当前九条数据库 candidate 分别记录人工 disposition（七组练习中 B/C 各含 current + historical 两条）并能回答这些问题，本阶段才算完成。系统不会根据本工作簿自动写数据库。
