import requests
import numpy as np
import pandas as pd
import datetime as dt
import time
import os

ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', 'YOUR_API_KEY_HERE')

# Cache to avoid multiple API calls
_data_cache = {}
_overview_cache = {}

def get_daily_data(symbol, outputsize='full', use_cache=True):
    """Get daily stock data from Alpha Vantage with caching"""
    cache_key = f"{symbol}_{outputsize}"
    
    # Return cached data if available and use_cache is True
    if use_cache and cache_key in _data_cache:
        return _data_cache[cache_key].copy()
    
    url = f'https://www.alphavantage.co/query'
    params = {
        'function': 'TIME_SERIES_DAILY',
        'symbol': symbol,
        'outputsize': outputsize,
        'apikey': ALPHA_VANTAGE_API_KEY
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if 'Error Message' in data:
        raise ValueError(f"Error fetching data for {symbol}: {data['Error Message']}")
    
    if 'Note' in data:
        raise ValueError(f"API limit reached: {data['Note']}")
    
    time_series = data.get('Time Series (Daily)', {})
    
    if not time_series:
        raise ValueError(f"No time series data found for {symbol}")
    
    # Convert to DataFrame
    df_data = []
    for date_str, values in time_series.items():
        df_data.append({
            'Date': pd.to_datetime(date_str),
            'Open': float(values['1. open']),
            'High': float(values['2. high']),
            'Low': float(values['3. low']),
            'Close': float(values['4. close']),
            'Volume': int(values['5. volume'])
        })
    
    df = pd.DataFrame(df_data)
    df.set_index('Date', inplace=True)
    df.sort_index(inplace=True)
    
    # Cache the result
    if use_cache:
        _data_cache[cache_key] = df.copy()
    
    return df

def get_company_overview(symbol, use_cache=True):
    """Get company overview data from Alpha Vantage with caching"""
    if use_cache and symbol in _overview_cache:
        return _overview_cache[symbol].copy()
    
    url = f'https://www.alphavantage.co/query'
    params = {
        'function': 'OVERVIEW',
        'symbol': symbol,
        'apikey': ALPHA_VANTAGE_API_KEY
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if 'Error Message' in data:
        raise ValueError(f"Error fetching overview for {symbol}: {data['Error Message']}")
    
    if use_cache:
        _overview_cache[symbol] = data.copy()
    
    return data

def stock_data(company):
    end = dt.datetime.now()
    start = end - dt.timedelta(days=100000)
    
    # Get data from Alpha Vantage (this will be cached)
    df = get_daily_data(company)
    
    # Filter data based on date range (similar to yfinance behavior)
    df = df[(df.index >= start) & (df.index <= end)]
    
    prices = np.array(df['Close'])
    dates = np.array(df.index)
    prices_list = prices.tolist()
    dates_list = dates.tolist()

    stock_variable_obj = stock_variables(company)

    search_object = {
        "prices": prices_list,
        "dates": dates_list,
        "stock": stock_variable_obj
    }

    return search_object

def stock_variables(company):
    # Get historical data (use cached version)
    df = get_daily_data(company, use_cache=True)
    
    # Get last 252 trading days (approximately 1 year)
    past_price = df.tail(252)
    
    if len(past_price) == 0:
        raise ValueError(f"No data found for {company}")
    
    initial_price = int(past_price['Close'].iloc[0])
    
    high = float(np.array(past_price['High'].max()))  # 52 Week High
    low = float(np.array(past_price['Low'].min()))    # 52 Week Low
    prev_close = float(past_price['Close'].iloc[-1])  # Prev Close
    returns = (((prev_close - initial_price)/initial_price) * 100)  # 52 Week Returns
    avg_volume = float(np.array(past_price['Volume'].mean())/1000000)  # Average Volume #M
    high_prev = float(past_price['High'].iloc[-1])
    low_prev = float(past_price['Low'].iloc[-1])
    
    # Get company overview for market cap and shares (use cached version)
    try:
        overview = get_company_overview(company, use_cache=True)
        shares_outstanding = float(overview.get('SharesOutstanding', 0))
        if shares_outstanding > 0:
            market_cap = (shares_outstanding * prev_close) / 1e12
        else:
            market_cap = 0.0
    except:
        market_cap = 0.0
        
    high = float("{:.2f}".format(high))
    low = float("{:.2f}".format(low))
    prev_close = float("{:.2f}".format(prev_close))
    returns = float("{:.2f}".format(returns))
    avg_volume = float("{:.2f}".format(avg_volume))
    high_prev = float("{:.2f}".format(high_prev))
    low_prev = float("{:.2f}".format(low_prev))
    market_cap = float("{:.2f}".format(market_cap))

    variable_object = {
        "high": high,
        "low": low,
        "prev_close": prev_close,
        "returns": returns,
        "avg_volume": avg_volume,
        "high_prev": high_prev,
        "low_prev": low_prev,
        "market_cap": market_cap
    }

    return variable_object

def clear_cache():
    """Clear the data cache - useful for testing or getting fresh data"""
    global _data_cache, _overview_cache
    _data_cache.clear()
    _overview_cache.clear()