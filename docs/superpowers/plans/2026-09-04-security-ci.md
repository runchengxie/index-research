# index-research Security and CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 升级前端安全依赖并在发布前执行自动化质量门禁。

**Architecture:** 依赖变更集中在 `web/package.json` 和 lockfile。CI 复用仓库现有脚本，在部署前完成 Python、前端、构建和敏感信息检查。

**Tech Stack:** npm、Vite、ECharts、Node test runner、pytest、GitHub Actions。

**Spec:** `docs/superpowers/specs/2026-09-04-security-ci-design.md`

## Global Constraints

- 不修改研究数据口径。
- 不提交原始数据、令牌或构建缓存。
- 发布 job 只能消费已通过 build job 的 artifact。

---

### Task 1: 升级前端依赖

**Files:** `web/package.json`、`web/package-lock.json`

- [ ] 写入依赖升级并安装 lockfile。
- [ ] 运行 `npm test`、`npm run build` 和 `npm audit`。
- [ ] 发现破坏性兼容问题时回退该版本组合并记录原因。

### Task 2: 加强 Pages CI

**Files:** `.github/workflows/pages.yml`

- [ ] 在构建前运行 Python 测试、语法检查和敏感信息扫描。
- [ ] 运行前端测试和构建。
- [ ] 通过后上传并部署 Pages artifact。

### Task 3: 交付

- [ ] 运行全部门禁和 `git diff --check`。
- [ ] 创建 PR，等待远程检查通过后合并。
- [ ] 清理分支和 worktree。
