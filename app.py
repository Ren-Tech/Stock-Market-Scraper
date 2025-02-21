from flask import Flask, render_template, request
import pandas as pd
from scraping import get_stock_market_news, get_stock_data, get_stock_specific_news

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def current_affairs():
    symbols = []
    stock_data = {}
    news_data = []  # Start with empty news
    
    if request.method == "POST":
        # Get the submitted stock symbols from the form
        symbols = [symbol.strip() for symbol in request.form.getlist("stock_symbols") if symbol.strip()]
        
        if symbols:
            # Get stock-specific news only when symbols are provided
            combined_news = []
            for symbol in symbols:
                symbol_news = get_stock_specific_news(symbol)
                combined_news.extend(symbol_news)
            
            news_data = combined_news if combined_news else []
            
            # Fetch stock data for each submitted symbol
            for symbol in symbols:
                try:
                    stock_data[symbol] = get_stock_data(symbol)
                except Exception as e:
                    stock_data[symbol] = pd.DataFrame()
        else:
            # If no symbols provided, show empty news
            news_data = []
    
    return render_template("current_affairs.html", news_data=news_data, stock_data=stock_data, symbols=symbols)

@app.route("/market_news", methods=["GET", "POST"])
def market_news():
    # Get general market news
    news_data = get_stock_market_news()
    
    # Initialize stock data with major indices
    stock_symbols = ["^DJI", "^IXIC", "^GSPC"]  # Dow Jones, NASDAQ, S&P 500
    stock_data = {}
    
    # Add any submitted symbols
    if request.method == "POST":
        symbols = [symbol.strip() for symbol in request.form.getlist("stock_symbols") if symbol.strip()]
        stock_symbols.extend(symbols)
    
    # Get data for all symbols
    for symbol in stock_symbols:
        try:
            stock_data[symbol] = get_stock_data(symbol)
        except Exception as e:
            stock_data[symbol] = pd.DataFrame()
    
    return render_template("market_news.html", 
                         news_data=news_data, 
                         stock_data=stock_data)
@app.route("/calendar", methods=["GET", "POST"])
def calendar():
    return render_template("calendar.html")  # Static calendar page (no dynamic data)

@app.route("/stocks", methods=["GET", "POST"])
def stocks():
    symbols = []
    stock_data = {}
    news_data = []  # Start with empty news
    
    if request.method == "POST":
        # Get the submitted stock symbols from the form
        symbols = [symbol.strip() for symbol in request.form.getlist("stock_symbols") if symbol.strip()]
        
        if symbols:
            # Get stock-specific news only when symbols are provided
            combined_news = []
            for symbol in symbols:
                symbol_news = get_stock_specific_news(symbol)
                combined_news.extend(symbol_news)
            
            news_data = combined_news if combined_news else []
            
            # Fetch stock data for each submitted symbol
            for symbol in symbols:
                try:
                    stock_data[symbol] = get_stock_data(symbol)
                except Exception as e:
                    stock_data[symbol] = pd.DataFrame()
    
    return render_template("stocks.html", news_data=news_data, stock_data=stock_data, symbols=symbols)

@app.route("/sector_news", methods=["GET", "POST"])
def sector_news():
    symbols = []
    stock_data = {}
    news_data = []  # Start with empty news
    
    if request.method == "POST":
        # Get the submitted stock symbols from the form
        symbols = [symbol.strip() for symbol in request.form.getlist("stock_symbols") if symbol.strip()]
        
        if symbols:
            # Get stock-specific news only when symbols are provided
            combined_news = []
            for symbol in symbols:
                symbol_news = get_stock_specific_news(symbol)
                combined_news.extend(symbol_news)
            
            news_data = combined_news if combined_news else []
            
            # Fetch stock data for each submitted symbol
            for symbol in symbols:
                try:
                    stock_data[symbol] = get_stock_data(symbol)
                except Exception as e:
                    stock_data[symbol] = pd.DataFrame()
    
    return render_template("sector_news.html", news_data=news_data, stock_data=stock_data, symbols=symbols)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)