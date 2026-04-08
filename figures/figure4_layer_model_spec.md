# Figure 4: Five-Layer Architecture — 完整图表规格说明

## 图表标题
**主标题**: Five-Layer Architecture — Observation, Action, Injection & bid Lifecycle
**副标题**: 三种 Agent 的观察/操作路径、Variant 注入作用域、bid 生命周期与 Phantom bid 机制

---

## 一、整体布局

图分为两大区域：
- **左侧主区域（~65% 宽度）**：五层水平带从底到顶堆叠
- **右侧辅助区域（~35% 宽度）**：注入机制 + Phantom bid + Variant 传播路径

---

## 二、五层定义（从底到顶）

---

### Layer 0: WebArena Server (HTTP)
- **背景色**: 浅紫色带
- **含义**: 运行在 Docker 中的 Web 应用服务器

#### 框 L0-A: "WebArena Services"
- 文字: Magento storefront (:7770) / Magento admin (:7780) / Postmill (:9999) / GitLab (:8023)
- 说明: 接收 HTTP 请求，返回原始 HTML/CSS/JS

#### 框 L0-B: "NOT MODIFIED"
- 文字: 我们不修改此层。无服务端代码变更、无数据库编辑、无模板修改。所有操作发生在客户端。
- 样式: 灰色背景，加粗文字，表示"禁区"

#### 连线 L0→L1:
- **L0-A 顶部 → L1-A 底部**: 实线向上箭头
- 标注: "HTTP Response (HTML)" — 服务器返回的原始 HTML 文档

---

### Layer 1: DOM (Live Document Object Model)
- **背景色**: 浅绿色带
- **含义**: 浏览器内存中的文档对象模型，是我们所有 variant patch 的唯一操作目标
- **关键**: 这是整张图的核心层——所有注入都指向这里，所有观察都从这里派生

#### 框 L1-A: "Live DOM Elements"
- 文字:
  - HTML 语义元素: `<nav>`, `<main>`, `<header>`, `<h1>`-`<h6>`, `<a href>`, `<button>`
  - ARIA 属性: `aria-label`, `aria-hidden`, `role`, `aria-expanded`
  - 表单: `<label>`, `<input>`, `placeholder`
  - 表格: `<thead>`, `<th>`, `<tbody>`
  - 其他: `alt`, `lang`, `tabindex`, 事件处理器 (`onclick`, `onkeydown`)
- 说明: 这是浏览器解析 HTML 后在内存中构建的活文档。所有 variant JS 通过 `document.querySelector` + `element.replaceWith` / `removeAttribute` / `setAttribute` 直接操作这些元素和属性。

#### 框 L1-B: "bid Attribute (BrowserGym 写入)"
- 文字: `browsergym_set_of_marks="42"`
- 说明: BrowserGym 在每次 `env.step()` / `env.reset()` 后遍历 DOM，给每个"可交互"元素注入此自定义属性。bid 数字是 BrowserGym 分配的唯一标识符。
- 样式: 金色背景，加粗边框，表示 bid 是跨层桥梁
- **关键标注**: "bid 诞生于 Layer 3 (BrowserGym)，但被写回到 Layer 1 (DOM)"

#### 框 L1-C: "Rendered Pixels (视觉渲染)"
- 文字: CSS + DOM → 视觉布局 → `page.screenshot()` 捕获为 PNG 位图
- 说明: 浏览器的渲染引擎将 DOM + CSS 合成为屏幕像素。CUA agent 直接观察这个层面。
- 样式: 浅灰色背景

#### 连线 L1→L2:
- **L1-A 顶部 → L2-A 底部**: 实线向上箭头
- 标注: "Chrome Blink 自动从 DOM 构建 AX Tree"
- 说明: 这是自动派生关系，不是我们控制的——Chrome 读取 DOM 元素、CSS computed styles、ARIA 属性，构建内部 accessibility tree

#### 连线 L3→L1 (bid 写回):
- **L3-C 底部 → L1-B 顶部**: 金色虚线向下箭头
- 标注: "BrowserGym 写 bid 回 DOM"
- 说明: bid 的反向写入——从 Layer 3 写回 Layer 1

