# F_UNK Manual Review — Reviewer-of-Reviewer 审计报告

**审计人**: Kiro (reviewer-of-reviewer)
**审计日期**: 2026-04-19
**审计对象**: `experiment/docs/f-unk-manual-review.md`
**审计方法**: 交叉验证 Layer 1 (combined-experiment.csv)、Layer 2 (trace-summaries.jsonl)、论文原文、key-numbers.md

---

## 一、总体评价

Reviewer 的工作整体质量较高：126 个 case 全部填写了分类和理由，summary table 的算术完全正确（逐类计数验证通过），统计概览表的 F_UNK 数量和百分比与 CSV 数据完全一致。分类框架（taxonomy）设计合理，覆盖了主要失败模式。

但经过逐 case 交叉验证，我发现了 **若干分类错误、一个事实性错误、以及几个需要讨论的边界判断**。以下按严重程度排列。

---

## 二、事实性错误（Critical）

### 2.1 Cases #41–48: Ground Truth 写错

**问题**: Reviewer 在 cases #41–48（ecom:*:26:text:llama4，"customer service" 任务）的 rationale 中写道"正确答案是 Dion in Vegas"。

**实际情况**: 根据成功 case 的 trace（`ecommerce:base:26:text-only:claude-sonnet:0:1`），agent 提交 `"Bob in Vegas, RemyRRemyR"` 获得 success=True。因此 ground truth 包含 "Bob in Vegas" 和 "RemyRRemyR" 两个 reviewer。

**影响**:
- Llama4 提交 "Bob in Vegas" 实际上是**部分正确**（找到了一个 reviewer 但漏了另一个），而非完全错误
- "Dion in Vegas" 反而是 SoM agent（case #96）提交的**错误答案**
- F_REA 分类仍然成立（agent 确实给出了不完整的答案），但 rationale 需要修正为"agent 只找到了一个 reviewer（Bob in Vegas），漏掉了 RemyRRemyR"

**建议**: 修正 cases #41–48 的 rationale。同时注意 case #96（SoM 提交 "Dion in Vegas"）的 F_SOM_MISREAD 分类是正确的——"Dion in Vegas" 确实不在 ground truth 中。

---

## 三、分类错误（Major）

### 3.1 Cases #106–109: 应为 F_SIF，非 F_SOM_MISREAD

**涉及 cases**:
- #106: `ecom:low:26:som:claude:0:2`
- #107: `ecom:low:26:som:claude:0:3`
- #108: `ecom:low:26:som:claude:0:4`
- #109: `ecom:low:26:som:claude:0:5`

**问题**: Reviewer 将这 4 个 case 分类为 F_SOM_MISREAD（视觉误读），但 trace 显示 agent 的 final message 分别是：
- #106: `"No customer reviews are displayed on this page, so I cannot identify any reviewers who mention customer service complaints."`
- #107: `"No customer reviews found on this page that mention customer service complaints"`
- #108: `"No customer reviews are displayed on this page. Despite having a Reviews (12) tab, the individual customer review content is not available to analyze for customer service complaints."`
- #109: `"No customer reviews are displayed on this page. The Reviews section only shows product specifications and features, not individual customer review text where complaints about customer service might be mentioned."`

Agent **没有误读任何内容**——它正确识别出 review 内容不可见。CSV 中 `task_feasible=False`，确认这是结构性不可完成的任务。

**正确分类**: F_SIF（Structural Infeasibility）。Agent 在 low variant 下无法看到 review 内容，这与 text-only Claude 在同一任务上的 F_SIF 分类完全一致。

**影响**: 这会改变 summary table：
- F_SOM_MISREAD: 36 → **32** (−4)
- F_SIF: 26 → **30** (+4)
- SoM group 的 dominant type 仍然是 F_SOM_MISREAD，但比例从 63% 降至 56%

### 3.2 Cases #60–61: 应为 F_REA 或 F_WEA，非 F_SIF

**涉及 cases**:
- #60: `admin:low:94:text:llama4:0:3`
- #61: `admin:low:94:text:llama4:0:5`

**问题**: Reviewer 将这 2 个 case 分类为 F_SIF（结构性不可完成），但 CSV 显示 `task_feasible=True`，且同一 agent 在同一 variant 下的 reps 1、2、4 均 **成功**（success=True）。

**实际情况**: 任务在 low variant 下是可完成的（3/5 reps 成功）。Agent 在 rep 3 和 rep 5 失败是因为导航/推理错误，不是因为任务结构性不可完成。

