
# from GBS.ipynb

# File Contains: Python code containing closed-form solutions for the valuation of European Options,
# American Options, Asian Options, Spread Options, Heat Rate Options, and Implied Volatility
#
# This document demonstrates a Python implementation of some option models described in books written by Davis
# Edwards: "Energy Trading and Investing", "Risk Management in Trading", "Energy Investing Demystified".
#
# for backward compatability with Python 2.7
from __future__ import division

# import necessary libaries
import unittest
import math
import numpy as np
from scipy.stats import norm
from scipy.stats import mvn

# Developer can toggle _DEBUG to True for more messages
# normally this is set to False
_DEBUG = False

# This class contains the limits on inputs for GBS models
# It is not intended to be part of this module's public interface
class _GBS_Limits:
    # An GBS model will return an error if an out-of-bound input is input
    MAX32 = 2147483248.0

    MIN_T = 1.0 / 1000.0  # requires some time left before expiration
    MIN_X = 0.01
    MIN_FS = 0.01

    # Volatility smaller than 0.5% causes American Options calculations
    # to fail (Number to large errors).
    # GBS() should be OK with any positive number. Since vols less
    # than 0.5% are expected to be extremely rare, and most likely bad inputs,
    # _gbs() is assigned this limit too
    MIN_V = 0.005

    MAX_T = 100
    MAX_X = MAX32
    MAX_FS = MAX32

    # Asian Option limits
    # maximum TA is time to expiration for the option
    MIN_TA = 0

    # This model will work with higher values for b, r, and V. However, such values are extremely uncommon. 
    # To catch some common errors, interest rates and volatility is capped to 100%
    # This reason for 1 (100%) is mostly to cause the library to throw an exceptions 
    # if a value like 15% is entered as 15 rather than 0.15)
    MIN_b = -1
    MIN_r = -1

    MAX_b = 1
    MAX_r = 1
    MAX_V = 1
      
# This is the public interface for European Options
# Each call does a little bit of processing and then calls the calculations located in the _gbs module

# Inputs: 
#    option_type = "p" or "c"
#    fs          = price of underlying
#    x           = strike
#    t           = time to expiration
#    v           = implied volatility
#    r           = risk free rate
#    q           = dividend payment
#    b           = cost of carry
# Outputs: 
#    value       = price of the option
#    delta       = first derivative of value with respect to price of underlying
#    gamma       = second derivative of value w.r.t price of underlying
#    theta       = first derivative of value w.r.t. time to expiration
#    vega        = first derivative of value w.r.t. implied volatility
#    rho         = first derivative of value w.r.t. risk free rates


# The primary class for calculating Generalized Black Scholes option prices and deltas
# It is not intended to be part of this module's public interface



# Inputs: option_type = "p" or "c", fs = price of underlying, x = strike, t = time to expiration, r = risk free rate
#         b = cost of carry, v = implied volatility
# Outputs: value, delta, gamma, theta, vega, rho
def _gbs(option_type, fs, x, t, r, b, v):
    _debug("Debugging Information: _gbs()")
    # -----------
    # Test Inputs (throwing an exception on failure)
    _gbs_test_inputs(option_type, fs, x, t, r, b, v)

    # -----------
    # Create preliminary calculations
    t__sqrt = math.sqrt(t)
    d1 = (math.log(fs / x) + (b + (v * v) / 2) * t) / (v * t__sqrt)
    d2 = d1 - v * t__sqrt

    if option_type == "c":
        # it's a call
        _debug("     Call Option")
        value = fs * math.exp((b - r) * t) * norm.cdf(d1) - x * math.exp(-r * t) * norm.cdf(d2)
        delta = math.exp((b - r) * t) * norm.cdf(d1)
        gamma = math.exp((b - r) * t) * norm.pdf(d1) / (fs * v * t__sqrt)
        theta = -(fs * v * math.exp((b - r) * t) * norm.pdf(d1)) / (2 * t__sqrt) - (b - r) * fs * math.exp(
            (b - r) * t) * norm.cdf(d1) - r * x * math.exp(-r * t) * norm.cdf(d2)
        vega = math.exp((b - r) * t) * fs * t__sqrt * norm.pdf(d1)
        rho = x * t * math.exp(-r * t) * norm.cdf(d2)
    else:
        # it's a put
        _debug("     Put Option")
        value = x * math.exp(-r * t) * norm.cdf(-d2) - (fs * math.exp((b - r) * t) * norm.cdf(-d1))
        delta = -math.exp((b - r) * t) * norm.cdf(-d1)
        gamma = math.exp((b - r) * t) * norm.pdf(d1) / (fs * v * t__sqrt)
        theta = -(fs * v * math.exp((b - r) * t) * norm.pdf(d1)) / (2 * t__sqrt) + (b - r) * fs * math.exp(
            (b - r) * t) * norm.cdf(-d1) + r * x * math.exp(-r * t) * norm.cdf(-d2)
        vega = math.exp((b - r) * t) * fs * t__sqrt * norm.pdf(d1)
        rho = -x * t * math.exp(-r * t) * norm.cdf(-d2)

    _debug("     d1= {0}\n     d2 = {1}".format(d1, d2))
    _debug("     delta = {0}\n     gamma = {1}\n     theta = {2}\n     vega = {3}\n     rho={4}".format(delta, gamma,
                                                                                                        theta, vega,
                                                                                                        rho))
    
    return value, delta, gamma, theta, vega, rho    



