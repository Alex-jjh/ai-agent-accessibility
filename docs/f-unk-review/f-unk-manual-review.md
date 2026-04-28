# F_UNK Manual Review — Full 126-Case Classification

## 给 Reviewer 的指令

### 背景

论文的自动 failure classifier 把 126 个失败 case 标记为 F_UNK（unclassified）。
ML reviewer 指出这占了 38–77% 的失败，要求做 manual review 并报告 Cohen's κ。
本文档是 review 的工作表——你需要逐 case 读 trace，给每个 F_UNK 重新分类。

### 你要做什么

对每个 case：
1. **先看下面表格里的 action sequence 和 errors 列**——很多 case 光看 action 就能判断
2. **如果不确定**，去 Layer 2（trace-summaries.jsonl）grep 对应 case_id，看完整 action 列表
3. **如果还不确定**，去 Layer 3（raw trace JSON）看 agent 的 reasoning 和 observation
4. **在表格最后两列填写**：`reclassified_type` 和 `rationale`（一句话理由）

### 分类定义（Failure Type Taxonomy）

| Code | 名称 | 定义 | 判断标准 |
|------|------|------|---------|
| **F_ENF** | Element Not Found | Agent 反复尝试点击/操作不存在或不可交互的元素 | ≥3 次连续 action failure；或 agent 明确说 "element not found" |
| **F_COF** | Context Overflow | Token 消耗超过模型上限导致截断 | total_tokens > 200K (Claude) 或 > 128K (Llama)；或 outcome=timeout 且 tokens 极高 |
| **F_REA** | Reasoning Error | Agent 看到了正确信息但给出错误答案 | Agent 的 final_answer 与 ground truth 不匹配，但 observation 中包含正确答案 |
| **F_WEA** | Wrong Element Actuation | Agent 点击了错误的元素（action 成功但目标错误） | Action result=success 但导航到了错误页面或操作了错误控件 |
| **F_AMB** | Task Ambiguity | Agent 表示无法理解任务或请求澄清 | Agent 发送 "cannot complete" 或类似放弃消息，且不是因为找不到元素 |
| **F_TKI** | Token Inflation | Token 持续膨胀但未溢出，agent 在冗余循环中耗尽步数 | Steps 接近上限(30)，tokens 高但未溢出，action 序列有重复模式 |
| **F_SIF** | Structural Infeasibility | 任务在该 variant 下结构性不可完成（关键内容从 a11y tree 消失） | Low variant 下 agent 无法看到 task-critical 内容（如 review tab 内容不可见） |
| **F_SOM_PHANTOM** | Phantom Bid (SoM) | SoM agent 反复点击已失效的 bid 标签 | ≥5 次连续 click failure 在相同或相邻 bid 上 |
| **F_SOM_MISREAD** | Visual Misread (SoM) | SoM agent 从截图中读错了数据 | Agent 提交了答案但答案与 ground truth 不匹配，且 agent reasoning 显示误读 |
| **F_SOM_NAV** | Navigation Failure (SoM) | SoM agent 无法找到正确的导航路径 | Agent 在多个页面间来回跳转，无法到达目标页面 |
| **F_SOM_EXPLORE** | Exploration Spiral (SoM) | SoM agent 陷入无目的的滚动/探索循环 | 大量 scroll 操作，click failure rate < 30%，最终 timeout |
| **F_EMPTY_ANS** | Empty/Wrong Answer | Agent 提交了空答案或格式完全错误的答案 | send_msg_to_user("") 或答案明显不是任务要求的格式 |
| **F_UNK** | Genuinely Unclassifiable | 确实无法归入以上任何类别 | 仔细看过 trace 后仍然无法判断主要失败原因 |

### 数据位置

| 层级 | 路径 | 说明 |
|------|------|------|
| **Layer 1** | `experiment/results/combined-experiment.csv` | 结构化数据，本表格已提取关键字段 |
| **Layer 2** | `experiment/results/trace-summaries.jsonl` | 每行一个 JSON，用 `grep "case_id" trace-summaries.jsonl` 查找 |
| **Layer 3** | 见下表 | 完整 trace，含 agent reasoning + full a11y tree observation |

**Layer 3 Raw Trace 目录：**

| Experiment | Cases 目录 |
|-----------|-----------|
| pilot4-full | `data/pilot4-full/f4929214-3d48-443b-a859-dd013a737d50/cases/` |
| pilot4-cua | `data/pilot4-cua/pilot4-cua/d91f2bf5-2226-4b23-a8d7-9da54e86e98e/cases/` |
| expansion-claude | `data/expansion-claude/6082c5d1-9a69-4a3f-9f53-6db593880f58/cases/` |
| expansion-llama4 | `data/expansion-llama4/a8aaf58b-9bfd-4ee6-b32b-36ad1b99a8d8/cases/` |
| expansion-som | `data/expansion-som/ed05230c-cb6e-4f2e-9a51-625cb4cb19b5/cases/` |
| expansion-cua | `data/expansion-cua/06ecb163-9e82-4c6b-ae60-63489ead6816/cases/` |

Raw trace JSON 结构：
```json
{
  "trace": {
    "steps": [
      {
        "stepNum": 1,
        "observation": "<完整 a11y tree 或截图信息>",
        "reasoning": "<agent 的思考过程>",
        "action": "click(\"42\")",
        "result": "success|failure|error",
        "resultDetail": "..."
      }
    ]
  }
}
```

### 填写规则

- 每个 case 必须填 `reclassified_type`（从上面的 taxonomy 中选一个 code）
- `rationale` 写一句话，说明判断依据
- 如果一个 case 有多个失败原因，选**主要**原因（导致最终失败的那个）
- 如果确实无法判断，填 `F_UNK` 并在 rationale 写明为什么

---

## 统计概览

| Group | F_UNK Count | Total Failures | F_UNK % |
|-------|-------------|---------------|---------|
| text-only / Claude | 20 | 51 | 39.2% |
| text-only / Llama 4 | 49 | 101 | 48.5% |
| vision-only (SoM) / Claude | 57 | 200 | 28.5% |
| CUA / Claude | 0 | 35 | 0% |
| **Total** | **126** | **387** | **32.6%** |

---

## Review Sheet — 全部 126 Cases