**正确分类**: F_REA（Reasoning Error）或 F_WEA（Wrong Element Actuation）——agent 在可完成的任务上犯了错误。需要看 trace 细节来区分，但绝对不是 F_SIF。

**影响**:
- F_SIF: 26 → 24 (−2)（加上 3.1 的修正后为 28）
- F_REA 或 F_WEA: 相应 +2

### 3.3 Case #52: F_SIF 存疑，task_feasible=True

**涉及 case**: `reddit:low:29:text:llama4:0:3`

**问题**: Reviewer 分类为 F_SIF，但 CSV 显示 `task_feasible=True`。Agent 的行为是 `click→noop→noop→scroll→fill("DIY")→click→noop→send("cannot complete")`。

**分析**: 虽然 task_feasible=True，但 observation_sizes 极小（1127–1168 bytes），说明 a11y tree 确实非常稀疏。然而，同一任务的其他 reps 和 variants 也有 F_UNK（base variant 的 reps 4、5 也失败了），说明这可能是 Llama4 在 reddit 任务上的普遍困难，而非 low variant 特有的结构性问题。

Agent 搜索了 "DIY"（与 downvote 任务无关），说明它对任务理解有误。这更像 F_AMB（agent 无法理解如何完成任务）或 F_REA（推理错误）。

