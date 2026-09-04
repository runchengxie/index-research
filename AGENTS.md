# index-research 维护须知

本项目研究指数、ETF、主题和长期风险指标。它不等同于交易执行系统，也不把历史价格回报自动解释成未来收益。

## 数据管理

* 原始 Tushare 数据由现有 `market-data-platform` 统一维护，不复制进本仓库。
* 项目完整派生数据归档在 `~/data/index-research/outputs/`。其中较大的 Parquet 不提交 Git。
* 仓库 `outputs/` 只保留可公开分享、规模可控的 CSV 快照，供代码复现和 GitHub Pages 使用。
* 页面构建时将公开快照复制到 `site/outputs/`，页面不得访问本机路径、Token、代理地址或其他内部地址。
* 本地优先：先用本机已有原始数据和缓存生成增量结果，检查结果后再提交代码和小型公开快照。
* GitHub Actions 是 fallback，不是每日全量重建器。工作流应只补缺失日期或新数据，并复用 Actions cache；只有研究口径变化时才允许显式全量重算。
* 每个结果必须记录数据窗口、价格回报/总回报口径、流动性门槛和幸存者偏差等限制。
* 微盘股研究的 Wind 原始序列、Tushare 重建序列和 ETF 代理必须分开保存，并在页面上显示来源和频率。
* `outputs/microcap/` 是微盘股页面的公开快照目录。页面不得把公开资料参考值标记为 Tushare 原始值或 Wind 实时值。
* 连续净值使用 `build_microcap_reconstruction.py` 生成。每日先按总市值选取上海、深圳市场最小 400 只股票，再等权计算下一交易日收益。输出的 `reconstructed_daily_nav.csv`、`reconstructed_underwater_periods.csv` 和 `reconstructed_summary.json` 必须保持独立命名。
* 页面应同时说明两条序列的覆盖范围和口径差异。公开资料参考序列用于长历史展示，Tushare 规则重建序列用于 2015 年以来的连续路径、日频最大回撤和水下时间分析。

## Git 与多 agent 流程

* `main` 只通过 PR 接收改动，不直接在 `main` 上开发。
* 每个独立任务从最新 `main` 创建独立 worktree 和分支，建议使用 `feat/<topic>`、`fix/<topic>` 或 `data/<topic>`。
* 多个 agent 不得共享 worktree、分支或临时输出目录。若任务会修改同一核心文件，必须串行合并或先拆分边界。
* worktree 内必须完成页面测试、脚本语法检查、数据泄露扫描和必要的本地页面验证，再 push 分支并开 PR。
* PR 合并后，确认远端 PR 已合并且 worktree 无未提交改动，再删除远端分支、本地分支和 worktree。
* 大型数据下载、分析口径调整、页面改版和部署配置应尽量拆成独立 PR，减少 agent 间竞争。

## 验证门禁

```bash
python -m pytest -q tests
python -m py_compile analyze.py fetch_linked_indices.py pair_and_rank.py
git diff --check
rg -n '/home/|/Users/|TUSHARE_TOKEN=|fast\.xiaodefa\.cn' site .github README.md AGENTS.md
```

页面部署使用 `.github/workflows/pages.yml`。它只组装 `site/` 和公开 `outputs/` 快照，并通过 GitHub Pages 发布静态快照。
