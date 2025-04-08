import random
from flask import Flask, render_template, request, jsonify
import pandas as pd
from scraping import get_stock_market_news, get_stock_data, get_stock_specific_news
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import os

app = Flask(__name__)

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
def fetch_top_news(url, max_articles=10):
    """Fetch top news articles from a given URL
    
    Args:
        url (str): The URL of the news website
        max_articles (int): Maximum number of articles to fetch
        
    Returns:
        list: List of news article dictionaries
    """
    news_items = []
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, timeout=10)
        
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Common article container selectors across news sites
        article_selectors = [
            'article', '.story', '.news-item', '.article', 
            'div[data-testid="story"]', '.story-body', '.card',
            '.news-card', '.news-package', '.article-card',
            'li.js-stream-content', '.post', '.entry'
        ]
        
        # Try each selector to find article containers
        articles = []
        for selector in article_selectors:
            found_articles = soup.select(selector)
            if found_articles and len(found_articles) >= 3:
                articles = found_articles
                break
                
        # If we didn't find articles with specific selectors, try a broader approach
        if not articles:
            # Look for div or li elements with certain classes
            articles = soup.find_all(['div', 'li'], class_=lambda c: c and any(
                keyword in str(c).lower() for keyword in 
                ['article', 'story', 'news', 'headline', 'entry', 'post']
            ))
            
        # If still no articles, look for headings with links
        if not articles:
            headings = soup.select('h1 a, h2 a, h3 a')
            articles = [h.parent.parent for h in headings if h.parent and h.parent.parent]
        
        # Process each found article
        count = 0
        processed_links = set()  # To avoid duplicates
        
        for article in articles:
            if count >= max_articles:
                break
                
            # Extract title - check multiple heading tags and common title classes
            title = None
            for heading in ['h1', 'h2', 'h3', 'h4', '.headline', '.title', '[data-test="title"]']:
                title_elem = article.select_one(heading)
                if title_elem:
                    title = title_elem.get_text().strip()
                    break
            
            # If we still don't have a title, look for any linked text that might be a title
            if not title:
                link_elem = article.select_one('a')
                if link_elem:
                    title = link_elem.get_text().strip()
            
            if not title or len(title) < 5:  # Avoid items with no/very short titles
                continue
                
            # Extract link
            link = None
            link_elem = article.select_one('a')
            if link_elem and 'href' in link_elem.attrs:
                link = link_elem['href']
                # Handle relative URLs
                if link.startswith('/'):
                    base_url = "/".join(url.split('/')[:3])  # Get domain part
                    link = base_url + link
                elif not link.startswith('http'):
                    continue  # Skip invalid links
            else:
                continue  # Skip if no link
                
            # Skip if we already processed this link
            if link in processed_links:
                continue
            processed_links.add(link)
                
            # Extract image
            image = None
            img_elem = article.select_one('img')
            if img_elem and 'src' in img_elem.attrs:
                image = img_elem['src']
                # Handle relative URLs
                if image.startswith('/'):
                    base_url = "/".join(url.split('/')[:3])  # Get domain part
                    image = base_url + image
            
            # If no image, try to find picture element or background image
            if not image:
                picture = article.select_one('picture source')
                if picture and 'srcset' in picture.attrs:
                    srcset = picture['srcset'].split(',')[0].strip().split(' ')[0]
                    image = srcset
                    
            # Default image if none found
            if not image:
                image = "/static/images/default_news.jpg"
                
            # Extract content/summary
            content = None
            content_selectors = ['p', '.summary', '.description', '.excerpt', '[data-test="description"]']
            for selector in content_selectors:
                content_elem = article.select_one(selector)
                if content_elem:
                    content = content_elem.get_text().strip()
                    break
                    
            # If no content found, try to get summary from meta tags
            if not content and title:
                meta_desc = soup.find('meta', {'name': 'description'})
                if meta_desc and 'content' in meta_desc.attrs:
                    content = meta_desc['content']
            
            # Default content if none found
            if not content:
                content = f"Read the latest news from {url.split('/')[2]}."
                
            # Determine category
            category = assign_category(title + " " + (content or ""))
            
            # Add to results
            news_items.append({
                'title': title,
                'content': content[:200] + "..." if content and len(content) > 200 else content,
                'image': image,
                'link': link,
                'category': category,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'source': url.split('/')[2]  # Extract domain as source
            })
            count += 1
            
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
                        
                        source_news = fetch_top_news(url, max_articles=10)
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
    # Fetch a broader set of market news, possibly from various sources
    news_data = get_stock_market_news()  # Get stock news data
    
    # Initialize stock symbols (e.g., major indices)
    stock_symbols = [
   
  
    "V",  # Visa Inc.
    "WMT",  # Walmart Inc.
    "PG",  # Procter & Gamble Co.
    "DIS",  # Walt Disney Company
    "NFLX",  # Netflix Inc.
    "AMD",  # Advanced Micro Devices
    "INTC",  # Intel Corporation
    "BA",  # Boeing Company
    "XOM",  # ExxonMobil Corporation
]

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
    # Define sectors with their constituent stocks
    sectors = {
        "technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "INTC", "AMD"],
        "healthcare": ["JNJ", "PFE", "UNH", "ABBV", "MRK"],
        "finance": ["JPM", "BAC", "GS", "WFC", "C", "V", "MA"],
        "consumer": ["AMZN", "WMT", "HD", "MCD", "SBUX", "NKE", "DIS"],
        "energy": ["XOM", "CVX", "COP", "BP", "SLB"],
        "industrial": ["GE", "BA", "CAT", "MMM", "UPS"]
    }
    
    # Initialize empty URLs dictionary for each sector
    urls = {
        "technology": [],
        "healthcare": [],
        "finance": [],
        "consumer": [],
        "energy": [],
        "industrial": [],
        "utilities": [],
        "mining": [],
        "retail": [],
        "automotive": []
    }
    
    # Default to technology sector if none selected
    selected_sector = "technology"
    
    # Handle form submission
    if request.method == "POST" and "sector" in request.form:
        selected_sector = request.form.get("sector")
    elif request.method == "GET" and "sector" in request.args:
        selected_sector = request.args.get("sector")
        
    # Safety check - ensure the selected sector exists
    if selected_sector not in sectors:
        selected_sector = "technology"  # Default fallback
    
    # Get symbols for the selected sector
    symbols = sectors.get(selected_sector, [])
    
    # Initialize empty news data
    sector_news = []
    
    # Try to fetch news if we have the function available
    try:
        # First try to get general market news
        try:
            market_news = get_stock_market_news()
            if market_news:
                sector_news.extend(market_news)
        except Exception as e:
            print(f"Error fetching market news: {str(e)}")
        
        # Then try to get specific stock news (limit to 3 stocks to avoid too many requests)
        for symbol in symbols[:3]:
            try:
                symbol_news = get_stock_specific_news(symbol)
                if symbol_news:
                    sector_news.extend(symbol_news)
            except Exception as e:
                print(f"Error fetching news for {symbol}: {str(e)}")
    except Exception as e:
        print(f"Error with news functions: {str(e)}")
    
    # Initialize empty stock data
    stock_data = {}
    
    # Try to fetch stock data if we have the function available
    try:
        for symbol in symbols:
            try:
                data = get_stock_data(symbol)
                if data is not None and not data.empty:
                    stock_data[symbol] = data
            except Exception as e:
                print(f"Error fetching stock data for {symbol}: {str(e)}")
    except Exception as e:
        print(f"Error with stock data function: {str(e)}")
    
    # Deduplicate news based on title
    unique_news = []
    seen_titles = set()
    
    for news in sector_news:
        # Skip if news item doesn't have a title
        if not isinstance(news, dict) or "title" not in news:
            continue
            
        if news["title"] not in seen_titles:
            seen_titles.add(news["title"])
            unique_news.append(news)
    
    # Return the template with all data we've gathered
    return render_template("sector_news.html", 
                         sectors=sectors,
                         selected_sector=selected_sector,
                         news_data=unique_news[:20],  # Limit to first 20 news items
                         stock_data=stock_data,
                         symbols=symbols,
                         urls=urls)  # Pass the urls dictionary to the template


