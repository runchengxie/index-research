const DATA = {
  price: 'outputs/linked_indices/ten_year_price_returns.csv',
  etf: 'outputs/linked_indices/paired_index_etf_representatives.csv',
  api: 'outputs/index_api_probe.csv',
};

function csv(text) {
  const rows=[]; let row=[], cell='', quoted=false;
  for(let i=0;i<text.length;i++){const c=text[i],n=text[i+1]; if(c==='"'&&quoted&&n==='"'){cell+='"';i++;} else if(c==='"'){quoted=!quoted;} else if(c===','&&!quoted){row.push(cell);cell='';} else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&n==='\n')i++;row.push(cell);if(row.some(Boolean))rows.push(row);row=[];cell='';} else cell+=c;} if(cell||row.length){row.push(cell);rows.push(row);} const head=rows.shift(); return rows.map(r=>Object.fromEntries(head.map((h,i)=>[h,r[i]??''])));
}
const pct=x=>(Number(x)*100).toFixed(1)+'%';
const money=x=>Number(x).toLocaleString('zh-CN');
function bars(el, rows, label, value, cls='') { const max=Math.max(...rows.map(r=>Number(r[value]))); el.innerHTML=rows.map(r=>`<div class="bar-row"><div class="bar-label" title="${r[label]}">${r[label]}</div><div class="bar-track"><div class="bar-fill ${cls}" style="width:${Math.max(2,Number(r[value])/max*100)}%"></div></div><div class="bar-value">${pct(r[value])}</div></div>`).join(''); }
function dualBars(el, rows) { const max=Math.max(...rows.map(r=>Math.max(Number(r.etf_cagr),Number(r.index_cagr)))); el.innerHTML=rows.map(r=>`<div class="bar-row"><div class="bar-label" title="${r.name}">${r.name}</div><div class="dual-wrap"><div class="dual-fill" style="width:${Math.max(2,Number(r.etf_cagr)/max*100)}%"></div><div class="dual-index" style="width:${Math.max(2,Number(r.index_cagr)/max*100)}%"></div></div><div class="bar-value">${pct(r.etf_cagr)}</div></div>`).join(''); }
function load(path){return fetch(path).then(r=>r.text()).then(csv)}
Promise.all([load(DATA.price),load(DATA.etf),load(DATA.api)]).then(([price,etf,api])=>{
  price.sort((a,b)=>Number(b.cagr)-Number(a.cagr)); etf.sort((a,b)=>Number(b.etf_cagr)-Number(a.etf_cagr));
  const top=price.slice(0,10); bars(document.querySelector('#price-chart'),top,'indx_name','cagr');
  const e=etf.slice(0,10); dualBars(document.querySelector('#etf-chart'),e);
  document.querySelector('#price-leader').textContent=top[0].indx_name.replace('中证','').replace('指数','');
  document.querySelector('#price-leader-value').textContent=`十年年化价格回报 ${pct(top[0].cagr)}`;
  document.querySelector('#mapped-count').textContent=price.length;
  document.querySelector('#etf-count').textContent=etf.length;
  document.querySelector('#api-count').textContent=api.filter(r=>r.status==='ok').length;
  document.querySelector('#api-list').innerHTML=api.map(r=>`<div class="api-row"><span>${r.label}</span><span>${r.min_date?r.min_date.slice(0,4)+' — '+r.max_date.slice(0,4):'映射记录'}</span><span>${r.rows?money(r.rows):r.rows||'560'}</span></div>`).join('');
}).catch(err=>{document.querySelector('#price-chart').innerHTML='<p class="caption">数据加载失败，请从 GitHub Pages 正常入口打开。</p>'; console.error(err)});
const savedTheme=localStorage.getItem('index-research-theme'); if(savedTheme) document.documentElement.dataset.theme=savedTheme;
document.querySelector('#theme-toggle').addEventListener('click',()=>{const dark=document.documentElement.dataset.theme==='dark'; document.documentElement.dataset.theme=dark?'light':'dark'; localStorage.setItem('index-research-theme',dark?'light':'dark');});
