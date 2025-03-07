from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import concurrent.futures

app = Flask(__name__)

# Add suffix to Philippine stock symbols for Yahoo Finance
def format_symbol(symbol):
    return f"{symbol.strip().upper()}.PS"

# Get stock data using yfinance
def get_stock_data(symbols):
    formatted_symbols = [format_symbol(symbol) for symbol in symbols]
    
    try:
        # Get data for all symbols at once
        data = yf.download(formatted_symbols, period="1d", group_by="ticker")
        
        stocks_data = []
        for i, symbol in enumerate(symbols):
            formatted_symbol = formatted_symbols[i]
            
            # Handle single stock case differently than multiple stocks
            if len(symbols) == 1:
                current_data = data
            else:
                current_data = data[formatted_symbol]
            
            # Skip if no data available
            if current_data.empty:
                continue
                
            # Get company info
            try:
                ticker = yf.Ticker(formatted_symbol)
                company_name = ticker.info.get('longName', symbol)
            except:
                company_name = symbol
            
            # Calculate price change
            last_price = current_data['Close'].iloc[-1]
            prev_close = current_data['Open'].iloc[0]
            change = last_price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else 0
            
            stock_info = {
                'symbol': symbol,
                'name': company_name,
                'last_price': f"₱{last_price:.2f}",
                'change': f"{'+' if change >= 0 else ''}{change:.2f}",
                'change_pct': f"{'+' if change_pct >= 0 else ''}{change_pct:.2f}%",
                'high': f"₱{current_data['High'].iloc[-1]:.2f}",
                'low': f"₱{current_data['Low'].iloc[-1]:.2f}",
                'volume': f"{int(current_data['Volume'].iloc[-1]):,}"
            }
            
            stocks_data.append(stock_info)
            
        return stocks_data
    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return []

# Get Philippine stock market news
def get_news():
    try:
        # Use BusinessWorld as source for Philippine business news
        url = "https://www.bworldonline.com/category/stock-market/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        news_items = []
        # Modify the selector based on the actual structure of the BusinessWorld website
        articles = soup.select("article.elementor-post")[:6]  # Get top 6 news items
        
        for article in articles:
            try:
                title_elem = article.select_one(".elementor-post__title a")
                image_elem = article.select_one("img")
                excerpt_elem = article.select_one(".elementor-post__excerpt p")
                
                title = title_elem.text.strip() if title_elem else "No title available"
                link = title_elem['href'] if title_elem else "#"
                image = image_elem['src'] if image_elem else "https://via.placeholder.com/150"
                content = excerpt_elem.text.strip() if excerpt_elem else "No content available"
                
                news_items.append({
                    'title': title,
                    'link': link,
                    'image': image,
                    'content': content[:150] + "..." if len(content) > 150 else content
                })
            except Exception as e:
                print(f"Error parsing news item: {e}")
                continue
                
        return news_items
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []