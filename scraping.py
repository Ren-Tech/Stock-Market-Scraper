import requests
from bs4 import BeautifulSoup
import yfinance as yf

def get_stock_market_news(stock_symbol="AAPL"):
    """
    Scrapes stock-related news from CNBC based on a stock symbol.
    """
    url = f"https://www.cnbc.com/quotes/{stock_symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    news_list = []

    articles = soup.find_all("div", class_="LatestNews-headlineWrapper", limit=5)
    for article in articles:
        title_tag = article.find("a")
        if title_tag:
            title = title_tag.text.strip()
            link = title_tag["href"]
            image = "https://via.placeholder.com/100"  # Placeholder image
            news_list.append({"title": title, "link": link, "image": image})

    return news_list

def get_stock_info(stock_symbol):
    """
    Fetches stock details using yfinance.
    """
    try:
        stock = yf.Ticker(stock_symbol)
        info = stock.info
        return {
            "name": info.get("shortName", "N/A"),
            "price": info.get("regularMarketPrice", "N/A"),
            "currency": info.get("currency", "USD"),
        }
    except Exception as e:
        print("Error fetching stock data:", e)
        return None
