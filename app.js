
let mode='scalp',running=false;

function choose(m){
  if(running)return;
  mode=m;
  for(const id of ['scalp','swing'])
    document.getElementById(id).classList.toggle('active',id===m);
  document.getElementById('frames').textContent=
    m==='scalp'?'15분 · 30분 · 1시간봉':'1시간 · 4시간 · 일봉';
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

// 화면 표시용 번역: 분석 데이터와 매매 판단은 변경하지 않음.
function koText(value){
  if(value==null)return '확인 필요';
  let text=String(value);
  const phrases=[
    [/confirmed downward trendline breakout/gi,'하락 추세선 상향 돌파(거래량 확인)'],
    [/confirmed upward trendline breakdown/gi,'상승 추세선 하향 이탈(거래량 확인)'],
    [/hidden bullish RSI divergence candidate/gi,'히든 상승 RSI 다이버전스 후보'],
    [/hidden bearish RSI divergence candidate/gi,'히든 하락 RSI 다이버전스 후보'],
    [/bullish RSI divergence candidate/gi,'일반 상승 RSI 다이버전스 후보'],
    [/bearish RSI divergence candidate/gi,'일반 하락 RSI 다이버전스 후보'],
    [/EMA bearish alignment/gi,'이동평균선 하락 정렬'],
    [/EMA bullish alignment/gi,'이동평균선 상승 정렬'],
    [/EMA20 below EMA50/gi,'20기간 이동평균선이 50기간선 아래'],
    [/EMA20 above EMA50/gi,'20기간 이동평균선이 50기간선 위'],
    [/MACD histogram falling negative/gi,'MACD 히스토그램 음수 구간에서 하락'],
    [/MACD histogram rising positive/gi,'MACD 히스토그램 양수 구간에서 상승'],
    [/RSI bearish range/gi,'RSI 하락 우세 구간'],
    [/RSI bullish range/gi,'RSI 상승 우세 구간'],
    [/5-wave impulse candidate/gi,'5파 충격파 후보'],
    [/ABC correction candidate/gi,'ABC 조정파 후보'],
    [/Alternating A-B-C swings/gi,'A-B-C 파동이 교대로 진행'],
    [/B retracement within plausible range/gi,'B파 되돌림이 가능한 범위'],
    [/C length within Fibonacci range/gi,'C파 길이가 피보나치 범위 안에 있음'],
    [/rising volume with green candle/gi,'양봉과 함께 거래량 증가'],
    [/rising volume with red candle/gi,'음봉과 함께 거래량 증가'],
    [/Wave 2 does not exceed wave 1 origin/gi,'2파가 1파 시작점을 넘지 않음'],
    [/Wave 3 is not the shortest motive wave/gi,'3파가 추진파 중 가장 짧지 않음'],
    [/Wave 4 does not overlap wave 1 territory/gi,'4파가 1파 가격 영역과 겹치지 않음'],
    [/Fibonacci retracements checked/gi,'피보나치 되돌림 조건 확인'],
    [/bearish divergence/gi,'하락 다이버전스'],
    [/bullish divergence/gi,'상승 다이버전스'],
    [/sideways/gi,'횡보'],
    [/neutral/gi,'중립'],
    [/medium/gi,'보통'],
    [/high/gi,'높음'],
    [/low/gi,'낮음'],
    [/down/gi,'하락'],
    [/up/gi,'상승'],
    [/short/gi,'숏'],
    [/long/gi,'롱']
  ];
  for(const [pattern,replacement] of phrases)text=text.replace(pattern,replacement);
  return text;
}

function showDivergence(root,x){
  const names={
    bullish:'일반 상승',bearish:'일반 하락',
    hidden_bullish:'히든 상승',hidden_bearish:'히든 하락'
  };
  const ds=Array.isArray(x.divergence_details)?x.divergence_details:[];
  root.append(el('h4','','RSI 다이버전스'));
  if(!ds.length){
    root.append(el('p','','최근 확정된 다이버전스 없음'));
  }else{
    for(const d of ds){
      const age=Number.isFinite(Number(d.age_bars))?d.age_bars+'개 봉 전':'시점 확인 필요';
      root.append(el('p','',
        (names[d.type]||koText(d.type))+' 다이버전스 · '+age+
        ' · 가격 변화 '+fmt(d.price_change_pct)+'%'+
        ' · RSI 변화 '+fmt(d.rsi_change)
      ));
    }
  }
  if(x.divergence_warning===true){
    root.append(el('p','','⚠ 우세 방향과 반대되는 다이버전스: 추천 제한'));
  }
}

function showTrendline(root,x){
  root.append(el('h4','','자동 추세선 · 돌파/이탈'));
  const t=x.trendlines;
  if(!t||typeof t!=='object'){
    root.append(el('p','','추세선 분석 데이터 없음'));
    return;
  }
  if(t.support){
    root.append(el('p','','상승 지지 추세선: '+fmt(t.support.current_level)+' USDT'));
  }else{
    root.append(el('p','','상승 지지 추세선: 유효한 선 없음'));
  }
  if(t.resistance){
    root.append(el('p','','하락 저항 추세선: '+fmt(t.resistance.current_level)+' USDT'));
  }else{
    root.append(el('p','','하락 저항 추세선: 유효한 선 없음'));
  }
  const labels={
    BREAKOUT_UP:'하락 추세선 상향 돌파',
    BREAKDOWN_DOWN:'상승 추세선 하향 이탈',
    POSSIBLE_FALSE_BREAK:'가짜 돌파/이탈 가능성'
  };
  const events=Array.isArray(t.events)?t.events:[];
  if(!events.length){
    root.append(el('p','','최근 확정봉에서 돌파·이탈 신호 없음'));
  }
  for(const e of events){
    const v=e.volume_confirmed===true?' · 거래량 확인':
      e.volume_confirmed===false?' · 거래량 미확인':'';
    root.append(el('p','',
      (labels[e.type]||koText(e.type))+
      ' · 기준 '+fmt(e.level)+' USDT'+
      ' · 거래량 '+fmt(e.volume_ratio)+'배'+v
    ));
  }
  if(t.warning===true){
    root.append(el('p','','⚠ 돌파·이탈 후보이나 거래량 확인 부족'));
  }
  if(x.trendline_warning===true){
    root.append(el('p','','⚠ 우세 방향과 반대되는 추세선 돌파/이탈: 추천 제한'));
  }
  root.append(el('p','','추세선은 확정된 두 고점/저점 기반의 계산값이며, 차트에 실제 선을 그린 것은 아닙니다.'));
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
      const confirmed=x.recommendation==='LONG'||x.recommendation==='SHORT';
      const recommendation=confirmed
        ?(x.recommendation==='LONG'?'롱 추천':'숏 추천')
        :('관망 · '+(side==='롱'?'롱 우세':side==='숏'?'숏 우세':'방향 확인 필요'));

      a.append(el('h3','',x.symbol+' · '+recommendation+' · '+score+'점'));
      a.append(el('p','','판정: '+recommendation+' · 거래소: '+x.exchange));
      if(isMajor && !confirmed){
        a.append(el('p','','BTC·ETH 참고 방향이며 정식 매매 추천 조건은 충족하지 않았습니다.'));
      }

      a.append(el('p','',
        (confirmed?'진입 기준 ':'참고 기준가 (관망) ')+fmt(x.entry_reference)+
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
        return tf+' '+koText(v);
      }).join(' · ');

      a.append(el('p','','시간봉 추세: '+(trendText||'데이터 없음')));
      const trendValues=Object.values(trends).map(t=>typeof t==='string'?t:(t?.trend||t?.direction));
      const known=trendValues.length>0 && trendValues.every(t=>t==='UP'||t==='DOWN');
      const allSame=known && trendValues.every(t=>t===trendValues[0]);
      const expected=x.candidate_side==='LONG'?'UP':x.candidate_side==='SHORT'?'DOWN':null;
      const follows=known && expected!=null && trendValues.every(t=>t===expected);
      a.append(el('p','','시간봉끼리 추세 일치: '+(known?(allSame?'예':'아니오'):'확인 필요')));
      a.append(el('p','','우세 방향과 시간봉 일치: '+(known?(follows?'예':'아니오'):'확인 필요')));
      if(known && !follows){
        a.append(el('p','',allSame?'주의: 모든 시간봉이 우세 방향과 반대 · 역추세 후보':'주의: 일부 시간봉이 우세 방향과 다름 · 추세 혼재'));
      }else if(!known){
        a.append(el('p','','주의: 시간봉 추세 자료 확인 필요'));
      }

      showDivergence(a,x);
      showTrendline(a,x);

      const waves=Array.isArray(x.wave_candidates)?x.wave_candidates:[];

      if(waves.length){
        for(const w of waves){
          a.append(el('p','',
            '엘리엇 파동: '+koText(w.pattern)+
            ' · '+koText(w.direction)+
            ' · 신뢰 수준 '+koText(w.confidence)
          ));
          if(w.invalidation_price!=null){
            a.append(el('p','',
              '파동 무효화 기준: '+fmt(w.invalidation_price)
            ));
          }
          if(w.reasons?.length){
            a.append(el('p','','파동 근거: '+w.reasons.map(koText).join(' / ')));
          }
        }
      }else{
        a.append(el('p','','엘리엇 파동: 현재 확인된 후보 없음'));
      }

      if(x.reasons?.length){
        a.append(el('p','','기술적 분석 근거: '+x.reasons.map(koText).join(' / ')));
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
        '표시 종목 '+candidates.length+'개 (BTC·ETH 포함) · 오류 '+fail+'개';

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
