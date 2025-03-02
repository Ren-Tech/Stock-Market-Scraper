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

@app.route("/", methods=["GET", "POST"])
def current_affairs():
    urls = []
    news_data = []
    error_messages = []

    # Default top news sources if user doesn't provide any
    default_news_sources = [
    "https://www.wsj.com/world",
    "https://www.nytimes.com/section/world",
    "https://edition.cnn.com/",
    "https://www.bbc.co.uk/news/world",
    "https://www.msnbc.com/",
    "https://www.cnbc.com/world/?region=world",
    "https://uk.finance.yahoo.com/topic/news",
    "https://www.ft.com/",
    "https://news.sky.com/world/",
    "https://www.france24.com/en/",
    "https://www.dw.com/en/top-stories/s-9097",
    "https://www.bbc.co.uk/news/world/",
    "https://www.reuters.com/",
    "https://www.aljazeera.com/news/",
    "https://lemonde.fr/en/",
    "https://www.japantimes.co.jp/news/",
    "https://www.manilatimes.net/world",

    ]

    if request.method == "POST":
        urls = [url.strip() for url in request.form.getlist("web_urls") if url.strip()]
        
        # If no URLs provided, use defaults
        if not urls:
            urls = default_news_sources
    else:
        # For initial page load, use defaults
        urls = default_news_sources

    # Scrape each URL with improved error handling
    for url in urls:
        try:
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=10)
            
            # Check if request was successful
            if response.status_code != 200:
                error_messages.append(f"Failed to access {url}: Status code {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # More robust scraping with multiple fallback methods
            # Method 1: Try meta tags
            try:
                title = soup.find('title').text
                content_meta = soup.find('meta', {'name': 'description'})
                content = content_meta['content'] if content_meta else ""
                image_meta = soup.find('meta', {'property': 'og:image'})
                image = image_meta['content'] if image_meta else ""
                
                # If we got good data, add it
                if title and content:
                    # Determine category based on content
                    category = assign_category(title + " " + content)
                    
                    news_data.append({
                        'title': title,
                        'content': content[:200] + "..." if len(content) > 200 else content,
                        'image': image or "/static/images/default_news.jpg",  # Use default if no image
                        'link': url,
                        'category': category,
                        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    continue  # If successful, move to next URL
            except Exception as e:
                print(f"Meta tag scraping failed for {url}: {str(e)}")
                # Continue to next method...
                
            # Method 2: Look for news articles and headlines
            try:
                # Common selectors for news sites
                article_selectors = ['article', '.story', '.news-item', '.article', 
                                   'div[data-testid="story"]', '.story-body']
                headline_selectors = ['h1', 'h2', 'h3', '.headline', '.title']
                
                # Try to find articles
                for article_selector in article_selectors:
                    articles = soup.select(article_selector)
                    if articles:
                        # Get up to 3 articles from this source
                        for article in articles[:3]:
                            # Find headline
                            headline = None
                            for headline_selector in headline_selectors:
                                headline_elem = article.select_one(headline_selector)
                                if headline_elem:
                                    headline = headline_elem.text.strip()
                                    break
                                    
                            if not headline:
                                continue
                                
                            # Find content
                            content_elem = article.select_one('p')
                            content = content_elem.text.strip() if content_elem else ""
                            
                            # Find image
                            img = article.select_one('img')
                            image = img['src'] if img and 'src' in img.attrs else ""
                            
                            # Find link
                            link_elem = article.select_one('a')
                            if link_elem and 'href' in link_elem.attrs:
                                article_url = link_elem['href']
                                # Handle relative URLs
                                if article_url.startswith('/'):
                                    article_url = url.rstrip('/') + article_url
                            else:
                                article_url = url
                                
                            # Determine category based on content
                            category = assign_category(headline + " " + content)
                            
                            news_data.append({
                                'title': headline,
                                'content': content[:200] + "..." if len(content) > 200 else content,
                                'image': image or "/static/images/default_news.jpg",
                                'link': article_url,
                                'category': category,
                                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                        
                        if len(news_data) > 0:  # If we found articles, break
                            break
            except Exception as e:
                print(f"Article scraping failed for {url}: {str(e)}")
                error_messages.append(f"Could not extract news from {url}")
                
        except requests.exceptions.RequestException as e:
            error_messages.append(f"Failed to connect to {url}: {str(e)}")
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
    port = int(os.environ.get("PORT", 10000))  # Default to 10000 if PORT is not set
    app.run(host="0.0.0.0", port=port)