@app.route("/ph_stocks", methods=["GET", "POST"])
def ph_stocks():
    symbols = []
    stocks_data = []
    news_data = []
    error_message = None
    
    # Sample Philippine stock data (20 stocks)
    sample_stocks = [
    {"symbol": "JFC", "name": "Jollibee Foods Corporation", "last_price": "252.40", "change": "+3.80", "change_pct": "+1.53%", "high": "253.60", "low": "248.20", "volume": "1,356,700"},
    {"symbol": "SM", "name": "SM Investments Corporation", "last_price": "968.50", "change": "+6.50", "change_pct": "+0.68%", "high": "970.00", "low": "958.00", "volume": "378,920"},
    {"symbol": "ALI", "name": "Ayala Land, Inc.", "last_price": "33.85", "change": "-0.35", "change_pct": "-1.02%", "high": "34.30", "low": "33.75", "volume": "2,678,500"},
    {"symbol": "BDO", "name": "BDO Unibank, Inc.", "last_price": "147.20", "change": "+1.50", "change_pct": "+1.03%", "high": "148.00", "low": "146.00", "volume": "952,300"},
    {"symbol": "SMPH", "name": "SM Prime Holdings, Inc.", "last_price": "39.85", "change": "+0.75", "change_pct": "+1.92%", "high": "40.00", "low": "39.10", "volume": "1,725,400"},
    {"symbol": "AC", "name": "Ayala Corporation", "last_price": "758.00", "change": "-7.00", "change_pct": "-0.91%", "high": "766.00", "low": "757.50", "volume": "142,350"},
    {"symbol": "BPI", "name": "Bank of the Philippine Islands", "last_price": "113.80", "change": "+1.30", "change_pct": "+1.16%", "high": "114.20", "low": "112.60", "volume": "567,400"},
    {"symbol": "TEL", "name": "PLDT Inc.", "last_price": "1,528.00", "change": "-8.00", "change_pct": "-0.52%", "high": "1,540.00", "low": "1,526.00", "volume": "62,450"},
    {"symbol": "MER", "name": "Manila Electric Company", "last_price": "387.60", "change": "+3.40", "change_pct": "+0.89%", "high": "388.50", "low": "384.00", "volume": "105,280"},
    {"symbol": "URC", "name": "Universal Robina Corporation", "last_price": "130.50", "change": "-1.60", "change_pct": "-1.21%", "high": "132.80", "low": "130.20", "volume": "456,700"},
    {"symbol": "ICT", "name": "International Container Terminal Services, Inc.", "last_price": "269.40", "change": "+3.60", "change_pct": "+1.35%", "high": "270.00", "low": "265.70", "volume": "168,350"},
    {"symbol": "MEG", "name": "Megaworld Corporation", "last_price": "2.94", "change": "+0.08", "change_pct": "+2.80%", "high": "2.95", "low": "2.86", "volume": "6,124,500"},
    {"symbol": "BLOOM", "name": "Bloomberry Resorts Corporation", "last_price": "8.82", "change": "-0.14", "change_pct": "-1.56%", "high": "9.00", "low": "8.80", "volume": "1,345,200"},
    {"symbol": "MPI", "name": "Metro Pacific Investments Corporation", "last_price": "4.36", "change": "+0.11", "change_pct": "+2.59%", "high": "4.38", "low": "4.25", "volume": "3,457,800"},
    {"symbol": "GTCAP", "name": "GT Capital Holdings, Inc.", "last_price": "574.00", "change": "-4.50", "change_pct": "-0.78%", "high": "578.50", "low": "572.50", "volume": "52,480"},
    {"symbol": "RLC", "name": "Robinsons Land Corporation", "last_price": "17.28", "change": "+0.34", "change_pct": "+2.01%", "high": "17.30", "low": "16.92", "volume": "924,600"},
    {"symbol": "DMC", "name": "DMCI Holdings, Inc.", "last_price": "11.14", "change": "-0.12", "change_pct": "-1.07%", "high": "11.30", "low": "11.12", "volume": "987,500"},
    {"symbol": "AGI", "name": "Alliance Global Group, Inc.", "last_price": "11.06", "change": "+0.22", "change_pct": "+2.03%", "high": "11.10", "low": "10.84", "volume": "1,562,400"},
    {"symbol": "GLO", "name": "Globe Telecom, Inc.", "last_price": "2,095.00", "change": "-17.00", "change_pct": "-0.80%", "high": "2,115.00", "low": "2,090.00", "volume": "22,360"},
    {"symbol": "PGOLD", "name": "Puregold Price Club, Inc.", "last_price": "37.20", "change": "+0.35", "change_pct": "+0.95%", "high": "37.40", "low": "36.85", "volume": "287,500"},
    {"symbol": "AP", "name": "Aboitiz Power Corporation", "last_price": "39.10", "change": "+0.60", "change_pct": "+1.56%", "high": "39.15", "low": "38.45", "volume": "1,248,600"},
    {"symbol": "CEB", "name": "Cebu Air, Inc.", "last_price": "95.20", "change": "-1.60", "change_pct": "-1.65%", "high": "97.50", "low": "95.00", "volume": "372,800"},
    {"symbol": "CNVRG", "name": "Converge ICT Solutions Inc.", "last_price": "18.74", "change": "+0.44", "change_pct": "+2.41%", "high": "18.80", "low": "18.30", "volume": "1,587,200"},
    {"symbol": "FGEN", "name": "First Gen Corporation", "last_price": "21.85", "change": "-0.25", "change_pct": "-1.13%", "high": "22.15", "low": "21.80", "volume": "924,700"},
    {"symbol": "FNI", "name": "Global Ferronickel Holdings, Inc.", "last_price": "3.52", "change": "+0.07", "change_pct": "+2.03%", "high": "3.54", "low": "3.45", "volume": "2,564,300"},
    {"symbol": "GMA7", "name": "GMA Network, Inc.", "last_price": "12.72", "change": "+0.12", "change_pct": "+0.95%", "high": "12.75", "low": "12.60", "volume": "586,400"},
    {"symbol": "LTG", "name": "LT Group, Inc.", "last_price": "9.65", "change": "-0.15", "change_pct": "-1.53%", "high": "9.82", "low": "9.62", "volume": "1,345,600"},
    {"symbol": "MAXS", "name": "Max's Group, Inc.", "last_price": "14.46", "change": "+0.26", "change_pct": "+1.83%", "high": "14.50", "low": "14.20", "volume": "387,900"},
    {"symbol": "PIZZA", "name": "Shakey's Pizza Asia Ventures, Inc.", "last_price": "10.68", "change": "+0.18", "change_pct": "+1.71%", "high": "10.70", "low": "10.50", "volume": "492,500"},
    {"symbol": "RRHI", "name": "Robinsons Retail Holdings, Inc.", "last_price": "69.80", "change": "+0.90", "change_pct": "+1.31%", "high": "69.90", "low": "68.90", "volume": "267,800"},
    {"symbol": "SCC", "name": "Semirara Mining and Power Corporation", "last_price": "32.10", "change": "-0.30", "change_pct": "-0.93%", "high": "32.45", "low": "32.00", "volume": "1,456,700"},
    {"symbol": "SECB", "name": "Security Bank Corporation", "last_price": "146.50", "change": "+1.50", "change_pct": "+1.03%", "high": "146.80", "low": "145.00", "volume": "378,600"},
    {"symbol": "VLL", "name": "Vista Land & Lifescapes, Inc.", "last_price": "1.89", "change": "+0.04", "change_pct": "+2.16%", "high": "1.90", "low": "1.85", "volume": "3,785,400"},
    {"symbol": "WLCON", "name": "Wilcon Depot, Inc.", "last_price": "26.15", "change": "+0.35", "change_pct": "+1.36%", "high": "26.20", "low": "25.80", "volume": "485,700"},
    {"symbol": "2GO", "name": "2GO Group, Inc.", "last_price": "12.25", "change": "-0.15", "change_pct": "-1.21%", "high": "12.42", "low": "12.20", "volume": "256,800"},
    {"symbol": "ANS", "name": "A. Soriano Corporation", "last_price": "7.58", "change": "+0.08", "change_pct": "+1.07%", "high": "7.60", "low": "7.50", "volume": "142,500"},
    {"symbol": "CHIB", "name": "China Banking Corporation", "last_price": "29.20", "change": "+0.30", "change_pct": "+1.04%", "high": "29.25", "low": "28.90", "volume": "372,800"},
    {"symbol": "DD", "name": "DoubleDragon Properties Corp.", "last_price": "9.36", "change": "+0.16", "change_pct": "+1.74%", "high": "9.38", "low": "9.20", "volume": "485,900"},
    {"symbol": "FPH", "name": "First Philippine Holdings Corporation", "last_price": "79.10", "change": "+0.60", "change_pct": "+0.76%", "high": "79.20", "low": "78.50", "volume": "256,800"},
    {"symbol": "ION", "name": "ION Energy Corporation", "last_price": "1.28", "change": "+0.03", "change_pct": "+2.40%", "high": "1.29", "low": "1.25", "volume": "1,345,600"},
    {"symbol": "JGS", "name": "JG Summit Holdings, Inc.", "last_price": "62.95", "change": "+0.55", "change_pct": "+0.88%", "high": "63.00", "low": "62.40", "volume": "372,800"},
    {"symbol": "NOW", "name": "Now Corporation", "last_price": "1.12", "change": "+0.02", "change_pct": "+1.82%", "high": "1.13", "low": "1.10", "volume": "2,485,900"},
    {"symbol": "PAL", "name": "PAL Holdings, Inc.", "last_price": "8.75", "change": "-0.15", "change_pct": "-1.69%", "high": "8.92", "low": "8.72", "volume": "485,900"},
    {"symbol": "PSE", "name": "The Philippine Stock Exchange, Inc.", "last_price": "186.80", "change": "+1.80", "change_pct": "+0.97%", "high": "187.00", "low": "185.00", "volume": "145,600"},
    {"symbol": "PX", "name": "Philex Mining Corporation", "last_price": "3.25", "change": "+0.05", "change_pct": "+1.56%", "high": "3.26", "low": "3.20", "volume": "1,356,700"},
    {"symbol": "RFM", "name": "RFM Corporation", "last_price": "4.58", "change": "+0.08", "change_pct": "+1.78%", "high": "4.60", "low": "4.50", "volume": "372,800"},
    {"symbol": "ROCK", "name": "Rockwell Land Corporation", "last_price": "1.38", "change": "+0.03", "change_pct": "+2.22%", "high": "1.39", "low": "1.35", "volume": "485,900"},
    {"symbol": "SPC", "name": "Splash Corporation", "last_price": "0.87", "change": "+0.02", "change_pct": "+2.35%", "high": "0.88", "low": "0.85", "volume": "1,345,600"},
    {"symbol": "SSI", "name": "SSI Group, Inc.", "last_price": "2.14", "change": "+0.04", "change_pct": "+1.90%", "high": "2.15", "low": "2.10", "volume": "372,800"},
    {"symbol": "STI", "name": "STI Education Systems Holdings, Inc.", "last_price": "0.97", "change": "+0.02", "change_pct": "+2.11%", "high": "0.98", "low": "0.95", "volume": "485,900"},
    {"symbol": "TECH", "name": "TKC Steel Corporation", "last_price": "1.53", "change": "+0.03", "change_pct": "+2.00%", "high": "1.54", "low": "1.50", "volume": "1,345,600"},
    {"symbol": "VITA", "name": "Vitarich Corporation", "last_price": "1.23", "change": "+0.03", "change_pct": "+2.50%", "high": "1.24", "low": "1.20", "volume": "372,800"},
    {"symbol": "VUL", "name": "Vulcan Industrial & Mining Corporation", "last_price": "0.77", "change": "+0.02", "change_pct": "+2.67%", "high": "0.78", "low": "0.75", "volume": "485,900"}
]
    
    # Sample news data
    sample_news = [
        {
            "title": "Philippine Stock Market Closes Higher on Economic Optimism",
            "content": "The Philippine Stock Exchange index closed higher today as investors remain optimistic about economic recovery despite global challenges.",
            "image": "https://via.placeholder.com/150",
            "link": "#"
        },
        {
            "title": "Jollibee Foods Corporation Reports Strong Q1 Earnings",
            "content": "JFC announced better-than-expected first quarter results, with domestic sales up 15% year-over-year.",
            "image": "https://via.placeholder.com/150",
            "link": "#"
        },
        {
            "title": "SM Investments Expands Retail Footprint in Provincial Areas",
            "content": "SM plans to open 15 new stores in emerging provincial markets by the end of the year.",
            "image": "https://via.placeholder.com/150",
            "link": "#"
        },
        {
            "title": "Ayala Land Launches New Sustainable Development Project",
            "content": "ALI introduces eco-friendly residential development in Cavite featuring renewable energy solutions.",
            "image": "https://via.placeholder.com/150",
            "link": "#"
        }
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
    
    # Always include news data
    news_data = sample_news
    
    return render_template("ph_stocks.html", stocks_data=stocks_data, news_data=news_data, symbols=symbols, error_message=error_message)
@app.route("/simulation", methods=["GET", "POST"])
def simulation():
    # Here you can handle any logic for the simulation page if needed
    return render_template("simulation.html")  # Make sure to create this template
@app.route("/analytics")
def analytics():
    return render_template("analytics.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Default to 10000 if PORT is not set
    app.run(host="0.0.0.0", port=port)