---

### Layer 2: Blink AX Tree (Chrome Internal Accessibility Representation)
- **背景色**: 浅蓝色带
- **含义**: Chrome 的 Blink 引擎从 DOM 自动构建的 accessibility tree，是所有 a11y 数据的源头

#### 框 L2-A: "Blink AX Tree"
- 文字:
  - 每个节点包含: nodeId, role, name, properties, childIds, backendDOMNodeId
  - bid 作为节点 property 出现（来自 DOM 上的 `browsergym_set_of_marks` 属性）
  - 示例节点: `{role: "link", name: "Home", properties: [{name: "browsergym_set_of_marks", value: "42"}]}`
- 说明: 这棵树是 DOM 的语义投影。我们不直接操作它，但因为它从 DOM 派生，DOM 层的 variant patch 会自动反映到这里。

#### 框 L2-B: "派生关系说明"
- 文字:
  - AX Tree 是 DERIVED（派生的），不是独立的
  - 如果 variant patch 在 DOM 上删除了 `aria-label` → Blink 重建 AX Tree → 对应节点失去 accessible name
  - 如果 variant patch 把 `<nav>` 替换为 `<div>` → AX Tree 中 `navigation` role 消失，变为 `generic`
  - 如果 variant patch 把 `<a>` 替换为 `<span>` → AX Tree 中 `link` role 消失 + bid 属性丢失（旧 DOM 节点被删除）
- 样式: 信息框，浅蓝背景

#### 连线 L2→L3:
- **L2-A 顶部 → L3-A 底部**: 实线向上箭头
- 标注: "CDP Accessibility.getFullAXTree (Experimental API)"
- 说明: BrowserGym 通过 Chrome DevTools Protocol 拉取完整 AX Tree。这是所有 a11y tree 数据的唯一入口。
- 样式: 蓝色加粗标注

---

### Layer 3: BrowserGym Processing
- **背景色**: 浅黄色带
- **含义**: BrowserGym 框架的加工层，负责 AX Tree 序列化、SoM overlay 生成、bid 管理

#### 框 L3-A: "AXTree Serialization"
- 文字:
  - 函数: `flatten_axtree_to_str()`
  - 输入: CDP 返回的 AXTree JSON
  - 输出: 文本格式，每行一个节点
  - 示例输出:
    ```
    [42] link 'Home'
    [43] button 'Submit'
    [44] textbox 'Search...' required
    ```
  - 方括号里的数字 = bid
- 说明: 这是 Text-Only agent 实际看到的内容。序列化过程中 BrowserGym 的过滤策略决定了哪些节点可见。

#### 框 L3-B: "SoM Overlay Generation"
- 文字:
  - 函数: `render_som_overlay()` (我们的 bridge 代码)
  - 输入: screenshot (numpy array) + `extra_element_properties` dict
  - 处理: 对每个 `clickable=True` 且 `visibility>0.5` 的 bid:
    1. 读取 `bbox: [x, y, w, h]`（来自 DOM 的 `getBoundingClientRect()`）
    2. 用 PIL 在截图上画红色小方块 + 白色 bid 数字
  - 输出: 带标注的截图 PNG
- 说明: 这是 SoM Vision agent 看到的内容。标签的位置和存在性取决于 DOM 元素的状态。

#### 框 L3-C: "bid Mapping System"
- 文字:
  - BrowserGym 维护 bid ↔ DOM element 的映射
  - 分配: 遍历 DOM，给可交互元素写入 `browsergym_set_of_marks="N"` 属性
  - 解析: 当 agent 输出 `click("42")` 时，查找 DOM 中 `[browsergym_set_of_marks="42"]` 的元素
  - 执行: 找到元素后调用 Playwright `.click()` 方法
- 样式: 金色背景，表示 bid 系统的核心

