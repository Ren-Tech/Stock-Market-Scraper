import yfinance as yf
import requests
from bs4 import BeautifulSoup

# Function to get stock market news from Yahoo Finance
def get_stock_market_news():
    url = "https://finance.yahoo.com/quote/%5EGSPC?p=%5EGSPC"  # Replace with the desired stock index URL or ticker
    response = requests.get(url)
    
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.content, "html.parser")

    # Find the relevant news articles (adjust the selector based on the website structure)
    news_items = soup.find_all("li", class_="js-stream-content")

    news = []

    for item in news_items:
        title = item.find("h3").get_text() if item.find("h3") else "No Title"
        link = "https://finance.yahoo.com" + item.find("a")["href"] if item.find("a") else "#"
        image = item.find("img")["src"] if item.find("img") else None
        content = item.find("p").get_text() if item.find("p") else "No Content"

        news.append({
            "title": title,
            "link": link,
            "image": image,
            "content": content
        })

    return news

# Function to fetch stock data using yfinance
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    stock_data = stock.history(period="5d")  # Get data for the last 5 days
    return stock_data
