import random
from flask import Flask, render_template, request, jsonify, session
import pandas as pd
from scraping import get_stock_market_news, get_stock_data, get_stock_specific_news
from datetime import datetime, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests
import feedparser
import os
import re
import yfinance as yf

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a secret key for session management

# API_KEY = 'NWV90QOIWFFO75C5'



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
# Mock functions - replace with your actual implementations
def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)  # Replace multiple whitespace with single space
    return text.strip()

def get_news_from_url(url, sector):
    """Fetch actual news content from the provided URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Handle RSS feeds
        if any(ext in url.lower() for ext in ['rss', 'feed', 'xml']):
            feed = feedparser.parse(url)
            articles = []
            for entry in feed.entries[:5]:  # Limit to 5 articles
                title = clean_text(entry.get('title', 'No title'))
                description = clean_text(entry.get('description', title))
                link = entry.get('link', url)
                date = entry.get('published', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                articles.append({
                    'title': title,
                    'content': description,
                    'link': link,
                    'source': urlparse(url).netloc,
                    'date': date,
                    'sector': sector
                })
            return articles
        
        # Handle regular news websites
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Common patterns for news websites
        articles = []
        
        # Try to find article elements - these selectors work for many news sites
        article_elements = soup.find_all('article') or \
                          soup.find_all(class_=re.compile('article|post|story', re.I)) or \
                          soup.find_all(itemtype='http://schema.org/NewsArticle')
        
        for article in article_elements[:5]:  # Limit to 5 articles
            # Try to extract title
            title_elem = article.find(['h1', 'h2', 'h3']) or \
                        article.find(class_=re.compile('title|headline', re.I))
            title = clean_text(title_elem.get_text()) if title_elem else "No title"
            
            # Try to extract content
            content_elem = article.find(class_=re.compile('content|entry|post-body', re.I)) or \
                          article.find(['p', 'div'])
            content = clean_text(content_elem.get_text()) if content_elem else title
            
            # Try to extract link
            link_elem = article.find('a', href=True)
            link = link_elem['href'] if link_elem else url
            if link.startswith('/'):
                link = f"{urlparse(url).scheme}://{urlparse(url).netloc}{link}"
            
            # Try to extract date
            date_elem = article.find(class_=re.compile('date|time', re.I)) or \
                       article.find('time')
            date = clean_text(date_elem.get('datetime') or date_elem.get_text()) if date_elem else \
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            articles.append({
                'title': title,
                'content': content,
                'link': link,
                'source': urlparse(url).netloc,
                'date': date,
                'sector': sector
            })
        
        return articles
    
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return []
def assign_category(text):
    """Assign a news category based on text content"""
    text = text.lower()
    
    # Simple keyword-based categorization
    if any(word in text for word in ['europe', 'eu', 'european', 'brexit', 'uk', 'germany', 'france', 'spain', 'italy']):
        return 'europe'
    elif any(word in text for word in ['asia', 'china', 'japan', 'india', 'korea', 'singapore', 'malaysia', 'indonesia']):
        return 'asia'
    elif any(word in text for word in ['north america', 'america', 'us', 'usa', 'united states', 'canada', 'mexico']):
        return 'north_america'
    elif any(word in text for word in ['south america', 'brazil', 'argentina', 'colombia', 'peru', 'chile']):
        return 'south_america'
    elif any(word in text for word in ['africa', 'south africa', 'nigeria', 'kenya', 'egypt']):
        return 'africa'
    elif any(word in text for word in ['australia', 'new zealand', 'oceania']):
        return 'australia'
    elif any(word in text for word in ['middle east', 'mena', 'arab', 'saudi', 'uae', 'qatar', 'iran', 'iraq']):
        return 'mena'
    else:
        return 'world'  # Default category
def fetch_top_news(url, max_articles=20):  # Increased from 10 to 15
    """Fetch top news articles from a given URL
    
    Args:
        url (str): The URL of the news website
        max_articles (int): Maximum number of articles to fetch
        
    Returns:
        list: List of news article dictionaries
    """
    news_items = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # CNN-specific handling
        if 'cnn.com' in url:
            articles = soup.select('article, div.container__item, div.card')
            for article in articles[:max_articles]:
                title_elem = article.select_one('span.container__headline-text, h3.card__headline')
                if not title_elem:
                    continue
                    
                title = clean_text(title_elem.get_text())
                
                # Try to find the actual article content, not just the headline
                content_elem = article.select_one('div.container__description, div.card__description')
                content = clean_text(content_elem.get_text()) if content_elem else title
                
                # Skip generic CNN descriptions
                if content == "View the latest news and breaking news today for U.S., world, weather, entertainment, politics and health at CNN.com.":
                    continue
                    
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                    
                link = link_elem['href']
                if link.startswith('/'):
                    link = f"https://www.cnn.com{link}"
                    
                image_elem = article.select_one('img')
                image = image_elem['src'] if image_elem and 'src' in image_elem.attrs else "/static/images/default_news.jpg"
                
                date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                news_items.append({
                    'title': title,
                    'content': content[:200] + "..." if content and len(content) > 200 else content,
                    'image': image,
                    'link': link,
                    'category': assign_category(title + " " + content),
                    'date': date,
                    'source': 'cnn.com'
                })
                
            return news_items
        
        # Rest of the original scraping logic for other sites
        article_selectors = [
            'article', '.story', '.news-item', '.article', 
            'div[data-testid="story"]', '.story-body', '.card',
            '.news-card', '.news-package', '.article-card',
            'li.js-stream-content', '.post', '.entry'
        ]
        
        # ... rest of the original function ...
        
    except Exception as e:
        print(f"Error fetching news from {url}: {str(e)}")
        
    return news_items
@app.route("/", methods=["GET", "POST"])
def current_affairs():
    urls = {
        'world': [],
        'north_america': [],
        'south_america': [],
        'europe': [],
        'asia': [],
        'africa': [],
        'australia': [],
        'mena': []
    }
    news_data = []
    error_messages = []
    urls_provided = False  # Flag to track if any URLs were provided

    if request.method == "POST":
        # Get URLs for each region
        for region in urls.keys():
            region_urls = [url.strip() for url in request.form.getlist(f"{region}_urls") if url.strip()]
            urls[region] = region_urls
            if region_urls:
                urls_provided = True
        
        # Only fetch news if URLs were provided
        if urls_provided:
            for region, region_urls in urls.items():
                for url in region_urls:
                    try:
                        # Add protocol if missing
                        if not url.startswith(('http://', 'https://')):
                            url = 'https://' + url
                        
                        source_news = fetch_top_news(url, max_articles=20)
                        if source_news:
                            # Override the auto-detected category with our region
                            for news_item in source_news:
                                news_item['category'] = region
                            news_data.extend(source_news)
                        else:
                            error_messages.append(f"Could not extract news from {url} (Region: {region})")
                    except Exception as e:
                        error_messages.append(f"Error processing {url} (Region: {region}): {str(e)}")
        else:
            error_messages.append("Please provide at least one URL to fetch news")

    # Sort news by date (most recent first)
    news_data = sorted(news_data, key=lambda x: x.get('date', ''), reverse=True)
    
    return render_template("current_affairs.html", 
                         news_data=news_data, 
                         urls=urls, 
                         error_messages=error_messages,
                         urls_provided=urls_provided)
@app.route("/market_news", methods=["GET", "POST"])
def market_news():
    # Initialize market_urls dictionary
    market_urls = {
        "us": [],
        "uk": [],
        "ge": [],
        "fr": [],
        "china": [],
        "europe": [],
        "asia": [],
        "south_america": []
    }
    
    # Default selected market
    selected_market = request.args.get("market", "us")
    
    # Process form submission for URLs
    if request.method == "POST":
        # Get market selection if provided
        if "market" in request.form:
            selected_market = request.form.get("market")
        
        # Process URLs for each market
        for market in market_urls.keys():
            urls = request.form.getlist(f"{market}_urls")
            market_urls[market] = [url for url in urls if url.strip()]
    
    # Collect news based on the URLs for the selected market
    news_data = []
    
    # Check if we have URLs for the selected market
    if market_urls[selected_market]:
        # Use the URLs from the selected market to fetch news
        for url in market_urls[selected_market]:
            try:
                # Use get_news_from_url function to fetch news from the URL
                market_news = get_news_from_url(url, selected_market)
                if market_news:
                    news_data.extend(market_news)
            except Exception as e:
                # Log any errors
                print(f"Error fetching news from {url}: {str(e)}")
    else:
        # If no URLs for the selected market, use the default news function
        news_data = get_stock_market_news()
    
    # Add news type and image to each news item

    # Render the template with all necessary data
    return render_template("market_news.html",
                          news_data=news_data,
                          market_urls=market_urls,
                          selected_market=selected_market)

@app.template_filter('url_shorten')
def url_shorten_filter(url, length=30):
    """Shorten URL for display purposes"""
    if not url:
        return ""
    # Remove protocol and www
    short_url = url.replace('https://', '').replace('http://', '').replace('www.', '')
    # Shorten if needed
    if len(short_url) > length:
        return short_url[:length] + '...'
    return short_url
# Add these custom template filters
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d'):
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return value
    return value.strftime(format)

@app.template_filter('groupby')
def groupby(items, attribute):
    groups = {}
    for item in items:
        key = item.get(attribute)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    return groups.items()
@app.route("/calendar", methods=["GET", "POST"])
def calendar():
    # Extended dummy data - in production this would come from a database
    calendar_events = [
        # Earnings Reports (Q3 2023)
        {
            "date": "2023-11-02",
            "company": "Apple Inc.",
            "symbol": "AAPL",
            "type": "earnings",
            "quarter": "Q4 2023",
            "time": "After Market Close"
        },
        {
            "date": "2023-11-02",
            "company": "Starbucks Corporation",
            "symbol": "SBUX",
            "type": "earnings",
            "quarter": "Q4 2023",
            "time": "After Market Close"
        },
        {
            "date": "2023-11-07",
            "company": "Walt Disney Company",
            "symbol": "DIS",
            "type": "earnings",
            "quarter": "Q4 2023",
            "time": "After Market Close"
        },
        {
            "date": "2023-11-09",
            "company": "NVIDIA Corporation",
            "symbol": "NVDA",
            "type": "earnings",
            "quarter": "Q3 2023",
            "time": "After Market Close"
        },
        {
            "date": "2023-11-14",
            "company": "Home Depot Inc.",
            "symbol": "HD",
            "type": "earnings",
            "quarter": "Q3 2023",
            "time": "Before Market Open"
        },
        
        # Upcoming Earnings (Q1 2024)
        {
            "date": "2024-01-24",
            "company": "Tesla Inc.",
            "symbol": "TSLA",
            "type": "earnings",
            "quarter": "Q4 2023",
            "time": "After Market Close"
        },
        {
            "date": "2024-01-25",
            "company": "Intel Corporation",
            "symbol": "INTC",
            "type": "earnings",
            "quarter": "Q4 2023",
            "time": "After Market Close"
        },
        {
            "date": "2024-01-30",
            "company": "Microsoft Corporation",
            "symbol": "MSFT",
            "type": "earnings",
            "quarter": "Q2 2024",
            "time": "After Market Close"
        },
        
        # Dividend Events
        {
            "date": "2023-11-10",
            "company": "Johnson & Johnson",
            "symbol": "JNJ",
            "type": "dividend",
            "amount": "$1.19",
            "ex_date": "2023-11-08",
            "record_date": "2023-11-09"
        },
        {
            "date": "2023-11-15",
            "company": "Procter & Gamble",
            "symbol": "PG",
            "type": "dividend",
            "amount": "$0.94",
            "ex_date": "2023-11-13",
            "record_date": "2023-11-14"
        },
        {
            "date": "2023-11-30",
            "company": "Coca-Cola Company",
            "symbol": "KO",
            "type": "dividend",
            "amount": "$0.46",
            "ex_date": "2023-11-28",
            "record_date": "2023-11-29"
        },
        
        # Stock Splits
        {
            "date": "2023-11-16",
            "company": "Amazon.com Inc.",
            "symbol": "AMZN",
            "type": "split",
            "ratio": "20:1",
            "effective_date": "2023-11-16"
        },
        {
            "date": "2023-12-01",
            "company": "Alphabet Inc.",
            "symbol": "GOOGL",
            "type": "split",
            "ratio": "20:1",
            "effective_date": "2023-12-01"
        },
        
        # IPOs
        {
            "date": "2023-11-17",
            "company": "AstroTech",
            "symbol": "ASTRO",
            "type": "ipo",
            "price_range": "$18-$21",
            "shares": "12.5M",
            "exchange": "NASDAQ"
        },
        {
            "date": "2023-12-05",
            "company": "GreenEnergy Solutions",
            "symbol": "GES",
            "type": "ipo",
            "price_range": "$22-$25",
            "shares": "8.2M",
            "exchange": "NYSE"
        },
        
        # Economic Events
        {
            "date": "2023-11-03",
            "company": "Federal Reserve",
            "symbol": "FED",
            "type": "economic",
            "event": "Non-Farm Payrolls Report",
            "impact": "High"
        },
        {
            "date": "2023-11-22",
            "company": "U.S. Bureau of Economic Analysis",
            "symbol": "BEA",
            "type": "economic",
            "event": "GDP Q3 Preliminary",
            "impact": "Medium"
        },
        
        # Shareholder Meetings
        {
            "date": "2023-11-20",
            "company": "Berkshire Hathaway",
            "symbol": "BRK.B",
            "type": "meeting",
            "event": "Annual Shareholder Meeting",
            "location": "Omaha, NE"
        },
        
        # Product Launches
        {
            "date": "2023-12-12",
            "company": "Apple Inc.",
            "symbol": "AAPL",
            "type": "event",
            "event": "Expected iPhone 16 Launch",
            "location": "Cupertino, CA"
        },
        
        # Conference Presentations
        {
            "date": "2023-11-28",
            "company": "Moderna Inc.",
            "symbol": "MRNA",
            "type": "conference",
            "event": "J.P. Morgan Healthcare Conference",
            "presenter": "CEO Stéphane Bancel"
        }
    ]
    
    # Calculate total pages (5 items per page)
    total_pages = (len(calendar_events) // 5) + (1 if len(calendar_events) % 5 else 0)
    
    return render_template("calendar.html", 
                         calendar_events=calendar_events,
                         total_pages=total_pages)

@app.route('/stock_reports')
def stock_reports():
    # Get the stock data from the main stocks page
    symbols = [
       "WMT", "DIS", "JNJ", "GE", "INTU", "ADBE",
        "NVDA", "BA", "XOM", "T", "ORCL", "BIDU", "GS",
    ]
    
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

@app.route("/api/earnings/<symbol>/<quarter>")
def get_earnings_data(symbol, quarter):
    try:
        # Replace this with actual data fetching logic
        # This could come from a database or financial API
        earnings_data = {
            "symbol": symbol,
            "quarter": quarter,
            "estimatedEps": random.uniform(1.0, 5.0),
            "actualEps": random.uniform(0.8, 5.5),
            "estimatedRevenue": random.uniform(10, 100),
            "actualRevenue": random.uniform(8, 110),
            "grossMargin": random.uniform(0.3, 0.6),
            "operatingMargin": random.uniform(0.1, 0.4),
            "netIncome": random.uniform(5, 50),
            "yoyGrowth": random.uniform(-0.1, 0.3),
            "highlights": [
                f"Strong performance in {random.choice(['cloud services', 'hardware sales', 'advertising'])}",
                f"Announced new {random.choice(['product', 'service', 'partnership'])}",
                f"Guidance for next quarter exceeds analyst expectations"
            ],
            "guidance": f"Company expects revenue between ${random.uniform(10, 20):.2f}B and ${random.uniform(21, 30):.2f}B for next quarter."
        }
        return jsonify(earnings_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stocks", methods=["GET", "POST"])
def stocks():
    # Initialize variables
    symbols = []
    stock_data = {}
    
    # Define default symbols here (same as you already have in the code)
    default_symbols = [
           "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NFLX", "NVDA", "GOOG", "BABA",
    "INTC", "AMD", "PYPL", "SPY", "BRK-B", "V", "WMT", "DIS", "JNJ", "GE", "INTU", "ADBE",
    "NVDA", "BA", "XOM", "T", "ORCL", "CSCO", "PFE", "UPS", "MCD", "CVX", "BIDU", "GS",

  
    ]
    
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
    # Initialize URLs from form data or session
    if request.method == "POST":
        urls = {
            "technology": [url.strip() for url in request.form.getlist("technology_urls") if url.strip()],
            "health_care": [url.strip() for url in request.form.getlist("health_care_urls") if url.strip()],
            "financials": [url.strip() for url in request.form.getlist("financials_urls") if url.strip()],
            "retail": [url.strip() for url in request.form.getlist("retail_urls") if url.strip()],
            "energy": [url.strip() for url in request.form.getlist("energy_urls") if url.strip()],
            "mining": [url.strip() for url in request.form.getlist("mining_urls") if url.strip()],
            "utilities": [url.strip() for url in request.form.getlist("utilities_urls") if url.strip()],
            "automotive": [url.strip() for url in request.form.getlist("automotive_urls") if url.strip()]
        }
        session['sector_urls'] = urls
    else:
        urls = session.get('sector_urls', {
            sector: [] for sector in SECTORS.keys()
        })
    
    # Get selected sector from URL parameter
    selected_sector = request.args.get('sector', 'technology')
    
    # Initialize news data
    sector_news = []
    sector_urls = urls.get(selected_sector, [])
    
    # Only fetch news if URLs are provided for the selected sector
    if sector_urls:
        for url in sector_urls:
            if url:
                try:
                    news_items = get_news_from_url(url, selected_sector)
                    if news_items:
                        sector_news.extend(news_items)
                except Exception as e:
                    print(f"Error fetching news from {url}: {str(e)}")
    
    # Deduplicate news
    unique_news = []
    seen_titles = set()
    for news in sector_news:
        if isinstance(news, dict) and "title" in news and news["title"] not in seen_titles:
            seen_titles.add(news["title"])
            unique_news.append(news)
    
    return render_template("sector_news.html", 
                         selected_sector=selected_sector,
                         news_data=unique_news[:20],
                         urls=urls,
                         sectors=SECTORS.keys(),
                         has_urls=bool(sector_urls))  # Add this new variable

@app.route("/ph_stocks", methods=["GET", "POST"])
def ph_stocks():
    symbols = []
    stocks_data = []
    news_data = []
    error_message = None
    
    # Sample Philippine stock data (20 stocks)
   
   
    sample_stocks = [
    # Top movers first
    {"symbol": "PX", "name": "Philex Mining Corporation", "last_price": "4.15", "change": "+0.85", "change_pct": "+25.76%", "high": "4.20", "low": "3.50", "volume": "3,125,400", "sector": "Basic Materials"},
    {"symbol": "NOW", "name": "NOW Corporation", "last_price": "2.76", "change": "+0.31", "change_pct": "+12.65%", "high": "2.85", "low": "2.42", "volume": "9,812,100", "sector": "Technology"},
    {"symbol": "VLL", "name": "Vista Land & Lifescapes, Inc.", "last_price": "2.30", "change": "+0.16", "change_pct": "+7.48%", "high": "2.35", "low": "2.05", "volume": "4,425,800", "sector": "Real Estate"},
    {"symbol": "DITO", "name": "DITO CME Holdings Corp.", "last_price": "3.82", "change": "+0.26", "change_pct": "+7.30%", "high": "3.88", "low": "3.58", "volume": "13,405,600", "sector": "Communication Services"},
    {"symbol": "MEG", "name": "Megaworld Corporation", "last_price": "3.50", "change": "+0.18", "change_pct": "+5.42%", "high": "3.60", "low": "3.20", "volume": "7,550,400", "sector": "Real Estate"},
    
    # Popular bluechips refreshed
    {"symbol": "JFC", "name": "Jollibee Foods Corporation", "last_price": "285.00", "change": "+6.40", "change_pct": "+2.30%", "high": "288.00", "low": "278.00", "volume": "2,687,900", "sector": "Consumer Cyclical"},
    {"symbol": "SM", "name": "SM Investments Corporation", "last_price": "1038.50", "change": "+13.75", "change_pct": "+1.34%", "high": "1045.00", "low": "1015.00", "volume": "506,250", "sector": "Conglomerates"},
    {"symbol": "ALI", "name": "Ayala Land, Inc.", "last_price": "37.10", "change": "+0.85", "change_pct": "+2.34%", "high": "37.25", "low": "36.20", "volume": "3,642,800", "sector": "Real Estate"},
    {"symbol": "BDO", "name": "BDO Unibank, Inc.", "last_price": "158.40", "change": "+2.60", "change_pct": "+1.67%", "high": "159.50", "low": "156.00", "volume": "1,465,600", "sector": "Financial Services"},
    {"symbol": "SMPH", "name": "SM Prime Holdings, Inc.", "last_price": "44.50", "change": "+0.75", "change_pct": "+1.71%", "high": "44.75", "low": "43.60", "volume": "2,445,800", "sector": "Real Estate"},

    # Other key stocks
    {"symbol": "GTCAP", "name": "GT Capital Holdings, Inc.", "last_price": "530.00", "change": "+10.00", "change_pct": "+1.92%", "high": "532.00", "low": "520.00", "volume": "92,400", "sector": "Conglomerates"},
    {"symbol": "AP", "name": "Aboitiz Power Corporation", "last_price": "43.00", "change": "+0.65", "change_pct": "+1.54%", "high": "43.30", "low": "42.20", "volume": "1,704,200", "sector": "Utilities"},
    {"symbol": "ACEN", "name": "ACEN Corporation", "last_price": "7.10", "change": "+0.23", "change_pct": "+3.35%", "high": "7.20", "low": "6.80", "volume": "5,532,100", "sector": "Utilities"},
    {"symbol": "MBT", "name": "Metropolitan Bank & Trust Company", "last_price": "63.75", "change": "+0.90", "change_pct": "+1.43%", "high": "64.00", "low": "62.50", "volume": "1,975,400", "sector": "Financial Services"},
    {"symbol": "ICT", "name": "International Container Terminal Services, Inc.", "last_price": "300.20", "change": "+4.60", "change_pct": "+1.56%", "high": "302.00", "low": "295.00", "volume": "255,780", "sector": "Industrials"},

      {"symbol": "GLO", "name": "Globe Telecom, Inc.", "last_price": "2176.25", "change": "-45.75", "change_pct": "-2.06%", "high": "2225.00", "low": "2155.00", "volume": "34,580", "sector": "Communication Services"},
    {"symbol": "TEL", "name": "PLDT Inc.", "last_price": "1587.50", "change": "-39.50", "change_pct": "-2.43%", "high": "1625.00", "low": "1575.00", "volume": "85,740", "sector": "Communication Services"},
    {"symbol": "AC", "name": "Ayala Corporation", "last_price": "793.50", "change": "-28.50", "change_pct": "-3.47%", "high": "820.00", "low": "778.00", "volume": "187,920", "sector": "Conglomerates"},
    {"symbol": "BDO", "name": "BDO Unibank, Inc.", "last_price": "155.80", "change": "-4.60", "change_pct": "-2.87%", "high": "159.00", "low": "152.00", "volume": "1,435,600", "sector": "Financial Services"},
    {"symbol": "AP", "name": "Aboitiz Power Corporation", "last_price": "42.35", "change": "-1.20", "change_pct": "-2.76%", "high": "43.80", "low": "41.50", "volume": "1,654,200", "sector": "Utilities"},
    # New tech and consumer defensive picks
    {"symbol": "MONDE", "name": "Monde Nissin Corporation", "last_price": "14.55", "change": "+0.27", "change_pct": "+1.89%", "high": "14.60", "low": "14.20", "volume": "2,445,700", "sector": "Consumer Defensive"},
    {"symbol": "NIKL", "name": "Nickel Asia Corporation", "last_price": "5.95", "change": "+0.22", "change_pct": "+3.84%", "high": "6.00", "low": "5.70", "volume": "3,782,400", "sector": "Basic Materials"},
    {"symbol": "TECH", "name": "Cirtek Holdings Philippines Corp.", "last_price": "4.60", "change": "+0.32", "change_pct": "+7.47%", "high": "4.70", "low": "4.20", "volume": "3,356,700", "sector": "Technology"},
    {"symbol": "CLI", "name": "Cebu Landmasters, Inc.", "last_price": "3.60", "change": "+0.18", "change_pct": "+5.26%", "high": "3.65", "low": "3.40", "volume": "1,343,800", "sector": "Real Estate"},
    {"symbol": "FOOD", "name": "Alliance Select Foods International", "last_price": "1.02", "change": "+0.07", "change_pct": "+7.37%", "high": "1.05", "low": "0.95", "volume": "5,334,600", "sector": "Consumer Defensive"},
]

    if request.method == "POST":
        stock_symbols_input = request.form.get("stock_symbols", "")
        if stock_symbols_input.strip():
            symbols = [s.strip().upper() for s in stock_symbols_input.split(",")]
            # Filter stocks based on user input
            stocks_data = [stock for stock in sample_stocks if stock["symbol"] in symbols]
            if not stocks_data:
                error_message = "No matching stocks found. Please check your symbols and try again."
        else:
            # If no input, show all stocks
            stocks_data = sample_stocks
            symbols = [stock["symbol"] for stock in sample_stocks]
    else:
        # For GET requests, show all stocks
        stocks_data = sample_stocks
        symbols = [stock["symbol"] for stock in sample_stocks]
    
   
    return render_template("ph_stocks.html", stocks_data=stocks_data, news_data=news_data, symbols=symbols, error_message=error_message)

@app.route('/uk_stocks', methods=['GET', 'POST'])
def uk_stocks():
    # Extended list of UK stocks (LSE symbols)
    all_uk_stocks = [
        'LLOY.L', 'VOD.L', 'BARC.L', 'HSBA.L', 'BP.L', 'TSCO.L', 'RIO.L', 
        'GLEN.L', 'SHELL.L', 'GSK.L', 'AZN.L', 'ULVR.L', 'HSBA.L', 'DGE.L', 
        'REL.L', 'AAL.L', 'NWG.L', 'IMB.L', 'NG.L', 'LGEN.L'
    ]
    
    stocks = []
    error_message = None
    
    if request.method == 'POST':
        stock_symbol = request.form.get('stock_symbol', '').strip().upper()
        if stock_symbol:
            # Check if it's a UK stock (ends with .L or .LON)
            if not (stock_symbol.endswith('.L') or stock_symbol.endswith('.LON')):
                error_message = f"'{stock_symbol}' is not a UK stock. Please search for stocks ending with .L or .LON"
            else:
                data = fetch_stock_data_yahoo(stock_symbol)
                if data:
                    stocks.append(data)
                else:
                    error_message = f"Stock symbol '{stock_symbol}' not found or data unavailable."
    else:
        # If not a POST request, show all UK stocks
        stocks = [data for symbol in all_uk_stocks 
                 if (data := fetch_stock_data_yahoo(symbol))]
    
    return render_template('uk_stocks.html', 
                         stocks=stocks, 
                         error_message=error_message)
def fetch_stock_data_yahoo(symbol):
    try:
        # Get data for the last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Download stock data
        stock = yf.Ticker(symbol)
        hist = stock.history(period='1y')  # Get 1 year of data for better calculations
        
        if hist.empty:
            return None
            
        # Convert to our desired format
        history_data = []
        for date, row in hist.iterrows():
            history_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(row['Open'], 2),
                'high': round(row['High'], 2),
                'low': round(row['Low'], 2),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume'])
            })
        
        # Get company info
        info = stock.info
        company_name = info.get('longName', symbol)
        
        # Calculate 52-week high/low from the data
        fifty_two_week_high = round(hist['High'].max(), 2)
        fifty_two_week_low = round(hist['Low'].min(), 2)
        
        return {
            'symbol': symbol,
            'name': company_name,
            'history': history_data[-30:],  # Last 30 days for display
            'fifty_two_week_high': fifty_two_week_high,
            'fifty_two_week_low': fifty_two_week_low,
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', 'N/A'),
            'dividend_yield': info.get('dividendYield', 0),
            'beta': info.get('beta', 'N/A'),
            'eps': info.get('trailingEps', 'N/A'),
            'description': info.get('longBusinessSummary', '')
        }
        
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        return None

@app.route('/ge_stocks', methods=['GET', 'POST'])
def ge_stocks():
    # Full list of German stock symbols you want to always show
    all_ge_stocks = [
        'SAP.DE', 'BMW.DE', 'VOW3.DE', 'ALV.DE', 'DBK.DE', 
        'BAS.DE', 'BAYN.DE', 'DTE.DE', 'RWE.DE', 'SIE.DE',
        'ADS.DE', 'FRE.DE', 'IFX.DE', 'HEN3.DE', 'LIN.DE'
    ]

    stocks = []
    error_message = None

    # Always fetch all German stocks by default
    stocks = [data for symbol in all_ge_stocks 
              if (data := fetch_stock_data_yahoo(symbol))]

    # Optionally allow additional search and add to the list (if not already included)
    if request.method == 'POST':
        stock_symbol = request.form.get('stock_symbol', '').strip().upper()
        if stock_symbol:
            if not (stock_symbol.endswith('.DE') or stock_symbol.endswith('.F')):
                error_message = f"'{stock_symbol}' is not a German stock. Please search for stocks ending with .DE or .F"
            else:
                data = fetch_stock_data_yahoo(stock_symbol)
                if data:
                    if not any(stock['symbol'] == stock_symbol for stock in stocks):
                        stocks.insert(0, data)  # Add it on top
                else:
                    error_message = f"Stock symbol '{stock_symbol}' not found or data unavailable."

    return render_template('ge_stocks.html', 
                           stocks=stocks, 
                           error_message=error_message)

    
    # Always show default stocks if no specific symbol was searched
    if not stocks and request.method != 'POST':
        stocks = [data for symbol in default_ge_stocks 
                 if (data := fetch_stock_data_yahoo(symbol))]
    
    return render_template('ge_stocks.html', 
                        stocks=stocks, 
                        error_message=error_message)

@app.route("/simulation", methods=["GET", "POST"])
def simulation():
    # Here you can handle any logic for the simulation page if needed
    return render_template("simulation.html")  # Make sure to create this template
@app.route("/analytics")
def analytics():
    return render_template("analytics.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/login")
def login():
    return render_template("login.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Default to 10000 if PORT is not set
    app.run(host="0.0.0.0", port=port)