#### 框 L3-D: "BrowserGym 过滤策略 (PSL divergence)"
- 文字:
  - `aria-hidden="true"` → 标记 `hidden=True` 但保留 bid 和 role ⚠️
  - `role="presentation"` → 在 headings/landmarks 上可能被忽略 ⚠️
  - `display:none` → 完全过滤 ✓
  - 正常元素 → 保留 role + name + bid
- 标注: "⚠️ 与真实 screen reader 行为不一致（PSL 实验发现）"
- 样式: 带红色虚线边框的警告框

#### 连线 L3→L4 (观察传递):
- **L3-A 顶部 → L4-A 底部**: 蓝色实线向上箭头，标注 "AXTree text"
- **L3-B 顶部 → L4-B 底部**: 绿色实线向上箭头，标注 "SoM screenshot"
- **L1-C → L4-C**: 红色虚线向上箭头（跨层），标注 "Raw screenshot (跳过 L2-L3)"

---

### Layer 4: Agent Observation & Action
- **背景色**: 浅粉色带
- **含义**: LLM agent 的感知和行动层

#### 框 L4-A: "Text-Only Agent"
- 边框色: 蓝色（与连线颜色一致）
- 文字:
  - **LLM**: Claude Sonnet 3.5 via LiteLLM → AWS Bedrock
  - **观察输入**: Layer 3 序列化的 AXTree 文本
    - 示例: `[42] link 'Home'\n[43] button 'Submit'`
  - **操作输出**: `click("42")`, `fill("43", "text")`, `goto("url")`, `send_msg_to_user("answer")`
  - **操作解析路径**: agent 输出 bid → executor.ts 发送给 bridge → BrowserGym 在 DOM 查找 `[browsergym_set_of_marks="42"]` → Playwright `.click()`
- 说明: 纯文本 agent，完全依赖 AX Tree 的语义信息。对 DOM 语义变化最敏感。

#### 框 L4-B: "SoM Vision Agent"
- 边框色: 绿色
- 文字:
  - **LLM**: Claude Sonnet 3.5 via LiteLLM → AWS Bedrock
  - **观察输入**: Layer 3 生成的 SoM 截图（带红色 bid 数字标签）
    - 不包含 AXTree 文本（vision-only 模式）
  - **操作输出**: `click("42")` — 与 Text-Only 相同的 bid-based 操作
  - **操作解析路径**: 与 Text-Only 完全相同（bid → DOM lookup → Playwright）
- 说明: 虽然观察的是截图，但操作仍然依赖 bid 系统。SoM 标签来自 DOM 状态，所以 DOM 变化会导致标签失效（phantom bid）。

#### 框 L4-C: "CUA Agent"
- 边框色: 红色
- 文字:
  - **LLM**: Claude Sonnet 3.5 via boto3 → AWS Bedrock Converse API (computer_use_20250124 tool)
  - **观察输入**: Layer 1 渲染的原始截图（`page.screenshot()`）
    - 无 bid 标签、无 AXTree、无 BrowserGym 加工
  - **操作输出**: `mouse.click(x, y)`, `keyboard.type("text")`, `key("Enter")`
    - 坐标基于截图像素位置
  - **操作解析路径**: agent 输出坐标 → cua_bridge.py → `page.mouse.click(x/scale, y/scale)` → 直接 Playwright mouse API
- 说明: 完全绕过 Layer 2 和 Layer 3。零 DOM 语义依赖。是"纯视觉"控制条件。

#### 框 L4-D: "executor.ts (Step Loop)"
- 文字:
  - 协调所有 agent 类型的执行循环
  - Text-Only/SoM: executor 调用 LLM → 解析 action → 发送给 bridge → 读取 observation → 循环
  - CUA: executor 启动 bridge → bridge 内部运行自己的 agent loop → executor 等待最终结果
  - 所有类型: executor 负责 wall-clock timeout、reward 评估、trace 记录
- 说明: executor 是 TypeScript 进程，bridge 是 Python 子进程，通过 JSON-line stdin/stdout 通信

---

## 三、send_msg_to_user 操作的交互路径

`send_msg_to_user("answer")` 是 agent 完成任务时发送答案的操作。它的路径：

