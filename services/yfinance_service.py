from datetime import datetime

import yfinance as yf


class Yfinance:

    def get_n_days_data(self, days, symbol):
        ticker = yf.Ticker(symbol)
        res = {}
        hist = ticker.history(period=f"{days}d")
        for key, value in hist.items():
            res[str(key).lower()] = value
        res['timestamp'] = list(hist.Close.index)
        response = []
        for i, j, k, l, m in zip(res['timestamp'], res['open'], res['high'], res['low'], res['close']):
            response.append({
                "timestamp": i,
                "open": j,
                "high": k,
                "low": l,
                "close": m
            })

        return response



    def get_1min_day_data(self, symbol, interval="1m", start=None, end=None):
        ticker = yf.Ticker(symbol)
        res = {}
        hist = ticker.history(period=f"{1}d", interval=interval, start=start, end=end)
        for key, value in hist.items():
            res[str(key).lower()] = value
        res['timestamp'] = list(hist.Close.index)
        response = []
        for i, j, k, l, m in zip(res['timestamp'], res['open'], res['high'], res['low'], res['close']):
            response.append({
                "timestamp": i,
                "open": j,
                "high": k,
                "low": l,
                "close": m
            })

        return response

    def get_max_days_data(self, symbol):
        ticker = yf.Ticker(symbol)

        hist = ticker.history(period="max")
        res = {
            "close": hist["Close"],
            "open": hist["Open"],
            "high": hist["High"],
            "Low": hist["Low"],
        }

        return res