# ------------------------------
# This function makes sure inputs are OK
# It throws an exception if there is a failure
def _gbs_test_inputs(option_type, fs, x, t, r, b, v):
    # -----------
    # Test inputs are reasonable
    _test_option_type(option_type)

    if (x < _GBS_Limits.MIN_X) or (x > _GBS_Limits.MAX_X):
        raise GBS_InputError(
            "Invalid Input Strike Price (X). Acceptable range for inputs is {1} to {2}".format(x, _GBS_Limits.MIN_X,
                                                                                               _GBS_Limits.MAX_X))

    if (fs < _GBS_Limits.MIN_FS) or (fs > _GBS_Limits.MAX_FS):
        raise GBS_InputError(
            "Invalid Input Forward/Spot Price (FS). Acceptable range for inputs is {1} to {2}".format(fs,
                                                                                                      _GBS_Limits.MIN_FS,
                                                                                                      _GBS_Limits.MAX_FS))

    if (t < _GBS_Limits.MIN_T) or (t > _GBS_Limits.MAX_T):
        raise GBS_InputError(
            "Invalid Input Time (T = {0}). Acceptable range for inputs is {1} to {2}".format(t, _GBS_Limits.MIN_T,
                                                                                             _GBS_Limits.MAX_T))

    if (b < _GBS_Limits.MIN_b) or (b > _GBS_Limits.MAX_b):
        raise GBS_InputError(
            "Invalid Input Cost of Carry (b = {0}). Acceptable range for inputs is {1} to {2}".format(b,
                                                                                                      _GBS_Limits.MIN_b,
                                                                                                      _GBS_Limits.MAX_b))

    if (r < _GBS_Limits.MIN_r) or (r > _GBS_Limits.MAX_r):
        raise GBS_InputError(
            "Invalid Input Risk Free Rate (r = {0}). Acceptable range for inputs is {1} to {2}".format(r,
                                                                                                       _GBS_Limits.MIN_r,
                                                                                                       _GBS_Limits.MAX_r))

    if (v < _GBS_Limits.MIN_V) or (v > _GBS_Limits.MAX_V):
        raise GBS_InputError(
            "Invalid Input Implied Volatility (V = {0}). Acceptable range for inputs is {1} to {2}".format(v,
                                                                                                           _GBS_Limits.MIN_V,
                                                                                                           _GBS_Limits.MAX_V))

# ------------------------------
# This function verifies that the Call/Put indicator is correctly entered
def _test_option_type(option_type):
    if (option_type != "c") and (option_type != "p"):
        raise GBS_InputError("Invalid Input option_type ({0}). Acceptable value are: c, p".format(option_type))


# ---------------------------
# Black Scholes: stock Options (no dividend yield)
def black_scholes(option_type, fs, x, t, r, v):
    b = r
    return _gbs(option_type, fs, x, t, r, b, v)

# ---------------------------
# Merton Model: Stocks Index, stocks with a continuous dividend yields
def merton(option_type, fs, x, t, r, q, v):
    b = r - q
    return _gbs(option_type, fs, x, t, r, b, v)


