# Bug Report — Full Codebase Review (2026-04-02)

Severity: P0 = 会影响实验结果正确性, P1 = 会导致运行时失败, P2 = 潜在问题/代码异味

---

## P0 — 影响实验结果正确性

### BUG-01: `determineOutcome` 成功判定逻辑过于脆弱
**文件**: `src/runner/agents/executor.ts` (L223-240)
**问题**: 成功判定依赖 `lastStep.action.includes('done')`，但 LLM 可能输出 `send_msg_to_user("I'm done")` 或 `send_msg_to_user("Task done successfully")` 等变体。更严重的是，如果 LLM 输出 `send_msg_to_user("I cannot complete this, done trying")`，同时包含 "cannot complete" 和 "done"，由于 `includes('done')` 先匹配，会被错误判定为成功。
**影响**: 实验中的 success/failure 标签可能不准确，直接污染统计分析的因变量。

### BUG-02: `detectHAL` 与 `detectENF` 检测逻辑重叠，分类不稳定
**文件**: `src/classifier/taxonomy/classify.ts`
**问题**: `detectENF` 检测连续3次 failure（不看原因），`detectHAL` 检测 action 引用了 observation 中不存在的 bid。当 agent 因为 hallucinate 一个不存在的 bid 而连续失败3次时，两个 detector 都会触发。最终分类取决于 confidence 排序，但 `detectENF` 的 confidence = `0.6 + 3*0.1 = 0.9`，而 `detectHAL` 的 confidence = `0.7 + n*0.1`。当 hallucination 证据恰好3条时两者 confidence 相同（0.9），排序不稳定。
**影响**: 同一失败模式在不同运行中可能被分类为不同的 failure type，影响 failure taxonomy 分析的可重复性。

### BUG-03: `detectWEA` 几乎永远不会触发
**文件**: `src/classifier/taxonomy/classify.ts` (L71-92)
**问题**: `detectWEA` 要求 `step.result === 'success'` 且 `step.resultDetail` 包含 "wrong/unexpected/incorrect/unintended"。但在 `executeAgentTask` 中，当 BrowserGym 返回 `last_action_error` 时 result 被设为 `'failure'`，当没有错误时 result 是 `'success'` 但 `resultDetail` 为 `undefined`。BrowserGym 不会在成功执行时返回 "wrong element" 这样的 detail。因此 `detectWEA` 的触发条件在实际运行中几乎不可能满足。
**影响**: F_WEA（Wrong Element Actuation）这个 failure type 在自动分类中永远不会出现，failure taxonomy 分析缺失一个重要类别。

### BUG-04: `classifyFailure` 对成功的 trace 也会被调用
**文件**: `src/index.ts` (runTrackA, ~L230)
**问题**: 代码中 `if (!trace.success)` 才调用 `classifyFailure`，这是正确的。但 `determineOutcome` 返回的是 4 种状态（success/partial_success/failure/timeout），而 `ActionTrace.success` 只在 `outcome === 'success'` 时为 true。这意味着 `partial_success` 也会被分类为 failure 并进入 classifier。对于 `timeout` 的 case，classifier 没有专门的 timeout detector，会被默认归类为 `F_REA`（reasoning error），这是不准确的。
**影响**: Timeout 类型的失败被错误归类，污染 failure taxonomy 数据。

### BUG-05: `TaskOutcome.outcome` 与 `ActionTrace.success` 不一致
**文件**: `src/index.ts` (runTrackA, ~L220)
**问题**: `TaskOutcome.outcome` 被硬编码为 `trace.success ? 'success' : 'failure'`，但 `determineOutcome` 实际上可以返回 `'timeout'` 和 `'partial_success'`。这两个状态在 TaskOutcome 中都被映射为 `'failure'`，丢失了重要的区分信息。
**影响**: 导出的 CSV 和 manifest 中 outcome 字段丢失了 timeout/partial_success 的区分，影响后续分析。

### BUG-06: Composite Score 验证权重与实际计算权重不一致
**文件**: `src/variants/validation/index.ts` vs `src/index.ts`
**问题**: Variant validation 使用 `DEFAULT_COMPOSITE_WEIGHTS`（所有9个指标权重=1），但 `src/index.ts` 中的 `DEFAULT_COMPOSITE_OPTIONS` 使用了不同的权重（lighthouse=0.5, axeViolations=2.0, 其他=1.0）。这意味着 variant validation 和实际 pipeline 计算的 composite score 不同，validation 可能通过但实际 score 不在预期范围内，反之亦然。
**影响**: Variant validation 结果不可靠，可能放行不合格的 variant 或拒绝合格的 variant。