### Text-Only / SoM Agent:
1. **Agent (L4)** 输出: `send_msg_to_user("Luma")`
2. **executor.ts** 通过 JSON-line 发送 `{"action": "send_msg_to_user(\"Luma\")"}` 给 bridge
3. **bridge (L3)** 调用 `env.step('send_msg_to_user("Luma")')` — BrowserGym 的 action 执行
4. **BrowserGym** 内部: 将消息记录为 agent 的回答，触发 evaluator
5. **Evaluator**: 根据 task 定义的 eval 方式（string_match / program_html / url_match）比较 agent 答案与 ground truth
6. **返回**: `reward` 值（1.0 = 正确，0.0 = 错误）通过 observation 返回给 executor
7. **executor.ts**: 读取 reward，设置 `outcome = reward > 0 ? 'success' : 'failure'`

### CUA Agent:
1. **CUA agent (L4)** 输出文本: `"DONE: Luma"`
2. **cua_bridge.py** 解析 "DONE:" 前缀，提取答案 "Luma"
3. **cua_bridge.py** 调用 `env.step('send_msg_to_user("Luma")')` — 同样走 BrowserGym evaluator
4. **返回**: reward 值，cua_bridge 将结果打包为 JSON summary 发送给 executor

### 关键点:
- `send_msg_to_user` 不操作 DOM，不涉及 bid
- 它的交互对象是 BrowserGym 的 evaluator（Layer 3 内部），不是浏览器
- Evaluator 可能需要检查 DOM 状态（program_html 类型的 eval 会在浏览器中执行 JS 检查）

---

## 四、Variant 注入的作用域连线

### 注入机制（三层，都指向 Layer 1 DOM）

#### 框 INJ-1: "Layer 1 注入: page.evaluate(variant_js)"
- 文字: env.reset() 后一次性执行。直接在当前页面 DOM 上运行 variant JS。
- 连线: **INJ-1 → L1-A**: 红色实线箭头，标注 "直接 DOM 操作"
- 时机: 最早，但不持久——页面导航后失效

#### 框 INJ-2: "Layer 2 注入: page.on('load', re-inject)"
- 文字: 监听 Playwright page 的 load 事件，在 SPA 内导航时重新 evaluate variant JS。
- 连线: **INJ-2 → L1-A**: 红色实线箭头，标注 "导航后重注入"
- 时机: 应对 Magento KnockoutJS 异步重渲染覆盖 patch 的问题
- 局限: 只对当前 page 对象有效；agent 打开新 tab 或 goto() 触发完整页面加载时，旧 page 的 listener 不会触发

#### 框 INJ-3: "Layer 3 注入 (Plan D): context.route('**/*')"
- 文字:
  - Playwright BrowserContext 级别的网络拦截
  - 拦截所有 `resource_type == "document"` 的 HTTP response
  - 在 HTML 的 `</body>` 前注入 `<script>` 标签
  - 注入的脚本包含:
    1. `window.addEventListener("load", ...)` — 等页面完全加载
    2. `setTimeout(500ms)` — 等 Magento RequireJS/KnockoutJS 异步渲染完成
    3. 执行 variant JS（与 INJ-1/INJ-2 相同的代码）
    4. 设置 `data-variant-patched="true"` sentinel 属性
    5. `MutationObserver` — 监控 DOM 变化，如果 `[data-variant-revert]` 标记消失则重新 patch
- 连线: **INJ-3 → L1-A**: 红色粗实线箭头，标注 "网络层 HTML 注入 → DOM 执行"
- 时机: 最晚但最可靠——catches 所有 HTML response，包括 agent 触发的 goto() 导航
- 样式: 深红色背景，表示这是主力机制

#### 关键标注:
- "三层机制执行的是同一套 JS 代码（apply-low.js / apply-medium-low.js / apply-high.js）"
- "区别只在于 WHEN（什么时机）和 HOW（通过什么入口）把 JS 送到 DOM 层执行"
- "Plan D 是 Pilot 4 的主力保障：33/33 goto trace 显示 persistent degradation"

