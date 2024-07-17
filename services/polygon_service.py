import json
from polygon import RESTClient
from dotenv import dotenv_values
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()


class PolygonService:
    def __init__(self, api_key=None):
        if not api_key:
            self.api_key = os.getenv("POLYGON_API_KEY")
        else:
            self.api_key = api_key
        self.client = RESTClient(self.api_key)


    def get_n_day_data(self, days, ticker):
        from_date = datetime.now() - timedelta(days)
        agg = self.client.get_aggs(ticker, 1, "day", from_date, datetime.now())
        response = []
        for i in agg:
            response.append({
                "timestamp": i.timestamp,
                "open": i.open,
                "high": i.high,
                "low": i.low,
                "close": i.close
            })
        return response

    def get_1min_day_data(self, ticker, interval="minute", from_date=datetime.now(), limit=None):
        agg = self.client.get_aggs(ticker, 1, interval, str(from_date.date()), str(datetime.now().date()), limit=limit,
                                   sort="desc")
        response = []
        for i in agg:
            response.append({
                "timestamp": i.timestamp,
                "open": i.open,
                "high": i.high,
                "low": i.low,
                "close": i.close
            })
        return sorted(response, key=lambda x: x.timestamp)


    def get_1_day_live_data(self, ticker):
        agg = self.client.get_last_quote(ticker)
        response = []
        response.append({
            "timestamp": agg.timestamp,
            "open": agg.open,
            "high": agg.high,
            "low": agg.low,
            "close": agg.close
        })
        return response


    def get_all_tickers(self):
        response = self.client.list_tickers(limit=1000)
        data = []
        try:
            for t in response:
                data.append(t)
        except Exception as e:
            print(e)
        return data

    def get_all_tickers_complete(self):
        tickers = self.get_all_tickers()
        ticker_complete = []
        count = 0
        try:
            for t in tickers:
                print(count)
                count += 1
                # details = self.client.get_ticker_details(t.ticker)
                logo = None  # details.branding.logo_url if details.branding else None
                options = False  # any(json.loads(self.client.list_options_contracts(ticker, limit=1, raw=True).data)['results'])
                data = {}
                data['symbol'] = t.ticker
                data['option'] = options
                data['logo'] = logo
                data['company_name'] = t.name
                data['is_crypto'] = False
                ticker_complete.append(data)
        except Exception as e:
            pass
        return ticker_complete

    def update_db_tickers(self, db, theta=None):
        skip = 0
        limit = 1000
        complete_data = []
        db_tickers = db.table('ticker').select('id', 'symbol').range(skip, limit).execute().data
        complete_data += db_tickers
        while any(db_tickers):
            skip += 1000
            limit += 1000
            db_tickers = db.table('ticker').select('id', 'symbol').range(skip, limit).execute().data
            complete_data += db_tickers
        # id = db_tickers[-1]['id'] + 1
        complete_data = [t['symbol'] for t in complete_data]
        j = 0
        tickers = self.get_all_tickers()
        ticker_complete = []
        count = 0
        try:
            for ind, t in enumerate(tickers):
                print(count)
                count += 1
                if t.ticker not in complete_data:
                    logo = None
                    data = {}
                    # data['id'] = id
                    data['symbol'] = t.ticker
                    data['option'] = any(json.loads(self.client.list_options_contracts(t.ticker, limit=1, raw=True)
                                                    .data)['results'])
                    data['logo'] = logo
                    data['company_name'] = t.name
                    data['is_crypto'] = False
                    ticker_complete.append(data)
                    # id += 1
                if ind % 500 == 0 and ind != 0 and any(ticker_complete):
                    try:
                        db.table('ticker').insert(ticker_complete[j:j + 500]).execute()
                        j += 500
                    except Exception as e:
                        raise Exception(e)
        except Exception as e:
            print(e)
        return ticker_complete