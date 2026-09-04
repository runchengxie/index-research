# index-research 依赖与 CI 维护设计

## 目标

让前端依赖通过当前安全审计，并让 Pages 发布前执行项目已有的 Python、前端和敏感信息检查。

## 方案

升级 ECharts 与 Vite 到 npm audit 提供的安全版本，必要时同步 React 插件。保留现有构建方式和静态数据复制逻辑。Pages workflow 增加 Python 测试、语法检查、前端测试、构建与敏感路径扫描，只有这些步骤通过后才上传 Pages artifact。

## 边界

本次不改研究计算口径，不重写数据生成脚本，不升级 Python 数据依赖。大模块拆分放到独立变更中。

## 验收

- `npm audit --audit-level high` 无高危漏洞，若仍有中危漏洞需记录原因。
- `npm test`、`npm run build` 和 Python 测试通过。
- Pages workflow 包含并执行上述门禁。