---

### 各 Variant 的具体作用域

#### 框 VAR-LOW: "apply-low.js (13 patches)"
连线目标全部指向 **L1-A (DOM Elements)**，按类型分三组：

**纯语义 patches（~6 个）→ 只影响 L2 AX Tree → 只影响 Text-Only agent**
- 删除所有 `aria-*` 和 `role` 属性 → L1 DOM attr 变化 → L2 AX Tree 节点失去 role/name
- 删除 `<img>` 的 `alt`, `title`, `aria-label` → L2 图片节点失去 accessible name
- 删除 `<html>` 的 `lang` 属性 → L2 根节点失去语言信息
- 删除 `tabindex` 属性 → L2 节点失去 focusable 状态
- 替换 `<h1>`-`<h6>` → styled `<div>` → L2 heading role 消失
- 连线: VAR-LOW → L1-A (红色实线) → L2-A (蓝色虚线，标注"自动派生") → L3-A (蓝色虚线) → L4-A (蓝色虚线)
- 标注: "截图不变 → L4-C (CUA) 不受影响"

**结构 patches（~3 个）→ 影响 L2 + 可能微影响 L1-C 渲染**
- `<nav>`, `<main>`, `<header>`, `<footer>` → `<div>` → L2 landmark role 消失
- `<thead>`, `<th>` → `<div>`, `<td>` → L2 表格语义消失
- 删除 `<label>` 元素 → L2 表单控件失去关联标签
- 连线: VAR-LOW → L1-A → L2-A → L3-A → L4-A (主路径)
- 连线: VAR-LOW → L1-C (虚线，标注"视觉变化极小——保留了 CSS 样式")

**功能性 patches（~4 个）→ 影响 L1 DOM 行为 → 影响所有 agent**
- `<a href>` → `<span onclick>`: 删除 href 属性，用 onclick JS 模拟。旧 DOM 节点被删除 → bid 丢失。
  - 连线: VAR-LOW → L1-A (红色粗线) → L2-A (link role 消失) → L3-A/B (bid 失效) → L4-A/B (phantom bid)
  - 连线: VAR-LOW → L1-A → L1-C (视觉不变但行为变了) → L4-C (CUA 点击后导航失败)
- Closed Shadow DOM wrapping: 把交互元素包进 closed shadow root → L2 AX Tree 看不到 → L3 无法分配 bid
- `onfocus="this.blur()"`: 键盘焦点陷阱 → 影响 BrowserGym 的 focus-based 操作
- 删除 keyboard event handlers → 影响 BrowserGym 的键盘操作
- 标注: "⚠️ 这组 patch 是 cross-layer confound 的来源。CUA 在 low variant 的 100% 失败都来自这里。"

#### 框 VAR-MEDLOW: "apply-medium-low.js (pseudo-compliance)"
连线目标: **L1-A (DOM Elements)**

- 空 `<button>` → `<div>` (保留 role 属性): L1 元素替换 → L2 节点 role 保留但元素类型变了
- `role="button"` 元素: clone-replace 去除 JS 事件监听器 → L1 行为变化（ARIA 说是 button，但点击无反应）
- 删除无 placeholder 的 `<input>` 的 `<label>` → L2 表单控件失去标签
- 删除这些 input 的 `aria-label` / `aria-labelledby` → L2 节点失去 accessible name
- 连线: VAR-MEDLOW → L1-A → L2-A → L3-A → L4-A
- 标注: "设计意图: 模拟真实世界的'看起来 accessible 但实际不是'模式（ARIA present, handlers missing）"
- 标注: "Pilot 4 结果: medium-low 100% 成功（Text-Only）— 说明 BrowserGym agent 不依赖键盘操作"

#### 框 VAR-BASE: "base (no patches)"
- 文字: 不注入任何 JS。原始 WebArena DOM 不做修改。
- 连线: 无注入连线
- 标注: "控制条件。WebAIM Million 2025: 94.8% 的网站本身就不完全 accessible"

