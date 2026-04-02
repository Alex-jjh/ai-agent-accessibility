# Bug Report — Full Codebase Review (2026-04-02)

经人工 review 后的最终版本。去掉了不成立、重复、已修复的条目，调整了优先级。

前置参考：`docs/bugfix-2026-04-02.md`（Round 1-2）、`docs/bugfix-2026-04-02-round3.md`（Round 3-4）
已修复的 bug 不再重复列出。

---

## 需要修复 — 阻塞 regression

### BUG-01 [P0]: `determineOutcome` 成功判定逻辑脆弱
**文件**: `src/runner/agents/executor.ts` (L223-240)
**问题**: 成功判定依赖 `lastStep.action.includes('done')`。如果 LLM 输出
`send_msg_to_user("I cannot complete this, done trying")`，同时包含
"cannot complete" 和 "done"，由于 `includes('done')` 先于 `includes('cannot complete')`
匹配，会被错误判定为成功。更根本的问题是：BrowserGym 的 `obs.reward` 才是
ground truth 成功信号，但当前代码完全没用它。
**建议**: 优先用 `obs.reward > 0` 判定成功，`includes('done')` 作为 fallback。
同时调整 if 顺序，先检查 "cannot complete" 再检查 "done"。
**工作量**: ~30min

### BUG-04+05 [P0]: timeout/partial_success 丢失 + timeout 被误分类为 F_REA
**文件**: `src/runner/agents/executor.ts`, `src/index.ts`, `src/classifier/taxonomy/classify.ts`
**问题**:
1. `TaskOutcome.outcome` 被硬编码为 `trace.success ? 'success' : 'failure'`，
   丢掉了 `determineOutcome` 返回的 `'timeout'` 和 `'partial_success'` 状态。
2. Timeout 的 trace 进入 classifier 后没有专门的 timeout detector，
   默认 fallback 到 `F_REA`（reasoning error），这是不准确的。
**建议**:
- `TaskOutcome.outcome` 直接使用 `determineOutcome()` 的返回值，不要二值化。
- 在 `classifyFailure` 之前先判断 outcome type，timeout 直接标记为
  新增的 `F_TMO` 或在 ActionTrace 上标记 `failureType = 'timeout'`，不走 detector 链。
**工作量**: ~1h

### BUG-09 [P1]: `cleanAction` bracket stripping 不处理单引号 bid
**文件**: `src/runner/agents/executor.ts` (L156-174)
**问题**: Regex `\("?\[(\d+)\]"?` 只匹配双引号包裹的 `[bid]`。
LLM 偶尔输出单引号形式 `click('[413]')`，不会被 strip。
**建议**: Regex 改为 `\(["']?\[(\d+)\]["']?`，或在 cleanAction 开头统一把单引号替成双引号。
**工作量**: ~15min

### BUG-10 [P1]: `parseLlmResponse` fallback regex 缺少 `select_option`
**文件**: `src/runner/agents/executor.ts` (L177-220)
**问题**: Fallback regex 的 action 列表没有 `select_option`。
BrowserGym 支持 `select_option("bid", "value")` 用于下拉选择，
如果 LLM 输出这个动作且不在 JSON 格式中，会被 fallback 为 `noop()`。
**建议**: 在 regex alternation 中加上 `select_option`。
**工作量**: ~15min

---

## 需要修复 — 不阻塞 regression，后续处理

### BUG-07 [P1]: Track B `runTrackB` 导航到 `about:blank` 导致扫描空白页
**文件**: `src/index.ts` (runTrackB, ~L380)
**问题**: HAR replay session 创建后导航到 `about:blank`，不触发 HAR 匹配。
需要从 HAR 文件中提取原始 URL 来导航。Round 2 修了 `notFound: 'fallback'`
（R2-2），但导航目标的问题还在。
**状态**: Track B 还没跑过，不阻塞当前 regression。Pilot 2 前需修。

### BUG-17 [P2]: `loadConfig` 不验证 `tasksPerApp` 中的任务 ID 范围
**文件**: `src/config/loader.ts`
**问题**: 用户可以配置 `ecommerce: ["200", "201"]`（实际是 gitlab 的任务 ID），
不会收到任何警告。静默的任务路由错误。
**建议**: 在 validation 中加 task ID range 校验，至少 warn。

