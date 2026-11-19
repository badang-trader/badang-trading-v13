import unittest
from badang_okx_history import fetch_okx_closed_history
STEP=900000
class Response:
    def __init__(self,data):self.data=data
    def raise_for_status(self):pass
    def json(self):return {'code':'0','data':self.data}
class Session:
    def __init__(self,pages):self.pages=list(pages);self.calls=[]
    def get(self,url,params,timeout):
        self.calls.append(dict(params))
        return Response(self.pages.pop(0))
def candle(i,confirm='1'):
    return [str(i*STEP),'100','110','90','100','10','0','0',confirm]
class OKXHistoryTests(unittest.TestCase):
    def test_confirmed_only_and_ascending(self):
        s=Session([[candle(2,'0'),candle(1),candle(0)]])
        r=fetch_okx_closed_history('BTC','15m',pages=1,session=s,now_ms=3*STEP)
        self.assertEqual(len(r['candles']),2)
        self.assertEqual(r['candles'][0][0],0)
        self.assertEqual(r['provenance']['source'],'OKX_PUBLIC_HISTORY_API')
    def test_gap_rejected(self):
        s=Session([[candle(3),candle(1)]])
        with self.assertRaisesRegex(ValueError,'missing'):
            fetch_okx_closed_history('ETH','15m',pages=1,session=s,now_ms=4*STEP)
    def test_pagination_older(self):
        s=Session([[candle(3),candle(2)],[candle(1),candle(0)]])
        r=fetch_okx_closed_history('ETH','15m',pages=2,session=s,now_ms=4*STEP)
        self.assertEqual(len(r['candles']),4)
        self.assertEqual(s.calls[1]['after'],str(2*STEP))
    def test_future_close_rejected(self):
        s=Session([[candle(2)]])
        with self.assertRaisesRegex(ValueError,'future'):
            fetch_okx_closed_history('BTC','15m',pages=1,session=s,now_ms=2*STEP)
if __name__=='__main__':unittest.main()