#### 框 VAR-HIGH: "apply-high.js (enhance)"
连线目标: **L1-A (DOM Elements)**

- 给无名交互元素添加 `aria-label` → L2 节点获得 accessible name
- 插入 skip-navigation `<a>` 链接（在 body 末尾，避免 bid 偏移）→ L2 新增 link 节点
- 添加 landmark roles (`banner`, `navigation`, `main`, `contentinfo`) → L2 新增 landmark 节点
- 给无标签表单控件添加 `<label>` 或 `aria-label` → L2 表单节点获得标签
- 给无 alt 的 `<img>` 添加 alt 文字 → L2 图片节点获得 accessible name
- 添加 `lang="en"` → L2 根节点获得语言信息
- 添加 `scope="col"/"row"` 到 `<th>` → L2 表格语义增强
- 添加 `aria-current="page"` → L2 导航链接标记当前页
- 连线: VAR-HIGH → L1-A (绿色实线) → L2-A (绿色虚线) → L3-A → L4-A
- 标注: "Pilot 4 结果: high 76.7%（Text-Only）— 低于 base 86.7%，可能因为额外 ARIA 增加了 token 量"

---

## 五、bid 完整生命周期（连线序列）

用金色线条标注以下循环路径：

```
1. BrowserGym (L3-C) 遍历 DOM，分配 bid 数字
       ↓ 金色虚线向下
2. 写入 DOM 属性 (L1-B): element.setAttribute("browsergym_set_of_marks", "42")
       ↓ 自动派生（向上）
3. Chrome Blink (L2-A) 读取 DOM → 构建 AX Tree，bid 作为节点 property
       ↓ CDP 拉取（向上）
4. BrowserGym (L3-A) 序列化: "[42] link 'Home'"
   BrowserGym (L3-B) 画 SoM: 截图上红色 "42" 标签
       ↓ 传递给 agent（向上）
5. Agent (L4-A/B) 看到 bid 42，决定操作: click("42")
       ↓ 操作返回（向下）
6. executor.ts (L4-D) → bridge (L3) → BrowserGym 查 DOM: [browsergym_set_of_marks="42"]
       ↓ 解析到 DOM 元素（向下）
7. Playwright (L1) 执行 .click() 在该 DOM 元素上
```

标注: "bid 是 BrowserGym 发明的跨层桥梁，连接 agent 的感知和行动"

---

## 六、Phantom bid 机制（右侧专题区）

#### 框 PHANTOM-1: "正常 bid 循环"
- 文字: Step N: BrowserGym 给 `<a href="/forum">` 分配 bid="229"，写入 DOM
- 样式: 绿色背景

#### 框 PHANTOM-2: "Variant patch 打断循环"
- 文字: apply-low.js patch 11: `<a>` → `<span onclick>`. 旧 DOM 节点（带 bid="229"）被删除。新 `<span>` 没有 bid 属性。
- 样式: 红色背景
- 连线: PHANTOM-1 → PHANTOM-2: 红色箭头，标注 "DOM 节点替换"

#### 框 PHANTOM-3: "SoM 标签残留"
- 文字: SoM overlay 在 Step N 的截图上画了红色 "229" 标签。截图是位图——不会因为 DOM 变化而更新。标签在 Step N+1 的截图上仍然可见（因为视觉位置没变）。
- 样式: 橙色背景
- 连线: PHANTOM-2 → PHANTOM-3: 箭头，标注 "截图不感知 DOM 变化"

#### 框 PHANTOM-4: "Agent 陷入循环"
- 文字:
  - Step N+1: Agent 看到截图上的 "229"，输出 click("229")
  - BrowserGym 查 DOM: `[browsergym_set_of_marks="229"]` → NOT FOUND
  - 返回: "Could not find element with bid 229"
  - Agent 重试 click("229") → 同样失败
  - 循环 20+ 次 → 最终 timeout
- 样式: 深红色背景
- 连线: PHANTOM-3 → PHANTOM-4: 箭头，标注 "overlay false affordance"

