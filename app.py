from flask import Flask, render_template, request, jsonify
import pandas as pd
from scraping import get_stock_market_news, get_stock_data, get_stock_specific_news
from datetime import datetime
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
    # Fetch a broader set of market news, possibly from various sources
    news_data = get_stock_market_news()  # Get stock news data
    
    # Initialize stock symbols (e.g., major indices)
    stock_symbols = ["^DJI", "^IXIC", "^GSPC"]  # Dow Jones, NASDAQ, S&P 500
    stock_data = {}
    
    # Allow users to add additional stock symbols via form submission
    if request.method == "POST":
        symbols = [symbol.strip() for symbol in request.form.getlist("stock_symbols") if symbol.strip()]
        stock_symbols.extend(symbols)
    
    # Fetch data for all stock symbols
    for symbol in stock_symbols:
        try:
            stock_data[symbol] = get_stock_data(symbol)
        except Exception as e:
            stock_data[symbol] = pd.DataFrame()  # Handle any errors
    
    # Send the data to the template for rendering
    return render_template("market_news.html", 
                         news_data=news_data, 
                         stock_data=stock_data)

@app.route("/calendar", methods=["GET", "POST"])
def calendar():
    return render_template("calendar.html")  # Static calendar page (no dynamic data)

@app.route('/stock_reports')
def stock_reports():
    # Get the stock data from the main stocks page
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]  # Default symbols
    stock_data = {}
    
    for symbol in symbols:
        try:
            data = get_stock_data(symbol)
            if not data.empty:
                stock_data[symbol] = data
        except Exception as e:
            continue
    
    return render_template('stock_reports.html', 
                         stock_data=stock_data,
                         datetime=datetime)

@app.route("/stocks", methods=["GET", "POST"])
def stocks():
    # Initialize variables
    symbols = []
    stock_data = {}
    
    # Default symbols for the initial page load
    default_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]
    
    if request.method == "POST":
        # Get symbols from form input
        symbol_input = request.form.get("stock_symbols", "")
        if symbol_input:
            # Split by comma and clean up each symbol
            symbols = [s.strip().upper() for s in symbol_input.split(",") if s.strip()]
        else:
            symbols = default_symbols
    else:
        # For GET requests, use default symbols
        symbols = default_symbols
    
    # Fetch stock data for each symbol
    for symbol in symbols:
        try:
            data = get_stock_data(symbol)
            if not data.empty:
                stock_data[symbol] = data
        except Exception as e:
            # Log error (You should define logger or use print for debugging)
            print(f"Error fetching stock data for {symbol}: {str(e)}")
    
    # Also get news related to these stocks
    news_data = []
    if symbols:
        for symbol in symbols[:3]:  # Limit to first 3 symbols to avoid too many requests
            try:
                symbol_news = get_stock_specific_news(symbol)
                news_data.extend(symbol_news)
            except Exception as e:
                print(f"Error fetching news for {symbol}: {str(e)}")
    
    return render_template("stocks.html", 
                          stock_data=stock_data, 
                          news_data=news_data, 
                          symbols=symbols,
                          datetime=datetime)

# New route for AJAX requests to update stock data

@app.route("/stocks_data", methods=["POST"])
def stocks_data():
    try:
        # Initialize variables
        symbols = []
        stock_data = {}
        
        # Get symbols from form input
        symbol_input = request.form.get("stock_symbols", "")
        if symbol_input:
            # Split by comma and clean up each symbol
            symbols = [s.strip().upper() for s in symbol_input.split(",") if s.strip()]
        else:
            # Default symbols if none provided
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]
        
        # Fetch stock data for each symbol
        for symbol in symbols:
            try:
                data = get_stock_data(symbol)
                if not data.empty:
                    stock_data[symbol] = data
            except Exception as e:
                print(f"Error fetching stock data for {symbol}: {str(e)}")
        
        # Get news data (optional for AJAX updates)
        news_data = []
        if symbols:
            for symbol in symbols[:3]:
                try:
                    symbol_news = get_stock_specific_news(symbol)
                    news_data.extend(symbol_news)
                except Exception as e:
                    print(f"Error fetching news for {symbol}: {str(e)}")
        
        # Render only the content portion
        html_content = render_template("stocks.html", 
                                      stock_data=stock_data, 
                                      news_data=news_data, 
                                      symbols=symbols,
                                      datetime=datetime)
        
        # Extract container div content from rendered HTML
        # This is a simple approach - for more complex cases, you might use BeautifulSoup
        start_idx = html_content.find('<div class="container')
        end_idx = html_content.rfind('</div>') + 6
        container_html = html_content[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'html': container_html
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
    
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

@app.route("/simulation", methods=["GET", "POST"])
def simulation():
    # Here you can handle any logic for the simulation page if needed
    return render_template("simulation.html")  # Make sure to create this template


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)