"""BADANG Trading v1.7.2 read-only dashboard. No DB or order execution."""
from flask import Blueprint, Response

badang_dashboard = Blueprint('badang_dashboard', __name__)

HTML = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BADANG Trading | Dashboard</title>
<style>
:root{color-scheme:dark;font-family:system-ui,-apple-system,'Malgun Gothic',sans-serif;background:#0b1220;color:#eef4ff}*{box-sizing:border-box}body{margin:0}main{max-width:1200px;margin:auto;padding:24px 16px 70px}header,.toolbar,.cards,.stats,.meta{display:flex;align-items:center;gap:12px;flex-wrap:wrap}header{justify-content:space-between;margin-bottom:24px}h1{font-size:clamp(24px,4vw,34px);margin:0}h2{font-size:18px;margin:0 0 12px}.muted{color:#98a8c1}.sub{font-size:13px}.panel,.card{background:#141f32;border:1px solid #293a55;border-radius:16px;padding:18px}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));margin:18px 0}.stats .panel{padding:16px}.number{font-size:28px;font-weight:750;margin-top:4px}.toolbar{margin:16px 0}button,select{background:#1c2b42;color:#edf4ff;border:1px solid #38506d;border-radius:9px;padding:10px 13px;font:inherit}button{cursor:pointer}button.primary{background:#2563eb;border-color:#2563eb}button:disabled{opacity:.6;cursor:wait}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(285px,1fr));align-items:stretch}.card{min-width:0}.head{display:flex;align-items:center;justify-content:space-between;gap:8px}.coin{font-size:20px;font-weight:750}.badge{padding:5px 9px;border-radius:7px;font-size:12px;font-weight:800;background:#374151}.LONG{background:#124c3e;color:#8df1cc}.SHORT{background:#63303a;color:#ffb1bc}.WAIT{background:#364152;color:#d6deeb}.price{font-size:25px;font-weight:750;margin:13px 0 3px;overflow-wrap:anywhere}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:16px 0}.metric{background:#10192a;border-radius:9px;padding:10px}.metric .val{font-weight:650;margin-top:4px;overflow-wrap:anywhere}.warn{color:#ffd28a}.up{color:#8df1cc}.down{color:#ffacb7}.foot{border-top:1px solid #30405a;margin-top:13px;padding-top:12px}.error{color:#ffb2b2}.empty{padding:26px;text-align:center}.detail{margin-top:12px}.detail summary{cursor:pointer;color:#a9c7ff}.detail pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px;color:#becbe0}a{color:#9cc3ff}@media(max-width:550px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}main{padding:18px 12px 50px}.panel,.card{padding:14px}}
</style></head><body><main>
<header><div><h1>🌊 BADANG <span style="color:#75b5ff">Trading</span></h1><div class="muted sub">v1.7.2 · 실시간 요청형 분석 대시보드 · 자동매매 아님</div></div><a href="/">기존 화면 ↗</a></header>
<section class="stats"><div class="panel"><div class="muted sub">조회 완료</div><div class="number" id="total">–</div></div><div class="panel"><div class="muted sub">LONG</div><div class="number up" id="long">–</div></div><div class="panel"><div class="muted sub">SHORT</div><div class="number down" id="short">–</div></div></section>
<section class="panel"><div class="toolbar"><label>분석 모드 <select id="mode"><option value="scalp">단타 (15m·30m·1H)</option><option value="swing">스윙 (1H·4H·1D)</option></select></label><button class="primary" id="load">분석 새로고침</button><button id="next" disabled>다음 종목</button></div><div id="status" class="muted sub" role="status">분석을 시작하려면 새로고침을 눌러줘.</div><div id="updated" class="muted sub" style="margin-top:5px"></div></section>
<div class="meta" style="justify-content:space-between;margin:22px 0 12px"><h2>종목별 분석</h2><div class="muted sub" id="range">한 종목씩 조회</div></div><div class="cards" id="cards"><div class="panel empty muted">데이터를 불러오지 않았어.</div></div>
<p class="muted sub" style="margin-top:24px">OI는 현재 계약 수량이며 변화율이 아닙니다. 체결 압력은 최근 최대 500건의 표본으로 전체 CVD가 아닙니다. VWAP은 봉 기반 근삿값입니다. 모든 판단은 연구용이며 투자 수익을 보장하지 않습니다.</p>
</main><script>
'use strict';
const $=id=>document.getElementById(id);let nextOffset=0,busy=false;
const esc=x=>String(x??'–').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(n,d=4)=>n===null||n===undefined||n===''||!Number.isFinite(Number(n))?'–':Number(n).toLocaleString('en-US',{maximumFractionDigits:d});
const pct=n=>n===null||n===undefined?'–':fmt(Number(n)*100,4)+'%';
const trend=t=>t==='UP'?'<span class="up">상승 ↑</span>':t==='DOWN'?'<span class="down">하락 ↓</span>':esc(t||'–');
const metric=(label,value)=>`<div class="metric"><div class="muted sub">${esc(label)}</div><div class="val">${value}</div></div>`;
const plainSide=s=>s==='LONG'?'상승 후보':s==='SHORT'?'하락 후보':'진입 대기';
const explainDecision=(x,s)=>{const a=Number(x.long_score),b=Number(x.short_score);if(s==='WAIT')return '현재는 진입 신호가 확정되지 않았어. 점수만 보고 진입하지 말고 다음 확정봉을 기다려줘.';if(Number.isFinite(a)&&Number.isFinite(b))return (s==='LONG'?'상승':'하락')+' 쪽 근거가 우세해 보여. 다만 점수는 수익 확률이 아니며 손절 기준을 먼저 확인해야 해.';return '방향 후보는 있지만 판단 근거를 충분히 확인할 수 없어.'};
const divergenceText=x=>{const d=x.divergence_explained_46;if(!d||typeof d!=='object')return '다이버전스 분석 자료가 없어.';const parts=[];for(const [tf,signals] of Object.entries(d)){if(!Array.isArray(signals))continue;const valid=signals.filter(z=>z&&z.status==='RECENT_UNCONFIRMED_REVERSAL'&&z.pivot_confirmed===true&&z.confirmed===false);const bull=valid.filter(z=>['regular_bullish','hidden_bullish'].includes(z.type));const bear=valid.filter(z=>['regular_bearish','hidden_bearish'].includes(z.type));if(bull.length&&bear.length)parts.push(tf+': 상승·하락 단서 혼재 (진입 확정 아님)');else if(bull.length)parts.push(tf+': 상승 단서 '+bull.map(z=>z.type.startsWith('hidden')?'추세 지속형':'일반형').join('/')+' (반전 미확정)');else if(bear.length)parts.push(tf+': 하락 단서 '+bear.map(z=>z.type.startsWith('hidden')?'추세 지속형':'일반형').join('/')+' (반전 미확정)')}return parts.length?parts.join(' · '):'최근 유효한 다이버전스 후보 없음 (과거·무효 신호 제외)'};

const waveText=x=>{const data=x.wave_by_timeframe_32||{};if(!data||typeof data!=='object')return '파동 자료 없음';const parts=[];for(const [tf,rec] of Object.entries(data)){if(!rec||rec.status!=='AVAILABLE'||!Array.isArray(rec.candidates))continue;const v=rec.candidates.filter(z=>z&&z.structure_status==='TIME_ORDER_VALID'&&z.age_class==='RECENT'&&z.completion==='UNCONFIRMED');if(!v.length)continue;const z=v[0];const side=String(z.direction||'').toLowerCase()==='up'?'상승':String(z.direction||'').toLowerCase()==='down'?'하락':'방향 불명';parts.push(tf+': '+side+' 과거 전환점 파동 후보 (현재 진행·완료 미확정)')}return parts.length?parts.join(' · '):'현재 유효한 파동 후보를 확인할 수 없어.'};
const riskText=x=>{const values=[x.entry_reference,x.stop_loss,x.take_profit_1];const side=x.recommendation;if(values.some(v=>v===null||v===undefined||v===''||typeof v==='boolean'))return '진입·손절·목표 정보 부족: 손익비 검증 불가';const [entry,stop,tp]=values.map(Number);if(![entry,stop,tp].every(Number.isFinite)||entry<=0||stop<=0||tp<=0||!['LONG','SHORT'].includes(side))return '진입·손절·목표 정보 부족: 손익비 검증 불가';const risk=side==='LONG'?entry-stop:stop-entry,reward=side==='LONG'?tp-entry:entry-tp;if(risk<=0||reward<=0)return '진입·손절·목표의 방향이 맞지 않아 재검증 필요';return '표시 가격 기준 예상 손익비 1:'+fmt(reward/risk,2)+' (수수료·슬리피지 미반영)'};

function render(x){
  const side=x.technical_side;
  const ready=x.decision_427?.state==='READY_REVIEW'&&x.integrated_audit_439?.status==='REVIEW_ONLY';
  const plan=(ready?x.decision_427?.plan:x.technical_plan)||{};
  const frames=x.mode==='swing'?['1H','4H','1D']:['15m','30m','1H'];
  const quality=x.data_quality||{};
  const levels=frames.map(tf=>{
    const f=x.structure_427?.[tf]||{};
    const support=f.support_levels||[], resistance=f.resistance_levels||[];
    const wave=(f.wave?.alternatives||[]).map(w=>(w.direction==='UP'?'상승 ':'하락 ')+w.wave+'파 · 무효화 '+fmt(w.invalidation,8)).join(' / ');
    return tf+' · 지지 '+support.map(v=>fmt(v,8)).join(' → ')+' · 저항 '+resistance.map(v=>fmt(v,8)).join(' → ')+(wave?' · '+wave:'');
  }).map(esc).join('<br>');
  const caveats=(x.data_caveats||[]).map(esc).join(' · ');
  return `<article class="card"><div class="head"><span class="coin">${esc(x.symbol)} · ${x.mode==='swing'?'스윙':'단타'}</span><span class="badge ${side}">${side==='LONG'?'롱':'숏'} ${fmt(x.technical_score,0)}점</span></div>
  <div class="metric"><strong>바당의 쉬운 판단 · ${ready?'진입 조건 충족':'진입 대기 · 기술적 후보'}</strong>
  <p class="sub">확정봉 ${quality.candles==='VERIFIED'?'검증 통과':'점검 필요'} · ${caveats} · 검증된 승률 자료 없음</p>
  <p class="sub">${esc(divergenceText(x))}</p><p class="sub">${levels}</p></div>
  <div class="grid">${metric(ready?'검증된 진입 기준가':'기술적 참고 진입가',fmt(plan.entry,8))}
  ${metric('손절 기준',fmt(plan.stop,8))}${metric('1차 목표',fmt(plan.tp1,8))}
  ${metric('2차 목표',fmt(plan.tp2,8))}${metric(ready?'1차 순손익비':'1차 가격 손익비',fmt(ready?plan.rr1_net_estimate:plan.rr1_gross,2)+'R')}
  ${metric('확정봉 분석 기준가',fmt(x.analysis_reference_price,8))}</div>
  <details class="detail"><summary>분석 원본 상세 보기</summary><pre>${esc(JSON.stringify(x,null,2))}</pre></details></article>`;
}
async function load(next=false){if(busy)return;busy=true;const button=$('load'),nextButton=$('next');button.disabled=true;nextButton.disabled=true;const at=next?nextOffset:0;$('status').textContent='거래소 데이터를 조회 중이야. 종목당 여러 API 요청으로 시간이 걸릴 수 있어…';try{const ctl=new AbortController();const timer=setTimeout(()=>ctl.abort(),110000);let response;try{response=await fetch(`/api/v13-scan?mode=${encodeURIComponent($('mode').value)}&offset=${at}`,{cache:'no-store',signal:ctl.signal});}finally{clearTimeout(timer)}if(!response.ok)throw new Error(`서버 HTTP ${response.status}`);const data=await response.json();if(data.error)throw new Error(data.error);const analyzed=Array.isArray(data.results)?data.results:[];
const candidates=new Map((data.technical_candidates||[]).map(x=>[x.symbol,x]));
const rows=analyzed.filter(x=>candidates.has(x.symbol));
nextOffset=data.next_offset;
$('total').textContent=analyzed.length;
$('long').textContent=rows.filter(x=>x.technical_side==='LONG').length;
$('short').textContent=rows.filter(x=>x.technical_side==='SHORT').length;
$('cards').innerHTML=rows.length?rows.map(render).join(''):'<div class="panel empty muted">이 종목에는 80점 이상 롱·숏 후보가 없습니다.</div>';
$('range').textContent='전체 '+fmt(data.total,0)+'종목 중 '+Math.min(at+1,data.total)+'번째';
const errors=Array.isArray(data.errors)?data.errors:[];$('status').textContent=`${analyzed.length}종목 조회 완료${errors.length?` · 오류 ${errors.length}건`:''}`;if(errors.length){$('status').textContent+=' · '+errors.map(e=>`${e.symbol}: ${e.error}`).join(' / ').slice(0,220)}$('updated').textContent='마지막 조회: '+new Date().toLocaleString('ko-KR');nextButton.disabled=!(data.next_offset<data.total);}catch(e){$('status').innerHTML=`<span class="error">조회 실패: ${esc(e.message)}</span>`;nextButton.disabled=true;}finally{busy=false;button.disabled=false}}
$('load').addEventListener('click',()=>load(false));$('next').addEventListener('click',()=>load(true));$('mode').addEventListener('change',()=>{$('cards').innerHTML='<div class="panel empty muted">모드가 바뀌었어. 분석 새로고침을 눌러줘.</div>';$('next').disabled=true;nextOffset=0});
</script></body></html>'''

@badang_dashboard.get('/dashboard')
def dashboard():
    return Response(HTML, mimetype='text/html; charset=utf-8', headers={'Cache-Control': 'no-store'})
