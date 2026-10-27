import json
import numpy as np
import pandas as pd

RANGE_BARRAS = {"1d": 1, "5d": 5, "1mo": 21, "3mo": 63, "6mo": 126, "1y": 252, "2y": 504}


class Resp:
    def __init__(self, status=200, payload=None, texto=None, url=""):
        self.status_code = status
        self.text = texto if texto is not None else json.dumps(payload)
        self.url = url
        self.headers = {}
        self.content = self.text.encode()
        self.reason = "OK" if status < 400 else "ERR"

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            from curl_cffi.requests.exceptions import HTTPError
            raise HTTPError(f"HTTP {self.status_code}", response=self)


def payloadChart(simbolo, barras, nome="Petroleo Brasileiro S.A. - Petrobras", moeda="BRL"):
    rng = np.random.default_rng(3)
    datas = pd.bdate_range(end="2026-10-02", periods=barras)
    ts = [int(pd.Timestamp(d.year, d.month, d.day, 13).timestamp()) for d in datas]
    t = np.arange(barras)
    fecha = 30 + 0.02 * t + 4 * np.sin(t / 9) + rng.normal(0, 0.3, barras)
    return {"chart": {"result": [{
        "meta": {
            "currency": moeda, "symbol": simbolo, "exchangeName": "SAO", "fullExchangeName": "Sao Paulo",
            "instrumentType": "EQUITY", "firstTradeDate": 946900800, "regularMarketTime": ts[-1],
            "hasPrePostMarketData": False, "gmtoffset": -10800, "timezone": "BRT",
            "exchangeTimezoneName": "America/Sao_Paulo", "regularMarketPrice": float(fecha[-1]),
            "fiftyTwoWeekHigh": float(fecha.max()), "fiftyTwoWeekLow": float(fecha.min()),
            "regularMarketDayHigh": float(fecha[-1] + 0.4), "regularMarketDayLow": float(fecha[-1] - 0.4),
            "regularMarketVolume": 1000, "longName": nome, "shortName": "PETROBRAS PN N2",
            "chartPreviousClose": float(fecha[-2] if barras > 1 else fecha[-1]), "priceHint": 2,
            "currentTradingPeriod": {
                "pre": {"timezone": "BRT", "start": ts[-1] - 10000, "end": ts[-1] - 100, "gmtoffset": -10800},
                "regular": {"timezone": "BRT", "start": ts[-1], "end": ts[-1] + 25200, "gmtoffset": -10800},
                "post": {"timezone": "BRT", "start": ts[-1] + 25200, "end": ts[-1] + 30000, "gmtoffset": -10800},
            },
            "dataGranularity": "1d", "range": "1y",
            "validRanges": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
        },
        "timestamp": ts,
        "indicators": {
            "quote": [{
                "open": [float(x) for x in fecha - 0.1], "high": [float(x) for x in fecha + 0.4],
                "low": [float(x) for x in fecha - 0.4], "close": [float(x) for x in fecha],
                "volume": [1000 + int(i) for i in range(barras)],
            }],
            "adjclose": [{"adjclose": [float(x) for x in fecha]}],
        },
    }], "error": None}}


def payloadQuoteSummary(simbolo):
    return {"quoteSummary": {"result": [{
        "assetProfile": {"sector": "Energy", "industry": "Oil & Gas Integrated", "country": "Brazil",
                         "website": "https://www.petrobras.com.br",
                         "longBusinessSummary": "Petroleo Brasileiro S.A. explores and produces oil and gas."},
        "quoteType": {"longName": "Petroleo Brasileiro S.A. - Petrobras", "shortName": "PETROBRAS PN N2", "symbol": simbolo},
        "summaryDetail": {"currency": "BRL"},
        "financialData": {"currentPrice": 38.21},
        "defaultKeyStatistics": {},
    }], "error": None}}


def payloadQuote(simbolo):
    return {"quoteResponse": {"result": [{"symbol": simbolo, "regularMarketPrice": 38.21,
                                          "longName": "Petroleo Brasileiro S.A. - Petrobras"}], "error": None}}


class SessaoFalsa:
    def __init__(self, modo="ok"):
        self.modo = modo
        self.chamadas = []
        self.proxies = {}
        self.headers = {}
        self.cookies = type("C", (), {"_cookies": {}, "clear": lambda s: None, "update": lambda s, d: None})()

    def get(self, url, params=None, timeout=None, **kw):
        self.chamadas.append((url, dict(params or {})))
        if self.modo == "429":
            return Resp(429, texto="Too Many Requests", url=url)
        if self.modo == "queda":
            raise ConnectionError("Failed to connect: rede indisponivel")
        if "getcrumb" in url:
            return Resp(200, texto="CRUMB123", url=url)
        if "fc.yahoo.com" in url:
            return Resp(404, texto="", url=url)
        simbolo = url.rstrip("/").split("/")[-1].split("?")[0]
        if "/v8/finance/chart/" in url:
            if simbolo.startswith("ZZZZ"):
                return Resp(404, payload={"chart": {"result": None, "error": {
                    "code": "Not Found", "description": "No data found, symbol may be delisted"}}}, url=url)
            barras = RANGE_BARRAS.get((params or {}).get("range", "1y"), 252)
            return Resp(200, payload=payloadChart(simbolo, barras), url=url)
        if "fundamentals-timeseries" in url:
            return Resp(200, payload={"timeseries": {"result": [], "error": None}}, url=url)
        if "quoteSummary" in url:
            return Resp(200, payload=payloadQuoteSummary(simbolo), url=url)
        if "/v7/finance/quote" in url:
            return Resp(200, payload=payloadQuote((params or {}).get("symbols", simbolo)), url=url)
        return Resp(404, texto="nao simulado: " + url, url=url)

    def post(self, *a, **k):
        return Resp(404, texto="", url="")


def instalar(modo="ok"):
    from yfinance.data import YfData
    dados = YfData()
    sessao = SessaoFalsa(modo)
    dados._session = sessao
    dados._cookie = "cookie-falso"
    dados._crumb = "CRUMB123"
    return sessao
