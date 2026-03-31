# BrowserGym API Notes & Integration Plan

## API Surface

### Environment Lifecycle

BrowserGym follows the Gymnasium (formerly OpenAI Gym) interface:

```python
import gymnasium as gym
import browsergym.webarena  # registers webarena tasks

env = gym.make("browsergym/webarena.310")
obs, info = env.reset()

while True:
    action = agent.decide(obs)
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        break

env.close()
```

- `env.reset()` → `(obs: dict, info: dict)` — initializes browser, navigates to start URL
- `env.step(action: str)` → `(obs, reward, terminated, truncated, info)` — executes action, returns new observation
- `env.close()` — releases browser resources

### Observation Space

The `obs` dict contains multimodal page state:

| Key | Type | Description |
|-----|------|-------------|
| `goal` | `str` | Natural language task instruction |
| `open_pages_urls` | `list[str]` | URLs of all open tabs |
| `active_page_index` | `int` | Index of the currently active tab |
| `axtree_txt` | `str` | Serialized Accessibility Tree with BrowserGym IDs (bid) |
| `dom_txt` | `str` | Pruned DOM HTML with bid annotations |
| `screenshot` | `np.ndarray` | Viewport screenshot as RGB numpy array (H×W×3) |
| `last_action_error` | `str` | Error message from previous action (empty if success) |
| `focused_element_bid` | `str` | bid of currently focused element |

The AXTree text format annotates each node with a unique `bid` identifier:
```
[1] RootWebArea 'Page Title'
  [2] navigation 'Main Nav'
    [3] link 'Home'
    [4] link 'About'
  [5] main ''
    [6] heading 'Welcome'
    [7] textbox 'Search' focused
```

### Action Space

Actions are Python code strings executed in a sandboxed environment. Primitive high-level actions:

| Action | Format | Description |
|--------|--------|-------------|
| Click | `click("bid")` | Click element by BrowserGym ID |
| Fill | `fill("bid", "text")` | Clear and type into input |
| Type | `type("bid", "text")` | Type text without clearing |
| Hover | `hover("bid")` | Mouse hover |
| Press | `press("bid", "key_combo")` | Keyboard shortcut |
| Scroll | `scroll("bid", "direction")` | Scroll element (up/down) |
| Tab focus | `focus("bid")` | Focus element |
| Go to URL | `goto("url")` | Navigate to URL |
| Go back | `go_back()` | Browser back |
| Go forward | `go_forward()` | Browser forward |
| New tab | `new_tab()` | Open new tab |
| Close tab | `tab_close()` | Close current tab |
| Switch tab | `tab_focus(index)` | Switch to tab by index |
| Send message | `send_msg_to_user("text")` | Send message to chat (task completion) |
| No-op | `noop()` | Do nothing |

Actions can also be raw Playwright Python code in advanced mode.

### Screenshot Format

- Returned as `np.ndarray` (RGB, shape H×W×3)
- Can be encoded to base64 PNG for LLM vision APIs
- Not a file path — must be serialized if needed for storage

## Integration Plan

### Architecture Decision: TypeScript Wrapper over Python BrowserGym

Since our platform is TypeScript (modules 1–5) but BrowserGym is Python, we use a **subprocess bridge**:

1. **Python agent script** (`src/runner/browsergym_bridge.py`): Thin wrapper that:
   - Creates BrowserGym env with task config
   - Exposes a JSON-line protocol over stdin/stdout
   - Sends observations as JSON, receives actions as JSON
   - Reports step results, token usage, and task outcome

2. **TypeScript executor** (`src/runner/agents/executor.ts`): Manages the Python subprocess:
   - Spawns `python browsergym_bridge.py` with task config
   - Reads observation JSON from stdout
   - Sends observation to LLM via `callLlm()`
   - Parses LLM response into BrowserGym action string
   - Writes action JSON to stdin
   - Logs `ActionTraceStep` per step
   - Enforces step limit and timeout

### Variant DOM Patch Injection

- Inject **after** `env.reset()` but **before** the first agent step
- BrowserGym exposes the Playwright `page` object via `env.page`
- Execute variant patches via `env.page.evaluate(patchScript)`
- Re-capture observation after patching (call a no-op step or re-read obs)

### Token Usage Extraction

- LiteLLM proxy returns `usage: { prompt_tokens, completion_tokens }` in the response
- Track per-step via `LlmResponse.tokensUsed`
- Accumulate in `ActionTrace.totalTokens`

### Text-Only vs Vision Observation

- **Text-Only**: Use `obs["axtree_txt"]` as the observation string sent to LLM
- **Vision**: Encode `obs["screenshot"]` to base64 PNG, send as image content block alongside AXTree text

### WebArena Task IDs

- Tasks registered as `browsergym/webarena.{id}` (e.g., `browsergym/webarena.310`)
- Each task has a goal, start URL, and evaluation function
- 4 apps: Reddit, GitLab, CMS (map), E-commerce (shopping)

## Dependencies

- Python: `browsergym-webarena`, `playwright`, `numpy`
- TypeScript: `child_process` (Node built-in) for subprocess bridge
- LiteLLM proxy running at `localhost:4000`

## Open Questions

- [ ] Exact BrowserGym version compatibility with our Playwright version
- [ ] Whether `env.page` is directly accessible or needs a custom wrapper
- [ ] Reset mechanism reliability per WebArena app (see Task 12.2)
- [ ] Token counting accuracy when using streaming responses
