import yfinance as yf
import requests
import pandas as pd
from bs4 import BeautifulSoup
import logging
import feedparser
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Define sectors with their constituent stocks
SECTORS = {
    "technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "INTC", "AMD"],
    "health_care": ["JNJ", "PFE", "UNH", "ABBV", "MRK"],
    "financials": ["JPM", "BAC", "GS", "WFC", "C", "V", "MA"],
    "retail": ["AMZN", "WMT", "HD", "MCD", "SBUX", "NKE", "DIS"],
    "energy": ["XOM", "CVX", "COP", "BP", "SLB"],
    "mining": ["RIO", "BHP", "VALE", "FCX", "NEM"],
    "utilities": ["NEE", "DUK", "SO", "D", "AEP"],
    "automotive": ["TSLA", "TM", "F", "GM", "HMC"]
}

def get_news_from_url(url, sector):
    """Fetch news from a given URL and categorize by sector"""
    try:
        # Handle RSS feeds
        if 'rss' in url.lower() or 'feed' in url.lower():
            feed = feedparser.parse(url)
            return [{
                'title': entry.title,
                'content': entry.description if hasattr(entry, 'description') else entry.title,
                'link': entry.link,
                'source': url,
                'date': entry.published if hasattr(entry, 'published') else None,
                'sector': sector
            } for entry in feed.entries[:5]]
        
        # Handle regular web pages (simplified example)
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This is a simplified example - you'll need to customize based on the sites you're scraping
        articles = []
        for article in soup.find_all('article')[:5]:
            title = article.find('h2').text if article.find('h2') else "No title"
            link = article.find('a')['href'] if article.find('a') else url
            if not link.startswith('http'):
                link = url + link
            content = article.find('p').text if article.find('p') else title
            
            articles.append({
                'title': title,
                'content': content,
                'link': link,
                'source': url,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'sector': sector
            })
        
        return articles
    
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return []

def get_stock_specific_news(symbol):
    """Fetch news for a specific stock symbol (mock implementation)"""
    # In a real implementation, you would use a financial API like Alpha Vantage, Yahoo Finance, etc.
    return [{
        'title': f"Latest news about {symbol}",
        'content': f"This is a sample news article about {symbol}. In a real app, this would come from an API.",
        'link': f"https://example.com/news/{symbol}",
        'source': "Financial News API",
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'sector': None  # Will be filtered by sector later
    }]

def get_stock_market_news():
    """Fetch general market news (mock implementation)"""
    # In a real implementation, this would come from a news API
    return [{
        'title': "General Market Update",
        'content': "This is a sample market news article. In a real app, this would come from an API.",
        'link': "https://example.com/market-news",
        'source': "Market News API",
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'sector': None  # Will be filtered by sector later
    }]