### BUG-07: Track B `runTrackB` 在 `about:blank` 上扫描
**文件**: `src/index.ts` (runTrackB, ~L380)
**问题**: HAR replay session 创建后，代码执行 `await page.goto('about:blank')`，然后检查 fidelity 并扫描。但 `routeFromHAR` 需要导航到实际 URL 才能触发 HAR 匹配。导航到 `about:blank` 不会触发任何 HAR 条目匹配，所以 `coverageGap` 始终为 0（因为 `totalFunctionalRequests` 为 0），`isLowFidelity` 始终为 false，扫描的是空白页面。
**影响**: Track B 的所有扫描结果都是对空白页面的扫描，完全无效。

### BUG-08: Cohen's Kappa 计算中 auto/manual 配对方式有缺陷
**文件**: `src/classifier/review/index.ts` (computeCohensKappa, ~L80)
**问题**: 注释说明 "we pair by array index (auto[i] ↔ manual[i])"，但 `selectForReview` 使用 Fisher-Yates shuffle 随机选择样本，返回的 `ReviewItem` 顺序是随机的。调用者需要确保 `autoClassifications` 数组的顺序与 `manualReviews` 数组一一对应，但没有任何机制保证这一点。如果调用者传入的两个数组顺序不匹配，kappa 值将是错误的。
**影响**: Inter-rater reliability 计算可能完全错误。

---

## P1 — 会导致运行时失败

### BUG-09: `cleanAction` 的 bracket stripping regex 不处理单引号 bid
**文件**: `src/runner/agents/executor.ts` (L156-174)
**问题**: Regex `\("?\[(\d+)\]"?` 只匹配双引号包裹的 `[bid]`，如 `click("[413]")`。但 LLM 有时会输出单引号形式 `click('[413]')` 或无引号形式 `click([413])`。这些情况下 bracket 不会被 strip。
**影响**: BrowserGym 收到 `click('[413]')` 会报错 "element not found"，导致 agent 步骤失败。

### BUG-10: `parseLlmResponse` 的 action regex 缺少 `select` 动作
**文件**: `src/runner/agents/executor.ts` (L177-220)
**问题**: Fallback regex 列出了 `click|fill|type|hover|press|scroll|goto|go_back|go_forward|new_tab|tab_close|tab_focus|send_msg_to_user|noop|focus`，但缺少 `select` 和 `select_option` 动作。BrowserGym 支持 `select_option("bid", "value")` 用于下拉选择，如果 LLM 输出这个动作且不在 JSON 格式中，会被 fallback 为 `noop()`。
**影响**: 涉及下拉选择的任务（如 ecommerce 筛选）会静默失败。

### BUG-11: Terraform IAM policy ARN 缺少 AWS 账号 ID
**文件**: `infra/webarena.tf` (L18)
**问题**: `policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"` 中 `iam::aws` 之间缺少 AWS 分区账号。正确格式应为 `arn:aws:iam::aws:policy/...`（AWS managed policy 的 account 字段为空是正确的，但双冒号之间不应有空格）。实际上这个 ARN 格式是正确的（AWS managed policies 的 account 为空），但 `main.tf` 中同样的 policy 也是这样写的，所以这不是 bug。
**更正**: 经复查，这个 ARN 格式是正确的，撤回此条。

### BUG-12: `apply-low.js` 中 selector 构建逻辑有 falsy 判断错误
**文件**: `src/variants/patches/inject/apply-low.js` (多处)
**问题**: 代码中 `String(el.className) ? '.' + String(el.className).split(' ')[0] : ''` 使用了三元表达式，但 `String(el.className)` 当 className 为空字符串时返回 `""`，这是 falsy 的，所以会走到 `''` 分支。但当 className 是 `"  "` (只有空格) 时，`String(el.className)` 是 truthy 的，`split(' ')[0]` 返回空字符串，最终 selector 变成 `"div."` 这样的无效 CSS selector。更严重的是，当 `el.id` 为空字符串时（`el.id` 存在但为 `""`），`el.id` 是 falsy 的，会跳过 id 选择器，这是正确的。但整体 selector 构建没有 fallback 到唯一标识符，多个同类型元素会生成相同的 selector，导致 revert 时只能恢复第一个匹配的元素。
**影响**: Variant revert 在有多个同类型无 id 元素的页面上会部分失败。虽然 revert 不在生产流程中使用（每个 test case 用新 page），但会影响 validation 和 debugging。