#### 框 PHANTOM-MODES: "两种 Phantom bid 模式 (Pilot 4)"
- Mode A (Magento): 元素仍在 DOM 但 `browsergym_set_of_marks="0"`（标记为不可交互）
  - 错误: "element is not visible"
  - 原因: 元素被 de-semanticize 但未被替换
- Mode B (Postmill): 元素被完全替换，旧 DOM 节点删除
  - 错误: "Could not find element with bid 229"
  - 原因: `<a>` → `<span>` 替换删除了旧节点

#### 框 PHANTOM-CUA: "CUA 免疫"
- 文字: CUA 不使用 bid。它输出 mouse.click(x, y) 坐标，Playwright 直接在页面像素位置点击。不查 DOM 属性，不查 bid。所以 phantom bid 对 CUA 无效。
- 但: 如果 `<a>` → `<span>` 删除了 href，CUA 点击后导航不会发生（功能性破坏，不是 phantom bid）。
- 样式: 绿色边框

---

## 七、Variant 传播路径汇总表

在图的底部画一个表格：

| Patch 类型 | 操作层 | 影响传播路径 | Text-Only | SoM | CUA |
|---|---|---|---|---|---|
| 纯语义 (rm aria, role, alt) | L1 DOM attrs | L1→L2→L3→L4-A | ✓ 受影响 | ✗ 不受影响 | ✗ 不受影响 |
| 结构 (h1→div, nav→div) | L1 DOM structure | L1→L2→L3→L4-A, L1→L1-C 微变 | ✓ 受影响 | ⚠ 极小影响 | ⚠ 极小影响 |
| 功能 (a→span rm href) | L1 DOM behavior | L1→L2 (role消失), L1→L1-C (行为变), L3 bid 断裂 | ✓ 受影响 | ✓ phantom bid | ✓ 导航失败 |
| 伪合规 (ARIA present, no handler) | L1 DOM attrs+JS | L1→L2 (role保留), L1 行为变 | ⚠ 部分 | ⚠ 部分 | ✗ 不受影响 |
| 增强 (add aria-label, landmarks) | L1 DOM attrs | L1→L2→L3→L4-A (信息增加) | ✓ 信息增加 | ✗ 不受影响 | ✗ 不受影响 |

---

## 八、连线颜色编码

| 颜色 | 含义 |
|---|---|
| 蓝色实线 | Text-Only Agent 的观察路径 |
| 绿色实线 | SoM Vision Agent 的观察路径 |
| 红色虚线 | CUA Agent 的路径（跨层，跳过 L2-L3） |
| 金色虚线 | bid 生命周期（L3→L1→L2→L3→L4→L3→L1） |
| 深红色实线 | Variant 注入路径（三层机制 → L1 DOM） |
| 灰色实线 | 层间自动派生关系（L0→L1, L1→L2） |
| 蓝色/绿色虚线 | 操作返回路径（L4→L3→L1, agent action → DOM execution） |

---

## 九、关键标注（散布在图中的文字说明）

1. **Layer 1 旁**: "所有 variant patch 的唯一操作目标。三层注入机制只是解决 timing 问题。"
2. **Layer 2 旁**: "AX Tree 是 DERIVED（派生的）。我们不直接操作它，但 DOM 变化自动反映到这里。"
3. **Layer 3 旁**: "BrowserGym 是 agent 和浏览器之间的中间层。我们不修改它（除了 SRF 提案）。"
4. **bid 循环旁**: "bid 诞生于 L3，写回 L1，经 L2 回到 L3，传给 L4，再经 L3 回到 L1 执行。"
5. **CUA 跨层线旁**: "CUA 完全跳过 L2-L3。这是 causal decomposition 的基础：CUA 的 30pp 下降 = 纯功能性破坏。"
6. **Phantom bid 区旁**: "Phantom bid = overlay false affordance。SoM 标签是位图残留，不感知 DOM 变化。"
7. **底部总结**: "我们只在 Layer 1 操作，但影响通过不同路径传播到不同 agent。这种差异化传播是 causal decomposition 的物理基础。"
