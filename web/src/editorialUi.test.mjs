import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const app=readFileSync(new URL("./App.tsx",import.meta.url),"utf8");
const chart=readFileSync(new URL("./components/ResearchChart.tsx",import.meta.url),"utf8");
const styles=readFileSync(new URL("./styles.css",import.meta.url),"utf8");
test("看板保留两个研究主题并整理微盘研究内容",()=>{assert.match(app,/微盘股研究/);assert.match(app,/指数长期回报/);assert.match(app,/收益来源/);assert.match(app,/复制难度/);assert.match(app,/research-note/)});
test("图表提供轴向 tooltip、缩放和自适应重绘",()=>{assert.match(chart,/tooltip/);assert.match(chart,/dataZoom/);assert.match(chart,/resize/);assert.match(styles,/--paper:/);assert.match(styles,/site-nav/)});
test("两个 Tab 都包含完整研究数据区域",()=>{assert.match(app,/rolling_cagr/);assert.match(app,/rolling_drawdown/);assert.match(app,/paired_index_etf_representatives/);assert.match(app,/ETF 代表明细/)});
test("微盘页面明确说明规则复现口径",()=>{assert.match(app,/规则重建研究/);assert.match(app,/不是 Wind 官方指数页面/);assert.match(app,/2026 年至今/)});
