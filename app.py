from flask import Flask, render_template
from scraping import get_stock_market_news

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/current_affairs")
def current_affairs():
    news = get_stock_market_news()
    return render_template("current_affairs.html", news=news)

@app.route("/market_news")
def market_news():
    news = get_stock_market_news()
    return render_template("market_news.html", news=news)

@app.route("/calendar")
def calendar():
    return render_template("calendar.html")

@app.route("/stocks")
def stocks():
    return render_template("stocks.html")

@app.route("/sector_news")
def sector_news():
    return render_template("sector_news.html")

if __name__ == "__main__":
    app.run(debug=True)
