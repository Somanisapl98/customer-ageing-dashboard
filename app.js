const $ = id => document.getElementById(id);
const state = { all: [], filtered: [], page: 1, pageSize: 6 };
const money = value => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(Number(value||0));
const number = value => new Intl.NumberFormat('en-IN',{maximumFractionDigits:0}).format(Number(value||0));
const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

function amountOf(c){ return Number(c.Outstanding ?? c.Ageing_Outstanding ?? c.OutstandingAmount ?? 0); }
function daysOf(c){ return Number(c.AgeingDays ?? c.Oldest_Days ?? c.Days ?? 0); }
function billsOf(c){ return Number(c.OpenBills ?? c.Open_Bills ?? c.Bills ?? 0); }
function codeOf(c){ return c.Code ?? c.party_code ?? c.CustomerCode ?? ''; }
function customerOf(c){ return c.Customer ?? c.CustomerName ?? c.Name ?? 'Unknown'; }
function salesmanOf(c){ return c.Salesman ?? c.salesman_name ?? ''; }
function branchOf(c){ return c.Branch ?? ''; }
function bandOf(c){ const d=daysOf(c); return d<=30?'0-30':d<=60?'31-60':d<=90?'61-90':'90+'; }
function priorityOf(c){ const d=daysOf(c); const a=amountOf(c); if(d>120||a>=500000)return ['Critical','critical']; if(d>60||a>=200000)return ['High','high']; if(d>30)return ['Watch','watch']; return ['Normal','normal']; }

async function loadData(){
  setLoading(true);
  try{
    const response = await fetch(`data/dashboard-data.json?v=${Date.now()}`, {cache:'no-store'});
    if(!response.ok) throw new Error('Latest dashboard data could not be loaded.');
    const payload = await response.json();
    state.all = Array.isArray(payload.customers) ? payload.customers : [];
    const stamp = payload.updatedAt ? new Date(payload.updatedAt) : null;
    $('updatedAt').textContent = stamp && !Number.isNaN(stamp.getTime()) ? `Last refresh: ${stamp.toLocaleString('en-IN')}` : 'Latest report loaded';
    populateFilters();
    applyFilters();
  }catch(error){
    $('customerRows').innerHTML = `<tr><td colspan="7"><div class="empty-state">${esc(error.message)}</div></td></tr>`;
    $('mobileCards').innerHTML = `<div class="empty-state">${esc(error.message)}</div>`;
    showToast(error.message);
  }finally{ setLoading(false); }
}

