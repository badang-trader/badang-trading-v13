"""Tests for the actual Bitget adapter imported by app.py."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
import bitget_market_data as market


class ActiveBitgetRetryTests(unittest.TestCase):
    def test_nonfinite_retry_after_uses_bounded_backoff(self):
        for invalid in ("NaN", "Infinity", "-Infinity", "-1", "invalid"):
            with self.subTest(header=invalid):
                limited = Mock(status_code=429, headers={"Retry-After": invalid})
                ok = Mock(status_code=200, headers={})
                ok.json.return_value = {"code": "00000", "data": []}
                with patch.object(market.SESSION, "get", side_effect=[limited, ok]) as getter:
                    with patch.object(market.time, "sleep") as sleep:
                        with patch.object(market.time, "monotonic", return_value=100.0):
                            with patch.object(market, "_LAST_REQUEST", [0.0]):
                                self.assertEqual(market._get("/test", {}), [])
                self.assertEqual(getter.call_count, 2)
                self.assertIn(0.8, [call.args[0] for call in sleep.call_args_list])

    def test_network_io_does_not_hold_global_request_pacing_lock(self):
        observed = []
        ok = Mock(status_code=200, headers={})
        ok.json.return_value = {"code": "00000", "data": ["ok"]}

        def get_without_global_lock(*args, **kwargs):
            acquired = market._REQUEST_LOCK.acquire(blocking=False)
            observed.append(acquired)
            if acquired:
                market._REQUEST_LOCK.release()
            return ok

        with patch.object(market.SESSION, "get", side_effect=get_without_global_lock):
            with patch.object(market.time, "monotonic", return_value=100.0):
                with patch.object(market, "_LAST_REQUEST", [0.0]):
                    self.assertEqual(market._get("/test", {}), ["ok"])
        self.assertEqual(observed, [True])

    def test_rate_limit_sleep_does_not_hold_global_lock(self):
        ok = Mock(status_code=200, headers={})
        ok.json.return_value = {"code": "00000", "data": []}
        lock_available_during_sleep = []

        def check_sleep(_duration):
            acquired = market._REQUEST_LOCK.acquire(blocking=False)
            lock_available_during_sleep.append(acquired)
            if acquired:
                market._REQUEST_LOCK.release()

        with patch.object(market.SESSION, "get", return_value=ok):
            with patch.object(market.time, "sleep", side_effect=check_sleep):
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [100.0]):
                        self.assertEqual(market._get("/test", {}), [])
        self.assertEqual(lock_available_during_sleep, [True])

    def test_sequential_request_slots_are_reserved_in_order(self):
        ok = Mock(status_code=200, headers={})
        ok.json.return_value = {"code": "00000", "data": []}
        delays = []
        with patch.object(market.SESSION, "get", return_value=ok) as getter:
            with patch.object(market.time, "sleep", side_effect=delays.append):
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        for _ in range(3):
                            self.assertEqual(market._get("/test", {}), [])
        self.assertEqual(getter.call_count, 3)
        self.assertEqual(len(delays), 2)
        self.assertAlmostEqual(delays[0], 0.16, places=6)
        self.assertAlmostEqual(delays[1], 0.32, places=6)

    def test_parallel_requests_reserve_distinct_pacing_slots(self):
        ok = Mock(status_code=200, headers={})
        ok.json.return_value = {"code": "00000", "data": []}
        delays = []
        from threading import Lock
        delays_lock = Lock()

        def record_sleep(duration):
            with delays_lock:
                delays.append(duration)

        with patch.object(market.SESSION, "get", return_value=ok) as getter:
            with patch.object(market.time, "sleep", side_effect=record_sleep):
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        with ThreadPoolExecutor(max_workers=8) as pool:
                            results = list(pool.map(lambda _: market._get("/test", {}), range(8)))
        self.assertEqual(results, [[] for _ in range(8)])
        self.assertEqual(getter.call_count, 8)
        self.assertEqual(len(delays), 7)
        for index, delay in enumerate(sorted(delays), start=1):
            self.assertAlmostEqual(delay, index*0.16, places=5)

    def test_transient_503_recovers(self):
        busy = Mock(status_code=503, headers={})
        ok = Mock(status_code=200, headers={})
        ok.json.return_value = {"code": "00000", "data": ["ok"]}
        with patch.object(market.SESSION, "get", side_effect=[busy, ok]) as getter:
            with patch.object(market.time, "sleep") as sleep:
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        self.assertEqual(market._get("/test", {}), ["ok"])
        self.assertEqual(getter.call_count, 2)
        self.assertIn(0.8, [call.args[0] for call in sleep.call_args_list])

    def test_success_code_with_malformed_data_rejected_immediately(self):
        for bad in (None, {}, "not-a-list", 42, True):
            with self.subTest(data=bad):
                ok=Mock(status_code=200,headers={})
                ok.json.return_value={"code":"00000","data":bad}
                with patch.object(market.SESSION,"get",return_value=ok) as getter:
                    with patch.object(market.time,"monotonic",return_value=100.0):
                        with patch.object(market,"_LAST_REQUEST",[0.0]):
                            with self.assertRaisesRegex(ValueError,"응답 데이터"):
                                market._get("/api/v2/mix/market/candles",{})
                self.assertEqual(getter.call_count,1)

    def test_derivative_endpoints_accept_valid_object_data(self):
        for path,data in (
            ("/api/v2/mix/market/open-interest",{"openInterest":"123.5"}),
            ("/api/v2/mix/market/current-fund-rate",{"fundingRate":"0.0001"}),
        ):
            with self.subTest(path=path):
                ok=Mock(status_code=200,headers={})
                ok.json.return_value={"code":"00000","data":data}
                with patch.object(market.SESSION,"get",return_value=ok) as getter:
                    with patch.object(market.time,"monotonic",return_value=100.0):
                        with patch.object(market,"_LAST_REQUEST",[0.0]):
                            self.assertEqual(market._get(path,{}),data)
                self.assertEqual(getter.call_count,1)

    def test_derivative_snapshot_parses_valid_oi_and_funding_objects(self):
        oi={"openInterest":"123.5"}
        funding={"fundingRate":"0.0001"}
        with patch.object(market,"_get",side_effect=[oi,funding]) as getter:
            snapshot=market.bitget_derivatives_snapshot("BTCUSDT",[])
        self.assertEqual(getter.call_count,2)
        self.assertEqual(snapshot["oi_contracts"],123.5)
        self.assertEqual(snapshot["funding_rate"],0.0001)
        self.assertEqual(snapshot["status"],"RESEARCH_ONLY")
        self.assertFalse(snapshot["eligible_for_alert"])
        self.assertFalse(snapshot["complete_hour_cvd"])

    def test_derivative_snapshot_rejects_nonfinite_metrics_without_trade_alert(self):
        with patch.object(market,"_get",
                          side_effect=[{"openInterest":"NaN"},
                                       {"fundingRate":"Infinity"}]):
            snapshot=market.bitget_derivatives_snapshot("BTCUSDT",[])
        self.assertIsNone(snapshot["oi_contracts"])
        self.assertIsNone(snapshot["funding_rate"])
        self.assertEqual(snapshot["errors"]["oi"],"ValueError")
        self.assertEqual(snapshot["errors"]["funding"],"ValueError")
        self.assertFalse(snapshot["eligible_for_alert"])

    def test_candle_endpoints_reject_object_data(self):
        for path in ("/api/v2/mix/market/candles",
                     "/api/v2/mix/market/history-candles"):
            with self.subTest(path=path):
                ok=Mock(status_code=200,headers={})
                ok.json.return_value={"code":"00000","data":{"bad":"shape"}}
                with patch.object(market.SESSION,"get",return_value=ok):
                    with patch.object(market.time,"monotonic",return_value=100.0):
                        with patch.object(market,"_LAST_REQUEST",[0.0]):
                            with self.assertRaisesRegex(ValueError,"캔들 배열"):
                                market._get(path,{})

    def test_transport_timeout_recovers_without_stale_fallback(self):
        timeout=market.requests.exceptions.Timeout("socket timed out")
        ok=Mock(status_code=200,headers={})
        ok.json.return_value={"code":"00000","data":["fresh"]}
        with patch.object(market.SESSION,"get",side_effect=[timeout,ok]) as getter:
            with patch.object(market.time,"sleep") as sleep:
                with patch.object(market.time,"monotonic",return_value=100.0):
                    with patch.object(market,"_LAST_REQUEST",[0.0]):
                        self.assertEqual(market._get("/test",{}),["fresh"])
        self.assertEqual(getter.call_count,2)
        self.assertIn(0.8,[call.args[0] for call in sleep.call_args_list])

    def test_transport_timeout_exhaustion_propagates_failure(self):
        timeout=market.requests.exceptions.Timeout("socket timed out")
        with patch.object(market.SESSION,"get",side_effect=timeout) as getter:
            with patch.object(market.time,"sleep") as sleep:
                with patch.object(market.time,"monotonic",return_value=100.0):
                    with patch.object(market,"_LAST_REQUEST",[0.0]):
                        with self.assertRaises(market.requests.exceptions.Timeout):
                            market._get("/test",{})
        self.assertEqual(getter.call_count,3)
        delays=[call.args[0] for call in sleep.call_args_list]
        self.assertIn(0.8,delays)
        self.assertIn(1.6,delays)
        self.assertNotIn(2.4,delays)

    def test_http_408_timeout_recovers_on_second_attempt(self):
        timeout=Mock(status_code=408,headers={})
        ok=Mock(status_code=200,headers={})
        ok.json.return_value={"code":"00000","data":["fresh"]}
        with patch.object(market.SESSION,"get",side_effect=[timeout,ok]) as getter:
            with patch.object(market.time,"sleep") as sleep:
                with patch.object(market.time,"monotonic",return_value=100.0):
                    with patch.object(market,"_LAST_REQUEST",[0.0]):
                        self.assertEqual(market._get("/test",{}),["fresh"])
        self.assertEqual(getter.call_count,2)
        self.assertIn(0.8,[call.args[0] for call in sleep.call_args_list])

    def test_http_408_exhaustion_does_not_return_candles(self):
        timeout=Mock(status_code=408,headers={})
        with patch.object(market.SESSION,"get",return_value=timeout) as getter:
            with patch.object(market.time,"sleep") as sleep:
                with patch.object(market.time,"monotonic",return_value=100.0):
                    with patch.object(market,"_LAST_REQUEST",[0.0]):
                        with self.assertRaisesRegex(ValueError,"HTTP 408"):
                            market._get("/test",{})
        self.assertEqual(getter.call_count,3)
        delays=[call.args[0] for call in sleep.call_args_list]
        self.assertIn(0.8,delays)
        self.assertIn(1.6,delays)
        self.assertNotIn(2.4,delays)

    def test_persistent_503_fails_after_three_attempts(self):
        busy = Mock(status_code=503, headers={})
        busy.raise_for_status.side_effect = RuntimeError("HTTP 503")
        with patch.object(market.SESSION, "get", return_value=busy) as getter:
            with patch.object(market.time, "sleep") as sleep:
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        with self.assertRaisesRegex(RuntimeError, "503"):
                            market._get("/test", {})
        self.assertEqual(getter.call_count, 3)
        self.assertIn(0.8, [call.args[0] for call in sleep.call_args_list])
        self.assertIn(1.6, [call.args[0] for call in sleep.call_args_list])

    def test_persistent_503_without_raise_for_status_still_fails_closed(self):
        busy = Mock(status_code=503, headers={})
        with patch.object(market.SESSION, "get", return_value=busy) as getter:
            with patch.object(market.time, "sleep") as sleep:
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        with self.assertRaisesRegex(ValueError, "HTTP 503"):
                            market._get("/test", {})
        self.assertEqual(getter.call_count, 3)
        retry_delays = [call.args[0] for call in sleep.call_args_list]
        self.assertIn(0.8, retry_delays)
        self.assertIn(1.6, retry_delays)
        self.assertNotIn(2.4, retry_delays)

    def test_http_429_exhaustion_does_not_return_stale_data(self):
        limited = Mock(status_code=429, headers={"Retry-After": "0"})
        with patch.object(market.SESSION, "get", return_value=limited) as getter:
            with patch.object(market.time, "sleep"):
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        with self.assertRaisesRegex(ValueError, "HTTP 429"):
                            market._get("/test", {})
        self.assertEqual(getter.call_count, 3)

    def test_bitget_body_rate_limit_retries_then_recovers(self):
        limited = Mock(status_code=200, headers={})
        limited.json.return_value = {"code": "40015", "msg": "rate limit"}
        ok = Mock(status_code=200, headers={})
        ok.json.return_value = {"code": "00000", "data": ["fresh"]}
        with patch.object(market.SESSION, "get", side_effect=[limited, ok]) as getter:
            with patch.object(market.time, "sleep") as sleep:
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        self.assertEqual(market._get("/test", {}), ["fresh"])
        self.assertEqual(getter.call_count, 2)
        self.assertIn(0.8, [call.args[0] for call in sleep.call_args_list])

    def test_valid_retry_after_is_capped(self):
        limited = Mock(status_code=429, headers={"Retry-After": "100"})
        ok = Mock(status_code=200, headers={})
        ok.json.return_value = {"code": "00000", "data": []}
        with patch.object(market.SESSION, "get", side_effect=[limited, ok]):
            with patch.object(market.time, "sleep") as sleep:
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        self.assertEqual(market._get("/test", {}), [])
        self.assertIn(4.0, [call.args[0] for call in sleep.call_args_list])


class ActiveBitgetTimestampTests(unittest.TestCase):
    def test_invalid_exchange_timestamp_rejected_before_pagination(self):
        for stamp in ("NaN", "Infinity", "-1", "900000.5", None, True, False):
            with self.subTest(timestamp=stamp):
                page = [[stamp, "100", "102", "98", "100", "10"]]
                with patch.object(market, "_get", return_value=page) as getter:
                    with self.assertRaisesRegex(ValueError, "캔들 시각"):
                        market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
                self.assertEqual(getter.call_count, 1)

class ActiveBitgetOHLCVTests(unittest.TestCase):
    STEP = 900_000
    BASE = 1_800_000_000_000

    def test_valid_initial_ohlcv_proceeds_to_history_lookup(self):
        page = [[str(self.BASE+220*self.STEP), "100", "102", "98", "100", "10"]]
        with patch.object(market, "_get", side_effect=[page, []]) as getter:
            with patch.object(market.time, "time",
                              return_value=(self.BASE+222*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError, "연속 확정봉 부족"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 2)

    def test_malformed_ohlcv_rejected_before_history_requests(self):
        invalid_rows = (
            ["100", "NaN", "98", "100", "10"],
            ["100", "102", "98", "100", "-1"],
            ["100", "99", "98", "100", "10"],
            ["100", "102", "101", "100", "10"],
            ["100", "Infinity", "98", "100", "10"],
            ["100", "102", "98", "100", "not-a-number"],
        )
        for values in invalid_rows:
            with self.subTest(values=values):
                page = [[str(self.BASE+220*self.STEP), *values]]
                with patch.object(market, "_get", return_value=page) as getter:
                    with patch.object(market.time, "time",
                                      return_value=(self.BASE+230*self.STEP)/1000):
                        with self.assertRaisesRegex(ValueError, "OHLCV"):
                            market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
                self.assertEqual(getter.call_count, 1)


class ActiveBitgetContinuityTests(unittest.TestCase):
    STEP = 900_000
    BASE = 1_800_000_000_000  # realistic epoch-ms, aligned to 15m

    def rows(self):
        return [[str((self.BASE+i*self.STEP)), "100", "102", "98", "100", "10"]
                for i in range(10, 230)]

    def test_future_bitget_bar_cannot_reach_closed_candle_analysis(self):
        rows = self.rows() + [[str((self.BASE+232*self.STEP)), "100", "102", "98", "100", "10"]]
        with patch.object(market, "_get", return_value=rows):
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError, "미래 시각"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])

    def test_future_single_row_rejected_without_history_requests(self):
        future = [[str(self.BASE+232*self.STEP), "100", "102", "98", "100", "10"]]
        with patch.object(market, "_get", return_value=future) as getter:
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError, "미래 시각"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 1)

    def test_misaligned_single_row_rejected_without_history_requests(self):
        misaligned = [[str(self.BASE+220*self.STEP+1), "100", "102", "98", "100", "10"]]
        with patch.object(market, "_get", return_value=misaligned) as getter:
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError, "시각 정렬"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 1)

    def test_two_unfinished_bars_cannot_reach_legacy_analysis(self):
        rows = self.rows() + [[str((self.BASE+230*self.STEP)), "100", "102", "98", "100", "10"],
                              [str((self.BASE+232*self.STEP)), "100", "102", "98", "100", "10"]]
        with patch.object(market, "_get", return_value=rows):
            with patch.object(market.time, "time", return_value=(self.BASE+231*self.STEP)/1000):
                # 230 is closed, 231 is current, 232 is future: reject future.
                with self.assertRaisesRegex(ValueError, "미래 시각"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])

    def test_220_recent_contiguous_bars_return_with_disposable_marker(self):
        with patch.object(market, "_get", return_value=self.rows()) as getter:
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                result = market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 1)
        self.assertEqual(len(result["candles"][:-1]), 220)
        self.assertEqual(int(result["candles"][-1][0]), (self.BASE+230*self.STEP))

    def test_exactly_205_closed_candles_are_accepted(self):
        # The engine's minimum must be inclusive; no interpolation is allowed.
        rows=self.rows()[-205:]
        with patch.object(market,"_get",return_value=rows) as getter:
            with patch.object(market.time,"time",
                              return_value=(self.BASE+230*self.STEP)/1000):
                result=market.fastest_candles("BTCUSDT","15m",exchanges=["bitget"])
        # Exactly 205 confirmed candles are sufficient: avoid unnecessary
        # pagination that increases Bitget rate-limit exposure.
        self.assertEqual(getter.call_count,1)
        self.assertTrue(getter.call_args_list[0].args[0].endswith("/candles"))
        self.assertEqual(len(result["candles"][:-1]),205)
        self.assertEqual(int(result["candles"][-1][0]),self.BASE+230*self.STEP)

    def test_205_closed_plus_live_candle_excludes_live_data(self):
        rows=self.rows()[-205:]
        forming=[str(self.BASE+230*self.STEP),"100","102","98","101","11"]
        with patch.object(market,"_get",return_value=rows+[forming]) as getter:
            with patch.object(market.time,"time",
                              return_value=(self.BASE+230*self.STEP)/1000):
                result=market.fastest_candles("BTCUSDT","15m",exchanges=["bitget"])
        # Exactly 205 confirmed candles are sufficient: avoid unnecessary
        # pagination that increases Bitget rate-limit exposure.
        self.assertEqual(getter.call_count,1)
        self.assertTrue(getter.call_args_list[0].args[0].endswith("/candles"))
        self.assertEqual(len(result["candles"][:-1]),205)
        self.assertEqual(result["candles"][-1][4],"101.0")
        self.assertEqual(result["candles"][-2][4],"100.0")

    def test_exactly_205_closed_bars_with_one_gap_are_repaired(self):
        # Total count alone is insufficient: all 205 bars must be consecutive.
        full=self.rows()[-205:]
        missing_ts=self.BASE+220*self.STEP
        broken=[r for r in full if int(r[0])!=missing_ts]
        replacement=[r for r in full if int(r[0])==missing_ts]
        with patch.object(market,"_get",side_effect=[broken,[],replacement]) as getter:
            with patch.object(market.time,"time",
                              return_value=(self.BASE+230*self.STEP)/1000):
                result=market.fastest_candles("BTCUSDT","15m",exchanges=["bitget"])
        self.assertEqual(getter.call_count,3)
        self.assertEqual(len(result["candles"][:-1]),205)
        self.assertIn(str(missing_ts),[r[0] for r in result["candles"][:-1]])

    def test_205_count_with_recent_gap_cannot_pass_without_repair(self):
        # 205 total closed bars is not equivalent to 205 contiguous bars.
        full=self.rows()[-206:]
        missing_ts=self.BASE+220*self.STEP
        broken=[r for r in full if int(r[0])!=missing_ts]
        self.assertEqual(len(broken),205)
        with patch.object(market,"_get",side_effect=[broken,[]]) as getter:
            with patch.object(market.time,"time",
                              return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError,"연속 확정봉 부족"):
                    market.fastest_candles("BTCUSDT","15m",exchanges=["bitget"])
        self.assertEqual(getter.call_count,2)
        self.assertTrue(getter.call_args_list[1].args[0].endswith("/history-candles"))
        self.assertIn("startTime",getter.call_args_list[1].args[1])

    def test_204_closed_candles_fail_without_invented_history(self):
        rows=self.rows()[-204:]
        with patch.object(market,"_get",side_effect=[rows,[]]) as getter:
            with patch.object(market.time,"time",
                              return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError,"연속 확정봉 부족"):
                    market.fastest_candles("BTCUSDT","15m",exchanges=["bitget"])
        self.assertEqual(getter.call_count,2)

    def test_missing_recent_bar_cannot_be_fabricated(self):
        rows = [r for r in self.rows() if int(r[0]) != (self.BASE+220*self.STEP)]
        with patch.object(market, "_get", side_effect=[rows, []]) as getter:
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError, "연속 확정봉 부족"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 2)
        self.assertTrue(getter.call_args_list[1].args[0].endswith("/history-candles"))
        self.assertIn("startTime", getter.call_args_list[1].args[1])

    def test_oversized_exchange_page_is_rejected_before_pagination(self):
        oversized = [[str((self.BASE+i*self.STEP)), "100", "102", "98", "100", "10"]
                     for i in range(1001)]
        with patch.object(market, "_get", return_value=oversized) as getter:
            with self.assertRaisesRegex(ValueError, "페이지 크기 비정상"):
                market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 1)

    def test_non_numeric_ohlcv_is_rejected(self):
        rows = self.rows()
        rows[0][4] = "not-a-price"
        with patch.object(market, "_get", return_value=rows):
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError, "OHLCV"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])

    def test_gap_repair_invalid_timestamp_is_rejected(self):
        rows=[r for r in self.rows()
              if int(r[0])!=(self.BASE+220*self.STEP)]
        invalid=[[True,"100","102","98","100","10"]]
        with patch.object(market,"_get",side_effect=[rows,invalid]) as getter:
            with patch.object(market.time,"time",
                              return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError,"캔들 시각"):
                    market.fastest_candles("BTCUSDT","15m",exchanges=["bitget"])
        self.assertEqual(getter.call_count,2)

    def test_gap_repair_conflicting_duplicate_is_rejected(self):
        rows=[r for r in self.rows()
              if int(r[0])!=(self.BASE+220*self.STEP)]
        conflicting=list(rows[-1])
        conflicting[4]="101"
        with patch.object(market,"_get",side_effect=[rows,[conflicting]]) as getter:
            with patch.object(market.time,"time",
                              return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError,"Conflicting"):
                    market.fastest_candles("BTCUSDT","15m",exchanges=["bitget"])
        self.assertEqual(getter.call_count,2)

    def test_gap_repair_rate_limit_error_is_not_hidden(self):
        rows=[r for r in self.rows()
              if int(r[0])!=(self.BASE+220*self.STEP)]
        with patch.object(market,"_get",
                          side_effect=[rows,ValueError("Bitget 요청 제한(HTTP 429)")]) as getter:
            with patch.object(market.time,"time",
                              return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError,"HTTP 429"):
                    market.fastest_candles("BTCUSDT","15m",exchanges=["bitget"])
        self.assertEqual(getter.call_count,2)

    def test_gap_repair_transport_failure_cannot_fabricate_candle(self):
        rows=[r for r in self.rows()
              if int(r[0])!=(self.BASE+220*self.STEP)]
        timeout=market.requests.exceptions.Timeout("network unavailable")
        with patch.object(market,"_get",side_effect=[rows,timeout]) as getter:
            with patch.object(market.time,"time",
                              return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError,"연속 확정봉 부족"):
                    market.fastest_candles("BTCUSDT","15m",exchanges=["bitget"])
        self.assertEqual(getter.call_count,2)

    def test_non_list_gap_repair_response_is_rejected(self):
        rows = [r for r in self.rows() if int(r[0]) != (self.BASE+220*self.STEP)]
        with patch.object(market, "_get", side_effect=[rows, {"bad": "shape"}]):
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError, "gap repair response"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])

    def test_oversized_history_page_rejected(self):
        initial = self.rows()[:100]
        oversized = [[str((self.BASE+i*self.STEP)), "100", "102", "98", "100", "10"]
                     for i in range(1001)]
        with patch.object(market, "_get", side_effect=[initial, oversized]) as getter:
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError, "페이지 크기 비정상"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 2)

    def test_future_candle_is_rejected(self):
        rows = self.rows()
        rows.append([str((self.BASE+232*self.STEP)), "100", "102", "98", "100", "10"])
        with patch.object(market, "_get", return_value=rows):
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError, "미래 시각"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])

    def test_conflicting_duplicate_candle_is_rejected(self):
        rows = self.rows()
        conflict = list(rows[-1])
        conflict[4] = "101"
        rows.append(conflict)
        with patch.object(market, "_get", return_value=rows) as getter:
            # Keep the synthetic candles in the past so duplicate validation,
            # rather than the independent future-candle guard, is exercised.
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError, "Conflicting"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 1)

    def test_repeated_scans_do_not_retain_candle_cache(self):
        with patch.object(market, "_get", return_value=self.rows()) as getter:
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                first = market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
                second = market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 2)
        self.assertEqual(first["candles"], second["candles"])
        self.assertIsNot(first["candles"], second["candles"])

    def test_duplicate_identical_timestamp_is_safe(self):
        rows = self.rows()
        rows.append(list(rows[-1]))
        with patch.object(market, "_get", return_value=rows):
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                result = market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(len(result["candles"][:-1]), 220)

    def test_bad_price_cannot_become_trade_signal(self):
        for bad in ("NaN", "Infinity", "-1", "0"):
            with self.subTest(value=bad):
                rows = self.rows()
                rows[-1][4] = bad
                with patch.object(market, "_get", return_value=rows):
                    with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                        with self.assertRaisesRegex(ValueError, "OHLCV"):
                            market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])

    def test_unsupported_exchange_rejected_before_network(self):
        with patch.object(market, "_get") as getter:
            with self.assertRaisesRegex(ValueError, "Bitget-only"):
                market.fastest_candles("BTCUSDT", "15m", exchanges=["okx"])
        getter.assert_not_called()

    def test_stale_history_rejected_even_when_contiguous(self):
        rows = self.rows()
        with patch.object(market, "_get", return_value=rows):
            with patch.object(market.time, "time", return_value=(self.BASE+234*self.STEP)/1000):
                with self.assertRaisesRegex(ValueError, "최근 확정봉 지연"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])

    def test_real_history_page_repairs_missing_bar(self):
        rows = [r for r in self.rows() if int(r[0]) != (self.BASE+220*self.STEP)]
        repaired = [r for r in self.rows() if int(r[0]) == (self.BASE+220*self.STEP)]
        with patch.object(market, "_get", side_effect=[rows, repaired]) as getter:
            with patch.object(market.time, "time", return_value=(self.BASE+230*self.STEP)/1000):
                result = market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 2)
        self.assertTrue(getter.call_args_list[1].args[0].endswith("/history-candles"))
        params=getter.call_args_list[1].args[1]
        self.assertEqual(int(params["startTime"]),self.BASE+218*self.STEP)
        self.assertEqual(int(params["endTime"]),self.BASE+222*self.STEP)
        self.assertEqual(len(result["candles"][:-1]), 220)
        self.assertIn(str((self.BASE+220*self.STEP)), [r[0] for r in result["candles"][:-1]])

if __name__ == "__main__":
    unittest.main()
