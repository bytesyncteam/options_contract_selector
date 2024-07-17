from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import logging
import os
from dotenv import load_dotenv
from app.cache_crud import get_common_options_tickers, delete_cache, cache_options
from database import get_supabase
from services.helper import after_market_hours, during_market_hours, get_closing_market_time_delta
from services.orats_service import Orats
from services.custom_indicators import CustomIndicators
from services.thetadata_service import ThetadataService
from services.yfinance_service import Yfinance
from datetime import datetime, timezone, timedelta
from app.bjerk import bjerkCall
import json


load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


app = FastAPI()

service = os.getenv("DATA_SERVICE")
# base_url = os.getenv("BASE_URL")
debug = int(os.getenv('DEBUG'))
if service == "THETADATA":
    try:
        # read user and password from env variables
        user = os.getenv('THETADATA_USER')
        password = os.getenv('THETADATA_PASSWORD')
        base_url = os.getenv('THETADATA_BASE_URL')
        data_service = ThetadataService(user, password, base_url)
    except Exception as e:
        data_service = Yfinance()
elif service == "ORATS":
    data_service = Orats()
else:
    raise HTTPException(status_code=500, detail="Error: invalid data service")


origins = [
    "http://127.0.0.1/",
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8081",
    "http://localhost:8080",
    "http://localhost:8000",
    "https://options-friend-git-main-finflit.vercel.app",
    "https://options-friend.vercel.app",
    "https://optionsfriend.com",
    "https://api.optionsfriend.com",
    "https://options-friend-free-options-profit-calculator.vercel.app",
    "https://free.optionsfriend.com",
    "https://app.ambly.io",
    "https://ambly.io"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

from pydantic import BaseModel


class hypothesis_data(BaseModel):
    ticker: str
    magnitude: float
    direction: str
    timeperiod: int


@app.post("/get_tickers/")
def get_tickers(db=Depends(get_supabase)):
    return {
        "data": db.table('ticker').select('*').execute().data,
    }


def run_update(db):
    """TODO: implement these"""
    #tickers = get_common_options_tickers(db)
    # for t in tickers:
    #     contracts = data_service.bulk_greeks_v2(t['root'])
    #     formatted = data_service.format_date(contracts)
    #     delete_cache(db, t['root'])
    #     cache_options(db, formatted)

@app.post("/search_ticker/{query}")
def search_ticker(query: str, db=Depends(get_supabase)):
    """
        :param db
        :param query: str
        :return: list

        This function accepts search string and performs full-text search in the database returns the ranked
        results based on the matches

        Reference: https://amitosh.medium.com/full-text-search-fts-with-postgresql-and-sqlalchemy-edc436330a0c
    """
    results = db.table('ticker').select("*").ilike('symbol', f'{query}%').order('symbol').limit(10).execute().data
    if len(results) < 10:
        results += db.table('ticker').select("*").ilike('company_name', f'%{query}%').order('company_name').limit(
            7).execute().data
    response = []
    for i in results:
        if i not in response:
            response.append(i)

    return response[:11]


@app.get("/sparkline")
async def get_sparkline():
    service = Yfinance()
    ticker_list = ["AAPL", "SPY", "QQQ", "TSLA", "MSFT"]
    data = {}
    # if not after_market_hours() or during_market_hours():
    # change this to check both after_market_hours() and during_market_hours()
    if during_market_hours():
        for ticker in ticker_list:
            res = service.get_1min_day_data(ticker)
            data[ticker] = {}
            data[ticker]['x'] = [x['close'] for x in res]
            data[ticker]['y'] = [str(x['timestamp']) for x in res]
    else:
        for ticker in ticker_list:
            res = service.get_1min_day_data(ticker, start=datetime.now().date()-timedelta(1), end=datetime.now().date())
            data[ticker] = {}
            data[ticker]['x'] = [x['close'] for x in res]
            data[ticker]['y'] = [str(x['timestamp']) for x in res]
    return data



@app.get("/get_ideal_options/{ticker}/{target_date}/")
async def get_ideal_options(
        ticker: str,  # AAPL
        target_date: str,  # "YYYY-MM-DD"
        magnitude: str,  # "5" for 5%
        direction: str,  # "up", "down"
        db=Depends(get_supabase),
):

    current_date_time = datetime.now(timezone.utc)
    today_string = current_date_time.strftime("%Y-%m-%d")
    today_datetime = datetime.strptime(today_string, "%Y-%m-%d")
    target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
    if target_datetime <= today_datetime and not debug:
        raise HTTPException(status_code=422, detail="Error, target date is not in the future")

    highest_options = find_highest_return_options(db, ticker, target_date, magnitude, direction)

    return JSONResponse(content=highest_options)


def select_3_closest_to_strike(strikes, options_json, value):
    closest_to_key = min(strikes, key=lambda x: abs(x - value))
    strikes.sort()
    return [strikes[strikes.index(closest_to_key) - 1], closest_to_key, strikes[strikes.index(closest_to_key) + 1]]

    # filtered_data = []
    #
    # for option in options_json.items():
    #     if len(options_json) < 3:
    #         return [option]
    #
    #     # Select only the option that is closest to the key
    #     if option == closest_to_key:
    #         index_of_strike = options_json.index(option)
    #
    #         if index_of_strike == 0:
    #             filtered_data.append(option)
    #             filtered_data.append(options_json[index_of_strike + 1])
    #             filtered_data.append(options_json[index_of_strike + 2])
    #         elif index_of_strike == len(options_json):
    #             filtered_data.append(option)
    #             filtered_data.append(options_json[index_of_strike - 1])
    #             filtered_data.append(options_json[index_of_strike - 2])
    #         else:
    #             filtered_data.append(options_json[index_of_strike - 1])
    #             filtered_data.append(option)
    #             filtered_data.append(options_json[index_of_strike + 1])
    #
    # return filtered_data


def calculate_earliest_viable_dte_options(options_quotes, target_date_string):
    filtered_quotes = []
    target_datetime = datetime.strptime(target_date_string, "%Y-%m-%d")
    for quote in options_quotes:
        if datetime.strptime(quote["expirDate"], "%Y-%m-%d") >= target_datetime:
            filtered_quotes.append(quote)
    return filtered_quotes


def find_highest_return_options(db, ticker, target_date_string, magnitude, direction):
    list_of_options = []
    list_of_options_on_expiry = []
    highest_return = 0
    on_expiry_highest_return = 0
    target_date = datetime.strptime(target_date_string, "%Y-%m-%d")
    right = "C"
    if direction == "down":
        right = "P"
        magnitude = - float(magnitude)
    target_increase = float(magnitude) / 100

    filtered_options = []
    if service == "THETADATA":
        if during_market_hours():
            res = data_service.bulk_greeks_v2(ticker)
            if not res[0]:
                raise HTTPException(status_code=500, detail="cannot fetch contracts data from thetadata api")
            # try:
            #     stock_price = data_service.get_stock_at_time(ticker, datetime.now())[3]
            # except Exception as e:
            #     raise HTTPException(status_code=500, detail="cannot fetch stock price from thetadata api")
            filtered_options = data_service.change_data_format(res)
            closest_strikes = data_service.get_options_with_closest_strike(filtered_options ,target_date_string, filtered_options[0].stockPrice)
        else:
            filtered_options, cached = data_service.get_previous_bulk_quotes(db, ticker, right, target_date)
            # if not cached:
            #     cache_options(db, filtered_options)
            closest_strikes =data_service.get_options_with_closest_strike(filtered_options, target_date_string, filtered_options[0].stockPrice)
    else:
        if debug:
            with open('cache/2023-01-19/AAPL-1600-response.txt', 'rb') as file:
                res = json.load(file)
        else:
            token = os.getenv('ORATS_TOKEN')
            try:
                res = data_service.get_response(token, ticker)
            except Exception as e:
                return HTTPException(status_code=500, detail="Error: invalid token")
        filtered_options = res["data"]
        closest_strikes = data_service.get_options_with_closest_strike(filtered_options, target_date_string)

    for single_option in closest_strikes:
        option_dict = single_option.dict()
        if option_dict["callAskPrice"] or option_dict["putAskPrice"]:
            if service == "THETADATA":
                if not option_dict["callMidIv"]:
                    option_dict["callMidIv"] = data_service.get_iv(
                        data_service.format_date(target_date), data_service.format_date(option_dict["expirDate"]), right, ticker)
            strike = option_dict["strike"]
            spot = option_dict["stockPrice"]
            q = 0  # Dividend rate
            r = .04329  # 3 month treasury risk free rate

            expiry_date = datetime.strptime(option_dict["expirDate"], "%Y-%m-%d")
            print(expiry_date)
            dte_on_target_date = (expiry_date - target_date).days
            time_at_expiry = dte_on_target_date / 365

            vol = option_dict["callMidIv"]

            dte = option_dict["dte"]
            expiry = option_dict["expirDate"]

            initial_call_value = option_dict["callAskPrice"] if option_dict["callAskPrice"] != 0 else 0.01

            t = (dte) / 365
            calculated_initial_call_value = bjerkCall(strike, spot, q, r, t, vol)

            spot_on_expiry = spot * (1 + target_increase)

            calculated_expiry_value = bjerkCall(strike, spot_on_expiry, q, r, time_at_expiry, vol)

            calculated_value_at_expiry = calculated_expiry_value

            return_pct_for_trade = (
                                               calculated_expiry_value - calculated_initial_call_value) / calculated_initial_call_value if calculated_initial_call_value else 0

            risk_reward = calculated_expiry_value / calculated_initial_call_value if calculated_initial_call_value else 0
            expiry_value = float("%.2f" % calculated_expiry_value)

            stock_price = option_dict["stockPrice"]
            moneyness_percentage = ((strike - stock_price) * 100) / stock_price

            if direction == "up":
                if moneyness_percentage > 0:
                    moneyness_type = "OTM"
                else:
                    moneyness_type = "ITM"
                option_type = "call"
                ask_value = option_dict["callAskPrice"]
            else:
                if moneyness_percentage < 0:
                    moneyness_type = "OTM"
                else:
                    moneyness_type = "ITM"
                option_type = "put"
                ask_value = option_dict["putAskPrice"]

            total_cost = float(ask_value) * 100

            risk_reward_one_decimal = "%.1f" % risk_reward
            risk_reward_string = f"1:{risk_reward_one_decimal}"

            moneyness_value_string = "%.1f" % moneyness_percentage
            normalized_moneyness_value_string = abs(float(moneyness_value_string))

            if expiry_date == target_date:
                list_of_options_on_expiry.append({
                    'cost': total_cost,
                    'ask': ask_value,
                    'moneynessType': moneyness_type,
                    'moneynessValuePct': normalized_moneyness_value_string,
                    'strike': float(strike),
                    'stockPrice': stock_price,
                    'optionType': option_type,
                    'expiry': expiry,
                    'estimatedGain': float("%.0f" % (highest_return * 100)),
                    'riskReward': risk_reward_string,
                    'calculatedValueAtExpiry': expiry_value
                })
                if return_pct_for_trade > on_expiry_highest_return:
                    print("HIGHER RETURN PCT THAN ON EXPIRY HIGHEST")
                    on_expiry_highest_return = return_pct_for_trade

    for single_option in filtered_options:
        option_dict = single_option.dict()
        strike = option_dict["strike"]
        spot = option_dict["stockPrice"]
        dividend_rate = 0  # Dividend rate
        risk_free_rate = .04329  # 3 month treasury risk free rate

        expiry_date = datetime.strptime(option_dict["expirDate"], "%Y-%m-%d")
        if expiry_date < target_date:
            continue
        dte_on_target_date = (expiry_date - target_date).days
        time_at_expiry = dte_on_target_date / 365

        vol = option_dict["callMidIv"]

        dte = option_dict["dte"]
        expiry = option_dict["expirDate"]

        initial_call_value = option_dict["callAskPrice"] if option_dict["callAskPrice"] != 0 else 0.0111
        # print("initial_call_value")
        # print(initial_call_value)

        time = (dte) / 365
        calculated_initial_call_value = bjerkCall(strike, spot, dividend_rate, risk_free_rate, time, vol)
        # print("calculated_initial_call_value")
        # print(calculated_initial_call_value)

        spot_on_expiry = spot * (1 + target_increase)
        calculated_expiry_value = bjerkCall(strike, spot_on_expiry, dividend_rate, risk_free_rate, time_at_expiry, vol)
        # print("calculated_expiry_value")
        # print(calculated_expiry_value)
        calculated_value_at_expiry = calculated_expiry_value

        return_pct_for_trade = (calculated_expiry_value - initial_call_value) / initial_call_value

        risk_reward = calculated_expiry_value / initial_call_value
        expiry_value = float("%.2f" % calculated_expiry_value)

        stock_price = option_dict["stockPrice"]
        moneyness_percentage = ((strike - stock_price) * 100) / stock_price

        if direction == "up":
            if moneyness_percentage > 0:
                moneyness_type = "OTM"
            else:
                moneyness_type = "ITM"
            option_type = "call"
            ask_value = option_dict["callAskPrice"]
        else:
            if moneyness_percentage < 0:
                moneyness_type = "OTM"
            else:
                moneyness_type = "ITM"
            option_type = "put"
            ask_value = option_dict["putAskPrice"]

        total_cost = float(ask_value) * 100

        risk_reward_one_decimal = "%.1f" % risk_reward
        risk_reward_string = f"1:{risk_reward_one_decimal}"

        moneyness_value_string = "%.1f" % moneyness_percentage
        normalized_moneyness_value_string = abs(float(moneyness_value_string))

        if return_pct_for_trade > highest_return:
            highest_return = return_pct_for_trade
            list_of_options.append({
                'debug': {
                    'dte': dte,
                    'strike': strike,
                    'initial_spot': spot,
                    'spot_on_expiry': spot_on_expiry,
                    'dividend_rate': dividend_rate,
                    'risk_free_rate': risk_free_rate,
                    'time_at_expiry': time_at_expiry,
                    'vol': vol,
                    'initial_real_option_value': initial_call_value,
                    'option_value_at_expiry': calculated_expiry_value
                },
                'strike': float(strike),
                'stockPrice': stock_price,
                'optionType': option_type,
                'cost': total_cost,
                'ask': ask_value,
                'moneynessType': moneyness_type,
                'moneynessValuePct': normalized_moneyness_value_string,
                'expiry': expiry,
                'estimatedGain': float("%.0f" % (highest_return * 100)),
                'riskReward': risk_reward_string,
                'calculatedValueAtExpiry': expiry_value
            })

    import matplotlib.pyplot as plt
    import numpy as np
    plt.style.use('ggplot')
    plt.rcParams['xtick.labelsize'] = 14
    plt.rcParams['ytick.labelsize'] = 14
    plt.rcParams['figure.titlesize'] = 18
    plt.rcParams['figure.titleweight'] = 'medium'
    plt.rcParams['lines.linewidth'] = 2.5

    #### make a funcion that lets you specify a few parameters and calculates the payoff
    # S = stock underlying # K = strike price # Price = premium paid for option
    def long_call(S, K, Price):
        # Long Call Payoff = max(Stock Price - Strike Price, 0)     # If we are long a call, we would only elect to call if the current stock price is greater than     # the strike price on our option
        P = list(map(lambda x: max(x - K, 0) - Price, S))
        return P

    def long_put(S, K, Price):
        # Long Put Payoff = max(Strike Price - Stock Price, 0)     # If we are long a call, we would only elect to call if the current stock price is less than     # the strike price on our option
        P = list(map(lambda x: max(K - x, 0) - Price, S))
        return P

    def short_call(S, K, Price):
        # Payoff a shortcall is just the inverse of the payoff of a long call
        P = long_call(S, K, Price)
        return [-1.0 * p for p in P]

    def short_put(S, K, Price):
        # Payoff a short put is just the inverse of the payoff of a long put
        P = long_put(S, K, Price)
        return [-1.0 * p for p in P]

    def binary_call(S, K, Price):
        # Payoff of a binary call is either:     # 1. Strike if current price > strike     # 2. 0
        P = list(map(lambda x: K - Price if x > K else 0 - Price, S))
        return P

    def binary_put(S, K, Price):
        # Payoff of a binary call is either:     # 1. Strike if current price < strike     # 2. 0
        P = list(map(lambda x: K - Price if x < K else 0 - Price, S))
        return P

    from scipy.stats import norm

    # S: underlying stock price # K: Option strike price # r: risk free rate # D: dividend value # vol: Volatility # T: time to expiry (assumed that we're measuring from t=0 to T)
    def d1_calc(S, K, r, vol, T, t):
        # Calculates d1 in the BSM equation
        return (np.log(S / K) + (r + 0.5 * vol ** 2) * (T - t)) / (vol * np.sqrt(T - t))

    # S: underlying stock price # K: Option strike price # r: risk free rate # D: dividend value # vol: Volatility # T: time to expiry (assumed that we're measuring from t=0 to T)
    def BS_call(S, K, r, vol, T, t):
        d1 = d1_calc(S, K, r, vol, T, t)
        d2 = d1 - vol * np.sqrt(T)
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

    def BS_put(S, K, r, vol, T, t):
        return BS_call(S, K, r, vol, T, t) - S + np.exp(-r * (T - t)) * K

    def BS_binary_call(S, K, r, vol, T, t):
        d1 = d1_calc(S, K, r, vol, T, t)
        d2 = d1 - vol * np.sqrt(T - t)
        return np.exp(-r * T) * norm.cdf(d2)

    def BS_binary_put(S, K, r, vol, T, t):
        return BS_binary_call(S, K, r, vol, T, t) - S + np.exp(-r * (T - t)) * K

    ########################################################################### #1st Order Greeks
    def delta(S, K, r, vol, T, t, otype):
        d1 = d1_calc(S, K, r, vol, T, t)
        d2 = d1 - vol * np.sqrt(T - t)

        if (otype == "call"):
            delta = np.exp(-(T - t)) * norm.cdf(d1)
        elif (otype == "put"):
            delta = -np.exp(-(T - t)) * norm.cdf(-d1)

        return delta

    # Gamma for calls/puts the same
    def vega(S, K, r, vol, T, t, otype):
        d1 = d1_calc(S, K, r, vol, T, t)
        return S * norm.pdf(d1) * np.sqrt(T - t)

    def rho(S, K, r, vol, T, t, otype):
        d1 = d1_calc(S, K, r, vol, T, t)
        d2 = d1 - vol * np.sqrt(T - t)

        if (otype == "call"):
            rho = K * (T - t) * np.exp(-r * (T - t)) * norm.cdf(d2)
        elif (otype == "put"):
            rho = -K * (T - t) * np.exp(-r * (T - t)) * norm.cdf(-d2)
        return rho

    def theta(S, K, r, vol, T, t, otype):
        d1 = d1_calc(S, K, r, vol, T, t)
        d2 = d1 - vol * np.sqrt(T - t)

        if (otype == "call"):
            theta = -(S * norm.pdf(d1) * vol / (2 * np.sqrt(T - t))) - r * K * np.exp(-r * (T - t)) * norm.cdf(d2)
        elif (otype == "put"):
            theta = -(S * norm.pdf(d1) * vol / (2 * np.sqrt(T - t))) + r * K * np.exp(-r * (T - t)) * norm.cdf(-d2)

        return theta

    # 2nd Order Greeks
    def gamma(S, K, r, vol, T, t, otype):
        d1 = d1_calc(S, K, r, vol, T, t)
        gamma = (norm.pdf(d1)) / (S * vol * np.sqrt(T - t))

        return gamma

    def charm(S, K, r, vol, T, t, otype):
        d1 = d1_calc(S, K, r, vol, T, t)
        d2 = d1 - vol * np.sqrt(T - t)
        charm = -norm.pdf(d1) * (2 * r * (T - t) - d2 * vol * np.sqrt(T - t)) / (2 * (T - t) * vol * np.sqrt(T - t))

        return charm

    return (list_of_options[-5:] + list_of_options_on_expiry[-5:])