function setLoading(active){ $('refreshBtn').classList.toggle('spinning',active); }
function populateFilters(){
  fillSelect($('salesmanFilter'), [...new Set(state.all.map(salesmanOf).filter(Boolean))].sort());
  fillSelect($('branchFilter'), [...new Set(state.all.map(branchOf).filter(Boolean))].sort());
}
function fillSelect(select, values){ const first=select.options[0].outerHTML; select.innerHTML=first+values.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join(''); }
function closeSuggestions(){const box=$('searchSuggestions');box.classList.remove('open');box.innerHTML='';}
function positionSuggestions(){
  const input=$('searchInput'),box=$('searchSuggestions'),r=input.getBoundingClientRect();
  box.style.left=`${Math.round(r.left)}px`;box.style.top=`${Math.round(r.bottom+7)}px`;box.style.width=`${Math.round(r.width)}px`;
}
function renderSuggestions(){
  const box=$('searchSuggestions'),q=$('searchInput').value.trim().toLowerCase();
  if(q.length<1){closeSuggestions();return;}
  const seen=new Set();
  const matches=state.all.filter(c=>{
    const key=customerOf(c).toLowerCase();
    const ok=`${customerOf(c)} ${codeOf(c)} ${salesmanOf(c)}`.toLowerCase().includes(q);
    if(!ok||seen.has(key))return false;seen.add(key);return true;
  }).slice(0,8);
  if(!matches.length){box.innerHTML='<div class="suggestion-empty">No matching customer</div>';positionSuggestions();box.classList.add('open');return;}
  box.innerHTML=matches.map(c=>`<button type="button" role="option" data-suggestion="${esc(customerOf(c))}"><span class="suggestion-main"><strong>${esc(customerOf(c))}</strong><small>${esc(codeOf(c))||'No code'}</small></span><span class="suggestion-meta">${money(amountOf(c))}<small>${number(daysOf(c))} days</small></span></button>`).join('');
  positionSuggestions();box.classList.add('open');
}
function applyFilters(){
  const q=$('searchInput').value.trim().toLowerCase(), salesman=$('salesmanFilter').value, branch=$('branchFilter').value, band=$('ageingFilter').value;
  state.filtered=state.all.filter(c=>(!q||`${customerOf(c)} ${codeOf(c)} ${salesmanOf(c)}`.toLowerCase().includes(q))&&(!salesman||salesmanOf(c)===salesman)&&(!branch||branchOf(c)===branch)&&(!band||bandOf(c)===band));
  state.page=1; renderAll();
}
function renderAll(){ renderKpis(); renderDistribution(); renderPriorities(); renderRecords(); }
function renderKpis(){
  const list=state.filtered, total=list.reduce((s,c)=>s+amountOf(c),0), bills=list.reduce((s,c)=>s+billsOf(c),0), over60=list.filter(c=>daysOf(c)>60), oldest=[...list].sort((a,b)=>daysOf(b)-daysOf(a))[0];
  $('totalOutstanding').textContent=money(total); $('totalCustomers').textContent=number(list.length); $('totalBills').textContent=number(bills);
  $('above60Amount').textContent=money(over60.reduce((s,c)=>s+amountOf(c),0)); $('above60Customers').textContent=`${number(over60.length)} customers`;
  $('oldestDays').textContent=oldest?`${number(daysOf(oldest))} days`:'0 days'; $('oldestCustomer').textContent=oldest?customerOf(oldest):'No data';
  $('filteredNote').textContent=list.length===state.all.length?'Across all customers':`Filtered from ${number(state.all.length)} customers`;
}
function renderDistribution(){
  const bands=[['0-30',0,30],['31-60',31,60],['61-90',61,90],['91-120',91,120],['121-180',121,180],['180+',181,Infinity]];
  const totals=bands.map(([label,min,max])=>[label,state.filtered.filter(c=>daysOf(c)>=min&&daysOf(c)<=max).reduce((s,c)=>s+amountOf(c),0)]), max=Math.max(...totals.map(x=>x[1]),1);
  $('distributionBars').innerHTML=totals.map(([label,value])=>`<div class="bar-row"><span class="bar-label">${label}</span><div class="bar-track"><div class="bar-fill" data-width="${(value/max)*100}"></div></div><span class="bar-value">${money(value)}</span></div>`).join('');
  requestAnimationFrame(()=>document.querySelectorAll('.bar-fill').forEach(el=>el.style.width=`${el.dataset.width}%`));
}
function renderPriorities(){
  const top=[...state.filtered].sort((a,b)=>amountOf(b)-amountOf(a)).slice(0,7);
  $('priorityList').innerHTML=top.length?top.map((c,i)=>{const [label,cls]=priorityOf(c);return `<div class="priority-item" style="animation-delay:${i*.04}s"><div><div class="priority-name" title="${esc(customerOf(c))}">${esc(customerOf(c))}</div><div class="priority-meta">${esc(codeOf(c))||'No code'} · ${number(billsOf(c))} bills · ${number(daysOf(c))} days</div></div><div><div class="priority-amount">${money(amountOf(c))}</div><span class="pill pill-${cls}">${label}</span></div></div>`}).join(''):'<div class="empty-state">No matching customers.</div>';
}
function renderRecords(){
  const pages=Math.max(1,Math.ceil(state.filtered.length/state.pageSize)); state.page=Math.min(state.page,pages); const start=(state.page-1)*state.pageSize, rows=state.filtered.slice(start,start+state.pageSize);
  $('resultsCount').textContent=`${number(state.filtered.length)} records`; $('pageInfo').textContent=`Page ${state.page} of ${pages}`; $('prevBtn').disabled=state.page<=1; $('nextBtn').disabled=state.page>=pages;
  $('customerRows').innerHTML=rows.length?rows.map(c=>{const [label,cls]=priorityOf(c);return `<tr><td><span class="customer-name" title="${esc(customerOf(c))}">${esc(customerOf(c))}</span><span class="customer-code">${esc(codeOf(c))}</span></td><td class="amount">${money(amountOf(c))}</td><td><span class="age-text">${number(daysOf(c))} days</span><span class="customer-code">${bandOf(c)}</span></td><td>${number(billsOf(c))}</td><td>${esc(salesmanOf(c))||'-'}</td><td>${esc(branchOf(c))||'-'}</td><td><span class="pill pill-${cls}">${label}</span></td></tr>`}).join(''):'<tr><td colspan="7"><div class="empty-state">No matching records.</div></td></tr>';
  $('mobileCards').innerHTML=rows.map(c=>{const [label,cls]=priorityOf(c);return `<article class="mobile-card"><div class="mobile-card-head"><div><h3>${esc(customerOf(c))}</h3><span class="customer-code">${esc(codeOf(c))}</span></div><div><div class="amount">${money(amountOf(c))}</div><span class="pill pill-${cls}">${label}</span></div></div><div class="mobile-card-meta"><div><span>Ageing</span><strong>${number(daysOf(c))} days</strong></div><div><span>Open bills</span><strong>${number(billsOf(c))}</strong></div><div><span>Salesman</span><strong>${esc(salesmanOf(c))||'-'}</strong></div><div><span>Branch</span><strong>${esc(branchOf(c))||'-'}</strong></div></div></article>`}).join('');
}
function exportCsv(){
  const headers=['Code','Customer','Outstanding','Ageing Days','Open Bills','Salesman','Branch','Priority'];
  const rows=state.filtered.map(c=>[codeOf(c),customerOf(c),amountOf(c),daysOf(c),billsOf(c),salesmanOf(c),branchOf(c),priorityOf(c)[0]]);
  const csv=[headers,...rows].map(row=>row.map(v=>`"${String(v??'').replace(/"/g,'""')}"`).join(',')).join('\r\n');
  const blob=new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}), url=URL.createObjectURL(blob), a=document.createElement('a'); a.href=url;a.download=`customer-ageing-filtered-${new Date().toISOString().slice(0,10)}.csv`;a.click();URL.revokeObjectURL(url);showToast('Filtered CSV exported.');
}
function resetFilters(){ $('searchInput').value='';$('salesmanFilter').value='';$('branchFilter').value='';$('ageingFilter').value='';applyFilters(); }
function showToast(message){const t=$('toast');t.textContent=message;t.classList.add('show');clearTimeout(showToast.timer);showToast.timer=setTimeout(()=>t.classList.remove('show'),2500);}
['salesmanFilter','branchFilter','ageingFilter'].forEach(id=>$(id).addEventListener('change',applyFilters)); $('searchInput').addEventListener('input',()=>{renderSuggestions();applyFilters();});
$('searchInput').addEventListener('focus',renderSuggestions);
document.addEventListener('click',e=>{const pick=e.target.closest('[data-suggestion]');if(pick){$('searchInput').value=pick.dataset.suggestion;closeSuggestions();applyFilters();return;}if(!e.target.closest('.search-field')&&!e.target.closest('#searchSuggestions'))closeSuggestions();});
$('pageSize').addEventListener('change',()=>{state.pageSize=Number($('pageSize').value);state.page=1;renderRecords();});
window.addEventListener('resize',()=>{if($('searchSuggestions').classList.contains('open'))positionSuggestions();});
window.addEventListener('scroll',closeSuggestions,{passive:true}); $('resetBtn').addEventListener('click',resetFilters); $('refreshBtn').addEventListener('click',loadData); $('exportBtn').addEventListener('click',exportCsv); $('prevBtn').addEventListener('click',()=>{if(state.page>1){state.page--;renderRecords();scrollToRecords();}}); $('nextBtn').addEventListener('click',()=>{if(state.page*state.pageSize<state.filtered.length){state.page++;renderRecords();scrollToRecords();}}); function scrollToRecords(){document.querySelector('.records-panel').scrollIntoView({behavior:'smooth',block:'start'});} loadData();
