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
    if any(word in text for word in ['europe', 'eu', 'european', 'brexit', 'uk', 'germany', 'france']):
        return 'europe'
    elif any(word in text for word in ['asia', 'china', 'japan', 'india', 'korea']):
        return 'asia'
    elif any(word in text for word in ['america', 'us', 'usa', 'united states', 'canada', 'mexico']):
        return 'north_america'
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
    urls = []
    news_data = []
    error_messages = []

    # Default top news sources
    default_news_sources = [
        "https://www.nytimes.com/section/world",
        "https://edition.cnn.com/",
        "https://www.bbc.co.uk/news/world",
        "https://www.msnbc.com/",
        "https://www.cnbc.com/world/?region=world",
        "https://uk.finance.yahoo.com/topic/news",
    ]

    if request.method == "POST":
        urls = [url.strip() for url in request.form.getlist("web_urls") if url.strip()]
        
        # If no URLs provided, use defaults
        if not urls:
            urls = default_news_sources
    else:
        # For initial page load, use defaults
        urls = default_news_sources

    # Scrape each URL using our improved function
    for url in urls:
        try:
            # Fetch top 10 news from each source
            source_news = fetch_top_news(url, max_articles=10)
            if source_news:
                news_data.extend(source_news)
            else:
                error_messages.append(f"Could not extract news from {url}")
        except Exception as e:
            error_messages.append(f"Error processing {url}: {str(e)}")

    # Sort news by date (most recent first)
    news_data = sorted(news_data, key=lambda x: x.get('date', ''), reverse=True)
    
    # Print diagnostics to help with debugging
    print(f"URLs processed: {len(urls)}")
    print(f"News items found: {len(news_data)}")
    print(f"Errors encountered: {len(error_messages)}")
    
    return render_template("current_affairs.html", 
                         news_data=news_data, 
                         urls=urls, 
                         error_messages=error_messages)
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

@app.route("/calendar", methods=["GET", "POST"])
def calendar():
    return render_template("calendar.html")  # Static calendar page (no dynamic data)

@app.route('/stock_reports')
def stock_reports():
    # Get the stock data from the main stocks page
    symbols = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NFLX", "NVDA", "GOOG", "BABA",
    "INTC", "AMD", "PYPL", "SPY", "BRK-B", "V", "WMT", "DIS", "JNJ", "GE", "INTU", "ADBE",
    "NVDA", "BA", "XOM", "T", "ORCL", "CSCO", "PFE", "UPS", "MCD", "CVX", "BIDU", "GS",


]
 # Default symbols
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
                         symbols=symbols)


@app.route("/ph_stocks", methods=["GET", "POST"])
def ph_stocks():
    symbols = []
    stocks_data = []
    news_data = []
    error_message = None
    
    # Sample Philippine stock data (20 stocks)
    sample_stocks = [
        {"symbol": "JFC", "name": "Jollibee Foods Corporation", "last_price": "248.60", "change": "+2.80", "change_pct": "+1.14%", "high": "250.20", "low": "245.40", "volume": "1,245,600"},
        {"symbol": "SM", "name": "SM Investments Corporation", "last_price": "962.00", "change": "+5.50", "change_pct": "+0.57%", "high": "965.00", "low": "952.50", "volume": "352,810"},
        {"symbol": "ALI", "name": "Ayala Land, Inc.", "last_price": "34.20", "change": "-0.30", "change_pct": "-0.87%", "high": "34.60", "low": "34.10", "volume": "2,541,300"},
        {"symbol": "BDO", "name": "BDO Unibank, Inc.", "last_price": "145.70", "change": "+1.20", "change_pct": "+0.83%", "high": "146.50", "low": "144.50", "volume": "875,400"},
        {"symbol": "SMPH", "name": "SM Prime Holdings, Inc.", "last_price": "39.10", "change": "+0.45", "change_pct": "+1.16%", "high": "39.30", "low": "38.65", "volume": "1,658,900"},
        {"symbol": "AC", "name": "Ayala Corporation", "last_price": "765.00", "change": "-5.00", "change_pct": "-0.65%", "high": "770.00", "low": "762.00", "volume": "126,450"},
        {"symbol": "BPI", "name": "Bank of the Philippine Islands", "last_price": "112.50", "change": "+0.70", "change_pct": "+0.63%", "high": "113.00", "low": "111.50", "volume": "532,800"},
        {"symbol": "TEL", "name": "PLDT Inc.", "last_price": "1,536.00", "change": "-8.00", "change_pct": "-0.52%", "high": "1,545.00", "low": "1,530.00", "volume": "54,360"},
        {"symbol": "MER", "name": "Manila Electric Company", "last_price": "384.20", "change": "+2.20", "change_pct": "+0.58%", "high": "386.00", "low": "380.80", "volume": "92,150"},
        {"symbol": "URC", "name": "Universal Robina Corporation", "last_price": "132.10", "change": "-1.40", "change_pct": "-1.05%", "high": "133.50", "low": "131.80", "volume": "423,850"},
        {"symbol": "ICT", "name": "International Container Terminal Services, Inc.", "last_price": "265.80", "change": "+3.60", "change_pct": "+1.37%", "high": "266.20", "low": "262.40", "volume": "156,780"},
        {"symbol": "MEG", "name": "Megaworld Corporation", "last_price": "2.86", "change": "+0.04", "change_pct": "+1.42%", "high": "2.87", "low": "2.83", "volume": "5,842,300"},
        {"symbol": "BLOOM", "name": "Bloomberry Resorts Corporation", "last_price": "8.96", "change": "-0.13", "change_pct": "-1.43%", "high": "9.10", "low": "8.95", "volume": "1,234,500"},
        {"symbol": "MPI", "name": "Metro Pacific Investments Corporation", "last_price": "4.25", "change": "+0.07", "change_pct": "+1.67%", "high": "4.27", "low": "4.20", "volume": "3,125,700"},
        {"symbol": "GTCAP", "name": "GT Capital Holdings, Inc.", "last_price": "578.50", "change": "-3.50", "change_pct": "-0.60%", "high": "582.00", "low": "575.00", "volume": "45,320"},
        {"symbol": "RLC", "name": "Robinsons Land Corporation", "last_price": "16.94", "change": "+0.24", "change_pct": "+1.44%", "high": "16.98", "low": "16.70", "volume": "865,400"},
        {"symbol": "DMC", "name": "DMCI Holdings, Inc.", "last_price": "11.26", "change": "-0.08", "change_pct": "-0.71%", "high": "11.36", "low": "11.22", "volume": "954,300"},
        {"symbol": "AGI", "name": "Alliance Global Group, Inc.", "last_price": "10.84", "change": "+0.16", "change_pct": "+1.50%", "high": "10.88", "low": "10.70", "volume": "1,423,600"},
        {"symbol": "GLO", "name": "Globe Telecom, Inc.", "last_price": "2,112.00", "change": "-14.00", "change_pct": "-0.66%", "high": "2,126.00", "low": "2,106.00", "volume": "18,520"},
        {"symbol": "PGOLD", "name": "Puregold Price Club, Inc.", "last_price": "36.85", "change": "+0.35", "change_pct": "+0.96%", "high": "37.00", "low": "36.50", "volume": "254,700"}
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Default to 10000 if PORT is not set
    app.run(host="0.0.0.0", port=port)