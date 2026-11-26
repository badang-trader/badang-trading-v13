"""Dashboard UI regression checks: no exchange access or orders."""
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "badang_dashboard.py").read_text(encoding="utf-8")

class DashboardClarityTests(unittest.TestCase):
    def test_flask_main_page_and_dashboard_routes(self):
        from app import app
        client = app.test_client()
        home = client.get('/')
        self.assertEqual(home.status_code, 200)
        self.assertIn(b'href="/dashboard"', home.data)
        dashboard = client.get('/dashboard')
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn('바당의 쉬운 판단'.encode('utf-8'), dashboard.data)
        self.assertIn(b'type="search" enterkeyhint="search"', dashboard.data)

    def test_position_calculator_is_removed(self):
        from app import app
        main = (ROOT / 'app.py').read_text(encoding='utf-8')
        for marker in ('positionScenario', 'psCalc', '/api/position-scenario', 'psAddQty'):
            self.assertNotIn(marker, main)
        client = app.test_client()
        self.assertEqual(client.post('/api/position-scenario', json={}).status_code, 404)

    def test_scan_exposes_separate_technical_candidate_feed(self):
        main = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn('technical_candidates=sorted([', main)
        self.assertIn("'probability_status': 'NOT_BACKTEST_VALIDATED'", main)
        self.assertIn("'timeframe_data_audit': item.get('timeframe_data_audit_49')", main)
        self.assertIn("item['technical_score']>=80", main)
        self.assertIn("'final_state': (item.get('decision_427') or {}).get('state')", main)
        self.assertIn("const d=technicalCandidate!==", main)

    def test_technical_candidates_are_not_hidden_by_final_gate(self):
        main = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn("const technicalCandidate=x.technical_candidate===true?scoredSide", main)
        self.assertIn("롱 기술적 후보 · 진입 조건 별도", main)
        self.assertIn("숏 기술적 후보 · 진입 조건 별도", main)
        self.assertNotIn("const d=finalReady?candidate:", main)

    def test_main_page_plain_language_grouping(self):
        main = (ROOT / "app.py").read_text(encoding="utf-8")
        for phrase in ("현재 판단: 진입 대기", "참고용 계산과 최종 판단의 차이:",
                       "상세 보류 사유", "groupedReasons", "groupedReasons.slice(0,3)", "기술적 점수는 조건 충족도",
                       "기술적 참고 가격", "현재 5파로 확정할 수 없음"):
            self.assertIn(phrase, main)

    def test_main_page_links_to_read_only_dashboard(self):
        main = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('href="/dashboard"', main)
        self.assertIn("읽기 전용 화면입니다", main)
        self.assertIn("app.register_blueprint(badang_dashboard)", main)

    def test_structured_divergence_only(self):
        self.assertIn("Array.isArray(signals)", SOURCE)
        self.assertIn("z.status==='RECENT_UNCONFIRMED_REVERSAL'", SOURCE)
        self.assertIn("z.pivot_confirmed===true", SOURCE)
        self.assertIn("z.confirmed===false", SOURCE)
        self.assertNotIn("JSON.stringify(val||{}).toLowerCase()", SOURCE)

    def test_user_explanations_and_no_orders(self):
        for phrase in ("바당의 쉬운 판단", "진입 대기", "반전 미확정", "혼재", "손절 기준"):
            self.assertIn(phrase, SOURCE)
        self.assertIn("자동매매 아님", SOURCE)

    def test_explanations_with_fixture_data(self):
        if not shutil.which("node"):
            self.skipTest("Node.js not available")
        script = re.findall(r"<script>(.*?)</script>", SOURCE, flags=re.S)[0]
        # Evaluate only pure helpers, without DOM or exchange calls.
        helpers = script[script.index("const plainSide="):script.index("function render(x)")]
        fixture = r"""
const fmt=(n,d=4)=>Number(n).toFixed(d);
const valid={type:'regular_bullish',status:'RECENT_UNCONFIRMED_REVERSAL',pivot_confirmed:true,confirmed:false};
const bad={...valid,status:'INVALIDATED'};
const assert=(ok,msg)=>{if(!ok)throw Error(msg)};
assert(divergenceText({divergence_explained_46:{'15m':[bad]}}).includes('없음'),'invalidated signal shown');
assert(divergenceText({divergence_explained_46:{'15m':[valid]}}).includes('상승 단서'),'valid bullish missing');
assert(divergenceText({divergence_explained_46:{'15m':[valid,{...valid,type:'regular_bearish'}]}}).includes('혼재'),'mixed signal missing');
assert(waveText({wave_by_timeframe_32:{'1H':{status:'AVAILABLE',candidates:[{structure_status:'TIME_ORDER_VALID',age_class:'RECENT',completion:'UNCONFIRMED',direction:'down'}]}}}).includes('과거 전환점'),'wave caveat missing');
assert(riskText({recommendation:'LONG',entry_reference:100,stop_loss:95,take_profit_1:110}).includes('1:2.00'),'rr calculation wrong');
assert(riskText({recommendation:'LONG',entry_reference:100,stop_loss:105,take_profit_1:110}).includes('재검증'),'invalid stop accepted');
assert(riskText({recommendation:'WAIT',entry_reference:100,stop_loss:95,take_profit_1:110}).includes('검증 불가'),'WAIT should not show rr');
assert(riskText({recommendation:'LONG',entry_reference:100,stop_loss:null,take_profit_1:110}).includes('검증 불가'),'null stop must not be zero');
assert(riskText({recommendation:'SHORT',entry_reference:100,stop_loss:105,take_profit_1:90}).includes('1:2.00'),'short rr calculation wrong');
assert(entryReason({price_action_45:{side:'WAIT',reason:'돌파 미확인'},entry_blockers:['기타']})==='돌파 미확인','actual wait reason missing');
const checkReasons=entryCheckDetails({signal_precision_418:{checks:{
  timeframe_alignment:{passed:false,evidence:{expected:'UP',off_trend:{'30m':'DOWN','1H':'DOWN'}}},
  risk_distance:{passed:false,evidence:{observed_pct:2.4388,minimum_pct:0.04,maximum_pct:2}}
}}});
assert(checkReasons[0].includes('30m 하락, 1H 하락'),'conflicting timeframe evidence missing');
assert(checkReasons[1].includes('2.4388')&&checkReasons[1].includes('0.0400~2.0000'),'risk distance evidence missing');
assert(entryCheckDetails({signal_precision_418:{checks:{risk_distance:{passed:false,applicable:false}}}}).length===0,'unassessed risk shown as failed');
assert(flowStatus({reversal_tracking_514:{status:'DATABASE_NOT_CONFIGURED'}}).includes('현재 조회만 계산'),'missing storage shown as connected');
const waveReport=renderResearch({symbol:'BTCUSDT',research_timeframes_47:['15m'],
  structure_427:{'15m':{wave:{alternatives:[
    {direction:'UP',wave:3,active_leg_invalidation:95,structural_invalidation:90,
     future_targets:[{price:122,ratio:1.618}]},
    {direction:'DOWN',wave:5,invalidation:110,structural_invalidation:115}
  ]},historical_wave_shapes:[{pattern:'ABC_FLAT_GEOMETRY',geometry_evidence:{
    variant:'RUNNING',b_retrace:1.10,c_extension:1,expected_subdivision:[3,3,5]
  },lower_pivot_evidence:{status:'PIVOT_COUNTS_ONLY',timeframe:'5m',leg_turn_counts:[3,null,5],
    expected_count_comparison:'INCOMPLETE'}}]}},
  reversal_path_514:{paths:[{direction:'DOWN',zones:[{
    low:90,high:92,expected_score:30,invalidation:90,near_reversal_target:99,
    components:{structure:20,candle:10,divergence:0},
    reasons:['같은 시간봉에 상승·하락 반전 단서가 함께 있어 점수 보류']
  }]}]}
});
assert(waveReport.includes('상승 3파 후보')&&waveReport.includes('하락 5파 후보'),'wave alternatives missing');
assert(waveReport.includes('현재 파동 무효화 95.00000000')&&waveReport.includes('구조 무효화 90.00000000'),'invalidation levels mixed');
assert(waveReport.includes('1.618배')&&waveReport.includes('ABC 플랫 러닝형')&&waveReport.includes('내부 파동 미검증'),'wave evidence missing');
assert(waveReport.includes('B 되돌림 110.0%')&&waveReport.includes('3-3-5'),'ABC evidence missing');
assert(waveReport.includes('5m 구간별 스윙 3 / 미확인 / 5'),'lower-frame observations missing');
assert(waveReport.includes('일부 스윙 수 미확인'),'incomplete ABC evidence shown as verified');
assert(waveReport.includes('지지·저항 구조 20점')&&waveReport.includes('캔들 반응 10점'),'score breakdown missing');
assert(waveReport.includes('점수 보류')&&!waveReport.includes('다이버전스 0점'),'conflicting evidence presentation wrong');
assert(waveReport.includes('반전 근거 30점'),'stateless reversal score missing');
const matching=[{timeframe:'15m',indicator:'RSI'}];
const opposite=[{timeframe:'15m',indicator:'MACD'}];
const applied=zoneScoreText({components:{divergence:10},
  divergence_evidence:{status:'APPLIED',points:10,matches:matching,conflicts:[]}});
assert(applied.some(line=>line.includes('10점 가산 · 15m RSI')),'source for awarded points missing');
const withheld=zoneScoreText({components:{divergence:0},divergence_evidence:{
  status:'HELD_CONFLICT',points:0,matches:matching,conflicts:opposite}});
assert(withheld.some(line=>line.includes('점수 보류')&&line.includes('15m RSI')&&line.includes('15m MACD')),
  'source for conflict missing');
const lower={status:'PIVOT_COUNTS_ONLY',timeframe:'15m',leg_turn_counts:[3,3,1,3,1]};
assert(historicalShapeText({pattern:'CONTRACTING_DIAGONAL_GEOMETRY',lower_pivot_evidence:lower}).includes('1파 3 / 2파 3 / 3파 1'),'diagonal labels missing');
assert(historicalShapeText({pattern:'WXY_DOUBLE_ZIGZAG_GEOMETRY',lower_pivot_evidence:lower}).includes('W의 C 1 / 첫 X 3 / Y의 A 1'),'WXY labels missing');
const flow=flowStatus({structure_427:{'1H':{wave:{alternatives:[{flow_validation:{oi_legs:[{status:'ENDPOINTS_AVAILABLE'},{status:'INSUFFICIENT_HISTORY'}]}}]}}}});
assert(flow.includes('1/2구간')&&flow.includes('CVD 미검증'),'partial OI coverage mistaken for CVD');
"""
        with tempfile.TemporaryDirectory() as directory:
            js = pathlib.Path(directory) / "fixtures.js"
            js.write_text("const esc=x=>String(x);\n" + helpers + fixture, encoding="utf-8")
            run = subprocess.run(["node", str(js)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)

    def test_body_timeout_restores_scan_controls(self):
        if not shutil.which("node"):
            self.skipTest("Node.js not available")
        script = re.findall(r"<script>(.*?)</script>", SOURCE, flags=re.S)[0]
        fixture = r"""
const nodes=new Map();
const document={getElementById(id){
  if(!nodes.has(id))nodes.set(id,{disabled:false,value:'scalp',addEventListener(){},replaceChildren(){this.innerHTML=''}});
  return nodes.get(id);
}};
let timeout;
const setTimeout=fn=>{timeout=fn;return 1};
const clearTimeout=()=>{timeout=null};
let readBody;
let result=null;
let requestedUrl;
const fetch=async (url, {signal})=>({ok:true,json(){
  requestedUrl=url;
  if(result)return Promise.resolve(result);
  return new Promise((resolve,reject)=>{
    signal.addEventListener('abort',()=>reject(new Error('aborted')));
    readBody=true;
  });
}});
"""
        checks = r"""
(async()=>{
  const pending=load();
  await Promise.resolve();
  if(!readBody || !timeout || !$('mode').disabled)throw Error('body timeout or mode lock missing');
  timeout();
  await pending;
  if($('load').disabled || $('mode').disabled || !$('status').innerHTML.includes('대기 시간')){
    throw Error('timeout did not restore scan controls');
  }
  result={results:[{symbol:'BTCUSDT',technical_score:66}],technical_candidates:[],next_offset:1,total:2};
  await load(false,'BTCUSDT');
  if(!$('cards').innerHTML.includes('80점 이상') || !$('research').innerHTML.includes('BTCUSDT · 파동과 반전 구간')){
    throw Error('manual research section must remain visible below the candidate score threshold');
  }
  if(!requestedUrl.includes('symbol=BTCUSDT') || !$('next').disabled){
    throw Error('individual lookup must use the requested symbol and disable pagination');
  }
})().catch(error=>{console.error(error);process.exitCode=1});
"""
        with tempfile.TemporaryDirectory() as directory:
            js = pathlib.Path(directory) / "fixtures.js"
            js.write_text(fixture + script + checks, encoding="utf-8")
            run = subprocess.run(["node", str(js)], capture_output=True, text=True, timeout=5)
            self.assertEqual(run.returncode, 0, run.stderr)

    def test_embedded_javascript_syntax(self):
        if not shutil.which("node"):
            self.skipTest("Node.js not available")
        scripts = re.findall(r"<script>(.*?)</script>", SOURCE, flags=re.S)
        self.assertEqual(len(scripts), 1)
        with tempfile.TemporaryDirectory() as directory:
            js = pathlib.Path(directory) / "dashboard.js"
            js.write_text(scripts[0], encoding="utf-8")
            run = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)

if __name__ == "__main__":
    unittest.main()
