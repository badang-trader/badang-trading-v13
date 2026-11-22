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

    def test_position_calculator_is_connected_to_main_screen(self):
        main = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn('id="positionScenario"', main)
        self.assertIn('id="psCalc"', main)
        self.assertIn('fetch("/api/position-scenario"', main)
        self.assertIn('평균 진입가 ', main)
        self.assertIn('실제 수수료·펀딩비·청산가', main)

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
        self.assertIn("const technicalCandidate=scoredValue>=80?scoredSide", main)
        self.assertIn("롱 기술적 후보 · 진입 조건 별도", main)
        self.assertIn("숏 기술적 후보 · 진입 조건 별도", main)
        self.assertNotIn("const d=finalReady?candidate:", main)

    def test_main_page_plain_language_grouping(self):
        main = (ROOT / "app.py").read_text(encoding="utf-8")
        for phrase in ("현재 판단: 진입 대기", "참고용 계산과 최종 판단의 차이:",
                       "상세 보류 사유", "groupedReasons", "groupedReasons.slice(0,3)", "기술적 점수는 조건 충족도",
                       "최종 계획 미확정", "현재 5파로 확정할 수 없음"):
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
"""
        with tempfile.TemporaryDirectory() as directory:
            js = pathlib.Path(directory) / "fixtures.js"
            js.write_text("const esc=x=>String(x);\n" + helpers + fixture, encoding="utf-8")
            run = subprocess.run(["node", str(js)], capture_output=True, text=True)
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