### BUG-19 [P2]: `scrubPii` 缺少 IP 地址和默认凭据脱敏
**文件**: `src/export/csv.ts`
**问题**: 没有处理内部 IP 地址（`10.0.1.49`）和 WebArena 默认凭据
（`admin/admin123`、`magentouser/MyPassword`）。
**建议**: 论文发布前补全。

---

## 已确认但不修 — Known Limitations / 设计决策

### BUG-02 [P2]: `detectENF` 与 `detectHAL` confidence 相同时排序依赖实现细节
**问题**: 当 hallucination 证据恰好3条时两者 confidence 都是 0.9，
排序取决于 V8 的稳定排序（按 detector 数组原始顺序，ENF 在前）。
结果可重复但依赖实现细节。
**建议**: 加 tiebreaker（按 domain 优先级），但不紧急。

### BUG-03 [P2]: `detectWEA` 几乎永远不触发
**问题**: BrowserGym 在 success 时不返回 "wrong element" detail，
触发条件在实际运行中不可能满足。
**状态**: 设计限制。检测 "操作了错误的元素" 需要 ground truth，BrowserGym 不提供。

### BUG-06 [P2]: Variant validation 权重与 pipeline 权重不一致
**问题**: validation 用等权（全 1），pipeline 用差异化权重。
**状态**: Round 2 (R2-9) 已移除了 validation 的调用（unused import cleanup），
当前 pipeline 不调用 validateVariant。未来启用时需统一权重。

### BUG-08 [P2]: Cohen's Kappa 配对方式依赖数组顺序
**问题**: `selectForReview` 返回 shuffle 后的顺序，调用者需按 traceId 配对。
**状态**: Review 模块 pilot 阶段还没用到。启用前需修。

### BUG-21 [P2]: `_VARIANT_ORDER` 等距整数编码假设
**问题**: 0,1,2,3 等距编码但 variant score ranges 不等距。
**状态**: 论文中讨论即可，代码不改。

### BUG-25 [设计决策]: `config-pilot.yaml` 省略 `medium-low`
**问题**: Pilot 省略 medium-low 导致 ordinal 编码不连续（0, 2, 3）。
**状态**: 有意的设计决策，减少 pilot case 数量。论文中注明。

---

## 不成立 / 已修复 / 重复 — 排除

| Bug | 判定 | 原因 |
|-----|------|------|
| BUG-11 | ❌ 自己撤回 | ARN 格式正确 |
| BUG-12 | P2 极低概率 | className 纯空格在 WebArena 页面不太可能出现 |
| BUG-13 | P2 低概率 | 起始元素通常是 body，Tab 回 body 概率低 |
| BUG-14 | ❌ 不成立 | BrowserGym 基于 Gymnasium，5值返回是标准 API |
| BUG-15 | ❌ 不成立 | spawn 有 stderr handler 在消费数据 |
| BUG-18 | ❌ 不成立 | caseId 包含 attempt 号，不会覆盖 |
| BUG-20 | ❌ 不是 bug | 返回完整 components 是 feature |
| BUG-22 | ❌ 无影响 | eps 重复定义，值相同 |
| BUG-23 | ❌ 不触发 | acquire/release 配对使用 |
| BUG-24 | ❌ 重复 | = Round 3 Bug 6，已修复 |

---

## 修复优先级总结

| # | Bug | 优先级 | 工作量 |
|---|-----|--------|--------|
| 1 | BUG-01: determineOutcome 用 BrowserGym reward 判定成功 | 🔴 P0 | 30min |
| 2 | BUG-04+05: timeout/partial_success 透传 + classifier 处理 | 🔴 P0 | 1h |
| 3 | BUG-09: bracket stripping 加单引号支持 | 🟡 P1 | 15min |
| 4 | BUG-10: parseLlmResponse 加 select_option | 🟡 P1 | 15min |
| 5 | BUG-07: Track B 导航逻辑（Pilot 2 前） | 🟡 P1 | 1h |
| 6 | BUG-17: task ID range 校验（建议） | 🔵 P2 | 30min |
| 7 | BUG-19: PII 脱敏补全（论文前） | 🔵 P2 | 30min |
