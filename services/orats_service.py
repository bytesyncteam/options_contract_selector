import json
from datetime import datetime, timezone, timedelta
import glob
import pandas_market_calendars as mcal
from pathlib import Path

import requests
from fastapi import HTTPException

from services.helper import during_market_hours, after_market_hours


class Orats:

    def get_response(self, token, ticker):
        return requests.get(f"https://api.orats.io/datav2" + f"/strikes?token={token}&ticker={ticker}").json()

    def get_options_with_closest_strike(self, filtered_options, target_date_string):
        expiries_after_target_date = self.calculate_earliest_viable_dte_options(filtered_options, target_date_string)
        closest_strikes = self.select_3_closest_to_strike(expiries_after_target_date, "strike",
                                                     filtered_options[0]["stockPrice"])
        return closest_strikes

    def calculate_earliest_viable_dte_options(self, options_quotes, target_date_string):
        filtered_quotes = []
        target_datetime = datetime.strptime(target_date_string, "%Y-%m-%d")
        for quote in options_quotes:
            if datetime.strptime(quote["expirDate"], "%Y-%m-%d") >= target_datetime:
                filtered_quotes.append(quote)
        return filtered_quotes

    def select_3_closest_to_strike(self, options_json, key, value):
        list_of_keys = []
        for option in options_json:
            list_of_keys.append(option[key])
        closest_to_key = min(list_of_keys, key=lambda x:abs(x-value))

        filtered_data = []

        for option in options_json:
            if len(options_json) < 3:
                return [option]

            if option[key] == closest_to_key:
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

    def get_cached_response(self, ticker, target_date):
        CACHE_ON = True

        current_date_time = datetime.now(timezone.utc)
        if during_market_hours() or after_market_hours():
            day_string = datetime.strftime(current_date_time, "%Y-%m-%d")
            day_file_matches = glob.glob(f"cache/{day_string}/{ticker}-*")
            if len(day_file_matches) and CACHE_ON:
                # For now do one API call a day
                last_file = day_file_matches[-1]
                # TODO  retrieve API if within 15 mins
                print("Using cached file instead of hitting API")
                p = Path(last_file)
                with open(p, 'rb') as file:
                    response = json.load(file)
            else:
                return
        else:
            # Go back to previous trading day
            nyse = mcal.get_calendar("NYSE")
            today = datetime.now().date()
            past_date = today - timedelta(days=365)
            last_trading_day = nyse.schedule(start_date=past_date, end_date=today).iloc[-2].name.date()

            # last_trading_day = nyse.previous_close().date()
            day_string = datetime.strftime(last_trading_day, "%Y-%m-%d")
            day_file_matches = glob.glob(f"cache/{day_string}/{ticker}-*")

            if len(day_file_matches):
                # TODO: Make sure it is EOD
                last_file = day_file_matches[-1]
                print("Using cached file from last trading day instead of hitting API")
                p = Path(last_file)
                with open(p, 'rb') as file:
                    response = json.load(file)
            else:
                # This is only necessary if we do not run a daily job that caches the previous day's options chain.
                response_dict = {
                    "error": "This is before market hours. Please wait until market hours or after to run OptionsFriend"
                }
                response = json.dumps(response_dict)

        today_string = current_date_time.strftime("%Y-%m-%d")
        today_datetime = datetime.strptime(today_string, "%Y-%m-%d")
        target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
        if target_datetime <= today_datetime:
            raise HTTPException(status_code=422, detail="Error, target date is not in the future")