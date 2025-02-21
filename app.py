from flask import Flask, render_template, request
from scraping import get_stock_market_news, get_stock_data  # Import the functions

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def current_affairs():
    news_data = get_stock_market_news()  # Fetch stock market news
    symbols = []
    stock_data = None
    if request.method == "POST":
        # Get the submitted stock symbols from the form
        symbols = [symbol.strip() for symbol in request.form.getlist("stock_symbols")]
        # Fetch stock data for each submitted symbol
        stock_data = {}
        for symbol in symbols:
            stock_data[symbol] = get_stock_data(symbol)  # Get stock data using yfinance

        return render_template("current_affairs.html", news_data=news_data, stock_data=stock_data, symbols=symbols)
    
    return render_template("current_affairs.html", news_data=news_data, stock_data=None, symbols=symbols)

@app.route("/market_news", methods=["GET", "POST"])
def market_news():
    news_data = get_stock_market_news()  # Fetch stock market news
    symbols = []
    stock_data = None
    if request.method == "POST":
        # Get the submitted stock symbols from the form
        symbols = [symbol.strip() for symbol in request.form.getlist("stock_symbols")]
        # Fetch stock data for each submitted symbol
        stock_data = {}
        for symbol in symbols:
            stock_data[symbol] = get_stock_data(symbol)  # Get stock data using yfinance

        return render_template("market_news.html", news_data=news_data, stock_data=stock_data, symbols=symbols)
    
    return render_template("market_news.html", news_data=news_data, stock_data=None, symbols=symbols)

@app.route("/calendar", methods=["GET", "POST"])
def calendar():
    return render_template("calendar.html")  # Static calendar page (no dynamic data)

@app.route("/stocks", methods=["GET", "POST"])
def stocks():
    news_data = get_stock_market_news()  # Fetch stock market news
    symbols = []
    stock_data = None
    if request.method == "POST":
        # Get the submitted stock symbols from the form
        symbols = [symbol.strip() for symbol in request.form.getlist("stock_symbols")]
        # Fetch stock data for each submitted symbol
        stock_data = {}
        for symbol in symbols:
            stock_data[symbol] = get_stock_data(symbol)  # Get stock data using yfinance

        return render_template("stocks.html", news_data=news_data, stock_data=stock_data, symbols=symbols)
    
    return render_template("stocks.html", news_data=news_data, stock_data=None, symbols=symbols)

@app.route("/sector_news", methods=["GET", "POST"])
def sector_news():
    news_data = get_stock_market_news()  # Fetch stock market news
    symbols = []
    stock_data = None
    if request.method == "POST":
        # Get the submitted stock symbols from the form
        symbols = [symbol.strip() for symbol in request.form.getlist("stock_symbols")]
        # Fetch stock data for each submitted symbol
        stock_data = {}
        for symbol in symbols:
            stock_data[symbol] = get_stock_data(symbol)  # Get stock data using yfinance

        return render_template("sector_news.html", news_data=news_data, stock_data=stock_data, symbols=symbols)
    
    return render_template("sector_news.html", news_data=news_data, stock_data=None, symbols=symbols)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
