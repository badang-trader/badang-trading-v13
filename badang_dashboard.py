"""BADANG Trading v1.7.2 read-only dashboard. No DB or order execution."""
from flask import Blueprint, Response

badang_dashboard = Blueprint('badang_dashboard', __name__)

HTML = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BADANG Trading | Dashboard</title>
<style>
:root{color-scheme:dark;font-family:system-ui,-apple-system,'Malgun Gothic',sans-serif;background:#0b1220;color:#eef4ff}*{box-sizing:border-box}body{margin:0}main{max-width:1200px;margin:auto;padding:24px 16px 70px}header,.toolbar,.cards,.stats,.meta{display:flex;align-items:center;gap:12px;flex-wrap:wrap}header{justify-content:space-between;margin-bottom:24px}h1{font-size:clamp(24px,4vw,34px);margin:0}h2{font-size:18px;margin:0 0 12px}.muted{color:#98a8c1}.sub{font-size:13px}.panel,.card{background:#141f32;border:1px solid #293a55;border-radius:16px;padding:18px}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));margin:18px 0}.stats .panel{padding:16px}.number{font-size:28px;font-weight:750;margin-top:4px}.toolbar{margin:16px 0}button,select{background:#1c2b42;color:#edf4ff;border:1px solid #38506d;border-radius:9px;padding:10px 13px;font:inherit}button{cursor:pointer}button.primary{background:#2563eb;border-color:#2563eb}button:disabled{opacity:.6;cursor:wait}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(285px,1fr));align-items:stretch}.card{min-width:0}.head{display:flex;align-items:center;justify-content:space-between;gap:8px}.coin{font-size:20px;font-weight:750}.badge{padding:5px 9px;border-radius:7px;font-size:12px;font-weight:800;background:#374151}.LONG{background:#124c3e;color:#8df1cc}.SHORT{background:#63303a;color:#ffb1bc}.WAIT{background:#364152;color:#d6deeb}.price{font-size:25px;font-weight:750;margin:13px 0 3px;overflow-wrap:anywhere}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:16px 0}.metric{background:#10192a;border-radius:9px;padding:10px}.metric .val{font-weight:650;margin-top:4px;overflow-wrap:anywhere}.warn{color:#ffd28a}.up{color:#8df1cc}.down{color:#ffacb7}.foot{border-top:1px solid #30405a;margin-top:13px;padding-top:12px}.error{color:#ffb2b2}.empty{padding:26px;text-align:center}.detail{margin-top:12px}.detail summary{cursor:pointer;color:#a9c7ff}.detail pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px;color:#becbe0}a{color:#9cc3ff}@media(max-width:550px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}main{padding:18px 12px 50px}.panel,.card{padding:14px}}
.cards{grid-template-columns:repeat(auto-fit,minmax(min(100%,285px),1fr))}.head{flex-wrap:wrap}.metric{min-width:0}.flow{overflow-wrap:anywhere}
.research{margin-top:16px;overflow-wrap:anywhere}.research ul{padding-inline-start:1.3em}.research li{margin:.4em 0}.research details{margin-top:12px}.research summary{cursor:pointer}
.search{display:flex;align-items:end;flex-wrap:wrap;gap:8px;margin-bottom:14px}.search input{display:block;width:min(100%,15rem);margin-top:5px;background:#1c2b42;color:#edf4ff;border:1px solid #38506d;border-radius:9px;padding:10px 13px;font:inherit}
.zone-score{margin:.2em 0 .65em}
@media(max-width:480px){
  .toolbar{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .toolbar label{grid-column:1/-1}.toolbar select{width:100%}
  .search{display:grid;grid-template-columns:minmax(0,1fr)}
  .search input{width:100%}
}
</style></head><body><main>
<header><div><h1>🌊 BADANG <span style="color:#75b5ff">Trading</span></h1><div class="muted sub">v1.7.2 · 실시간 요청형 분석 대시보드 · 자동매매 아님</div></div><a href="/">기존 화면 ↗</a></header>
<section class="stats"><div class="panel"><div class="muted sub">조회 완료</div><div class="number" id="total">–</div></div><div class="panel"><div class="muted sub">LONG</div><div class="number up" id="long">–</div></div><div class="panel"><div class="muted sub">SHORT</div><div class="number down" id="short">–</div></div></section>
<section class="panel"><div class="toolbar"><label>분석 모드 <select id="mode"><option value="scalp">단타 (15m·30m·1H)</option><option value="swing">스윙 (1H·4H·1D)</option></select></label><button class="primary" id="load">분석 새로고침</button><button id="next" disabled>다음 종목</button></div>
<form class="search" id="search"><label>코인 이름 또는 거래쌍<input id="symbol" type="search" enterkeyhint="search" autocapitalize="characters" spellcheck="false" placeholder="예: BTC, ETHUSDT" required maxlength="29" autocomplete="off"></label><button id="search-button" type="submit">종목 조회</button></form>
<div id="status" class="muted sub" role="status">분석을 시작하려면 종목을 조회하거나 새로고침을 눌러줘.</div><div id="updated" class="muted sub" style="margin-top:5px"></div></section>
<div class="meta" style="justify-content:space-between;margin:22px 0 12px"><h2>종목별 분석</h2><div class="muted sub" id="range">한 종목씩 조회</div></div><div class="cards" id="cards"><div class="panel empty muted">데이터를 불러오지 않았어.</div></div>
<div id="research"></div>
<p class="muted sub" style="margin-top:24px">OI는 현재 계약 수량이며 변화율이 아닙니다. 별도의 최근 체결 조회는 일부 표본을 제공하며 연속 CVD는 미검증입니다. VWAP은 봉 기반 근삿값입니다. 모든 판단은 연구용이며 투자 수익을 보장하지 않습니다.</p>
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

function entryReason(x){
  const action=x.price_action_45||{};
  if (action.side==='WAIT' && action.reason) return action.reason;
  return x.entry_blockers?.[0] || x.decision_427?.reasons?.[0] || '진입 조건 확인 대기';
}
function entryCheckDetails(x){
  const checks=x.signal_precision_418?.checks||{};
  const details=[];
  const alignment=checks.timeframe_alignment;
  if(alignment?.passed===false && alignment.evidence){
    const names={UP:'상승',DOWN:'하락',NEUTRAL:'중립'};
    const conflicts=Object.entries(alignment.evidence.off_trend)
      .map(([frame,direction])=>frame+' '+(names[direction]||'미확인'));
    details.push('진입에는 '+names[alignment.evidence.expected]+' 추세가 필요 · '+conflicts.join(', '));
  }
  const risk=checks.risk_distance;
  if(risk?.passed===false && risk.evidence){
    const {observed_pct,minimum_pct,maximum_pct}=risk.evidence;
    details.push('손절 거리 '+fmt(observed_pct,4)+'% · 허용 '+fmt(minimum_pct,4)+'~'+fmt(maximum_pct,4)+'%');
  }
  return details;
}
function flowStatus(x){
  const legs=Object.values(x.structure_427||{}).flatMap(f=>(f.wave?.alternatives||[])
    .flatMap(w=>w.flow_validation?.oi_legs||[]));
  const verified=legs.filter(leg=>leg.status==='ENDPOINTS_AVAILABLE').length;
  const oi=verified ? '파동 OI 관측 '+verified+'/'+legs.length+'구간 (시작·종료 관측값)'
    : '파동 OI 관측 자료 없음';
  const store=x.reversal_tracking_514?.status;
  const reversal=store==='SAVED' ? '반전 이력 저장됨'
    : store==='DATABASE_NOT_CONFIGURED' ? '반전 구간은 현재 조회만 계산'
    : store==='STORAGE_ERROR' ? '반전 이력 저장 오류' : '반전 이력 확인 대기';
  return oi+' · 연속 체결 CVD 미검증 · '+reversal;
}
function waveLines(frame){
  const directions={UP:'상승',DOWN:'하락'};
  return (frame.wave?.alternatives||[]).flatMap(wave=>{
    if(!directions[wave.direction] || !Number.isInteger(wave.wave))return [];
    const targets=(wave.future_targets||[]).map(target=>
      fmt(target.price,8)+' ('+fmt(target.ratio,3)+'배)');
    const level=wave.active_leg_invalidation??wave.invalidation;
    return [directions[wave.direction]+' '+wave.wave+'파 후보 · 현재 파동 무효화 '+fmt(level,8)
      +' · 구조 무효화 '+fmt(wave.structural_invalidation,8)
      +' · 미도달 피보나치 목표 '+(targets.join(', ')||'자료 없음')];
  });
}
const waveShapeLabels={
  ABC_ZIGZAG_GEOMETRY:'ABC 지그재그',ABC_FLAT_GEOMETRY:'ABC 플랫',
  WXY_DOUBLE_ZIGZAG_GEOMETRY:'W-X-Y 복합 조정',WXYXZ_TRIPLE_ZIGZAG_GEOMETRY:'W-X-Y-X-Z 복합 조정',
  CONTRACTING_DIAGONAL_GEOMETRY:'수렴 대각삼각형',EXPANDING_DIAGONAL_GEOMETRY:'확장 대각삼각형',
  TRUNCATED_FIFTH_GEOMETRY:'절단 5파',EXTENDED_1_GEOMETRY:'1파 연장',EXTENDED_3_GEOMETRY:'3파 연장',EXTENDED_5_GEOMETRY:'5파 연장'
};
function historicalShapeText(shape){
  const label=waveShapeLabels[shape.pattern];
  if(!label)return null;
  const evidence=shape.geometry_evidence;
  const lower=shape.lower_pivot_evidence;
  const segmentLabels=shape.pattern.includes('DIAGONAL')?['1파','2파','3파','4파','5파']
    : shape.pattern.startsWith('WXY')?['W의 A','W의 B','W의 C','첫 X','Y의 A','Y의 B','Y의 C',
      '둘째 X','Z의 A','Z의 B','Z의 C']:[];
  const lowerText=lower?.status==='PIVOT_COUNTS_ONLY'
    ? ' · '+lower.timeframe+' 구간별 스윙 '+lower.leg_turn_counts.map((n,i)=>
      (segmentLabels[i]?segmentLabels[i]+' ':'')+(n??'미확인')).join(' / ')
    : lower ? ' · 하위봉 전환점 대조 불가' : '';
  if(!evidence)return label+lowerText;
  const variants={RUNNING:'러닝형',EXPANDED:'확장형',NEAR_REGULAR:'일반형에 가까움'};
  const variant=variants[evidence.variant];
  const countLabels={MATCH:'스윙 수 일치',MISMATCH:'스윙 수 다름',INCOMPLETE:'일부 스윙 수 미확인'};
  const countLabel=countLabels[lower?.expected_count_comparison];
  return label+(variant?' '+variant:'')
    +' · B 되돌림 '+fmt(evidence.b_retrace*100,1)+'% · C/A '+fmt(evidence.c_extension,2)+'배'
    +' · 판별에 필요한 내부 구성 '+evidence.expected_subdivision.join('-')+lowerText
    +(countLabel?' · '+countLabel:'');
}
function zoneScoreText(zone){
  const labels={structure:'지지·저항 구조',wave:'파동 목표',fibonacci:'피보나치',ema:'EMA',
    volume:'거래량 반응',divergence:'다이버전스',candle:'캔들 반응'};
  const components=Object.entries(zone.components||{})
    .filter(([key,value])=>labels[key]&&Number.isFinite(value)&&value>0)
    .map(([key,value])=>labels[key]+' '+fmt(value,0)+'점');
  const details=components.length?['점수 구성: '+components.join(' · ')]:[];
  const evidence=zone.divergence_evidence;
  const sourceText=rows=>[...new Set(rows.map(row=>row.timeframe+' '+row.indicator))].join(', ');
  if(evidence?.status==='APPLIED'){
    details.push('다이버전스 '+fmt(evidence.points,0)+'점 가산 · '+sourceText(evidence.matches));
  }else if(evidence?.status==='HELD_CONFLICT'){
    details.push('다이버전스 점수 보류 · 구간 근거 '+sourceText(evidence.matches)
      +' · 같은 시간봉의 반대 단서 '+sourceText(evidence.conflicts));
  }else{
    for(const reason of zone.reasons||[]){
      if(typeof reason==='string'&&reason.includes('점수 보류'))details.push(reason);
    }
  }
  return details;
}
function renderResearch(item){
  const structures=item.structure_427||{};
  const frames=(item.research_timeframes_47||Object.keys(structures)).map(tf=>{
    const frame=structures[tf]||{};
    const waves=waveLines(frame);
    const shapes=(frame.historical_wave_shapes||[]).map(historicalShapeText).filter(Boolean);
    const lines=waves.length?waves:['현재 파동 미확정'];
    for(const shape of shapes)lines.push('과거 형태 후보: '+shape+' · 내부 파동 미검증');
    return '<div><strong>'+esc(tf)+'</strong><ul>'+lines.map(line=>'<li>'+esc(line)+'</li>').join('')+'</ul></div>';
  });
  const path=item.reversal_path_514||{};
  const labels={DOWN:'지지',UP:'저항'};
  const zones=(path.paths||[]).flatMap(({direction,zones})=>(zones||[]).map(zone=>{
    const summary=labels[direction]+' '+fmt(zone.low,8)+'~'+fmt(zone.high,8)
      +' · 반전 근거 '+fmt(zone.expected_score,0)+'점'
      +' · 이탈 기준 '+fmt(zone.invalidation,8)
      +' · 반전 참고 목표 '+fmt(zone.near_reversal_target,8);
    const details=zoneScoreText(zone).map(line=>'<p class="sub muted zone-score">'+esc(line)+'</p>');
    return '<li>'+esc(summary)+details.join('')+'</li>';
  }));
  return `<section class="panel research"><h2>${esc(item.symbol)} · 파동과 반전 구간</h2>
    <details><summary>시간봉별 엘리엇 파동 후보</summary>
    <p class="sub muted">확정봉에서 가능한 파동 해석을 보여줘요.</p>${frames.join('')||'<p>파동 자료 없음</p>'}</details>
    <details><summary>지지·저항과 반전 근거</summary><p class="sub muted">반전 근거 점수는 현재 구간의 근거 합계예요. 구간 도달 후 반전 확인은 별도예요.</p>
    ${zones.length?'<ul>'+zones.join('')+'</ul>':'<p>반전 구간 자료 없음</p>'}</details></section>`;
}
function render(x){
  const side=x.technical_side;
  const ready=x.decision_427?.state==='READY_REVIEW'&&x.integrated_audit_439?.status==='REVIEW_ONLY';
  const plan=(ready?x.decision_427?.plan:x.technical_plan)||{};
  const frames=x.mode==='swing'?['1H','4H','1D']:['15m','30m','1H'];
  const quality=x.data_quality||{};
  const levels=frames.map(tf=>{
    const f=x.structure_427?.[tf]||{};
    const support=f.support_levels||[], resistance=f.resistance_levels||[];
    return tf+' · 지지 '+support.map(v=>fmt(v,8)).join(' → ')+' · 저항 '+resistance.map(v=>fmt(v,8)).join(' → ');
  }).map(esc).join('<br>');
  const caveats=(x.data_caveats||[]).map(esc).join(' · ');
  const checks=ready?[]:entryCheckDetails(x);
  return `<article class="card"><div class="head"><span class="coin">${esc(x.symbol)} · ${x.mode==='swing'?'스윙':'단타'}</span><span class="badge ${side}">${side==='LONG'?'롱':'숏'} ${fmt(x.technical_score,0)}점</span></div>
  <div class="metric"><strong>바당의 쉬운 판단 · ${ready?'진입 조건 충족':'진입 대기 · 기술적 후보'}</strong>
  ${ready?'':`<p class="sub warn">${esc(entryReason(x))}</p>`}
  ${checks.map(text=>`<p class="sub warn">${esc(text)}</p>`).join('')}
  <p class="sub flow">${esc(flowStatus(x))}</p>
  <p class="sub">확정봉 ${quality.candles==='VERIFIED'?'검증 통과':'점검 필요'} · ${caveats} · 검증된 승률 자료 없음</p>
  <p class="sub">${esc(divergenceText(x))}</p><p class="sub">${levels}</p></div>
  <div class="grid">${metric(ready?'검증된 진입 기준가':'기술적 참고 진입가',fmt(plan.entry,8))}
  ${metric('손절 기준',fmt(plan.stop,8))}${metric('1차 목표',fmt(plan.tp1,8))}
  ${metric('2차 목표',fmt(plan.tp2,8))}${metric(ready?'1차 순손익비':'1차 가격 손익비',fmt(ready?plan.rr1_net_estimate:plan.rr1_gross,2)+'R')}
  ${metric('확정봉 분석 기준가',fmt(x.analysis_reference_price,8))}</div>
  <details class="detail"><summary>분석 원본 상세 보기</summary><pre>${esc(JSON.stringify(x,null,2))}</pre></details></article>`;
}
async function load(next=false,symbol=''){
  if(busy)return;
  busy=true;
  const button=$('load'),nextButton=$('next'),mode=$('mode');
  const symbolInput=$('symbol'),searchButton=$('search-button');
  button.disabled=true;
  nextButton.disabled=true;
  mode.disabled=true;
  symbolInput.disabled=true;
  searchButton.disabled=true;
  const at=next?nextOffset:0;
  $('research').replaceChildren();
  $('status').textContent='거래소 데이터를 조회 중이야. 종목당 여러 API 요청으로 시간이 걸릴 수 있어…';
  const ctl=new AbortController();
  const timer=setTimeout(()=>ctl.abort(),110000);
  try{
    const query=new URLSearchParams({mode:mode.value,offset:at});
    if(symbol)query.set('symbol',symbol);
    const response=await fetch('/api/v13-scan?'+query,{cache:'no-store',signal:ctl.signal});
    if(!response.ok)throw new Error(`서버 HTTP ${response.status}`);
    const data=await response.json();
    if(data.error)throw new Error(data.error);
    const analyzed=Array.isArray(data.results)?data.results:[];
    const candidates=new Set((data.technical_candidates||[]).map(x=>x.symbol));
    const rows=analyzed.filter(x=>candidates.has(x.symbol));
    nextOffset=data.next_offset;
    $('total').textContent=analyzed.length;
    $('long').textContent=rows.filter(x=>x.technical_side==='LONG').length;
    $('short').textContent=rows.filter(x=>x.technical_side==='SHORT').length;
    $('cards').innerHTML=rows.length?rows.map(render).join(''):'<div class="panel empty muted">이 종목에는 80점 이상 롱·숏 후보가 없습니다.</div>';
    $('research').innerHTML=analyzed.map(renderResearch).join('');
    $('range').textContent=symbol?'개별 종목 '+symbol:'전체 '+fmt(data.total,0)+'종목 중 '+Math.min(at+1,data.total)+'번째';
    const errors=Array.isArray(data.errors)?data.errors:[];
    $('status').textContent=`${analyzed.length}종목 조회 완료${errors.length?` · 오류 ${errors.length}건`:''}`;
    if(errors.length){
      $('status').textContent+=' · '+errors.map(e=>`${e.symbol}: ${e.error}`).join(' / ').slice(0,220);
    }
    $('updated').textContent='마지막 조회: '+new Date().toLocaleString('ko-KR');
    nextButton.disabled=Boolean(symbol)||!(data.next_offset<data.total);
  }catch(e){
    const message=ctl.signal.aborted?'응답 대기 시간이 길어졌어요. 새로고침으로 다시 시도해 주세요.':e.message;
    $('status').innerHTML=`<span class="error">조회 실패: ${esc(message)}</span>`;
    $('cards').innerHTML='<div class="panel empty muted">새 조회 결과가 없어요.</div>';
    nextButton.disabled=true;
  }finally{
    clearTimeout(timer);
    busy=false;
    button.disabled=false;
    mode.disabled=false;
    symbolInput.disabled=false;
    searchButton.disabled=false;
  }
}
$('load').addEventListener('click',()=>load(false));$('next').addEventListener('click',()=>load(true));$('mode').addEventListener('change',()=>{$('cards').innerHTML='<div class="panel empty muted">모드가 바뀌었어. 분석 새로고침을 눌러줘.</div>';$('research').replaceChildren();$('next').disabled=true;nextOffset=0});
$('search').addEventListener('submit',event=>{
  event.preventDefault();
  const entered=$('symbol').value.trim().toUpperCase();
  if(!entered)return;
  load(false, entered.endsWith('USDT')?entered:entered+'USDT');
});
</script></body></html>'''

@badang_dashboard.get('/dashboard')
def dashboard():
    return Response(HTML, mimetype='text/html; charset=utf-8', headers={'Cache-Control': 'no-store'})
