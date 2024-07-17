from datetime import datetime, timedelta
import pytz
import pandas_market_calendars as mcal


def during_market_hours():
    try:
        nyse = mcal.get_calendar('NYSE')
        time_now = datetime.now(pytz.UTC)
        market_hours = nyse.schedule(time_now - timedelta(days=1), time_now)
        market_open_time = market_hours.values.tolist()[-1][0].to_pydatetime()
        market_close_time = market_hours.values.tolist()[-1][1].to_pydatetime()

        if (market_open_time < time_now < market_close_time) and (datetime.date(
                (nyse.valid_days(start_date=time_now - timedelta(days=31), end_date=time_now)).tolist()[
                    -1]) == datetime.now().date()):
            print("It is currently DURING market hours.")
            return True
        else:
            print("It is currently NOT during market hours.")
            return False
    except Exception as e:
        print(e)
        return False