### BUG-13: `computeKeyboardNavigability` 的循环检测可能误判
**文件**: `src/scanner/tier2/scan.ts` (computeKeyboardNavigability, ~L159)
**问题**: 循环完成检测使用 `startKey === currentKey`，其中 key 格式为 `tag#id`。如果起始元素是 `<body>` (tag=body, id="")，而 Tab 到某个 `<body>` 内的无 id 元素时不会误判。但如果页面有多个同 tag 且同 id（或都无 id）的元素，可能会提前终止循环。例如，如果起始焦点在一个 `<input>` 上（key="input#"），Tab 到另一个 `<input>`（也是 key="input#"）时会被误判为循环完成。
**影响**: 键盘可导航性指标可能偏低，因为循环被提前终止。

### BUG-14: `browsergym_bridge.py` 中 `env.step()` 返回值解包假设5个值
**文件**: `src/runner/browsergym_bridge.py` (main, ~L290)
**问题**: `obs, reward, terminated, truncated, info = env.step(action)` 假设 BrowserGym 使用 Gymnasium 的新 API（5个返回值）。但某些版本的 BrowserGym 可能使用旧 API（4个返回值：`obs, reward, done, info`）。如果 BrowserGym 版本不匹配，会抛出 `ValueError: not enough values to unpack`。
**影响**: 如果 BrowserGym 版本不兼容，整个 bridge 会崩溃。

### BUG-15: `defaultBridgeSpawner` 未在代码中展示完整实现
**文件**: `src/runner/agents/executor.ts` (L408)
**问题**: `defaultBridgeSpawner` 通过 `child_process.spawn` 启动 Python 子进程，通过 stdin/stdout JSON 通信。但如果 Python 进程的 stderr 输出过多（如 BrowserGym 的 debug 日志），可能导致 stderr buffer 满而阻塞子进程。Node.js 的 `spawn` 默认 stdio buffer 有限。
**影响**: 长时间运行的 agent task 可能因为 stderr buffer 满而 hang。

---

## P2 — 潜在问题/代码异味

### BUG-16: `config.yaml` 中 `ecommerce_admin` 未配置但 `cms` 使用了相同端口
**文件**: `config.yaml`
**问题**: `config.yaml` 中 `cms` 的 URL 是 `http://localhost:7780`，这与 `ecommerce_admin` 的端口相同。WebArena 中 CMS 任务 (300-399) 和 ecommerce_admin 任务 (0-2) 共享同一个 Magento 后台。但 `config.yaml` 没有配置 `ecommerce_admin`，而 `buildTasksPerApp` 会为 `cms` 分配默认任务 ID 300-302。如果用户在 `config.yaml` 中添加 `ecommerce_admin`，两个 app 会指向同一个服务但使用不同的任务 ID 范围，这是正确的。但当前配置下 `cms` 的默认任务 ID (300-302) 可能不存在于 WebArena 的任务集中。
**影响**: 使用 `config.yaml` 运行时，cms 任务可能因为任务 ID 不存在而全部失败。

### BUG-17: `loadConfig` 不验证 `tasksPerApp` 中的任务 ID 范围
**文件**: `src/config/loader.ts`
**问题**: Config validation 检查了 `webarena.apps` 的结构，但没有验证 `webarena.tasksPerApp` 中的任务 ID 是否在对应 app 的有效范围内。用户可以配置 `ecommerce: ["200", "201"]`（实际是 gitlab 的任务 ID），不会收到任何警告。
**影响**: 静默的任务路由错误，agent 被发送到错误的网站。

### BUG-18: `ExperimentStore.storeRecord` 在多次 attempt 时会覆盖 scan result
**文件**: `src/export/store.ts` (storeRecord, ~L130)
**问题**: `storeRecord` 调用 `storeScanResult(runId, caseId, scanResults)`，文件路径是 `cases/{caseId}/scan-result.json`。但同一个 caseId 的不同 attempt 会覆盖同一个 scan-result.json 文件。虽然 scheduler 的 caseId 格式包含 attempt 号（`app:variant:taskId:configIdx:attempt`），所以实际上不会覆盖。但如果调用者使用不含 attempt 的 caseId，就会有覆盖风险。
**影响**: 低风险，当前使用方式不会触发。

### BUG-19: `scrubPii` 缺少对 IP 地址和用户名的脱敏
**文件**: `src/export/csv.ts` (scrubPii)
**问题**: PII scrubbing 处理了 email、cookie、auth token 和 URL user segment，但没有处理：
- IP 地址（如 `10.0.1.49` 出现在 URL 和 observation 中）
- WebArena 默认用户名/密码（如 `admin/admin123`、`magentouser/MyPassword`）
- 文件路径中的用户名
**影响**: 导出的 CSV 可能包含内部 IP 地址和默认凭据。