def get_stock_market_news():
    """Scrape real stock market news from Yahoo Finance with multiple fallback strategies"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    news = []
    urls_to_try = [
        "https://finance.yahoo.com/news/",
        "https://finance.yahoo.com/topic/stock-market-news",
        "https://finance.yahoo.com/topic/economic-news",
        "https://finance.yahoo.com/topic/earnings"
    ]
    
    # Try multiple URLs until we get valid news data
    for url in urls_to_try:
        try:
            logger.info(f"Attempting to scrape news from {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch data from {url}: Status code {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Try multiple CSS selectors that might capture news items
            selectors_to_try = [
                'li.js-stream-content',
                'div.Ov\(h\)',
                'div.NewsArticle',
                'div.IbBox',
                'div[data-test="mrt-node"]'
            ]
            
            for selector in selectors_to_try:
                news_items = soup.select(selector)
                if news_items and len(news_items) >= 3:  # Ensure we have at least 3 items
                    logger.info(f"Found {len(news_items)} news items with selector '{selector}'")
                    break
            else:
                # If no selector worked, try a more general approach
                logger.info("Trying general approach to find news items")
                news_items = soup.find_all(['div', 'li'], class_=lambda c: c and ('stream' in c.lower() or 'article' in c.lower()))
            
            # If we still don't have enough news items, try the next URL
            if not news_items or len(news_items) < 3:
                logger.warning(f"Insufficient news items found at {url}")
                continue
            
            # Process each news item
            for item in news_items[:10]:  # Limit to 10 news items
                try:
                    # Extract title - try multiple selectors
                    title_selectors = ['h3', '.headline', 'h2', '.Fw\(b\)', '[data-test="title"]', 'a']
                    title = None
                    for selector in title_selectors:
                        title_elem = item.select_one(selector)
                        if title_elem and title_elem.get_text().strip():
                            title = title_elem.get_text().strip()
                            break
                    
                    if not title:
                        continue  # Skip if no title found
                    
                    # Extract link
                    link_elem = item.select_one('a')
                    if not link_elem or 'href' not in link_elem.attrs:
                        continue  # Skip if no link found
                        
                    link = link_elem['href']
                    # Handle relative URLs
                    if link.startswith('/'):
                        link = "https://finance.yahoo.com" + link
                    elif not link.startswith('http'):
                        continue  # Skip invalid links
                    
                    # Extract image - if not found, we'll still use the article
                    img = item.select_one('img')
                    if img and 'src' in img.attrs:
                        image = img['src']
                    else:
                        # Use a stock image from Yahoo Finance
                        image = "https://s.yimg.com/ny/api/res/1.2/3kjv7IGvHl8Zp_95T9a2ug--/YXBwaWQ9aGlnaGxhbmRlcjt3PTY0MDtoPTQyNw--/https://media.zenfs.com/en/the_block_83/7d0a7c4ff346dae43159f5d9f76ebe24"
                    
                    # Extract content
                    content_selectors = ['p', '.description', '.Fz\(14px\)', '[data-test="description"]']
                    content = None
                    for selector in content_selectors:
                        content_elem = item.select_one(selector)
                        if content_elem and content_elem.get_text().strip():
                            content = content_elem.get_text().strip()
                            break
                    
                    if not content:
                        # Extract at least some text from the item
                        content = ' '.join([t for t in item.stripped_strings if t != title])[:200]
                        if not content:
                            content = f"Latest financial news about {title}."
                    
                    # Assign category based on content
                    category = assign_category(title + " " + content)
                    
                    # Add the processed news item
                    news.append({
                        "title": title,
                        "link": link,
                        "image": image,
                        "category": category,
                        "content": content[:150] + "..." if len(content) > 150 else content
                    })
                except Exception as e:
                    logger.error(f"Error processing news item: {str(e)}")
                    continue
            
            # If we found enough news items, we're done
            if len(news) >= 5:
                logger.info(f"Successfully scraped {len(news)} news items from {url}")
                break
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            continue
    
    # If we still couldn't find any news (very unlikely with all our fallbacks)
    # Make one final attempt to the main Yahoo Finance page
    if not news:
        try:
            logger.warning("All specific news pages failed, trying main Yahoo Finance page")
            response = requests.get("https://finance.yahoo.com/", headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Look for any links with news-related text
                news_links = soup.find_all('a', href=lambda href: href and ('/news/' in href or '/topic/' in href))
                
                for i, link_elem in enumerate(news_links[:10]):
                    title = link_elem.get_text().strip()
                    if not title or len(title) < 10:
                        continue
                        
                    link = link_elem['href']
                    if link.startswith('/'):
                        link = "https://finance.yahoo.com" + link
                    
                    image = "https://s.yimg.com/ny/api/res/1.2/3kjv7IGvHl8Zp_95T9a2ug--/YXBwaWQ9aGlnaGxhbmRlcjt3PTY0MDtoPTQyNw--/https://media.zenfs.com/en/the_block_83/7d0a7c4ff346dae43159f5d9f76ebe24"
                    content = f"Latest financial news from Yahoo Finance. Click to read more details."
                    category = assign_category(title)
                    
                    news.append({
                        "title": title,
                        "link": link,
                        "image": image,
                        "category": category,
                        "content": content
                    })
        except Exception as e:
            logger.error(f"Error in final fallback attempt: {str(e)}")
    
    logger.info(f"Returning {len(news)} news items")
    return news

def get_stock_specific_news(symbol):
    """Get news specific to a stock symbol"""
    if not symbol or symbol.isspace():
        return []
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    news = []
    try:
        logger.info(f"Fetching news for {symbol}")
        
        # Try the stock-specific news page
        url = f"https://finance.yahoo.com/quote/{symbol}/news"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"Failed to fetch news for {symbol}: Status code {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Try multiple CSS selectors that might capture news items
        selectors_to_try = [
            'li.js-stream-content',
            'div.Ov\(h\)',
            'div.NewsArticle',
            'div.IbBox',
            'div[data-test="mrt-node"]',
            'div[data-test="content"]'
        ]
        
        news_items = []
        for selector in selectors_to_try:
            news_items = soup.select(selector)
            if news_items and len(news_items) >= 2:
                logger.info(f"Found {len(news_items)} news items for {symbol} with selector '{selector}'")
                break
        
        # If still not found, try a more general approach
        if not news_items or len(news_items) < 2:
            logger.info(f"Trying general approach to find news items for {symbol}")
            news_items = soup.find_all(['div', 'li'], class_=lambda c: c and ('stream' in c.lower() or 'article' in c.lower()))
        
        # Process each news item
        for item in news_items[:10]:
            try:
                # Extract title - try multiple selectors
                title_selectors = ['h3', '.headline', 'h2', '.Fw\(b\)', '[data-test="title"]', 'a']
                title = None
                for selector in title_selectors:
                    title_elem = item.select_one(selector)
                    if title_elem and title_elem.get_text().strip():
                        title = title_elem.get_text().strip()
                        break
                
                if not title:
                    continue  # Skip if no title found
                
                # Extract link
                link_elem = item.select_one('a')
                if not link_elem or 'href' not in link_elem.attrs:
                    continue  # Skip if no link found
                    
                link = link_elem['href']
                # Handle relative URLs
                if link.startswith('/'):
                    link = "https://finance.yahoo.com" + link
                elif not link.startswith('http'):
                    continue  # Skip invalid links
                
                # Extract image - if not found, we'll still use the article
                img = item.select_one('img')
                if img and 'src' in img.attrs:
                    image = img['src']
                else:
                    # Use the Yahoo Finance logo or a symbol-related image
                    image = f"https://s.yimg.com/ny/api/res/1.2/3kjv7IGvHl8Zp_95T9a2ug--/YXBwaWQ9aGlnaGxhbmRlcjt3PTY0MDtoPTQyNw--/https://media.zenfs.com/en/the_block_83/7d0a7c4ff346dae43159f5d9f76ebe24"
                
                # Extract content
                content_selectors = ['p', '.description', '.Fz\(14px\)', '[data-test="description"]']
                content = None
                for selector in content_selectors:
                    content_elem = item.select_one(selector)
                    if content_elem and content_elem.get_text().strip():
                        content = content_elem.get_text().strip()
                        break
                
                if not content:
                    # Extract at least some text from the item
                    content = ' '.join([t for t in item.stripped_strings if t != title])[:200]
                    if not content:
                        content = f"Latest news about {symbol}. Click to read more details."
                
                # Assign category based on content
                category = assign_category(title + " " + content)
                
                # Add the processed news item
                news.append({
                    "title": title,
                    "link": link,
                    "image": image,
                    "category": category,
                    "content": content[:150] + "..." if len(content) > 150 else content
                })
            except Exception as e:
                logger.error(f"Error processing news item for {symbol}: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {str(e)}")
    
    # For additional news, try searching the symbol within general news
    if len(news) < 5:
        try:
            general_news = get_stock_market_news()
            symbol_lower = symbol.lower()
            
            # Filter general news for items mentioning the symbol
            for item in general_news:
                if (symbol_lower in item['title'].lower() or 
                    symbol_lower in item['content'].lower()) and len(news) < 10:
                    if not any(n['link'] == item['link'] for n in news):  # Avoid duplicates
                        news.append(item)
        except Exception as e:
            logger.error(f"Error fetching additional news for {symbol}: {str(e)}")
    
    logger.info(f"Returning {len(news)} news items for {symbol}")
    return news

def assign_category(text):
    """Assign a news category based on keywords in the text"""
    text = text.lower()
    
    if any(word in text for word in ['america', 'usa', 'us market', 'us stocks', 'nasdaq', 'dow jones', 'fed', 'fomc', 'treasury', 'nyse']):
        return "north_america"
    elif any(word in text for word in ['europe', 'eu', 'ecb', 'euro', 'london', 'brexit', 'germany', 'france', 'uk', 'ftse', 'dax']):
        return "europe"
    elif any(word in text for word in ['asia', 'china', 'japan', 'india', 'nikkei', 'hang seng', 'sensex', 'taiwan', 'south korea']):
        return "asia"
    else:
        return "world"

def get_stock_data(ticker):
    """Fetch stock data using yfinance"""
    if not ticker or ticker.isspace():
        return pd.DataFrame()
        
    try:
        logger.info(f"Fetching stock data for {ticker}")
        stock = yf.Ticker(ticker)
        stock_data = stock.history(period="5d")  # Get data for the last 5 days
        return stock_data
    except Exception as e:
        logger.error(f"Error fetching stock data for {ticker}: {str(e)}")
        return pd.DataFrame()