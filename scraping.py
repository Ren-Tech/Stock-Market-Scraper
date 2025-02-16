import requests
from bs4 import BeautifulSoup

def get_stock_market_news():
    url = "https://www.cnbc.com/markets/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    news_list = []
    articles = soup.find_all("div", class_="Card-titleContainer", limit=5)

    for article in articles:
        title = article.find("a").get_text()
        link = article.find("a")["href"]
        news_list.append({"title": title, "link": link})
    
    return news_list