### BUG-20: `computeCompositeScore` 在 `tier1-only` 模式下仍返回所有 normalized components
**文件**: `src/scanner/composite.ts` (L100-110)
**问题**: 无论 `mode` 是什么，`normalizedComponents` 始终包含 Tier1 + Tier2 的所有指标。这不是功能 bug，但可能误导下游消费者以为所有指标都参与了 composite score 计算。
**影响**: 低风险，但可能导致分析时的混淆。

### BUG-21: `primary.py` 中 `_VARIANT_ORDER` 使用整数编码可能影响 GEE 系数解释
**文件**: `analysis/models/primary.py`
**问题**: `_VARIANT_ORDER = {"low": 0, "medium-low": 1, "base": 2, "high": 3}` 使用等距整数编码（0,1,2,3），但 variant levels 之间的 accessibility score 差距不是等距的（low: 0-0.25, medium-low: 0.25-0.50, base: 0.40-0.70, high: 0.75-1.0）。等距编码假设了线性关系，可能不准确。
**影响**: GEE/CLMM 系数的解释可能不准确，特别是 base 和 medium-low 的 score range 有重叠（0.40-0.50）。

### BUG-22: `post_hoc_power` 中 `eps` 变量被重复定义
**文件**: `analysis/models/primary.py` (post_hoc_power)
**问题**: `eps = 1e-8` 在函数中被定义了两次（一次在 observed effect 计算中，一次在 power 计算中）。虽然值相同不影响结果，但是代码异味。
**影响**: 无功能影响。

### BUG-23: `Semaphore.release()` 没有防止 over-release
**文件**: `src/runner/concurrency.ts` (Semaphore class)
**问题**: `release()` 方法直接 `this.current--`，没有检查 `this.current > 0`。如果调用者错误地多次 release，`current` 会变成负数，导致 semaphore 允许超过 `max` 个并发任务。
**影响**: 低风险，当前代码中 acquire/release 是配对使用的。

### BUG-24: `runTrackA` 中 variant 应用和 agent 执行使用不同的 page
**文件**: `src/index.ts` (runTrackA, ~L200-220)
**问题**: `runTrackA` 的 `runTestCase` callback 中，variant 被应用到 `page` 上，scan 也在同一个 `page` 上执行。但 `executeAgentTask` 启动了一个独立的 BrowserGym Python 子进程，该子进程创建自己的浏览器实例和页面。虽然 `browsergym_bridge.py` 中有 `apply_variant` 逻辑会在 BrowserGym 的页面上重新应用 variant，但这意味着 variant 被应用了两次：一次在 pipeline 的 page 上（用于 scan），一次在 BrowserGym 的 page 上（用于 agent）。这两个 page 的 DOM 状态可能不完全一致（因为 BrowserGym 会先执行 `env.reset()` 导航到任务起始页，然后才应用 variant）。
**影响**: Scanner 扫描的页面状态（app 首页 + variant）与 agent 实际交互的页面状态（任务起始页 + variant）可能不同，导致 scan metrics 与 agent 行为之间的关联性降低。这是一个实验设计层面的问题。

### BUG-25: `config-pilot.yaml` 缺少 `medium-low` variant
**文件**: `config-pilot.yaml`
**问题**: `variants.levels` 只有 `["low", "base", "high"]`，缺少 `"medium-low"`。但 `config.yaml`（完整实验配置）包含所有4个 level。Pilot 配置有意省略 medium-low 以减少 case 数量，这可能是设计决策而非 bug。但如果 pilot 数据用于 `interaction_effect` 分析，缺少 medium-low 会导致 variant_ordinal 编码不连续（0, 2, 3），可能影响 GEE 系数估计。
**影响**: Pilot 数据的统计分析可能因为不连续的 ordinal 编码而产生偏差。

---

## 总结

| 严重度 | 数量 | 关键问题 |
|--------|------|----------|
| P0     | 8    | 成功判定逻辑脆弱、分类器重叠、Track B 扫描空白页、权重不一致 |
| P1     | 5    | bracket stripping 不完整、action regex 缺失、bridge 版本兼容性 |
| P2     | 9    | 任务 ID 未验证、PII 脱敏不完整、ordinal 编码假设 |

最高优先级修复建议：
1. **BUG-01**: 重构 `determineOutcome`，使用更严格的成功判定逻辑
2. **BUG-07**: 修复 Track B 的 HAR replay 导航逻辑
3. **BUG-06**: 统一 composite score 权重
4. **BUG-05**: 保留 `determineOutcome` 的完整 outcome 类型到 `TaskOutcome`
5. **BUG-04**: 为 timeout 添加专门的 failure type
