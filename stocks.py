from flask import Flask, request, jsonify
import yfinance as yf
from bs4 import BeautifulSoup
import requests
import logging
import concurrent.futures
import requests_cache 
import pandas as pd

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/v1/stock-price', methods=['GET'])
def get_stock_price_by_ticker():
    # Get the ticker name from the request
    session = requests_cache.CachedSession('yfinance.cache')
    session.headers['User-agent'] = 'bnhp-stock=app/1.0'
    ticker = request.args.get('ticker')
    
    if not ticker:
        return jsonify({'error': 'Ticker name is required'}), 400
    
    try:
        # Get data for the specified ticker
        stock = yf.Ticker(ticker, session = session)
        
        # Fetching additional data
        info = stock.info
        company_name = info['longName']
        currency = info['currency']
        yesterday_price = stock.history(period="2d")["Close"].iloc[-2]
        current_price = stock.history(period="1d")["Close"].iloc[-1]
        
        return jsonify({
            'ticker': ticker,
            'company_name': company_name,
            'current_price': current_price,
            'yesterday_price': yesterday_price,
            'currency': currency
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/sp500-tickers', methods=['GET'])
def get_top_50_tickers():
    tickers_and_names = get_sp500_tickers_with_names()
    
    # Fetch market caps for tickers concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        market_caps = list(executor.map(get_market_cap, tickers_and_names.keys()))
    
    # Combine tickers, names, and market caps
    tickers_names_market_caps = [(ticker, tickers_and_names[ticker], market_cap) for ticker, market_cap in zip(tickers_and_names.keys(), market_caps)]
    
    # Filter out tickers with None market cap values
    valid_tickers_names_market_caps = [(ticker, name, market_cap) for ticker, name, market_cap in tickers_names_market_caps if market_cap is not None]
    
    # Sort valid tickers by market cap
    sorted_tickers_names_market_caps = sorted(valid_tickers_names_market_caps, key=lambda x: x[2], reverse=True)
    
    # Get top 50 tickers and company names
    top_50_tickers_names = [{'ticker': ticker, 'name': name} for ticker, name, _ in sorted_tickers_names_market_caps[:50]]
    
    return jsonify({'companies': top_50_tickers_names})

def get_sp500_tickers_with_names():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'class': 'wikitable sortable'})
    rows = table.findAll('tr')[1:]
    tickers_and_names = {}
    for row in rows:
        cols = row.findAll('td')
        ticker = cols[0].text.strip()
        name = cols[1].text.strip()
        tickers_and_names[ticker] = name
    return tickers_and_names
    
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'class': 'wikitable sortable'})
    tickers = [row.findAll('td')[0].text.strip() for row in table.findAll('tr')[1:]]
    return tickers

def get_market_cap(ticker):
    try:
        session = requests_cache.CachedSession('yfinance.cache')
        session.headers['User-agent'] = 'bnhp-stock=app/1.0'
        stock = yf.Ticker(ticker, session=session)
        return stock.info.get('marketCap')
    except Exception as e:
        print(f"Error fetching market cap for {ticker}: {e}")
        return None

@app.route('/api/v1/sp500-stock-price', methods=['POST'])
def get_sp_500_stock_price():
    
    data = request.get_json()
    tickers = data.get('tickers')
    logger.info("tickers: %s", tickers)
    
    if not tickers:
        return jsonify({'error': 'List of tickers is required'}), 400
    
    try:
        # Convert list of tickers into space-separated string
        tickers_str = " ".join(tickers)
        
        # Get data for all tickers at once
        session = requests_cache.CachedSession('yfinance.cache')
        session.headers['User-agent'] = 'bnhp-stock=app/1.0'
        stocks = yf.Tickers(tickers_str, session = session)
                
        results = []
        
        for curr_ticker in tickers:
            # Fetching additional data
            info = stocks.tickers[curr_ticker].info
            company_name = info['longName']
            currency = info['currency']
            yesterday_price = stocks.tickers[curr_ticker].history(period="2d")["Close"].iloc[-2]
            current_price = stocks.tickers[curr_ticker].history(period="1d")["Close"].iloc[-1]
            
            results.append({
               'ticker': curr_ticker,
               'company_name': company_name,
                'current_price': current_price,
                'yesterday_price': yesterday_price,
                'currency': currency
            })
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/most-active', methods=['GET'])
def get_most_active_stocks():
    # URL for Yahoo Finance most active stocks screener
    url = "https://finance.yahoo.com/most-active"

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Parse the HTML to get the tickers
    tickers = []
    for row in soup.find_all('tr', attrs={'class': 'simpTblRow'}):
        ticker = row.find('td', attrs={'aria-label': 'Symbol'}).text
        tickers.append(ticker)
        if len(tickers) == 5:  # Get only top 5
            break

    return jsonify(tickers)
    

if __name__ == '__main__':
    app.run(debug=True)
