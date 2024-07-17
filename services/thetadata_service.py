from thetadata import DateRange, StockReqType, OptionReqType, OptionRight
from datetime import datetime, timedelta
import requests
from operator import itemgetter

from app.cache_crud import get_options_cache, cache_options
from app.options_schema import Option


class ThetadataService:

    def __init__(self, user_name=None, password=None, base_url=None):
        self.client = None  # ThetaClient(username=user_name, passwd=password)
        if base_url:
            self.base_url = base_url
        else:
            self.base_url = f"http://127.0.0.1:25510"

    def get_options_quotes(self, ticker, start_date, end_date, exp_date, strike, right):
        response = requests.get(self.base_url + f"hist/option/implied_volatility?root={ticker}&start_date={start_date}&"
                                                f"end_date={end_date}&strike={strike}&exp={exp_date}&"
                                                f"right={right}&ivl=3600000")
        data = response.json()
        return data

    def get_n_days_data(self, days, ticker):
        with self.client.connect():
            out = self.client.get_hist_stock(
                req=StockReqType.EOD,  # End of day data
                root=ticker,
                date_range=DateRange(datetime.now() - timedelta(days), datetime.now())
            )
        data = out.to_dict()
        res = {}
        for key, value in data.items():
            res[str(key).split('.')[-1].lower()] = value
        res['timestamp'] = res['date']
        response = []
        for i,j,k,l,m in zip(res['timestamp'].values(), res['open'].values(), res['high'].values(), res['low'].values(), res['close'].values()):
            response.append({
                "timestamp": i,
                "open": j,
                "high": k,
                "low": l,
                "close": m
            })

        return response

    def format_date(self, date):
        return str(date).split()[0].replace("-", "")

    def get_strikes(self, ticker, expiry):
        url = self.base_url + f"/list/strikes?root={ticker}&exp={expiry}"
        response = requests.get(url)
        data = response.json()['response']
        return data

    def get_options_hist(self, ticker, expiry, strike, right):
        with self.client.connect():
            out = self.client.get_hist_option(
                root=ticker,
                exp=expiry,
                strike=strike,
                right=right
            )
        return out

    def get_opt_expirations(self, ticker):
        url = self.base_url + f"/list/expirations?root={ticker}"
        response = requests.get(url)
        data = response.json()['response']
        return data

    def get_stock_hist(self, ticker, date):
        with self.client.connect():
            out = self.client.get_hist_stock(
                req=StockReqType.EOD,
                root=ticker,
                date_range=DateRange(date, date)
            )
        return out

    def get_stock_at_time(self, ticker, date):
        date = self.format_date(date)
        url = self.base_url + f"/hist/stock/eod?root={ticker}&start_date={date}&end_date={date}"
        response = requests.get(url)
        data = response.json()['response'][-1]
        return data

    def get_last(self, ticker, expiry, strike):
        with self.client.connect():
            out = self.client.get_last_option(
                req=OptionReqType.QUOTE,
                root=ticker,
                exp=expiry,
                strike=strike,
                right=OptionRight.CALL,
            )
        return out

    def get_opt_at_time(self, ticker, selected_expiry, s, right, daterange):
        with self.client.connect():
            out = self.client.get_opt_at_time(
                req=OptionReqType.EOD,
                root=ticker,
                exp=selected_expiry,
                strike=s,
                right=right,
                date_range=daterange
            )
        return out

    def get_all_contracts(self, ticker, right):
        # TODO: make sure that the start date is right (today's or yesterday's)
        start_date = int(str(datetime.now()-timedelta(days=1)).split(' ')[0].replace('-',''))
        response = requests.get(self.base_url + f"/list/contracts/option/trade?start_date={20240112}")
        data = response.json()['response']
        filtered_data = [x for x in data if x[0] == ticker and x[3] == right]
        return filtered_data

    def get_client_connection(self):
        return self.client.connect()

    def calculate_earliest_viable_dte_options(self, options_quotes, target_date_string):
        filtered_quotes = []
        target_datetime = datetime.strptime(target_date_string, "%Y-%m-%d")
        for quote in options_quotes:
            if datetime.strptime(quote.expirDate, "%Y-%m-%d") >= target_datetime:
                filtered_quotes.append(quote)
        return filtered_quotes

    def select_3_closest_to_strike(self, options_json, key, value):
        list_of_keys = []
        for option in options_json:
            list_of_keys.append(getattr(option, key))
        closest_to_key = min(list_of_keys, key=lambda x:abs(x-value))

        filtered_data = []

        for option in options_json:
            if len(options_json) < 3:
                return [option]

            if getattr(option, key) == closest_to_key:
                index_of_strike = options_json.index(option)

                if index_of_strike == 0:
                    filtered_data.append(option)
                    filtered_data.append(options_json[index_of_strike + 1])
                    filtered_data.append(options_json[index_of_strike + 2])
                elif index_of_strike == len(options_json):
                    filtered_data.append(option)
                    filtered_data.append(options_json[index_of_strike - 1])
                    filtered_data.append(options_json[index_of_strike - 2])
                else:
                    filtered_data.append(options_json[index_of_strike - 1])
                    filtered_data.append(option)
                    filtered_data.append(options_json[index_of_strike + 1])

        return filtered_data

    def get_options_with_closest_strike(self, filtered_options, target_date_string, stock_price):
        expiries_after_target_date = self.calculate_earliest_viable_dte_options(filtered_options, target_date_string)
        closest_strikes = self.select_3_closest_to_strike(expiries_after_target_date, "strike",
                                                     stock_price)
        return closest_strikes

    def get_options_with_closest_strike2(self, ticker, target_date):
        all_contracts = self.get_all_contracts()
        underlying_contracts = [x for x in all_contracts if x[0] == ticker]
        underlying_contracts = sorted(underlying_contracts, key=itemgetter(1))
        underlying_data = self.get_stock_at_time(ticker, datetime.now()).to_dict()
        price = underlying_data[list(underlying_data.keys())[3]][0]

        start_date = datetime.now()-timedelta(1) if datetime.now().weekday() == 0 else datetime.now()-timedelta(3)
        end_date = datetime.now()
        options = []
        for contract in underlying_contracts:
            call_quote = self.get_options_quotes(ticker, int(str(start_date).split(' ')[0].replace('-','')),
                                                 int(str(end_date).split(' ')[0].replace('-','')),
                                                 int(str(contract[1]).split(' ')[0].replace('-','')), int(contract[2]), 'C')
            put_quote = self.get_options_quotes(ticker, int(str(start_date).split(' ')[0].replace('-','')),
                                                int(str(end_date).split(' ')[0].replace('-','')),
                                                int(str(contract[1]).split(' ')[0].replace('-','')), int(contract[2]), 'P')
            call_ask = call_quote['response'][-1][5] if call_quote['header']['format'] and 'ask' in call_quote['header']['format'] else 0  # max(call_quote['response'], key=lambda x: x[1])[7] if call_quote['header']['format'] and 'ask' in call_quote['header']['format'] else 0
            put_ask = put_quote['response'][-1][5] if put_quote['header']['format'] and 'ask' in put_quote['header']['format'] else 0  # max(call_quote['response'], key=lambda x: x[1])[7] if call_quote['header']['format'] and 'ask' in put_quote['header']['format'] else 0
            mid = call_quote['response'][-1][6] if call_quote['header']['format'] and 'implied_vol' in call_quote['header']['format'] else 0  # max(call_quote['response'], key=lambda x: x[1])[7] if call_quote['header']['format'] and 'ask' in call_quote['header']['format'] else 0
            expiry_date_str = str(contract[1])
            expiry_date_obj = datetime(int(expiry_date_str[:4]), int(expiry_date_str[4:6]), int(expiry_date_str[6:8]))

            options.append(dict(Option.model_validate({
                "root": ticker,
                "strike": contract[2]/1000,
                "stockPrice": price,
                "expirDate": str(expiry_date_obj),
                "callMidIv": mid,  # TODO: Find way to get the mid iv from ThetaData
                "dte": (expiry_date_obj - datetime.now()).days,
                "callAskPrice": call_ask,
                "putAskPrice": put_ask
            })))

        return options

    def change_data_format(self, quotes):
        """
        TODO: Change the data format to the format that the logic expects
        :param options:
        :return:
        """
        res = []
        for q in quotes:
            if q['contract']['right'] == 'P':
                res.append(Option.model_validate({
                    "root": q['contract']['root'],
                    "strike": q['contract']['strike'],
                    "stockPrice": q['tick'][-2],
                    "expirDate": str(datetime.strptime(str(q['contract']['expiration']), "%Y%m%d")).split(' ')[0],
                    "callMidIv": q['tick'][9],
                    "dte": (datetime.strptime(str(q['contract']['expiration']), "%Y%m%d") - datetime.now()).days,
                    "callAskPrice": 0,
                    "putAskPrice": q['tick'][7]
                }))
            else:
                res.append(Option.model_validate({
                    "root": q['contract']['root'],
                    "strike": q['contract']['strike'],
                    "stockPrice": q['tick'][-2],
                    "expirDate": str(datetime.strptime(str(q['contract']['expiration']), "%Y%m%d")).split(' ')[0],
                    "callMidIv": q['tick'][9],
                    "dte": (datetime.strptime(str(q['contract']['expiration']), "%Y%m%d") - datetime.now()).days,
                    "callAskPrice": q['tick'][7],
                    "putAskPrice": 0
                }))

        return res

    def get_previous_bulk_quotes(self, db, ticker, right, target_date, previous_days=2):
        cached_contracts = get_options_cache(db, ticker)
        if any(cached_contracts):
            return cached_contracts, True
        contracts = self.get_all_contracts(ticker, right)
        start_date = int(str(datetime.now() - timedelta(days=previous_days)).split(' ')[0].replace('-', ''))
        res = []
        price = 0
        for c in contracts:
            if c[1] >= int(self.format_date(target_date)):
                quote = self.eod_quote_greeks(start_date, c[1], right, ticker, start_date, c[2])
                if quote[0]:
                    res.append(Option.model_validate({
                        "root": ticker,
                        "strike": c[2]/1000,
                        "stockPrice": quote[0][18],
                        "expirDate": str(datetime.strptime(str(c[1]), "%Y%m%d")).split(' ')[0],
                        "callMidIv": quote[0][11],
                        "dte": (datetime.strptime(str(c[1]), "%Y%m%d") - datetime.now()).days,
                        "callAskPrice": quote[0][16],
                        "putAskPrice": quote[0][16]
                    }))
        if not any(res):
            return self.get_previous_bulk_quotes(ticker, right, target_date, previous_days+1), False
        return res, False

    def get_bulk_quotes(self, root):
        print()
        return \
        requests.get(self.base_url + "/bulk_snapshot/option/quote?exp=0" + "&root=" + root).json()[
            'response']

    def get_bulk_greeks(self, root, expiry_date='0'):
        return \
        requests.get(self.base_url + "/bulk_snapshot/option/greek?exp=" + expiry_date + "&root=" + root).json()[
            'response']

    def get_iv(self, end, exp, right, root):
        url = f"/v2/hist/option/trade_greeks?end_date={end}&exp={exp}&right={right}&root={root}"
        return requests.get(self.base_url + url).json()['response'][0]["tick"][8]

    def eod_quote_greeks(self, end_date, exp, right, root, start_date, strike):
        url = self.base_url + f"/bulk_hist/option/eod_greeks?end_date={20240112}&exp={exp}&right={right}&root={root}" \
                              f"&start_date={20240112}&strike={strike}&ivl=900000"
        return requests.get(url).json()['response']

    def bulk_greeks_v2(self, root, expiry_date='0'):
        data = \
        requests.get(self.base_url + "/bulk_snapshot/option/greeks?exp=" + expiry_date + "&root=" + root).json()[
            'response']

        formatted_data = self.change_data_format(data)
        cache_options(formatted_data)
        return data
