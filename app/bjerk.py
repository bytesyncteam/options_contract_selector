import QuantLib as ql

# q dividend
# r risk free rate
# t time in years
# vol volatility
def bjerkStens(option_type, strike, spot, q, r, t, vol):
  spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
  today = ql.Date.todaysDate()
  calendar = ql.NullCalendar()
  day_count = int(t *360 + 0.5)
  exDate = today + day_count
  dc = ql.Actual360()
  payoff = ql.PlainVanillaPayoff(option_type, strike)
  flat_ts = ql.YieldTermStructureHandle(ql.FlatForward(today, r, dc))
  dividend_yield = ql.YieldTermStructureHandle(ql.FlatForward(today, q, dc))
  flat_vol_ts = ql.BlackVolTermStructureHandle(
      ql.BlackConstantVol(today, calendar, vol, dc)
  )
  bsm_process = ql.BlackScholesMertonProcess(spot_handle,
                                             dividend_yield,
                                             flat_ts,
                                             flat_vol_ts)
  eng = ql.BjerksundStenslandApproximationEngine(bsm_process)
  payoff = ql.PlainVanillaPayoff(option_type, strike)
  am_exercise = ql.AmericanExercise(today, exDate)
  american_option = ql.VanillaOption(payoff, am_exercise)
  american_option.setPricingEngine(eng)
  return american_option.NPV()

# Feb 18th 17 days
# 1000 strike
# 58.51 IV
#$24.25

# Nov 1st, 2021
# spot 1600.61
# strike 2225
# expiry January 20th 2023
# IV: 46.07%
# $170.8449


def bjerkCall(strike, spot, q, r, t, vol):
    return bjerkStens(ql.Option.Call, strike, spot, q, r, t, vol)

def bjerkPut(strike, spot, q, r, t, vol):
    return bjerkStens(ql.Option.Put, strike, spot, q, r, t, vol)


# print(bjerkCall(40.00, 42.00, 0.08, 0.04, 0.75, 0.35))
# test_cases = [
#      # from "  McGraw-Hill 1998, pag 27
#       [ ql.Option.Call,  40.00,  42.00, 0.08, 0.04, 0.75, 0.35,  5.2704 ],

# print(bjerkCall(40.00, 42.00, 0.08, 0.04, 0.75, 0.35))

# print(bjerkCall(100, 102, 0, .05, 2, .25))

print(bjerkCall(2225, 1600.61, 0, .045, 445/365, .4607))


# Should be: 20.02128028
# print(black_scholes('c', 102, 100, 2, 0.05, 0.25)[0])

# Inputs for Black Scholes: 
#    option_type = "p" or "c"
#    fs          = price of underlying
#    x           = strike
#    t           = time to expiration
#    v           = implied volatility
#    r           = risk free rate
#    q           = dividend payment
#    b           = cost of carry

# Black Scholes: stock Options (no dividend yield)
# def black_scholes(option_type, fs, x, t, r, v):
#     b = r
#     return _gbs(option_type, fs, x, t, r, b, v)
