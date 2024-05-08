from flask import Flask, request, jsonify
import yfinance as yf
from bs4 import BeautifulSoup
import requests
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/v1/stock-price', methods=['GET'])
def get_stock_price_by_ticker():
    # Get the ticker name from the request
    ticker = request.args.get('ticker')
    
    if not ticker:
        return jsonify({'error': 'Ticker name is required'}), 400
    
    try:
        # Get data for the specified ticker
        stock = yf.Ticker(ticker)
        
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
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'class': 'wikitable sortable'})
    tickers = []
    for row in table.findAll('tr')[1:]:
        ticker = row.findAll('td')[0].text.strip()
        tickers.append(ticker)
    return jsonify({'tickers': tickers})

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
        stocks = yf.Tickers(tickers_str)
                
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
        
if __name__ == '__main__':
    app.run(debug=True)
