# 微盘股研究双标签页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `index-research` 中新增默认微盘股研究页和指数长期回报页标签切换，并用可验证的公开快照展示微盘股长期收益与风险指标。

**Architecture:** 保持当前静态 HTML、原生 JavaScript 和 CSV 数据模式。新增 `microcap` 数据目录及生成脚本，页面通过 hash 路由在两个主题面板之间切换。微盘数据先采用带来源说明的公开资料快照，Tushare 重建接口作为后续增量数据源，不把两种口径合并。

**Tech Stack:** Python、DuckDB、pandas、静态 HTML、原生 JavaScript、CSS、GitHub Pages。

**Spec:** `docs/superpowers/specs/2026-09-04-microcap-dashboard-design.md`

## Global Constraints

- 默认入口必须是 `#microcap`，旧指数研究通过 `#indices` 保留。
- 微盘股 Wind 原始序列、Tushare 重建序列和 ETF 代理必须在数据文件及页面上明确区分。
- 月频最大回撤不得标注为日频最大回撤。
- 页面不得访问本机路径、Token、代理地址或内部地址。
- GitHub Actions 只补缺失日期并复用缓存，不在每日任务中全量重建多年历史。
- 页面文案使用自然中文、中文标点，保留必要的英文代码和指标缩写。

### Task 1: 建立微盘股静态数据模型

**Files:**
- Create: `outputs/microcap/summary.json`
- Create: `outputs/microcap/annual_returns.csv`
- Create: `outputs/microcap/rolling_cagr.csv`
- Create: `outputs/microcap/rolling_drawdown.csv`
- Create: `outputs/microcap/nav.csv`
- Create: `outputs/microcap/source_notes.json`
- Create: `tests/test_microcap_outputs.py`

**Interfaces:**
- `summary.json` 提供 `as_of`、`source_label`、`coverage_start`、`coverage_end`、`metrics` 和 `caveats`。
- `annual_returns.csv` 至少包含 `year,return,nav`。
- `rolling_cagr.csv` 至少包含 `as_of,window_years,cagr`。
- `rolling_drawdown.csv` 至少包含 `as_of,window_years,max_drawdown,frequency`。
- `nav.csv` 至少包含 `date,nav,source`。

- [ ] **Step 1: Write the failing schema tests**

```python
def test_microcap_files_have_stable_columns():
    assert read_csv("outputs/microcap/annual_returns.csv").columns.tolist() == ["year", "return", "nav"]
    assert read_csv("outputs/microcap/rolling_cagr.csv").columns.tolist() == ["as_of", "window_years", "cagr"]
    assert read_csv("outputs/microcap/rolling_drawdown.csv").columns.tolist() == [
        "as_of", "window_years", "max_drawdown", "frequency"
    ]
```

- [ ] **Step 2: Run the focused test and confirm the files are absent**

Run: `python -m pytest -q tests/test_microcap_outputs.py`

Expected: FAIL because the microcap output files do not exist yet.

- [ ] **Step 3: Add the compact public snapshot**

将对话中已经整理的 2000–2025 年年度收益、2025 年末累计净值、滚动 CAGR 和月频回撤写成 UTF-8 CSV/JSON。`source_notes.json` 记录 Wind、券商资料和对话整理文档的链接，并写明这些数字不是 Tushare 直接返回的 Wind 指数原始序列。

- [ ] **Step 4: Run the focused test and validate values**

Run: `python -m pytest -q tests/test_microcap_outputs.py`

Expected: PASS. Assert the first year is 2000, the last year is 2025, all five rolling windows are present, and every drawdown row has `frequency` equal to `monthly` or `daily_reference`.

- [ ] **Step 5: Commit the data contract**

```bash
git add outputs/microcap tests/test_microcap_outputs.py
git commit -m "建立微盘股研究公开数据模型"
```

### Task 2: 增加微盘股指标生成脚本

**Files:**
- Create: `build_microcap_snapshot.py`
- Modify: `tests/test_microcap_outputs.py`
- Modify: `README.md`

**Interfaces:**
- `build_microcap_snapshot.py --source <path> --out-dir outputs/microcap` 读取公开日频或月频序列，写出五类产物。
- `calculate_annual_returns(nav: DataFrame) -> DataFrame`。
- `calculate_rolling_cagr(nav: DataFrame, windows: tuple[int, ...]) -> DataFrame`。
- `calculate_rolling_drawdown(nav: DataFrame, windows: tuple[int, ...], frequency: str) -> DataFrame`。

- [ ] **Step 1: Add calculation tests for a small deterministic series**

测试序列使用 2020–2025 六个年末净值 `[1, 2, 1, 3, 2, 4]`，验证年度收益、2 年 CAGR 和峰谷回撤。测试同时验证缺失年份会报出明确错误。

- [ ] **Step 2: Run tests to confirm the calculation functions fail**

Run: `python -m pytest -q tests/test_microcap_outputs.py`

Expected: FAIL because `build_microcap_snapshot.py` and its calculation functions are not defined.

- [ ] **Step 3: Implement pure calculation functions**

统一日期为 `YYYY-MM-DD`，窗口使用完整年度末值，回撤使用滚动窗口内的累计净值峰值。函数只负责计算，不读取环境变量，也不写入仓库之外的路径。

- [ ] **Step 4: Add CLI input validation and source notes**