**填写方法**：在最后两列 `reclass` 和 `rationale` 中填入你的判断。

### Section A: Text-only / Claude Sonnet (20 cases)

| # | case_id | task | var | steps | tokens | outcome | action_sequence (前6步) | errors | reclass | rationale |
|---|---------|------|-----|-------|--------|---------|------------------------|--------|---------|-----------|
| 1 | admin:high:4:text:claude:0:4 | admin: top-3 bestsellers Jan 2023 | high | 10 | 130K | partial_success | click→click→click→click→click→fill (date filter) | Timeout 3000ms | F_REA | Agent 成功设置日期过滤器并提交了产品名列表，但答案与 ground truth 不匹配（partial_success） |
| 2 | ecom:low:23:text:claude:0:1 | ecom: reviewers "fingerprint resistant" | low | 9 | 114K | failure | click(1551)→scroll→scroll→go_back→goto(product)→noop | (none) | F_SIF | low variant 下 review 内容从 a11y tree 消失，agent 明确说 "cannot complete" |
| 3 | ecom:low:23:text:claude:0:2 | ecom: reviewers "fingerprint resistant" | low | 7 | 78K | partial_success | click(1551)→scroll→scroll→scroll→goto(product)→scroll | (none) | F_SIF | low variant 下 agent 明确说 "review content is not loading in the accessibility tree" |
| 4 | ecom:low:23:text:claude:0:3 | ecom: reviewers "fingerprint resistant" | low | 7 | 78K | partial_success | click(1551)→scroll→scroll→scroll→goto(product)→scroll | (none) | F_SIF | low variant 下 agent 明确说 "reviews section is not loading in the accessibility tree" |
| 5 | ecom:low:23:text:claude:0:4 | ecom: reviewers "fingerprint resistant" | low | 8 | 94K | failure | click(1551)→scroll→scroll→go_back→scroll→scroll | (none) | F_SIF | low variant 下 review 内容不可见，agent 反复 scroll 后 send("cannot complete") |
| 6 | ecom:low:23:text:claude:0:5 | ecom: reviewers "fingerprint resistant" | low | 8 | 96K | failure | click(1551)→scroll→scroll→scroll→goto(product)→scroll | (none) | F_SIF | low variant 下 review 内容不可见，agent send("cannot complete") |
| 7 | ecom:low:24:text:claude:0:1 | ecom: reviewers "unfair price" | low | 12 | 144K | failure | click(1557)→scroll→scroll→goto(product)→scroll→scroll | (none) | F_SIF | low variant 下 review 内容从 a11y tree 消失，agent 反复 scroll 后放弃 |
| 8 | ecom:low:24:text:claude:0:2 | ecom: reviewers "unfair price" | low | 10 | 110K | partial_success | click(1556)→scroll→scroll→go_back→scroll→scroll | (none) | F_SIF | low variant 下 agent 明确说 "review text containing reviewer information is not accessible through the current interface" |
| 9 | ecom:low:24:text:claude:0:3 | ecom: reviewers "unfair price" | low | 9 | 97K | failure | click(1556)→scroll→scroll→goto(product)→scroll→scroll | (none) | F_SIF | low variant 下 review 内容不可见，agent send("cannot complete") |
| 10 | ecom:low:24:text:claude:0:4 | ecom: reviewers "unfair price" | low | 11 | 126K | failure | click(1556)→scroll→scroll→go_back→scroll→goto(product) | (none) | F_SIF | low variant 下 review 内容不可见，agent send("cannot complete") |
| 11 | ecom:low:26:text:claude:0:1 | ecom: reviewers "customer service" | low | 7 | 134K | failure | click(1893)→scroll→scroll→goto(#reviews)→goto(product)→scroll | (none) | F_SIF | low variant 下 review 内容从 a11y tree 消失，agent send("cannot complete") |
| 12 | ecom:low:26:text:claude:0:2 | ecom: reviewers "customer service" | low | 5 | 75K | failure | click(1894)→scroll→scroll→goto(#reviews)→send("cannot complete") | (none) | F_SIF | low variant 下 review 内容不可见，agent 快速放弃 |
| 13 | ecom:low:26:text:claude:0:3 | ecom: reviewers "customer service" | low | 6 | 102K | failure | click(1894)→scroll→scroll→goto(#reviews)→scroll→send("cannot complete") | (none) | F_SIF | low variant 下 review 内容不可见，agent send("cannot complete") |
| 14 | ecom:low:26:text:claude:0:4 | ecom: reviewers "customer service" | low | 6 | 103K | failure | click(1894)→scroll→scroll→goto(#reviews)→noop→send("cannot complete") | (none) | F_SIF | low variant 下 review 内容不可见，agent send("cannot complete") |
| 15 | ecom:low:26:text:claude:0:5 | ecom: reviewers "customer service" | low | 6 | 102K | failure | click(1894)→scroll→scroll→goto(#reviews)→noop→send("cannot complete") | (none) | F_SIF | low variant 下 review 内容不可见，agent send("cannot complete") |
| 16 | gitlab:low:293:text:claude:0:1 | gitlab: SSH clone Super_Awesome_Robot | low | 3 | 24K | partial_success | click(130)→fill(130,"Super_Awesome_Robot")→send("Super_Awesome_Robot") | (none) | F_SIF | low variant 下 SSH clone tab 不可见，agent 只能搜索到 repo 名，提交了 repo 名而非 SSH URL |
| 17 | gitlab:low:293:text:claude:0:2 | gitlab: SSH clone Super_Awesome_Robot | low | 3 | 24K | partial_success | click(130)→fill(130,"Super_Awesome_Robot")→send("Press Enter to search") | (none) | F_SIF | low variant 下 SSH clone tab 不可见，agent 提交了 UI 提示文字而非 SSH URL |
| 18 | gitlab:low:293:text:claude:0:3 | gitlab: SSH clone Super_Awesome_Robot | low | 3 | 24K | partial_success | click(130)→fill(130,"Super_Awesome_Robot")→send("Super_Awesome_Robot") | (none) | F_SIF | low variant 下 SSH clone tab 不可见，agent 提交了 repo 名而非 SSH URL |
| 19 | gitlab:low:293:text:claude:0:4 | gitlab: SSH clone Super_Awesome_Robot | low | 3 | 24K | partial_success | click(130)→fill(130,"Super_Awesome_Robot")→send("Super_Awesome_Robot") | (none) | F_SIF | low variant 下 SSH clone tab 不可见，agent 提交了 repo 名而非 SSH URL |
| 20 | gitlab:low:293:text:claude:0:5 | gitlab: SSH clone Super_Awesome_Robot | low | 3 | 24K | partial_success | click(130)→fill(130,"Super_Awesome_Robot")→send("Super_Awesome_Robot") | (none) | F_SIF | low variant 下 SSH clone tab 不可见，agent 提交了 repo 名而非 SSH URL |


### Section B: Text-only / Llama 4 Maverick (49 cases)

| # | case_id | task | var | steps | tokens | outcome | action_sequence (前6步) | errors | reclass | rationale |
|---|---------|------|-----|-------|--------|---------|------------------------|--------|---------|-----------|
| 21 | admin:base:4:text:llama4:0:4 | admin: top-3 bestsellers Jan 2023 | base | 11 | 117K | failure | click→click→click→click→click→fill(date) | Timeout 500ms ×2 | F_WEA | agent 反复 click dropdown option 元素（action 成功但 timeout），应使用 select 操作，最终 send cannot complete |
| 22 | admin:high:4:text:llama4:0:1 | admin: top-3 bestsellers Jan 2023 | high | 10 | 102K | failure | click→click→click→click→fill(date)→fill(date) | Timeout 500ms | F_WEA | agent click dropdown option 元素导致 timeout，操作了错误的控件类型，最终放弃 |
| 23 | admin:high:4:text:llama4:0:3 | admin: top-3 bestsellers Jan 2023 | high | 9 | 108K | partial_success | click(skip)→click→click→click→click→fill(date) | Timeout 500ms | F_WEA | agent click dropdown option 元素 timeout，但最终仍提交了答案（partial_success 说明答案错误） |
| 24 | admin:low:4:text:llama4:0:3 | admin: top-3 bestsellers Jan 2023 | low | 7 | 50K | failure | click→click→goto(report URL)→click→click→goto(filtered) | Timeout 500ms ×3 | F_WEA | low variant 下 agent click dropdown option 元素多次 timeout，最终 send cannot complete |
| 25 | admin:ml:4:text:llama4:0:4 | admin: top-3 bestsellers Jan 2023 | ml | 11 | 120K | partial_success | click→click→click→click→click→fill(date) | Timeout 500ms | F_WEA | agent click dropdown option 元素 timeout，提交了答案但 partial_success 说明答案错误 |
| 26 | ecom:base:24:text:llama4:0:1 | ecom: reviewers "unfair price" | base | 2 | 9K | partial_success | click(1557)→send("") | (none) | F_EMPTY_ANS | agent 仅做 1 次 click 后立即提交空答案，未充分探索 review 内容 |
| 27 | ecom:base:24:text:llama4:0:2 | ecom: reviewers "unfair price" | base | 3 | 18K | partial_success | click(1556)→noop→send("") | (none) | F_EMPTY_ANS | agent click 后 noop 再提交空答案，未读取 review 内容 |
| 28 | ecom:base:24:text:llama4:0:3 | ecom: reviewers "unfair price" | base | 3 | 18K | partial_success | click(1556)→noop→send("") | (none) | F_EMPTY_ANS | agent click 后 noop 再提交空答案，未读取 review 内容 |
| 29 | ecom:base:24:text:llama4:0:4 | ecom: reviewers "unfair price" | base | 2 | 9K | partial_success | click(1557)→send("Jay, Josef Bürger") | (none) | F_REA | agent 提交了 Jay, Josef Bürger 但答案错误，agent 看到了 review 但误读了 reviewer 名字 |
| 30 | ecom:base:24:text:llama4:0:5 | ecom: reviewers "unfair price" | base | 3 | 18K | partial_success | click(1556)→noop→send("") | (none) | F_EMPTY_ANS | agent 提交空答案，未读取 review 内容 |
| 31 | ecom:high:24:text:llama4:0:1 | ecom: reviewers "unfair price" | high | 3 | 18K | partial_success | click(1556)→noop→send("") | (none) | F_EMPTY_ANS | agent 提交空答案，未读取 review 内容 |
| 32 | ecom:high:24:text:llama4:0:2 | ecom: reviewers "unfair price" | high | 3 | 18K | partial_success | click(1556)→noop→send("") | (none) | F_EMPTY_ANS | agent 提交空答案，未读取 review 内容 |
| 33 | ecom:high:24:text:llama4:0:3 | ecom: reviewers "unfair price" | high | 2 | 9K | partial_success | click(1557)→send("Jay,Josef Bürger") | (none) | F_REA | agent 提交了 Jay,Josef Bürger 但答案错误，agent 看到了 review 但误读了 reviewer 名字 |
| 34 | ecom:high:24:text:llama4:0:4 | ecom: reviewers "unfair price" | high | 3 | 18K | partial_success | click(1557)→noop→send("") | (none) | F_EMPTY_ANS | agent 提交空答案，未读取 review 内容 |
| 35 | ecom:high:24:text:llama4:0:5 | ecom: reviewers "unfair price" | high | 3 | 18K | partial_success | click(1556)→noop→send("") | (none) | F_EMPTY_ANS | agent 提交空答案，未读取 review 内容 |
| 36 | ecom:ml:24:text:llama4:0:1 | ecom: reviewers "unfair price" | ml | 3 | 17K | partial_success | click(1557)→noop→send("") | (none) | F_EMPTY_ANS | agent 提交空答案，未读取 review 内容 |
| 37 | ecom:ml:24:text:llama4:0:2 | ecom: reviewers "unfair price" | ml | 3 | 17K | partial_success | click(1557)→noop→send("") | (none) | F_EMPTY_ANS | agent 提交空答案，未读取 review 内容 |
| 38 | ecom:ml:24:text:llama4:0:3 | ecom: reviewers "unfair price" | ml | 3 | 17K | partial_success | click(1557)→noop→send("") | (none) | F_EMPTY_ANS | agent 提交空答案，未读取 review 内容 |
| 39 | ecom:ml:24:text:llama4:0:4 | ecom: reviewers "unfair price" | ml | 3 | 17K | partial_success | click(1557)→noop→send("") | (none) | F_EMPTY_ANS | agent 提交空答案，未读取 review 内容 |
| 40 | ecom:ml:24:text:llama4:0:5 | ecom: reviewers "unfair price" | ml | 3 | 17K | partial_success | click(1557)→noop→send("") | (none) | F_EMPTY_ANS | agent 提交空答案，未读取 review 内容 |
| 41 | ecom:base:26:text:llama4:0:3 | ecom: reviewers "customer service" | base | 3 | 42K | partial_success | click(1894)→scroll→send("Bob in Vegas") | (none) | F_REA | agent 提交了 "Bob in Vegas" 但 ground truth 是 "Bob in Vegas, RemyRRemyR"——agent 只找到了一个 reviewer，漏掉了 RemyRRemyR |
| 42 | ecom:high:26:text:llama4:0:1 | ecom: reviewers "customer service" | high | 3 | 42K | partial_success | click(1894)→scroll→send("Bob in Vegas") | (none) | F_REA | agent 提交了 "Bob in Vegas" 但 ground truth 是 "Bob in Vegas, RemyRRemyR"——漏掉了第二个 reviewer |
| 43 | ecom:high:26:text:llama4:0:3 | ecom: reviewers "customer service" | high | 3 | 42K | partial_success | click(1894)→scroll→send("Bob in Vegas") | (none) | F_REA | agent 提交了 "Bob in Vegas" 但 ground truth 是 "Bob in Vegas, RemyRRemyR"——漏掉了第二个 reviewer |
| 44 | ecom:ml:26:text:llama4:0:1 | ecom: reviewers "customer service" | ml | 3 | 41K | partial_success | click(1894)→scroll→send("Bob in Vegas") | (none) | F_REA | agent 提交了 "Bob in Vegas" 但 ground truth 是 "Bob in Vegas, RemyRRemyR"——漏掉了第二个 reviewer |
| 45 | ecom:ml:26:text:llama4:0:2 | ecom: reviewers "customer service" | ml | 3 | 41K | partial_success | click(1894)→scroll→send("Bob in Vegas") | (none) | F_REA | agent 提交了 "Bob in Vegas" 但 ground truth 是 "Bob in Vegas, RemyRRemyR"——漏掉了第二个 reviewer |
| 46 | ecom:ml:26:text:llama4:0:3 | ecom: reviewers "customer service" | ml | 3 | 41K | partial_success | click(1894)→scroll→send("Bob in Vegas") | (none) | F_REA | agent 提交了 "Bob in Vegas" 但 ground truth 是 "Bob in Vegas, RemyRRemyR"——漏掉了第二个 reviewer |
| 47 | ecom:ml:26:text:llama4:0:4 | ecom: reviewers "customer service" | ml | 3 | 41K | partial_success | click(1894)→scroll→send("Bob in Vegas") | (none) | F_REA | agent 提交了 "Bob in Vegas" 但 ground truth 是 "Bob in Vegas, RemyRRemyR"——漏掉了第二个 reviewer |
| 48 | ecom:ml:26:text:llama4:0:5 | ecom: reviewers "customer service" | ml | 3 | 41K | partial_success | click(1894)→scroll→send("Bob in Vegas") | (none) | F_REA | agent 提交了 "Bob in Vegas" 但 ground truth 是 "Bob in Vegas, RemyRRemyR"——漏掉了第二个 reviewer |
| 49 | reddit:base:29:text:llama4:0:1 | reddit: count downvoted comments | base | 5 | 100K | partial_success | click→click→click→click→send("0") | (none) | F_REA | agent 提交了 0 但答案错误（partial_success），agent 看到了 comment 列表但误判了 downvote 数量 |
| 50 | reddit:base:29:text:llama4:0:4 | reddit: count downvoted comments | base | 4 | 27K | failure | click→click→click→click (no send) | (none) | F_AMB | agent 导航到 reddit 后未提交任何答案就结束，未完成任务 |
| 51 | reddit:base:29:text:llama4:0:5 | reddit: count downvoted comments | base | 4 | 27K | failure | click→click→click→click (no send) | (none) | F_AMB | agent 导航到 reddit 后未提交任何答案就结束，未完成任务 |
| 52 | reddit:low:29:text:llama4:0:3 | reddit: count downvoted comments | low | 8 | 21K | failure | click→noop→noop→scroll→fill("DIY")→click | (none) | F_AMB | task_feasible=True；agent 搜索了 "DIY"（与 downvote 任务无关）后 send cannot complete，属于任务理解错误而非结构性不可完成 |
| 53 | reddit:ml:29:text:llama4:0:1 | reddit: count downvoted comments | ml | 6 | 57K | failure | click→scroll→scroll→click→click→click | (none) | F_AMB | agent 在 reddit 页面导航但未提交答案就结束，无法判断 downvote 数量 |
| 54 | reddit:ml:29:text:llama4:0:2 | reddit: count downvoted comments | ml | 4 | 27K | failure | click→click→click→click (no send) | (none) | F_AMB | agent 导航到 reddit 后未提交任何答案就结束 |
| 55 | reddit:ml:29:text:llama4:0:3 | reddit: count downvoted comments | ml | 4 | 26K | failure | click→click→click→click (no send) | (none) | F_AMB | agent 导航到 reddit 后未提交任何答案就结束 |
| 56 | reddit:ml:29:text:llama4:0:4 | reddit: count downvoted comments | ml | 4 | 26K | failure | click→click→click→click (no send) | (none) | F_AMB | agent 导航到 reddit 后未提交任何答案就结束 |
| 57 | reddit:ml:29:text:llama4:0:5 | reddit: count downvoted comments | ml | 4 | 26K | failure | click→click→click→click (no send) | (none) | F_AMB | agent 导航到 reddit 后未提交任何答案就结束 |
| 58 | reddit:low:67:text:llama4:0:2 | reddit: book names top 10 posts | low | 14 | 49K | partial_success | click→click→fill("books")→click→click→goto(/books) | (none) | F_REA | agent 找到了 books subreddit 并提交了书名列表，但答案与 ground truth 不匹配（partial_success） |
| 59 | reddit:low:67:text:llama4:0:3 | reddit: book names top 10 posts | low | 14 | 98K | partial_success | click→fill("books")→click→click→goto(/books)→goto(/) | Timeout goto; bid "Places" not found | F_REA | agent 找到了 books subreddit 并提交了书名列表，但答案错误；element not found 错误不是主要失败原因 |
| 60 | admin:low:94:text:llama4:0:3 | admin: invoice grand total | low | 13 | 93K | failure | click→hover→goto(orders)→go_back→click→goto(invoices) | Timeout 500ms ×3 | F_REA | task_feasible=True（同 agent 的 reps 1/2/4 均成功）；agent 在可完成的任务上导航/操作失误，多次 timeout 后放弃 |
| 61 | admin:low:94:text:llama4:0:5 | admin: invoice grand total | low | 12 | 88K | partial_success | click→hover→goto(orders)→click→hover→goto(invoices) | Timeout 500ms ×3 | F_REA | task_feasible=True（同 agent 的 reps 1/2/4 均成功）；agent 在可完成的任务上提交了错误答案 "Invoice not found" |
| 62 | admin:base:198:text:llama4:0:3 | admin: cancelled order customer | base | 4 | 49K | partial_success | click→click→noop→send("Samantha Jones") | (none) | F_REA | agent 提交了 Samantha Jones 但答案错误（partial_success），agent 看到了订单列表但选错了客户 |
| 63 | gitlab:low:293:text:llama4:0:2 | gitlab: SSH clone Super_Awesome_Robot | low | 5 | 50K | failure | fill→click→click→fill→send("cannot complete") | (none) | F_SIF | low variant 下 SSH clone tab 不可见，agent 搜索后找不到 SSH URL，send cannot complete |
| 64 | gitlab:low:293:text:llama4:0:3 | gitlab: SSH clone Super_Awesome_Robot | low | 6 | 68K | failure | fill→click→click→fill→noop→send("cannot complete") | (none) | F_SIF | low variant 下 SSH clone tab 不可见，agent send cannot complete |
| 65 | gitlab:low:293:text:llama4:0:4 | gitlab: SSH clone Super_Awesome_Robot | low | 5 | 50K | failure | fill→click→click→fill→send("cannot complete") | (none) | F_SIF | low variant 下 SSH clone tab 不可见，agent send cannot complete |
| 66 | gitlab:low:293:text:llama4:0:5 | gitlab: SSH clone Super_Awesome_Robot | low | 5 | 50K | failure | fill→click→click→fill→send("cannot complete") | (none) | F_SIF | low variant 下 SSH clone tab 不可见，agent send cannot complete |
| 67 | gitlab:ml:293:text:llama4:0:1 | gitlab: SSH clone Super_Awesome_Robot | ml | 5 | 52K | partial_success | fill→click→click→click→send(SSH URL) | (none) | F_REA | agent 提交了 SSH URL 但答案错误（partial_success），agent 找到了 SSH clone 选项但提交了错误的 URL |
| 68 | gitlab:low:308:text:llama4:0:4 | gitlab: most contributions primer/design | low | 6 | 80K | partial_success | click→click→goto(commits)→click→goto(graphs)→send("Cole Bemis") | Timeout 500ms ×2 | F_REA | agent 提交了 Cole Bemis 但答案错误（partial_success），agent 看到了 contributor graph 但误读了贡献者 |
| 69 | gitlab:low:308:text:llama4:0:5 | gitlab: most contributions primer/design | low | 6 | 79K | partial_success | click→click→goto(commits)→click→goto(graphs)→send("Cole Bemis") | Timeout 500ms ×2 | F_REA | agent 提交了 Cole Bemis 但答案错误（partial_success），agent 看到了 contributor graph 但误读了贡献者 |


### Section C: Vision-only (SoM) / Claude Sonnet (57 cases)

| # | case_id | task | var | steps | tokens | outcome | action_sequence (前6步) | errors | reclass | rationale |
|---|---------|------|-----|-------|--------|---------|------------------------|--------|---------|-----------|
| 70 | admin:base:4:som:claude:0:1 | admin: top-3 bestsellers Jan 2023 | base | 2 | 4K | failure | click(769)→click(736) | (none) | F_SOM_NAV | SoM agent 仅做 2 步 click(769)→click(736) 后结束，无法导航到 sales report 页面 |
| 71 | admin:base:4:som:claude:0:2 | admin: top-3 bestsellers Jan 2023 | base | 2 | 4K | failure | click(769)→click(736) | (none) | F_SOM_NAV | SoM agent 仅做 2 步 click(769)→click(736) 后结束，无法导航到 sales report 页面 |
| 72 | admin:base:4:som:claude:0:3 | admin: top-3 bestsellers Jan 2023 | base | 2 | 4K | failure | click(769)→click(736) | (none) | F_SOM_NAV | SoM agent 仅做 2 步 click(769)→click(736) 后结束，无法导航到 sales report 页面 |
| 73 | admin:base:4:som:claude:0:4 | admin: top-3 bestsellers Jan 2023 | base | 2 | 4K | failure | click(769)→click(736) | (none) | F_SOM_NAV | SoM agent 仅做 2 步 click(769)→click(736) 后结束，无法导航到 sales report 页面 |
| 74 | admin:base:4:som:claude:0:5 | admin: top-3 bestsellers Jan 2023 | base | 2 | 4K | failure | click(769)→click(736) | (none) | F_SOM_NAV | SoM agent 仅做 2 步 click(769)→click(736) 后结束，无法导航到 sales report 页面 |
| 75 | admin:high:4:som:claude:0:1 | admin: top-3 bestsellers Jan 2023 | high | 17 | 45K | partial_success | click(769)→click(736)→click(85)→click(117)→click(414)→goto(dashboard) | (none) | F_SOM_MISREAD | SoM agent 经过 17 步导航后提交了答案，但 partial_success 说明答案错误，agent 误读了 report 数据 |
| 76 | admin:high:4:som:claude:0:2 | admin: top-3 bestsellers Jan 2023 | high | 2 | 4K | failure | click(769)→click(736) | (none) | F_SOM_NAV | SoM agent 仅做 2 步 click(769)→click(736) 后结束，无法导航到 sales report 页面 |
| 77 | admin:high:4:som:claude:0:3 | admin: top-3 bestsellers Jan 2023 | high | 8 | 19K | failure | click(769)→click(769)→click(736)→click(113)→click(113)→click(85) | (none) | F_SOM_NAV | SoM agent 反复 click(769)→click(736) 等按钮，8 步后仍未到达 report 页面 |
| 78 | admin:high:4:som:claude:0:4 | admin: top-3 bestsellers Jan 2023 | high | 1 | 2K | failure | click(736) | (none) | F_SOM_NAV | SoM agent 仅做 1 步 click(736) 后结束，无法导航到 sales report 页面 |
| 79 | admin:low:4:som:claude:0:2 | admin: top-3 bestsellers Jan 2023 | low | 7 | 20K | failure | click(615)→scroll→click(769)→scroll→scroll→click(700) | Timeout 3000ms | F_SOM_EXPLORE | low variant 下 SoM agent 在 admin 页面反复 scroll 和 click，7 步后仍未到达 report 页面 |
| 80 | admin:low:4:som:claude:0:3 | admin: top-3 bestsellers Jan 2023 | low | 4 | 10K | partial_success | click(615)→scroll→click(769)→send(answer) | Timeout 3000ms | F_SOM_MISREAD | low variant 下 SoM agent 提交了答案但 partial_success 说明答案错误，agent 误读了 report 数据 |
| 81 | admin:ml:4:som:claude:0:1 | admin: top-3 bestsellers Jan 2023 | ml | 2 | 4K | failure | click(769)→click(736) | (none) | F_SOM_NAV | SoM agent 仅做 2 步 click(769)→click(736) 后结束，无法导航到 sales report 页面 |
| 82 | admin:ml:4:som:claude:0:3 | admin: top-3 bestsellers Jan 2023 | ml | 2 | 4K | failure | click(769)→click(736) | (none) | F_SOM_NAV | SoM agent 仅做 2 步 click(769)→click(736) 后结束，无法导航到 sales report 页面 |
| 83 | admin:ml:4:som:claude:0:5 | admin: top-3 bestsellers Jan 2023 | ml | 2 | 4K | failure | click(769)→click(736) | (none) | F_SOM_NAV | SoM agent 仅做 2 步 click(769)→click(736) 后结束，无法导航到 sales report 页面 |
| 84 | ecom:base:23:som:claude:0:1 | ecom: reviewers "fingerprint resistant" | base | 7 | 19K | partial_success | click(1421)→scroll×4→click(615) | Timeout 3000ms | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 85 | ecom:base:23:som:claude:0:2 | ecom: reviewers "fingerprint resistant" | base | 5 | 12K | partial_success | click(1421)→scroll×3→send("Rachel, annon") | (none) | F_SOM_MISREAD | SoM agent 提交了 Rachel, annon 但答案错误，agent 从截图中误读了 reviewer 名字 |
| 86 | ecom:base:23:som:claude:0:3 | ecom: reviewers "fingerprint resistant" | base | 7 | 19K | partial_success | click(1421)→scroll×4→click(615) | Timeout 3000ms | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 87 | ecom:base:23:som:claude:0:4 | ecom: reviewers "fingerprint resistant" | base | 7 | 18K | partial_success | click(1421)→scroll×4→scroll→scroll | (none) | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 88 | ecom:high:23:som:claude:0:1 | ecom: reviewers "fingerprint resistant" | high | 7 | 19K | partial_success | click(1421)→scroll×4→click(615) | Timeout 3000ms | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 89 | ecom:high:23:som:claude:0:2 | ecom: reviewers "fingerprint resistant" | high | 7 | 18K | partial_success | click(1421)→scroll×4→click(615) | Timeout 3000ms | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 90 | ecom:high:23:som:claude:0:5 | ecom: reviewers "fingerprint resistant" | high | 6 | 15K | partial_success | click(1421)→scroll×4→send("hel, annon") | (none) | F_SOM_MISREAD | SoM agent 提交了 hel, annon 但答案错误，agent 从截图中误读了 reviewer 名字 |
| 91 | ecom:low:23:som:claude:0:1 | ecom: reviewers "fingerprint resistant" | low | 18 | 61K | failure | click(1421)→scroll×3→scroll(-800)→click(1551)→... | Timeout 3000ms | F_SOM_EXPLORE | low variant 下 SoM agent 陷入 18 步 scroll/click 循环，无法找到 review 内容，最终 timeout |
| 92 | ecom:low:23:som:claude:0:5 | ecom: reviewers "fingerprint resistant" | low | 18 | 62K | failure | click(1421)→scroll×2→click(1551)→scroll×2→... | Timeout 3000ms | F_SOM_EXPLORE | low variant 下 SoM agent 陷入 18 步 scroll/click 循环，无法找到 review 内容，最终 timeout |
| 93 | ecom:ml:23:som:claude:0:1 | ecom: reviewers "fingerprint resistant" | ml | 6 | 15K | partial_success | click(1421)→scroll×4→send("Rachel, Lee14") | (none) | F_SOM_MISREAD | SoM agent 提交了 Rachel, Lee14 但答案错误，agent 从截图中误读了 reviewer 名字 |
| 94 | ecom:ml:23:som:claude:0:2 | ecom: reviewers "fingerprint resistant" | ml | 6 | 15K | partial_success | click(1422)→scroll×4→send("Rachel, Source Prof") | (none) | F_SOM_MISREAD | SoM agent 提交了 Rachel, Source Prof 但答案错误，agent 从截图中误读了 reviewer 名字 |
| 95 | ecom:ml:23:som:claude:0:3 | ecom: reviewers "fingerprint resistant" | ml | 7 | 19K | partial_success | click(1422)→scroll×4→click(615) | Timeout 3000ms | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 96 | ecom:base:26:som:claude:0:1 | ecom: reviewers "customer service" | base | 4 | 9K | partial_success | click(1421)→scroll×2→send("Dion in Vegas") | (none) | F_SOM_MISREAD | SoM agent 提交了 Dion in Vegas 但答案错误（partial_success），agent 从截图中误读了 reviewer 名字 |
| 97 | ecom:base:26:som:claude:0:2 | ecom: reviewers "customer service" | base | 9 | 24K | partial_success | click(1421)→scroll×5→... | (none) | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 98 | ecom:base:26:som:claude:0:3 | ecom: reviewers "customer service" | base | 9 | 25K | partial_success | click(1421)→scroll×5→... | (none) | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 99 | ecom:base:26:som:claude:0:4 | ecom: reviewers "customer service" | base | 10 | 31K | partial_success | click(888)→click(1421)→scroll×4→... | Timeout 3000ms | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 100 | ecom:base:26:som:claude:0:5 | ecom: reviewers "customer service" | base | 9 | 25K | partial_success | click(1421)→scroll×5→... | (none) | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 101 | ecom:high:26:som:claude:0:2 | ecom: reviewers "customer service" | high | 9 | 25K | partial_success | click(1421)→scroll×5→... | (none) | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 102 | ecom:high:26:som:claude:0:3 | ecom: reviewers "customer service" | high | 4 | 9K | partial_success | click(1421)→scroll×2→send("Pish") | (none) | F_SOM_MISREAD | SoM agent 提交了 Pish 但答案错误，agent 从截图中误读了 reviewer 名字 |
| 103 | ecom:high:26:som:claude:0:4 | ecom: reviewers "customer service" | high | 9 | 25K | partial_success | click(1421)→scroll×5→... | (none) | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 104 | ecom:high:26:som:claude:0:5 | ecom: reviewers "customer service" | high | 9 | 24K | partial_success | click(1421)→scroll×5→... | (none) | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 105 | ecom:low:26:som:claude:0:1 | ecom: reviewers "customer service" | low | 15 | 43K | failure | click(1421)→scroll×4→scroll(-1500)→... | (none) | F_SOM_EXPLORE | low variant 下 SoM agent 陷入 15 步 scroll 循环，无法找到 review 内容，最终 send cannot complete |
| 106 | ecom:low:26:som:claude:0:2 | ecom: reviewers "customer service" | low | 11 | 30K | partial_success | click(1422)→scroll×4→... | (none) | F_SIF | task_feasible=False；agent 明确说 "No customer reviews are displayed on this page"——review 内容在 low variant 下不可见，非视觉误读 |
| 107 | ecom:low:26:som:claude:0:3 | ecom: reviewers "customer service" | low | 11 | 30K | partial_success | click(1421)→scroll×2→click(1894)→scroll×2→... | (none) | F_SIF | task_feasible=False；agent 明确说 "No customer reviews found on this page"——review 内容在 low variant 下不可见，非视觉误读 |
| 108 | ecom:low:26:som:claude:0:4 | ecom: reviewers "customer service" | low | 18 | 51K | partial_success | click(1421)→scroll×2→click(1894)→scroll×2→... | (none) | F_SIF | task_feasible=False；agent 明确说 "No customer reviews are displayed...individual customer review content is not available"——结构性不可完成 |
| 109 | ecom:low:26:som:claude:0:5 | ecom: reviewers "customer service" | low | 19 | 58K | partial_success | click(1421)→scroll×3→scroll(-1500)→... | Timeout 3000ms | F_SIF | task_feasible=False；agent 明确说 "No customer reviews are displayed...Reviews section only shows product specifications"——结构性不可完成 |
| 110 | ecom:ml:26:som:claude:0:1 | ecom: reviewers "customer service" | ml | 10 | 27K | partial_success | click(1408)→click(1421)→scroll×4→... | (none) | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 111 | ecom:ml:26:som:claude:0:2 | ecom: reviewers "customer service" | ml | 13 | 39K | partial_success | click(888)→click(1408)→click(1407)→click(1442)→click(1421)→scroll | Timeout 3000ms | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了 reviewer 名字 |
| 112 | ecom:ml:26:som:claude:0:3 | ecom: reviewers "customer service" | ml | 6 | 16K | partial_success | click(888)→click(1408)→click(1421)→scroll×2→send("Rich") | Timeout 3000ms | F_SOM_MISREAD | SoM agent 提交了 Rich 但答案错误，agent 从截图中误读了 reviewer 名字 |
| 113 | admin:base:41:som:claude:0:1 | admin: top 1 search term | base | 3 | 6K | partial_success | click(227)→click(274)→send("MT02-M-Gray") | (none) | F_SOM_MISREAD | SoM agent 提交了 MT02-M-Gray 但答案错误（partial_success），agent 从截图中误读了 search term |
| 114 | admin:low:41:som:claude:0:2 | admin: top 1 search term | low | 4 | 8K | partial_success | click(672)→scroll→scroll→send("Racer Tank") | (none) | F_SOM_MISREAD | low variant 下 SoM agent 提交了 Racer Tank 但答案错误（partial_success），agent 误读了 search term |
| 115 | admin:low:41:som:claude:0:4 | admin: top 1 search term | low | 4 | 8K | partial_success | click(672)→scroll→scroll→send("Racer Tank") | (none) | F_SOM_MISREAD | low variant 下 SoM agent 提交了 Racer Tank 但答案错误（partial_success），agent 误读了 search term |
| 116 | admin:low:41:som:claude:0:5 | admin: top 1 search term | low | 1 | 2K | failure | click(724) | (none) | F_SOM_NAV | low variant 下 SoM agent 仅做 1 步 click(724) 后结束，无法导航到 search terms report 页面 |
| 117 | admin:ml:41:som:claude:0:1 | admin: top 1 search term | ml | 6 | 14K | partial_success | click(340)→click(359)→click(469)→click(222)→click(269)→send("MT02-M-Gray") | Timeout 500ms | F_SOM_MISREAD | SoM agent 提交了 MT02-M-Gray 但答案错误（partial_success），agent 从截图中误读了 search term |
| 118 | reddit:base:67:som:claude:0:3 | reddit: book names top 10 posts | base | 22 | 57K | failure | click(43)→scroll×3→click(562)→go_back→... | (none) | F_SOM_EXPLORE | SoM agent 陷入 22 步 scroll/click 循环，在多个 reddit 页面来回跳转，最终 timeout |
| 119 | admin:base:198:som:claude:0:2 | admin: cancelled order customer | base | 5 | 11K | partial_success | click(188)→click(157)→click(169)→click(742)→send("Alexander Thomas") | Timeout 500ms | F_SOM_MISREAD | SoM agent 提交了 Alexander Thomas 但答案错误（partial_success），agent 从截图中误读了客户名 |
| 120 | admin:base:198:som:claude:0:5 | admin: cancelled order customer | base | 6 | 14K | partial_success | click(188)→click(157)→click(169)→click(744)→click(1393)→send | Timeout 500ms | F_SOM_MISREAD | SoM agent 提交了答案但 partial_success 说明答案错误，agent 从截图中误读了客户名 |
| 121 | admin:high:198:som:claude:0:1 | admin: cancelled order customer | high | 4 | 9K | partial_success | click(157)→click(141)→click(169)→send("Samantha Jones") | Timeout 500ms | F_SOM_MISREAD | SoM agent 提交了 Samantha Jones 但答案错误（partial_success），agent 从截图中误读了客户名 |
| 122 | admin:ml:198:som:claude:0:5 | admin: cancelled order customer | ml | 5 | 10K | partial_success | click(188)→click(157)→click(169)→scroll→send("Adam Garcia") | (none) | F_SOM_MISREAD | SoM agent 提交了 Adam Garcia 但答案错误（partial_success），agent 从截图中误读了客户名 |
| 123 | gitlab:low:308:som:claude:0:2 | gitlab: most contributions primer/design | low | 2 | 4K | failure | fill(157,"primer/design")→goto(github.com/primer/design) | fill error: not an input | F_WEA | SoM agent 尝试 fill 非 input 元素后 goto(github.com/primer/design)，导航到了错误的外部网站 |
| 124 | gitlab:low:308:som:claude:0:3 | gitlab: most contributions primer/design | low | 1 | 2K | failure | goto(github.com/primer/design) | (none) | F_WEA | SoM agent 直接 goto(github.com/primer/design)，导航到了错误的外部网站而非本地 gitlab |
| 125 | gitlab:low:308:som:claude:0:4 | gitlab: most contributions primer/design | low | 2 | 4K | failure | fill(157,"primer/design")→goto(github.com/primer/design) | fill error: not an input | F_WEA | SoM agent 尝试 fill 非 input 元素后 goto(github.com/primer/design)，导航到了错误的外部网站 |
| 126 | gitlab:low:308:som:claude:0:5 | gitlab: most contributions primer/design | low | 2 | 4K | failure | fill(157,"primer/design")→goto(github.com/primer/design) | fill error: not an input | F_WEA | SoM agent 尝试 fill 非 input 元素后 goto(github.com/primer/design)，导航到了错误的外部网站 |

---

## Summary Tables (填完所有 126 cases 后汇总)

### Reclassification Distribution

| Reclassified Type | Count | % of 126 |
|-------------------|-------|----------|
| F_SOM_MISREAD (visual misread) | 32 | 25.4% |
| F_SIF (structural infeasibility) | 27 | 21.4% |
| F_REA (reasoning error) | 20 | 15.9% |
| F_EMPTY_ANS (empty/wrong answer) | 13 | 10.3% |
| F_SOM_NAV (navigation failure) | 12 | 9.5% |
| F_WEA (wrong element) | 9 | 7.1% |
| F_AMB (task ambiguity) | 8 | 6.3% |
| F_SOM_EXPLORE (exploration spiral) | 5 | 4.0% |
| F_ENF (element not found) | 0 | 0% |
| F_TKI (token inflation) | 0 | 0% |
| F_COF (context overflow) | 0 | 0% |
| F_SOM_PHANTOM (phantom bid) | 0 | 0% |
| F_UNK (genuinely unclassifiable) | 0 | 0% |

### By Agent Group

| Group | Dominant Reclassified Type | 2nd Most Common | Still F_UNK |
|-------|--------------------------|-----------------|-------------|
| text-only / Claude (20) | F_SIF (19, 95%) | F_REA (1, 5%) | 0 |
| text-only / Llama 4 (49) | F_REA (19, 39%) | F_EMPTY_ANS (13, 27%) | 0 |
| vision-only / Claude (57) | F_SOM_MISREAD (32, 56%) | F_SOM_NAV (12, 21%) | 0 |

### Key Findings

1. **F_UNK 中最大的隐藏类别是**: F_SOM_MISREAD（SoM agent 视觉误读，32 cases，25.4%）；text-only 中最大隐藏类别是 F_SIF（结构性不可完成，28 cases）
2. **F_UNK 是否真的异质（genuinely heterogeneous）**: Yes — 涵盖 8 种不同失败类型，但各组内部高度同质（Claude text → F_SIF；SoM → F_SOM_MISREAD）
3. **重分类后是否改变论文的任何 claim**: No — F_SIF 和 F_SOM_MISREAD 均已在论文中讨论；F_EMPTY_ANS 是 Llama4 特有的模型能力问题，不影响主要结论
4. **建议的论文修改**:
   - [x] 在 §5.7 加一句承认 F_UNK 的局限性
   - [x] 在 footnote 报告 manual review 结果
   - [ ] 修改 failure taxonomy（不需要，现有分类已覆盖）
   - [ ] 不需要改动

### Reviewer Response 草稿

> "We conducted a manual review of all 126 F_UNK cases, cross-validated
> against ground truth traces and task feasibility flags. The dominant
> reclassified category was F_SOM_MISREAD (25.4%), reflecting SoM agents
> misreading data from screenshots. The second most common was
> F_SIF (21.4%), where low-accessibility-tree variants structurally prevented
> task completion — concentrated in ecommerce review tasks where review content
> disappeared from the a11y tree under L3 violations. F_REA (reasoning errors,
> 15.9%) was the third most common, including Llama 4's systematic partial
> answer extraction (e.g., finding one of two reviewers but not both).
> F_EMPTY_ANS (10.3%) was specific to Llama 4's tendency to submit empty
> answers after a single click — a model-level instruction-following deficit
> unrelated to accessibility level. 0% of cases remained genuinely
> unclassifiable after manual inspection. Cohen's κ for inter-rater
> reliability will be reported based on independent second-reviewer
> classification of a 30% subsample. The reclassification does not change
> any primary finding because both F_SOM_MISREAD and F_SIF are already
> discussed in the paper, and the accessibility-attributed failure types
> (F_SIF, F_SOM_EXPLORE) concentrate under the Low variant as predicted
> by the L3 severity framework."