# Inputs: 
#    option_type = "p" or "c"
#    fs          = price of underlying
#    x           = strike
#    t           = time to expiration
#    v           = implied volatility
#    r           = risk free rate
#    q           = dividend payment
#    b           = cost of carry
# Outputs: 
#    value       = price of the option
#    delta       = first derivative of value with respect to price of underlying
#    gamma       = second derivative of value w.r.t price of underlying
#    theta       = first derivative of value w.r.t. time to expiration
#    vega        = first derivative of value w.r.t. implied volatility
#    rho         = first derivative of value w.r.t. risk free rates
def amer_implied_vol(option_type, fs, x, t, r, q, cp):
    b = r - q
    return _american_implied_vol(option_type, fs, x, t, r, b, cp)

# ---------------------------
# Helper Function for Debugging

# Prints a message if running code from this module and _DEBUG is set to true
# otherwise, do nothing

def _debug(debug_input):
    if (__name__ == "__main__") and (_DEBUG == True):
        print(debug_input)

# This class defines the Exception that gets thrown when invalid input is placed into the GBS function
class GBS_InputError(Exception):
    def __init__(self, mismatch):
        Exception.__init__(self, mismatch)

# This class defines the Exception that gets thrown when there is a calculation error
class GBS_CalculationError(Exception):
    def __init__(self, mismatch):
        Exception.__init__(self, mismatch)

# This function tests that two floating point numbers are the same
# Numbers less than 1 million are considered the same if they are within .000001 of each other
# Numbers larger than 1 million are considered the same if they are within .0001% of each other
# User can override the default precision if necessary
def assert_close(value_a, value_b, precision=.000001):
    my_precision = precision

    if (value_a < 1000000.0) and (value_b < 1000000.0):
        my_diff = abs(value_a - value_b)
        my_diff_type = "Difference"
    else:
        my_diff = abs((value_a - value_b) / value_a)
        my_diff_type = "Percent Difference"

    _debug("Comparing {0} and {1}. Difference is {2}, Difference Type is {3}".format(value_a, value_b, my_diff,
                                                                                     my_diff_type))

    if my_diff < my_precision:
        my_result = True
    else:
        my_result = False

    if (__name__ == "__main__") and (my_result == False):
        print("  FAILED TEST. Comparing {0} and {1}. Difference is {2}, Difference Type is {3}".format(value_a, value_b,
                                                                                                       my_diff,
                                                                                                       my_diff_type))
    else:
        print(".")

    return my_result


# ---------------------------
# Testing the external interface
if __name__ == "__main__":
    print("=====================================")
    print("External Interface Testing")
    print("=====================================")

    # BlackScholes(option_type, X, FS, T, r, V)
    print("Testing: GBS.BlackScholes")
    assert_close(black_scholes('c', 102, 100, 2, 0.05, 0.25)[0], 20.02128028)
    assert_close(black_scholes('p', 102, 100, 2, 0.05, 0.25)[0], 8.50502208)

# ------------------
# Benchmarking against other option models

if __name__ == "__main__":
    print("=====================================")
    print("Selected Comparison to 3rd party models")
    print("=====================================")

    print("Testing GBS.BlackScholes")
    assert_close(black_scholes('c', fs=60, x=65, t=0.25, r=0.08, v=0.30)[0], 2.13336844492)

    print("Testing GBS.Merton")
    assert_close(merton('p', fs=100, x=95, t=0.5, r=0.10, q=0.05, v=0.20)[0], 2.46478764676)

    print("Testing Gamma")
    assert_close(black_scholes('c', fs=55, x=60, t=0.75, r=0.10, v=0.30)[2], 0.0278211604769)
    assert_close(black_scholes('p', fs=55, x=60, t=0.75, r=0.10, v=0.30)[2], 0.0278211604769)

    print("Testing Theta")
    assert_close(merton('p', fs=430, x=405, t=0.0833, r=0.07, q=0.05, v=0.20)[3], -31.1923670565)

    print("Testing Vega")
    assert_close(black_scholes('c', fs=55, x=60, t=0.75, r=0.10, v=0.30)[4], 18.9357773496)
    assert_close(black_scholes('p', fs=55, x=60, t=0.75, r=0.10, v=0.30)[4], 18.9357773496)

    print("Testing Rho")
    assert_close(black_scholes('c', fs=72, x=75, t=1, r=0.09, v=0.19)[5], 38.7325050173)

# Should be: 20.02128028
print(black_scholes('c', 102, 100, 2, 0.05, 0.25)[0])