输入序列缺少 `date` 或 `nav` 时退出并说明缺失列。输出的 `source_notes.json` 包含来源 URL、数据频率、覆盖区间、回报口径和已知限制。

- [ ] **Step 5: Run focused and full Python tests**

Run: `python -m pytest -q tests/test_microcap_outputs.py tests`

Expected: PASS.

- [ ] **Step 6: Commit the generator**

```bash
git add build_microcap_snapshot.py tests/test_microcap_outputs.py README.md
git commit -m "增加微盘股收益与风险指标生成器"
```

### Task 3: 将现有页面拆成双标签页

**Files:**
- Modify: `site/index.html`
- Modify: `site/app.js`
- Modify: `site/styles.css`
- Modify: `tests/test_site_assets.py`

**Interfaces:**
- `renderMicrocapDashboard(data)` 渲染微盘股面板。
- `renderIndexDashboard(data)` 渲染当前指数研究面板。
- `setActiveTab(tab)` 更新 hash、导航状态和面板可见性。
- `loadMicrocapData()` 读取 `outputs/microcap/*.json|csv`。

- [ ] **Step 1: Add static page contract tests**

```python
def test_site_has_microcap_default_and_indices_tab():
    html = Path("site/index.html").read_text()
    assert 'href="#microcap"' in html
    assert 'href="#indices"' in html
    assert 'id="microcap-panel"' in html
    assert 'id="indices-panel"' in html
```

- [ ] **Step 2: Run the site tests and confirm the contract fails**

Run: `python -m pytest -q tests/test_site_assets.py`

Expected: FAIL because the current site has one panel and no microcap tab.

- [ ] **Step 3: Add the two-panel HTML shell**

默认 hash 为空时显示微盘股面板。指数页原有 DOM 内容整体迁移到 `indices-panel`，保持现有数据文件路径和文案口径。

- [ ] **Step 4: Implement hash navigation and data loading**

监听 `hashchange`，只接受 `microcap` 和 `indices`，其他值回退到 `microcap`。微盘数据加载失败时只在微盘面板显示来源和错误提示，不影响指数页。

- [ ] **Step 5: Add microcap charts and tables**

使用现有原生 SVG/CSS 图表风格，增加累计净值折线、年度收益柱、滚动 CAGR 多线图、滚动回撤图和指标明细表。所有图表都显示数据日期或频率说明。

- [ ] **Step 6: Run site tests and build locally**

Run: `python -m pytest -q tests/test_site_assets.py tests`; `python -m py_compile build_microcap_snapshot.py`; `git diff --check`。

Expected: PASS.

- [ ] **Step 7: Commit the dashboard shell**

```bash
git add site tests/test_site_assets.py
git commit -m "增加微盘股研究与指数研究双标签页"
```

### Task 4: 更新部署与项目说明

**Files:**
- Modify: `.github/workflows/pages.yml`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/wind-microcap-index-chat.md`

**Interfaces:**
- Pages workflow 将 `outputs/microcap` 复制到 `site/outputs/microcap`。
- 每日任务默认只补充新增快照，不覆盖完整历史文件。

- [ ] **Step 1: Add workflow path checks**

测试工作流文本包含 `outputs/microcap` 和 `site/outputs/microcap`，并且不包含 Token、代理地址或本机绝对路径。

- [ ] **Step 2: Update the documentation**

README 增加双标签页入口、微盘数据口径、Tushare 能力边界和专题文档链接。`AGENTS.md` 增加微盘数据产物和三类口径的管理规则。

- [ ] **Step 3: Run the full verification gate**

Run:

```bash
python -m pytest -q tests
python -m py_compile analyze.py build_microcap_snapshot.py fetch_linked_indices.py pair_and_rank.py
git diff --check
rg -n '/home/|/Users/|TUSHARE_TOKEN=|fast\.xiaodefa\.cn' site .github README.md AGENTS.md docs
```

Expected: tests, syntax and format checks pass. The only allowed path matches are the pre-existing verification command in `AGENTS.md`.

- [ ] **Step 4: Commit deployment documentation**

```bash
git add .github/workflows/pages.yml AGENTS.md README.md docs/wind-microcap-index-chat.md
git commit -m "完善微盘股看板数据更新说明"
```

### Task 5: 发布、检查和合并

**Files:**
- No additional files. Validate the complete branch.

- [ ] **Step 1: Push the branch and open a PR**

```bash
git push -u origin feat/microcap-dashboard
gh pr create --base main --head feat/microcap-dashboard --title "增加微盘股研究双标签页看板" --body-file /tmp/microcap-pr.md
```

- [ ] **Step 2: Verify the PR checks**

确认 Python 测试、页面静态检查和部署构建均通过。若检查失败，先在 worktree 修复并重新验证。

- [ ] **Step 3: Verify the built site locally**

使用 `python -m http.server` 在仓库根目录启动静态服务，分别打开 `#microcap` 和 `#indices`，确认刷新后 hash 和数据加载均正确。

- [ ] **Step 4: Merge and verify the published pages**

合并 PR 后检查 GitHub Pages 的微盘股默认页、指数研究标签、`site/outputs/microcap/summary.json` 和所有图表资源 HTTP 状态。

- [ ] **Step 5: Delete the branch and worktree**

确认远端 PR 已合并、worktree 无未提交改动后，删除远端分支、本地分支和 `.worktrees/microcap-dashboard`。