**建议**: 改为 F_AMB，与同一任务的 base/ml variant cases (#50, #51, #53–57) 保持一致。

---

## 四、分类可商榷但可接受（Minor）

### 4.1 Cases #50–51, #53–57: F_AMB vs. 新类别 "Premature Termination"

**问题**: 这 7 个 case 被分类为 F_AMB（Task Ambiguity），但 F_AMB 的定义要求 agent "发送 'cannot complete' 或类似放弃消息"。这些 case 中 agent **没有发送任何消息**——它只做了 4 次 click 就停止了（`final_answer=""`）。

**分析**: 这不是 task ambiguity（agent 没有表达困惑），而是 Llama4 的一个模型行为问题——agent 过早停止生成 action。现有 taxonomy 中没有完美匹配的类别：
- F_AMB: 要求 agent 表达无法完成，但这些 case 没有
- F_EMPTY_ANS: 要求 `send_msg_to_user("")`，但这些 case 连 send 都没调用
- F_REA: 要求 agent 看到正确信息但给出错误答案，但这些 case 没有给出任何答案

**建议**: F_AMB 是现有 taxonomy 中最接近的分类（agent 未能完成任务且未给出答案），可以接受。但建议在 rationale 中明确说明"agent 过早停止执行，未调用 send_msg_to_user"，而非"未提交任何答案就结束"。如果论文修订 taxonomy，可以考虑增加 F_PREMATURE（Premature Termination）类别。

### 4.2 Cases #123–126: F_WEA vs. F_REA

**问题**: SoM agent 导航到 `github.com/primer/design` 而非本地 gitlab 实例。Reviewer 分类为 F_WEA（Wrong Element Actuation）。

**分析**: F_WEA 的定义是"Agent 点击了错误的元素（action 成功但目标错误）"。但 case #124 中 agent 直接执行 `goto("https://github.com/primer/design")`——这不是点击了错误的元素，而是 agent **主动决定**去错误的 URL。这更像 F_REA（推理错误：agent 把本地 gitlab 的 repo 与 GitHub 上的真实 repo 混淆了）。

**影响**: 如果改为 F_REA，F_WEA 从 9 降至 5，F_REA 从 18 升至 22。但 F_WEA 也有一定道理（agent 确实操作了错误的目标），所以这是一个边界判断。

### 4.3 Cases #70–74, #76–78, #81–83: F_SOM_NAV 的 2-step 模式

**观察**: 这 12 个 F_SOM_NAV case 中有 10 个是完全相同的模式：`click(769)→click(736)`，2 步，4K tokens。Trace 显示 agent 从 admin dashboard 导航到了 Adobe 外部文档页面（`experienceleague.adobe.com`）。

**深层原因**: 这不仅仅是"无法导航"——agent 实际上是被 admin dashboard 上的一个外部链接（可能是 "Reports" 或 "Documentation" 链接）带到了 Adobe 的帮助文档。这是 SoM agent 的一个系统性问题：它无法区分内部导航链接和外部文档链接。

**建议**: F_SOM_NAV 分类可以接受，但 rationale 应该补充"agent 被外部文档链接误导，导航到了 experienceleague.adobe.com"。这个模式值得在论文中提及——它揭示了 SoM agent 在 admin 界面上的一个系统性弱点。

### 4.4 Cases #68–69: F_REA vs. F_SIF

**问题**: `gitlab:low:308:text:llama4:0:4` 和 `0:5`，task_feasible=False，但 reviewer 分类为 F_REA。

**分析**: 这是一个合理的边界判断。虽然 task_feasible=False，但 agent 确实提交了一个答案（"Cole Bemis"），说明它尝试了推理。同一任务的 reps 1–3 因 context overflow（695K, 175K, 259K tokens）被分类为 F_COF，而 reps 4–5 tokens 较低（80K）。

**判断**: F_REA 可以接受——agent 在结构性困难的任务上做出了推理尝试但答案错误。但也可以论证为 F_SIF（任务本身不可完成，agent 的任何答案都注定错误）。这取决于你是看"agent 做了什么"还是"任务是否可完成"。

---

## 五、Summary Table 修正后的数字

如果采纳上述 Major 修正（3.1–3.3），summary table 应更新为：

| Reclassified Type | 原始 Count | 修正后 Count | 变化 |
|-------------------|-----------|-------------|------|
| F_SOM_MISREAD | 36 | **32** | −4 |
| F_SIF | 26 | **27** | +1 (net: +4 from SoM, −2 from admin:94, −1 from reddit:29) |
| F_REA | 18 | **20** | +2 (from admin:94) |
| F_EMPTY_ANS | 13 | 13 | — |
| F_SOM_NAV | 12 | 12 | — |
| F_WEA | 9 | 9 | — |
| F_AMB | 7 | **8** | +1 (from reddit:low:29) |
| F_SOM_EXPLORE | 5 | 5 | — |

**注意**: 修正后总数仍为 126，F_UNK 仍为 0。主要结论不变：F_SOM_MISREAD 仍是最大类别，F_SIF 仍是第二大类别。

---

## 六、深层观察与补充 Notes

### 6.1 Llama4 的 F_EMPTY_ANS 模式揭示了一个模型级别的系统性缺陷

Cases #26–28, #30–40 展示了一个高度一致的模式：Llama4 在 ecom:24 任务上，跨所有 4 个 variant（base, high, ml, low 以外），都表现为 `click→noop→send("")`。这不是 accessibility 导致的失败——这是 Llama4 在处理长 a11y tree（ecom 页面 observation_size ~8K–17K）时的一个系统性行为：
- 第一步 click 成功
- 第二步 noop（agent 生成了一个无操作指令）
- 第三步提交空答案

这个模式在 base 和 high variant 上也出现，说明它与 accessibility level 无关。**这是 Llama4 的 instruction following 能力问题**，不是环境问题。论文应该在讨论 F_EMPTY_ANS 时明确指出这一点。

### 6.2 "Bob in Vegas" 的跨 variant 一致性暗示 Llama4 的 a11y tree 解析有固定偏差

Cases #41–48 中，Llama4 在 task 26 的 base、high、ml variant 上都提交了 "Bob in Vegas"（部分正确但不完整）。这说明 Llama4 能够正确识别第一个 reviewer，但系统性地忽略了第二个 reviewer（RemyRRemyR）。可能的原因：
- Llama4 在长 observation 中倾向于只提取第一个匹配项
- 或者 Llama4 的 reasoning 在找到第一个匹配后就停止搜索

这与 Claude 的行为形成对比——Claude 在同一任务上能找到两个 reviewer。

### 6.3 SoM 的 F_SOM_NAV 集中在 admin:4 任务上

12 个 F_SOM_NAV 中有 10 个来自 admin:4（top-3 bestsellers）任务。这不是随机分布的导航失败——这是 SoM agent 在 Magento admin dashboard 上的一个特定弱点。Dashboard 页面有大量 SoM 标签（bid 数量多），agent 无法从中识别出正确的导航路径到 Sales Report。

**深层原因**: Magento admin 的侧边栏导航使用了嵌套的 dropdown menu，SoM 标签可能无法正确标注这些动态展开的菜单项。Agent 反复点击 bid 769 和 736（可能是 dashboard 上的某个链接），被带到外部 Adobe 文档页面。

### 6.4 F_SIF 的分布验证了论文的 L3 severity framework

26 个 F_SIF case（修正前）中：
- 19 个来自 text-only Claude（全部是 low variant）
- 7 个来自 text-only Llama4（6 个 low variant + 1 个 low variant）

这些 case 集中在 3 个任务上：
- ecom:23 (fingerprint resistant reviews) — 5 Claude + 0 Llama4
- ecom:24 (unfair price reviews) — 4 Claude + 0 Llama4
- ecom:26 (customer service reviews) — 5 Claude + 0 Llama4
- gitlab:293 (SSH clone) — 5 Claude + 4 Llama4
- admin:94 (invoice) — 0 Claude + 2 Llama4 (**但这 2 个应该移除，见 3.2**）
- reddit:29 (downvoted comments) — 0 Claude + 1 Llama4 (**应该移除，见 3.3**）

ecom review 任务在 low variant 下 review 内容从 a11y tree 消失，这正是论文描述的 L3 structural violation 效果。gitlab SSH clone tab 在 low variant 下不可见，也是同样的机制。这些 F_SIF case 为论文的核心论点提供了直接的 case-level 证据。

### 6.5 Reviewer Response 草稿需要修正

Reviewer Response 中说"0% of cases remained genuinely unclassifiable"——这在修正后仍然成立。但需要注意：
1. 应该提到 ground truth 验证（"Bob in Vegas" 问题）
2. 应该提到 task_feasible 交叉验证
3. 应该提到 Cohen's κ 的计划——ML reviewer 明确要求了 inter-rater reliability

### 6.6 Cohen's κ 的问题

ML reviewer 要求报告 Cohen's κ。但目前只有一个 reviewer 做了分类。要计算 κ，需要第二个独立 reviewer 对同一组 case 进行分类。建议：
1. 让第二个 reviewer 独立分类至少 30% 的 case（~38 cases）
2. 计算 κ 并报告
3. 如果 κ > 0.80（almost perfect agreement），可以在论文中报告
4. 如果 κ < 0.60，需要修订 taxonomy 或增加分类指南

---

## 七、对论文修改的建议

### 必须做的：
1. ✅ 修正 cases #106–109 的分类（F_SOM_MISREAD → F_SIF）
2. ✅ 修正 cases #60–61 的分类（F_SIF → F_REA/F_WEA）
3. ✅ 修正 cases #41–48 的 rationale（ground truth 不是 "Dion in Vegas"）
4. ✅ 修正 case #52 的分类（F_SIF → F_AMB）
5. ✅ 更新 summary table 的数字
6. 🔲 安排第二个 reviewer 做独立分类，计算 Cohen's κ

### 建议做的：
7. 在 rationale 中补充 SoM NAV cases 的外部链接细节
8. 在论文中讨论 F_EMPTY_ANS 作为 Llama4 特有的模型缺陷
9. 在论文中讨论 "Bob in Vegas" 模式作为 Llama4 的 partial extraction 偏差
10. 考虑在 taxonomy 中增加 F_PREMATURE（Premature Termination）类别

### 不需要做的：
- 不需要改变主要结论（F_SOM_MISREAD 和 F_SIF 仍是最大类别）
- 不需要改变 Reviewer Response 的核心论点
- 不需要重新运行统计分析

---

## 八、修正后的 Reviewer Response 草稿

> "We conducted a manual review of all 126 F_UNK cases with cross-validation
> against ground truth traces and task feasibility flags. The dominant
> reclassified category was F_SOM_MISREAD (32 cases, 25.4%), reflecting SoM agents
> misreading data from screenshots. The second most common was F_SIF (27 cases,
> 21.4%), where low-accessibility-tree variants structurally prevented task
> completion — concentrated in ecommerce review tasks where review content
> disappeared from the a11y tree under L3 violations, and gitlab SSH clone tasks
> where the clone tab became invisible. F_REA (reasoning errors, 20 cases, 15.9%)
> was the third most common, spanning both text-only Llama 4 (partial answer
> extraction) and SoM Claude (data misinterpretation). F_EMPTY_ANS (13 cases,
> 10.3%) was specific to Llama 4's tendency to submit empty answers after a
> single click, a model-level instruction-following deficit unrelated to
> accessibility level. 0% of cases remained genuinely unclassifiable after
> manual inspection. Cohen's κ for inter-rater reliability will be reported
> based on independent second-reviewer classification of a 30% subsample.
> The reclassification does not change any primary finding: both F_SOM_MISREAD
> and F_SIF are already discussed in the paper, and the accessibility-attributed
> failure types (F_SIF, F_SOM_EXPLORE) concentrate under the Low variant as
> predicted by the L3 severity framework."
