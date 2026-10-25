const $=id=>document.getElementById(id);
let current=[],running=false,abort=false,allTotal=0;
const num=(n,d=4)=>n==null||!Number.isFinite(Number(n))?'—':Number(n).toLocaleString('ko-KR',{maximumFractionDigits:d});
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
const reasonMap={
'EMA bearish alignment':'이동평균선 하락 정렬','EMA bullish alignment':'이동평균선 상승 정렬',
'EMA20 below EMA50':'EMA20이 EMA50 아래','EMA20 above EMA50':'EMA20이 EMA50 위',
'MACD histogram falling negative':'MACD 하락세','MACD histogram rising positive':'MACD 상승세',
'RSI bearish range':'RSI 하락 우세','RSI bullish range':'RSI 상승 우세',
'hidden bearish RSI divergence candidate':'숨은 하락 다이버전스 후보',
'hidden bullish RSI divergence candidate':'숨은 상승 다이버전스 후보',
'rising volume with red candle':'음봉 거래량 증가','rising volume with green candle':'양봉 거래량 증가'
};
function korean(s){return reasonMap[s]||String(s||'확인 필요')}
function signal(x){return ['LONG','SHORT'].includes(x.recommendation)?x.recommendation:'WAIT'}
function render(){
  const filter=$('filter').value;
  const data=current.filter(x=>filter==='ALL'||signal(x)===filter);
  data.sort((a,b)=>Math.max(b.long_score||0,b.short_score||0)-Math.max(a.long_score||0,a.short_score||0));
  $('results').innerHTML=data.length?data.map(x=>{
    const dir=signal(x), score=dir==='LONG'?x.long_score:dir==='SHORT'?x.short_score:Math.max(x.long_score||0,x.short_score||0);
    const v=x.v17_research||{}, trends=x.timeframe_trends||{}, price=x.entry_reference;
    const labels=Object.entries(trends).map(([k,t])=>k+' '+(t==='UP'?'상승':t==='DOWN'?'하락':'중립')).join(' · ');
    const warns=(x.stability_warnings||[]).map(w=>w==='OPPOSING_RECENT_TRADE_SAMPLE'?'최근 체결 방향 충돌':w==='INVALID_TRADE_PLAN'?'가격 시나리오 부적합':w).join(' · ');
    const plan=dir==='WAIT'?'관망 · 진입 신호 없음':`진입 참고 ${num(price,8)} · 손절 ${num(x.stop_loss,8)} · 1차 목표 ${num(x.take_profit_1,8)} · 2차 목표 ${num(x.take_profit_2,8)}`;
    return `<article class="item"><div class="top"><div><strong>${esc(x.symbol)}</strong><small>${esc(x.exchange||'')} · ${esc(labels)}</small></div><div class="signal ${dir==='LONG'?'long':dir==='SHORT'?'short':'wait'}">${dir==='LONG'?'롱 후보':dir==='SHORT'?'숏 후보':'관망'} · ${num(score,0)}점</div></div><div class="metrics"><div>기준 가격<strong>${num(price,8)} USDT</strong></div><div>RSI<strong>${num(x.rsi,2)}</strong></div><div>롱 / 숏 점수<strong>${num(x.long_score,0)} / ${num(x.short_score,0)}</strong></div><div>펀딩비 (OKX)<strong>${num(v.funding_rate==null?null:v.funding_rate*100,4)}%</strong></div></div><details><summary>분석 근거 및 가격 구간</summary><p>${esc((x.reasons||[]).map(korean).join(' · ')||'뚜렷한 방향성 신호 없음')}</p><p><b>최종 판단:</b> ${esc(plan)}</p><p>현재 OI: ${num(v.oi_contracts,2)} 계약 · 최근 체결 불균형: ${num(v.sample_imbalance,3)} (최대 500건 표본)</p><p>VWAP 근사: ${num(v.vwap?.value,8)} · OI 변화율: 계산 불가 (이력 없음)</p>${warns?`<p class="warning">⚠ ${esc(warns)}</p>`:''}<p>이 결과는 연구용이며 자동 매매 신호가 아닙니다.</p></details></article>`;
  }).join(''):'<div class="empty">해당 조건의 종목이 없습니다.</div>';
}
async function begin(){
 if(running)return;
 running=true;abort=false;current=[];allTotal=0;
 $('scan').disabled=true;$('bar').style.width='0%';render();
 const mode=$('interval').value, limit=Number($('minVolume').value);
 let offset=0,errors=0;
 try{
  while(!abort){
   $('status').textContent=`분석 중… ${offset}종목 완료`;
   const res=await fetch(`/api/v13-scan?mode=${encodeURIComponent(mode)}&offset=${offset}`,{cache:'no-store'});
   const j=await res.json();
   if(!res.ok||j.error)throw Error(j.error||`HTTP ${res.status}`);
   allTotal=Number(j.total)||0;
   current.push(...(j.results||[]));errors+=(j.errors||[]).length;
   const next=Number(j.next_offset);
   if(!Number.isFinite(next)||next<=offset)throw Error('분석 진행 위치 오류');
   offset=next;
   $('count').textContent=current.length+' / '+(limit||allTotal);
   $('longCount').textContent=current.filter(x=>signal(x)==='LONG').length;
   $('shortCount').textContent=current.filter(x=>signal(x)==='SHORT').length;
   const target=limit?Math.min(limit,allTotal):allTotal;
   $('bar').style.width=(target?Math.min(100,Math.round(offset/target*100)):100)+'%';
   $('status').textContent=`${Math.min(offset,target)} / ${target}종목 확인 · 분석 실패 ${errors}건`;
   render();
   if(!j.results?.length&&!j.errors?.length || offset>=target || offset>=allTotal)break;
  }
  $('status').textContent+=` · 완료 (${new Date().toLocaleTimeString('ko-KR')})`;
 }catch(e){$('status').textContent='오류: '+e.message}
 finally{running=false;$('scan').disabled=false}
}
$('scan').addEventListener('click',begin);
$('filter').addEventListener('change',render);
