
let mode='scalp',running=false;

function choose(m){
  if(running)return;
  mode=m;
  for(const id of ['scalp','swing'])
    document.getElementById(id).classList.toggle('active',id===m);
  document.getElementById('frames').textContent=
    m==='scalp'?'5분 · 15분 · 1시간봉':'1시간 · 4시간 · 일봉';
}

function fmt(x){
  if(x==null||!Number.isFinite(Number(x)))return '—';
  return Number(x).toLocaleString('en-US',{maximumSignificantDigits:7});
}

function el(tag,cls,txt){
  const n=document.createElement(tag);
  if(cls)n.className=cls;
  if(txt!=null)n.textContent=txt;
  return n;
}

function line(root,k,v){
  const d=el('div','line');
  d.append(el('span','',k),el('b','',v));
  root.append(d);
}

function card(x){
  const a=x.setup,c=el('article','item'),top=el('div','top');
  top.append(el('div','name',x.symbol));
  top.append(el('span','tag '+(x.signal==='LONG'?'long':x.signal==='SHORT'?'short':''),
    x.signal==='LONG'?'롱 후보':x.signal==='SHORT'?'숏 후보':'관망'));
  c.append(top);
  const scores=el('div','scores');
  for(const [name,value,cls] of [
    ['롱 점수',x.long_score,'long-text'],
    ['숏 점수',x.short_score,'short-text']
  ]){
    const s=el('div','score');
    s.append(el('span','',name),el('strong',cls,value+'점'));
    scores.append(s);
  }
  c.append(scores);
  line(c,'기준 종가',fmt(a.price)+' USDT');
  line(c,'수급 추정',x.flow.state==='BUY'?'매수 우세':x.flow.state==='SELL'?'매도 우세':'중립/확인 불가');
  line(c,'거래대금 변화',fmt(x.flow.turnover_ratio)+'배');
  if(x.plan){
    line(c,'가상 진입가',fmt(x.plan.entry));
    line(c,'1차 익절가',fmt(x.plan.tp1));
    line(c,'2차 익절가',fmt(x.plan.tp2));
    line(c,'손절가',fmt(x.plan.stop));
    line(c,'목표 손익비','1:'+x.plan.rr1+' / 1:'+x.plan.rr2);
  }else{
    line(c,'진입·익절·손절','관망 — 제시하지 않음');
  }
  const details=el('details'),summary=el('summary','','상세 분석 보기');
  details.append(summary);
  line(details,'상위봉 추세',x.higher);
  line(details,'RSI / 거래량',a.rsi+' / '+a.volume_ratio+'배');
  line(details,'RSI 다이버전스',x.trigger);
  line(details,'가짜 돌파 경고',a.fake_breakout?'있음':'없음');
  line(details,'수급 추정 압력',fmt(x.flow.pressure)+'%');
  line(details,'수급 데이터 설명',x.flow.method);
  line(details,'OI / 펀딩','미반영 · 미확인');
  line(details,'판단 근거',x.reason);
  if(x.plan)line(details,'신호 무효화',x.plan.invalidation);
  c.append(details);
  return c;
}

const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));

async function retryFetch(url,status,offset){
  let lastError;
  for(let attempt=1;attempt<=3;attempt++){
    try{
      const r=await fetch(url,{cache:'no-store'});
      if(!r.ok){
        let msg='HTTP '+r.status;
        try{
          const j=await r.json();
          msg=j.error||msg;
        }catch(_){}
        throw Error(msg);
      }
      return await r.json();
    }catch(e){
      lastError=e;
      if(attempt===3)break;
      status.textContent=offset+'개 처리 후 연결 문제 · 재시도 '+attempt+'/2';
      await wait(attempt*2000);
    }
  }
  throw lastError;
}

async function start(){
  if(running)return;
  running=true;

  const btn=document.getElementById('scan'),
    status=document.getElementById('progress'),
    out=document.getElementById('results'),
    count=document.getElementById('counts'),
    majorOut=document.getElementById('majors'),
    majorStatus=document.getElementById('major-status');

  btn.disabled=true;
  out.replaceChildren();
  majorOut.replaceChildren();
  majorStatus.textContent='비트코인·이더리움 우선 분석 중';

  const selectedMode=mode;
  let offset=0,total=0,done=0,fail=0;
  const candidates=[];

  function showResults(){
    const rank=s=>s==='BTCUSDT'?0:s==='ETHUSDT'?1:2;
    const top=[...candidates].sort((a,b)=>
      rank(a.symbol)-rank(b.symbol)||
      Math.max(b.long_score||0,b.short_score||0)-
      Math.max(a.long_score||0,a.short_score||0)
    );

    majorOut.replaceChildren();

    for(const x of top){
      const a=el('article','item','');
      const score=Math.max(x.long_score||0,x.short_score||0);
      const side=x.candidate_side==='LONG'?'롱':
        x.candidate_side==='SHORT'?'숏':'방향 확인 필요';
      const isMajor=x.symbol==='BTCUSDT'||x.symbol==='ETHUSDT';

      a.append(el('h3','',x.symbol+' · '+side+' · '+score+'점'));

      const recommendation=isMajor
        ?(side==='롱'?'롱 방향':side==='숏'?'숏 방향':'방향 확인 필요')
        :x.recommendation==='LONG'?'롱 추천':
         x.recommendation==='SHORT'?'숏 추천':'관망';

      a.append(el('p','','추천: '+recommendation+' · 거래소: '+x.exchange));

      a.append(el('p','',
        '진입 기준 '+fmt(x.entry_reference)+
        ' · 손절 '+fmt(x.stop_loss)+
        ' · 1차 목표 '+fmt(x.take_profit_1)+
        ' · 2차 목표 '+fmt(x.take_profit_2)
      ));

      a.append(el('p','',
        'RSI '+fmt(x.rsi)+
        ' · 손익비 '+fmt(x.risk_reward_1)+
        ' · 거래량 '+fmt(x.volume_ratio)+'배'
      ));

      const trends=x.timeframe_trends||{};
      const trendText=Object.entries(trends).map(([tf,t])=>{
        const v=typeof t==='string'?t:
          (t?.trend||t?.direction||'확인 필요');
        return tf+' '+v;
      }).join(' · ');

      a.append(el('p','','시간봉 추세: '+(trendText||'데이터 없음')));
      a.append(el('p','','다중 시간봉 일치: '+(x.trend_aligned?'예':'아니오 또는 미확인')));

      if(!x.trend_aligned){
        a.append(el('p','','주의: 시간봉 방향 불일치 또는 미확인'));
      }

      const waves=Array.isArray(x.wave_candidates)?x.wave_candidates:[];

      if(waves.length){
        for(const w of waves){
          a.append(el('p','',
            '엘리엇 파동: '+w.pattern+
            ' · '+w.direction+
            ' · 신뢰 수준 '+w.confidence
          ));
          if(w.invalidation_price!=null){
            a.append(el('p','',
              '파동 무효화 기준: '+fmt(w.invalidation_price)
            ));
          }
          if(w.reasons?.length){
            a.append(el('p','','파동 근거: '+w.reasons.join(' / ')));
          }
        }
      }else{
        a.append(el('p','','엘리엇 파동: 현재 확인된 후보 없음'));
      }

      if(x.reasons?.length){
        a.append(el('p','','기술적 분석 근거: '+x.reasons.join(' / ')));
      }

      majorOut.append(a);
    }

    if(!top.length){
      majorOut.textContent='아직 표시할 분석 결과가 없습니다.';
    }
  }

  try{
    do{
      const url='/api/v13-scan?mode='+selectedMode+'&offset='+offset;
      const j=await retryFetch(url,status,offset);

      if(j.error)throw Error(j.error);

      total=j.total||0;
      done+=(j.results||[]).length;
      fail+=(j.errors||[]).length;

      for(const x of (j.results||[])){
        if(
          x.symbol==='BTCUSDT'||
          x.symbol==='ETHUSDT'||
          x.recommendation==='SHORT'||
          x.recommendation==='LONG'
        ){
          candidates.push(x);
        }
      }

      if(!Number.isInteger(j.next_offset)||j.next_offset<=offset){
        throw Error('스캔 진행 위치 오류');
      }

      offset=j.next_offset;

      status.textContent=
        Math.min(offset,total)+' / '+total+
        '개 분석 · 성공 '+done+' · 실패 '+fail;

      count.textContent=
        '추천 후보 '+candidates.length+'개 · 오류 '+fail+'개';

      showResults();

      majorStatus.textContent=
        '분석 진행 중 · '+Math.min(offset,total)+
        ' / '+total+'개 · 표시 '+candidates.length+'개';

      if(!total)break;
      if(offset<total)await wait(300);

    }while(offset<total);

    showResults();

    majorStatus.textContent=
      '전체 종목 분석 완료 · 표시 '+candidates.length+'개';

    out.textContent=
      '전체 종목 '+done+
      '개 분석 완료. BTC·ETH 및 추천 후보를 위에서 확인하세요.';

  }catch(e){
    status.textContent=
      '스캔 중단 ('+offset+'/'+total+'개): '+e.message;
    if(candidates.length){
      showResults();
      majorStatus.textContent=
        '검색 중단 · 확보한 분석 결과 '+candidates.length+'개';
    }
  }finally{
    running=false;
    btn.disabled=false;
  }
}
