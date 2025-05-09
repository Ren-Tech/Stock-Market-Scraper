import random
from flask import Flask, redirect, render_template, request, jsonify, session
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
from urllib.parse import urlparse, urljoin
from flask import url_for
import logging
from flask import session, flash
from functools import wraps
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a secret key for session management
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Add login credentials (in production, use a proper database)
VALID_USERS = {
    'oxbrigdeit@gmail.com': 'solutions2025',
}
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
# Configure request headers with multiple user agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Mobile/15E148 Safari/604.1'
]

# Dictionary of site-specific selectors for better targeting
SITE_SPECIFIC_SELECTORS = {
    'msnbc.com': {
        'article': '.gs-c-promo, article, .article-body, .info-card, .content-card',
        'title': '.gs-c-promo-heading__title, h1, h2, h3, .headline, .card-headline',
        'content': '.gs-c-promo-summary, .article-body__content, .info-card__content, p, .dek',
        'link': 'a',
        'image': 'img',
        'date': 'time, .date, .timestamp, .published-date'
    },
    'cnbc.com': {
        'article': '.Card-titleContainer, .summary, .LatestNews-item, .Card-standardBreakerCard, article',
        'title': '.Card-title, .headline, .title, h1, h2, h3',
        'content': '.Card-description, .desc, .summary, p, .card-text',
        'link': 'a',
        'image': 'img',
        'date': 'time, .time, .Card-time, .timestamp'
    },
    'batimes.com': {
        'article': 'article, .article, .news-article, .card',
        'title': 'h1, h2, h3, .article-title, .headline',
        'content': '.article-summary, .lead, p, .article-text',
        'link': 'a',
        'image': 'img',
        'date': '.article-date, time, .published-date'
    },
    'apnews.com': {
        'article': '.FeedCard, .CardHeadline, article, .Article, .hub-card',
        'title': '.CardHeadline-headlineText, h1, h2, h3, .headline',
        'content': '.CardHeadline-description, .content-text, p, .dek',
        'link': 'a',
        'image': 'img',
        'date': 'time, .timestamp, .published'
    },
    'folha.uol.com.br': {
        'article': '.c-headline, .c-list-links, article, .c-news-item',
        'title': '.c-headline__title, h1, h2, h3, .title',
        'content': '.c-headline__summary, p, .summary, .content',
        'link': 'a',
        'image': 'img',
        'date': '.c-headline__dateline, time, .date'
    },
    'france24.com': {
        'article': '.o-layout-list__item, article, .news-card, .m-item-list-article',
        'title': '.article__title, h1, h2, h3, .title',
        'content': '.article__desc, .article__summary, p, .desc',
        'link': 'a',
        'image': 'img',
        'date': '.article__date, time, .date'
    },
    'asia.nikkei.com': {
        'article': '.ezil__article, article, .article-card, .news-item',
        'title': '.ezil__title, h1, h2, h3, .headline',
        'content': '.ezil__subtitle, .ezil__summary, p, .summary',
        'link': 'a',
        'image': 'img',
        'date': '.ezil__date, time, .date'
    },
    'nhk.or.jp': {
        'article': '.p-article, article, .m-news-item, .news-card',
        'title': '.p-article__title, h1, h2, h3, .title',
        'content': '.p-article__text, p, .summary, .content',
        'link': 'a',
        'image': 'img',
        'date': '.p-article__date, time, .date'
    },
    'cnn.com': {
        'article': 'article, div.container__item, div.card, .card--section, .el__storyelement--standard',
        'title': 'span.container__headline-text, h3.card__headline, .headline, h1, h2, h3',
        'content': 'div.container__description, div.card__description, .description, p',
        'link': 'a',
        'image': 'img',
        'date': '.timestamp, time, .date'
    }
}

# Helper function to clean text
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
        return 'world'  # Default categor
def fetch_top_news(url, max_articles=20):
    """
    Fetch top news articles from a given URL with enhanced support for various news sites
    
    Args:
        url (str): The URL of the news website
        max_articles (int): Maximum number of articles to fetch
        
    Returns:
        list: List of news article dictionaries
    """
    news_items = []
    domain = urlparse(url).netloc.replace('www.', '')
    
    # Determine if we should use site-specific selectors
    site_key = next((k for k in SITE_SPECIFIC_SELECTORS.keys() if k in domain), None)
    
    logger.info(f"Fetching news from {url} (Site key: {site_key})")
    
    try:
        # Use a random user agent for each request
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
        # Handle RSS feeds
        if any(ext in url.lower() for ext in ['rss', 'feed', 'xml']):
            logger.info(f"Processing as RSS feed: {url}")
            feed = feedparser.parse(url)
            
            if not feed.entries:
                logger.warning(f"No entries found in feed: {url}")
                return []
                
            for entry in feed.entries[:max_articles]:
                title = clean_text(entry.get('title', 'No title'))
                description = clean_text(entry.get('description', title))
                link = entry.get('link', url)
                date = entry.get('published', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                # Try to get image from media content or enclosures
                image = None
                if 'media_content' in entry and entry.media_content:
                    media = entry.media_content[0]
                    if 'url' in media:
                        image = media.url
                elif 'enclosures' in entry and entry.enclosures:
                    for enclosure in entry.enclosures:
                        if 'type' in enclosure and enclosure.type.startswith('image'):
                            image = enclosure.href
                            break
                
                news_items.append({
                    'title': title,
                    'content': description[:200] + "..." if description and len(description) > 200 else description,
                    'image': image or "/static/images/default_news.jpg",
                    'link': link,
                    'category': assign_category(title + " " + description),
                    'date': date,
                    'source': domain
                })
                
            logger.info(f"Found {len(news_items)} articles in RSS feed")
            return news_items
        
        # Make HTTP request with retries
        max_retries = 3
        retry_count = 0
        session = requests.Session()
        
        while retry_count < max_retries:
            try:
                # Add delay to avoid rate limiting
                if retry_count > 0:
                    time.sleep(2)
                
                logger.info(f"Making request to {url} (Attempt {retry_count+1}/{max_retries})")
                response = session.get(url, headers=headers, timeout=15)
                
                # Check if we need to handle cookies or redirects
                if response.status_code == 403 or response.status_code == 301 or response.status_code == 302:
                    logger.info(f"Received status code {response.status_code}, retrying with cookies")
                    response = session.get(url, headers=headers, timeout=15, allow_redirects=True)
                
                if response.status_code != 200:
                    logger.warning(f"URL returned status {response.status_code}: {url}")
                    retry_count += 1
                    continue
                
                break  # Success, exit retry loop
                
            except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                logger.warning(f"Request failed (Attempt {retry_count+1}/{max_retries}): {str(e)}")
                retry_count += 1
                
                # If all retries failed
                if retry_count >= max_retries:
                    logger.error(f"All retry attempts failed for {url}")
                    return []
        
        # Try different parsers if the default one fails
        for parser in ['html.parser', 'lxml', 'html5lib']:
            try:
                soup = BeautifulSoup(response.content, parser)
                break
            except Exception as e:
                logger.warning(f"Parser {parser} failed: {str(e)}")
                if parser == 'html5lib':  # Last parser option
                    logger.error("All parsers failed")
                    return []
        
        # Use site-specific selectors if available
        if site_key:
            selectors = SITE_SPECIFIC_SELECTORS[site_key]
            logger.info(f"Using site-specific selectors for {site_key}")
            
            # Try to find articles using site-specific selectors
            articles = soup.select(selectors['article'])
            
            # If no articles found with the first selector, try a more generic approach
            if not articles:
                logger.info(f"No articles found with site-specific selector, trying generic selectors")
                articles = soup.find_all(['article', 'div', 'li', 'section'], 
                                        class_=lambda c: c and any(term in c.lower() 
                                                                for term in ['article', 'story', 'news', 'card', 'item', 'entry']))
            
            # Process each article
            for article in articles[:max_articles]:
                try:
                    # Try to find title
                    title_elem = article.select_one(selectors['title'])
                    if not title_elem:
                        continue
                    title = clean_text(title_elem.get_text())
                    
                    # Try to find content
                    content_elem = article.select_one(selectors['content'])
                    content = clean_text(content_elem.get_text()) if content_elem else title
                    
                    # Skip if content is generic default text
                    if any(default_text in content.lower() for default_text in 
                           ["view the latest news", "breaking news today", "all rights reserved"]):
                        continue
                    
                    # Try to find link
                    link_elem = article.select_one(selectors['link'])
                    if not link_elem or not link_elem.has_attr('href'):
                        continue
                    
                    link = link_elem['href']
                    if link.startswith('/'):
                        link = urljoin(url, link)
                    
                    # Try to find image
                    image_elem = article.select_one(selectors['image'])
                    image = None
                    
                    if image_elem:
                        if image_elem.has_attr('src'):
                            image = image_elem['src']
                        elif image_elem.has_attr('data-src'):
                            image = image_elem['data-src']
                        elif image_elem.has_attr('srcset'):
                            srcset = image_elem['srcset'].split(',')[0]
                            image = srcset.split(' ')[0]
                            
                    if image and image.startswith('/'):
                        image = urljoin(url, image)
                    
                    # Try to find date
                    date_elem = article.select_one(selectors['date'])
                    date = None
                    
                    if date_elem:
                        if date_elem.has_attr('datetime'):
                            date = date_elem['datetime']
                        else:
                            date = clean_text(date_elem.get_text())
                            
                    if not date:
                        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Add article to results
                    news_items.append({
                        'title': title,
                        'content': content[:200] + "..." if content and len(content) > 200 else content,
                        'image': image or "/static/images/default_news.jpg",
                        'link': link,
                        'category': assign_category(title + " " + content),
                        'date': date,
                        'source': domain
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing article: {str(e)}")
                    continue
                    
        else:
            # Generic article detection for sites without specific selectors
            logger.info("Using generic article detection")
            
            # Common article selectors
            article_selectors = [
                'article', '.story', '.news-item', '.article', 
                'div[data-testid="story"]', '.story-body', '.card',
                '.news-card', '.news-package', '.article-card',
                'li.js-stream-content', '.post', '.entry',
                '.item', '.news', '.headline-list li', '.story-wrapper'
            ]
            
            articles_found = False
            
            # Try each selector until we find articles
            for selector in article_selectors:
                try:
                    articles = soup.select(selector)
                    
                    if articles:
                        logger.info(f"Found {len(articles)} elements with selector: {selector}")
                        articles_found = True
                        
                        for article in articles[:max_articles]:
                            try:
                                # Find title (try multiple approaches)
                                title_elem = None
                                for title_selector in ['h1', 'h2', 'h3', 'h4', '.title', '.headline', '.heading']:
                                    title_elem = article.select_one(title_selector)
                                    if title_elem:
                                        break
                                        
                                if not title_elem:
                                    continue
                                    
                                title = clean_text(title_elem.get_text())
                                
                                # Find content
                                content_elem = None
                                for content_selector in ['p', '.summary', '.description', '.content', '.excerpt', '.teaser']:
                                    content_elem = article.select_one(content_selector)
                                    if content_elem:
                                        break
                                        
                                content = clean_text(content_elem.get_text()) if content_elem else title
                                
                                # Skip generic content
                                if len(content) < 20 or any(default_text in content.lower() for default_text in 
                                                        ["view the latest news", "breaking news today", "all rights reserved"]):
                                    continue
                                
                                # Find link
                                link_elem = article.find('a', href=True)
                                if not link_elem:
                                    continue
                                    
                                link = link_elem['href']
                                if link.startswith('/'):
                                    link = urljoin(url, link)
                                    
                                # Find image (try multiple attributes)
                                image_elem = article.find('img')
                                image = None
                                
                                if image_elem:
                                    for attr in ['src', 'data-src', 'data-original', 'data-lazy-src']:
                                        if image_elem.has_attr(attr):
                                            image = image_elem[attr]
                                            break
                                            
                                    if not image and image_elem.has_attr('srcset'):
                                        srcset = image_elem['srcset'].split(',')[0]
                                        image = srcset.split(' ')[0]
                                        
                                if image and image.startswith('/'):
                                    image = urljoin(url, image)
                                
                                # Find date
                                date_elem = article.find('time') or article.select_one('.date, .timestamp, .published')
                                date = None
                                
                                if date_elem:
                                    if date_elem.has_attr('datetime'):
                                        date = date_elem['datetime']
                                    else:
                                        date = clean_text(date_elem.get_text())
                                        
                                if not date:
                                    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                # Add article to results
                                news_items.append({
                                    'title': title,
                                    'content': content[:200] + "..." if content and len(content) > 200 else content,
                                    'image': image or "/static/images/default_news.jpg",
                                    'link': link,
                                    'category': assign_category(title + " " + content),
                                    'date': date,
                                    'source': domain
                                })
                                
                            except Exception as e:
                                logger.warning(f"Error processing generic article: {str(e)}")
                                continue
                                
                        # If we found articles with this selector, break the loop
                        if news_items:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {str(e)}")
                    continue
            
            # If no articles found with standard selectors, try a broad approach
            if not articles_found or not news_items:
                logger.info("No articles found with standard selectors. Trying broader approach.")
                
                # Look for any link with text that might be a news headline
                links = soup.find_all('a', href=True)
                processed_links = set()
                
                for link in links:
                    if len(news_items) >= max_articles:
                        break
                        
                    try:
                        href = link['href']
                        
                        # Skip duplicates, short links, anchors, and non-news links
                        if (href in processed_links or len(href) < 5 or href.startswith('#') or 
                            any(x in href.lower() for x in ['login', 'signin', 'subscribe', 'account'])):
                            continue
                            
                        processed_links.add(href)
                        
                        # Get link text and skip if too short
                        link_text = clean_text(link.get_text())
                        if len(link_text) < 15 or len(link_text) > 150:
                            continue
                            
                        # Normalize link
                        if href.startswith('/'):
                            href = urljoin(url, href)
                            
                        # Find image near the link
                        image = None
                        parent = link.parent
                        sibling = link.next_sibling
                        
                        # Look for image in parent or sibling elements
                        for elem in [link, parent, sibling]:
                            if elem:
                                img = elem.find('img')
                                if img and img.has_attr('src'):
                                    image = img['src']
                                    if image.startswith('/'):
                                        image = urljoin(url, image)
                                    break
                        
                        # Add article to results
                        news_items.append({
                            'title': link_text,
                            'content': link_text,  # Use title as content since we don't have content
                            'image': image or "/static/images/default_news.jpg",
                            'link': href,
                            'category': assign_category(link_text),
                            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'source': domain
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error processing link: {str(e)}")
                        continue
        
        # Make sure all news items have all required fields
        for item in news_items:
            for field in ['title', 'content', 'link', 'image', 'date', 'source', 'category']:
                if field not in item or not item[field]:
                    if field in ['title', 'content', 'link']:
                        # These fields are required - remove item if missing
                        news_items.remove(item)
                        break
                    else:
                        # These fields can have defaults
                        if field == 'image':
                            item[field] = "/static/images/default_news.jpg"
                        elif field == 'date':
                            item[field] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        elif field == 'source':
                            item[field] = domain
                        elif field == 'category':
                            item[field] = 'world'
        
        # Remove duplicates (based on title)
        titles_seen = set()
        unique_news_items = []
        
        for item in news_items:
            if item['title'] not in titles_seen:
                titles_seen.add(item['title'])
                unique_news_items.append(item)
                
        news_items = unique_news_items
        
        logger.info(f"Successfully scraped {len(news_items)} articles from {url}")
        return news_items
        
    except Exception as e:
        logger.error(f"Error fetching news from {url}: {str(e)}", exc_info=True)
        return []

@app.route("/current_affairs", methods=["GET", "POST"])
def current_affairs():
    # Initialize logging for this request
    logger.info(f"Current Affairs page accessed by {request.remote_addr}")
    
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
    urls_provided = False

    if request.method == "POST":
        logger.info("Current Affairs form submitted")
        
        # Log form data received
        form_data = {k: v for k, v in request.form.items() if not k.endswith('_urls')}
        logger.debug(f"Form data received: {form_data}")
        
        # Process URLs for each region
        for region in urls.keys():
            region_urls = [url.strip() for url in request.form.getlist(f"{region}_urls") if url.strip()]
            urls[region] = region_urls
            
            if region_urls:
                urls_provided = True
                logger.debug(f"URLs provided for {region}: {region_urls}")
            else:
                logger.debug(f"No URLs provided for {region}")

        if urls_provided:
            logger.info(f"Processing {sum(len(urls[r]) for r in urls)} URLs across all regions")
            
            for region, region_urls in urls.items():
                if not region_urls:
                    continue
                    
                logger.info(f"Processing {len(region_urls)} URLs for {region}")
                
                for url in region_urls:
                    try:
                        # Validate and normalize URL
                        if not url.startswith(('http://', 'https://')):
                            url = 'https://' + url
                            logger.debug(f"Added protocol to URL: {url}")
                        
                        # Fetch news from URL
                        logger.info(f"Fetching news from {url}")
                        source_news = fetch_top_news(url, max_articles=20)
                        
                        if source_news:
                            logger.info(f"Found {len(source_news)} articles at {url}")
                            for news_item in source_news:
                                news_item['category'] = region
                            news_data.extend(source_news)
                        else:
                            msg = f"Could not extract news from {url} (Region: {region})"
                            error_messages.append(msg)
                            logger.warning(msg)
                            
                    except requests.exceptions.Timeout:
                        msg = f"Timeout when trying to access {url}"
                        error_messages.append(msg)
                        logger.error(msg)
                    except requests.exceptions.RequestException as e:
                        msg = f"Network error accessing {url}: {str(e)}"
                        error_messages.append(msg)
                        logger.error(msg)
                    except Exception as e:
                        msg = f"Error processing {url} (Region: {region}): {str(e)}"
                        error_messages.append(msg)
                        logger.error(msg, exc_info=True)
        else:
            msg = "No URLs provided to fetch news"
            error_messages.append(msg)
            logger.warning(msg)

    # Process and sort news data
    if news_data:
        logger.info(f"Total articles collected: {len(news_data)}")
        news_data = sorted(news_data, key=lambda x: x.get('date', ''), reverse=True)
        
        # Log sample of collected articles
        sample_articles = [f"{n['title']} ({n['source']})" for n in news_data[:3]]
        logger.debug(f"Sample articles: {sample_articles}")
    else:
        logger.info("No news articles collected in this request")

    # Log any error messages
    if error_messages:
        logger.warning(f"Encountered {len(error_messages)} errors during processing")
        for error in error_messages:
            logger.debug(f"Error detail: {error}")

    return render_template("current_affairs.html", 
                         news_data=news_data, 
                         urls=urls, 
                         error_messages=error_messages,
                         urls_provided=urls_provided)



@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in VALID_USERS and VALID_USERS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            return jsonify({'success': True, 'redirect': url_for('current_affairs')})
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'})
    
    if session.get('logged_in'):
        return redirect(url_for('current_affairs'))
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Add login_required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function@app.route("/current_affairs", methods=["GET", "POST"])


@app.route("/market_news", methods=["GET", "POST"])
def market_news():
    # Initialize or get market URLs from session
    market_urls = session.get('market_urls', {
        "us": [], "uk": [], "ge": [], "fr": [], 
        "china": [], "europe": [], "asia": [], "south_america": []
    })
    
    selected_market = request.args.get("market", "us")
    
    if request.method == "POST":
        selected_market = request.form.get("market", selected_market)
        for market in market_urls.keys():
            urls = request.form.getlist(f"{market}_urls")
            market_urls[market] = [url.strip() for url in urls if url.strip()]
        session['market_urls'] = market_urls
    
    news_data = []
    if market_urls.get(selected_market):
        for url in market_urls[selected_market]:
            try:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                
                scraped_news = scrape_news_from_url(url)
                if scraped_news:
                    for item in scraped_news:
                        item['region'] = selected_market.replace('_', ' ').title()
                        item.setdefault('title', 'Untitled News')
                        item.setdefault('content', 'No content available')
                        item.setdefault('link', url)
                        item.setdefault('source', urlparse(url).netloc)
                        if 'date' not in item:
                            item['date'] = extract_date_from_url(url) or datetime.now().strftime("%Y-%m-%d")
                    
                    news_data.extend(scraped_news)
                else:
                    flash(f"No articles found at {url}", "warning")
            
            except requests.exceptions.Timeout:
                flash(f"Timeout when trying to scrape {url}", "danger")
            except Exception as e:
                flash(f"Error scraping {url}: {str(e)}", "danger")
                print(f"Error scraping {url}: {str(e)}")
    
    return render_template("market_news.html",
                         news_data=news_data,
                         market_urls=market_urls,
                         selected_market=selected_market)

def scrape_news_from_url(url):
    """Enhanced news scraping function with better error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)  # Increased timeout
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []
        
        # Common article selectors
        article_selectors = [
            'article',
            '.article',
            '.post',
            '.story',
            '.news-item',
            '[itemtype="http://schema.org/NewsArticle"]',
            '.teaser',
            '.card',
            'div[role="article"]'
        ]
        
        for selector in article_selectors:
            article_elements = soup.select(selector, limit=10)
            if article_elements:
                for article in article_elements:
                    try:
                        # Extract elements with fallbacks
                        title_elem = (article.find(['h1', 'h2', 'h3']) or 
                                    article.find(class_=re.compile('title|headline', re.I)))
                        
                        link_elem = article.find('a')
                        content_elem = (article.find('p') or 
                                      article.find(class_=re.compile('content|summary|description', re.I)))
                        
                        image_elem = article.find('img')
                        date_elem = (article.find('time') or 
                                   article.find(class_=re.compile('date|timestamp|time', re.I)))
                        
                        if title_elem:
                            title = title_elem.get_text().strip()
                            content = content_elem.get_text().strip()[:200] + '...' if content_elem else ''
                            
                            # Handle relative URLs
                            link = url
                            if link_elem and link_elem.get('href'):
                                link = urljoin(url, link_elem['href'])
                            
                            image = None
                            if image_elem and image_elem.get('src'):
                                image = urljoin(url, image_elem['src'])
                            
                            date = (date_elem.get_text().strip() 
                                  if date_elem 
                                  else extract_date_from_url(url) 
                                  or datetime.now().strftime("%Y-%m-%d"))
                            
                            articles.append({
                                'title': title,
                                'content': content,
                                'link': link,
                                'image': image,
                                'date': date,
                                'source': urlparse(url).netloc
                            })
                    except Exception as e:
                        print(f"Error parsing article element: {str(e)}")
                        continue
                
                if articles:
                    return articles
        
        return None
    
    except requests.exceptions.RequestException as e:
        print(f"Request error for {url}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error scraping {url}: {str(e)}")
        return None

def extract_date_from_url(url):
    """Extract date from URL patterns"""
    try:
        date_match = re.search(r'/(20\d{2})[/-](0?[1-9]|1[0-2])[/-](0?[1-9]|[12][0-9]|3[01])/', url)
        if date_match:
            return f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        return None
    except:
        return None
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

@app.route('/shorten-url', methods=['POST'])
def shorten_url():
    data = request.get_json()
    long_url = data.get('url')
    short = generate_short_url(long_url)  # Your custom logic
    return jsonify({"short_url": short})

    
    
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
  {"symbol": "PX", "name": "Philex Mining Corporation", "last_price": "6.25", "change": "+0.50", "change_pct": "+8.70%", "high": "6.42", "low": "6.10", "volume": "15,983,600", "sector": "Basic Materials"},
    
    {"symbol": "BDO", "name": "BDO Unibank, Inc.", "last_price": "172.50", "change": "+3.80", "change_pct": "+2.25%", "high": "173.20", "low": "170.10", "volume": "4,251,300", "sector": "Financial Services"},
    
    {"symbol": "AC", "name": "Ayala Corporation", "last_price": "765.00", "change": "-12.30", "change_pct": "-1.58%", "high": "775.50", "low": "762.00", "volume": "210,450", "sector": "Conglomerates"},
    
    {"symbol": "AP", "name": "Aboitiz Power Corporation", "last_price": "44.85", "change": "+1.15", "change_pct": "+2.63%", "high": "45.10", "low": "44.25", "volume": "892,700", "sector": "Utilities"},
    
    {"symbol": "NOW", "name": "NOW Corporation", "last_price": "2.18", "change": "-0.32", "change_pct": "-12.80%", "high": "2.25", "low": "2.12", "volume": "11,543,200", "sector": "Technology"},
    
    {"symbol": "GLO", "name": "Globe Telecom, Inc.", "last_price": "2,310.75", "change": "+46.50", "change_pct": "+2.05%", "high": "2,315.00", "low": "2,280.50", "volume": "42,380", "sector": "Communication Services"},
    
    {"symbol": "GTCAP", "name": "GT Capital Holdings, Inc.", "last_price": "535.25", "change": "+14.75", "change_pct": "+2.84%", "high": "538.00", "low": "522.50", "volume": "45,120", "sector": "Conglomerates"},
    
    {"symbol": "TEL", "name": "PLDT Inc.", "last_price": "1,495.00", "change": "-37.50", "change_pct": "-2.45%", "high": "1,510.25", "low": "1,490.00", "volume": "92,340", "sector": "Communication Services"},
    
    {"symbol": "SMPH", "name": "SM Prime Holdings, Inc.", "last_price": "25.80", "change": "+1.20", "change_pct": "+4.88%", "high": "26.10", "low": "25.50", "volume": "14,320,600", "sector": "Real Estate"},
    
    {"symbol": "VLL", "name": "Vista Land & Lifescapes, Inc.", "last_price": "1.85", "change": "-0.28", "change_pct": "-13.15%", "high": "1.95", "low": "1.82", "volume": "5,732,400", "sector": "Real Estate"},
    
    # Added 7 more stocks
    {"symbol": "JFC", "name": "Jollibee Foods Corporation", "last_price": "287.40", "change": "+12.60", "change_pct": "+4.58%", "high": "290.00", "low": "275.80", "volume": "1,247,300", "sector": "Consumer Cyclical"},
    
    {"symbol": "MBT", "name": "Metropolitan Bank & Trust Company", "last_price": "63.75", "change": "+1.25", "change_pct": "+2.00%", "high": "64.10", "low": "62.90", "volume": "2,154,800", "sector": "Financial Services"},
    
    {"symbol": "PGOLD", "name": "Puregold Price Club, Inc.", "last_price": "32.15", "change": "-2.85", "change_pct": "-8.14%", "high": "33.50", "low": "31.90", "volume": "3,542,700", "sector": "Consumer Defensive"},
    
    {"symbol": "ALI", "name": "Ayala Land, Inc.", "last_price": "34.70", "change": "+1.85", "change_pct": "+5.63%", "high": "35.00", "low": "33.80", "volume": "8,974,500", "sector": "Real Estate"},
    
    {"symbol": "MEG", "name": "Megaworld Corporation", "last_price": "2.52", "change": "+0.35", "change_pct": "+16.13%", "high": "2.58", "low": "2.41", "volume": "21,657,400", "sector": "Real Estate"},
    
    {"symbol": "DITO", "name": "DITO CME Holdings Corp.", "last_price": "1.87", "change": "-0.41", "change_pct": "-17.98%", "high": "2.15", "low": "1.78", "volume": "32,561,900", "sector": "Communication Services"},
    
    {"symbol": "FGEN", "name": "First Gen Corporation", "last_price": "19.35", "change": "-0.82", "change_pct": "-4.07%", "high": "20.05", "low": "19.20", "volume": "2,876,400", "sector": "Utilities"}
]

   
   

    # Get all unique sectors for the filter dropdown
    all_sectors = sorted(list({stock["sector"] for stock in sample_stocks}))
    
    if request.method == "POST":
        # Handle symbol search
        stock_symbols_input = request.form.get("stock_symbols", "").strip()
        
        # Get filter parameters
        sector_filter = request.form.get("sector", "")
        price_min = request.form.get("price_min", "")
        price_max = request.form.get("price_max", "")
        performance_filter = request.form.get("performance", "")
        
        # Start with all stocks or filtered by symbols
        if stock_symbols_input:
            symbols = [s.strip().upper() for s in stock_symbols_input.split(",")]
            stocks_data = [stock for stock in sample_stocks if stock["symbol"] in symbols]
        else:
            stocks_data = sample_stocks.copy()
        
        # Apply filters
        filtered_stocks = []
        for stock in stocks_data:
            # Convert price to float for comparison
            try:
                price = float(stock["last_price"])
            except ValueError:
                price = 0
            
            # Sector filter
            if sector_filter and stock["sector"] != sector_filter:
                continue
                
            # Price range filter
            if price_min:
                try:
                    if price < float(price_min):
                        continue
                except ValueError:
                    pass
                    
            if price_max:
                try:
                    if price > float(price_max):
                        continue
                except ValueError:
                    pass
                    
            # Performance filter
            if performance_filter:
                change_pct = stock["change_pct"]
                is_positive = change_pct.startswith('+')
                
                if performance_filter == "gainers" and not is_positive:
                    continue
                if performance_filter == "losers" and is_positive:
                    continue
                if performance_filter == "most_active" and float(stock["volume"].replace(',', '')) < 5000000:  # Example threshold
                    continue
            
            filtered_stocks.append(stock)
        
        stocks_data = filtered_stocks
        
        if not stocks_data:
            error_message = "No stocks match your filters. Please try different criteria."
        
        # Keep the symbols in search bar if they were provided
        if stock_symbols_input:
            symbols = [s.strip().upper() for s in stock_symbols_input.split(",")]
    
    else:
        # For GET requests, show all stocks with empty filters
        stocks_data = sample_stocks
    
    return render_template(
        "ph_stocks.html", 
        stocks_data=stocks_data, 
        news_data=news_data, 
        symbols=symbols, 
        error_message=error_message,
        all_sectors=all_sectors,
        current_sector=request.form.get("sector", "") if request.method == "POST" else "",
        current_price_min=request.form.get("price_min", "") if request.method == "POST" else "",
        current_price_max=request.form.get("price_max", "") if request.method == "POST" else "",
        current_performance=request.form.get("performance", "") if request.method == "POST" else ""
    )


@app.route('/uk_stocks', methods=['GET', 'POST'])
def uk_stocks():
    # Extended list of UK stocks (LSE symbols) with sectors
    uk_stocks_data = [
        {'symbol': 'LLOY.L', 'name': 'Lloyds Banking Group', 'sector': 'Banking'},
        {'symbol': 'VOD.L', 'name': 'Vodafone Group', 'sector': 'Telecommunications'},
        {'symbol': 'BARC.L', 'name': 'Barclays', 'sector': 'Banking'},
        {'symbol': 'HSBA.L', 'name': 'HSBC Holdings', 'sector': 'Banking'},
        {'symbol': 'BP.L', 'name': 'BP', 'sector': 'Energy'},
        {'symbol': 'TSCO.L', 'name': 'Tesco', 'sector': 'Consumer Goods'},
        {'symbol': 'RIO.L', 'name': 'Rio Tinto', 'sector': 'Mining'},
        {'symbol': 'GLEN.L', 'name': 'Glencore', 'sector': 'Mining'},
        {'symbol': 'SHEL.L', 'name': 'Shell', 'sector': 'Energy'},
        {'symbol': 'GSK.L', 'name': 'GSK', 'sector': 'Pharmaceuticals'},
        {'symbol': 'AZN.L', 'name': 'AstraZeneca', 'sector': 'Pharmaceuticals'},
        {'symbol': 'ULVR.L', 'name': 'Unilever', 'sector': 'Consumer Goods'},
        {'symbol': 'DGE.L', 'name': 'Diageo', 'sector': 'Consumer Goods'},
        {'symbol': 'REL.L', 'name': 'RELX', 'sector': 'Media'},
        {'symbol': 'AAL.L', 'name': 'Anglo American', 'sector': 'Mining'},
        {'symbol': 'NWG.L', 'name': 'NatWest Group', 'sector': 'Banking'},
        {'symbol': 'IMB.L', 'name': 'Imperial Brands', 'sector': 'Tobacco'},
        {'symbol': 'NG.L', 'name': 'National Grid', 'sector': 'Utilities'},
        {'symbol': 'LGEN.L', 'name': 'Legal & General', 'sector': 'Financial Services'}
    ]
    
    stocks = []
    error_message = None
    
    if request.method == 'POST':
        stock_symbol = request.form.get('stock_symbol', '').strip().upper()
        if stock_symbol:
            if not (stock_symbol.endswith('.L') or stock_symbol.endswith('.LON')):
                error_message = f"'{stock_symbol}' is not a UK stock. Please search for stocks ending with .L or .LON"
            else:
                data = fetch_stock_data_yahoo(stock_symbol)
                if data:
                    stocks.append(data)
                else:
                    error_message = f"Stock symbol '{stock_symbol}' not found or data unavailable."
    else:
        # Get all unique sectors for the filter dropdown
        sectors = sorted(list(set(stock['sector'] for stock in uk_stocks_data)))
        
        # Apply filters
        filtered_stocks = uk_stocks_data.copy()
        
        # Sector filter
        sector_filter = request.args.get('sector')
        if sector_filter:
            filtered_stocks = [stock for stock in filtered_stocks if stock['sector'] == sector_filter]
        
        # Price range filter
        price_range = request.args.get('price_range')
        if price_range:
            for stock in filtered_stocks[:]:  # Iterate over a copy
                data = fetch_stock_data_yahoo(stock['symbol'])
                if data:
                    price = data['history'][-1]['close']
                    if price_range == '0-1' and price >= 1:
                        filtered_stocks.remove(stock)
                    elif price_range == '1-5' and (price < 1 or price >= 5):
                        filtered_stocks.remove(stock)
                    elif price_range == '5-10' and (price < 5 or price >= 10):
                        filtered_stocks.remove(stock)
                    elif price_range == '10-50' and (price < 10 or price >= 50):
                        filtered_stocks.remove(stock)
                    elif price_range == '50-100' and (price < 50 or price >= 100):
                        filtered_stocks.remove(stock)
                    elif price_range == '100+' and price < 100:
                        filtered_stocks.remove(stock)
        
        # Performance filter
        performance = request.args.get('performance')
        if performance:
            stock_performances = []
            for stock in filtered_stocks:
                data = fetch_stock_data_yahoo(stock['symbol'])
                if data:
                    price_change = ((data['history'][-1]['close'] - data['history'][0]['open']) / 
                                  data['history'][0]['open'] * 100)
                    stock_performances.append((price_change, stock['symbol']))
            
            if stock_performances:
                if performance == 'best_today':
                    stock_performances.sort(reverse=True)
                elif performance == 'worst_today':
                    stock_performances.sort()
                elif performance == 'best_week':
                    # In a real app, you'd compare with week-ago prices
                    stock_performances.sort(reverse=True)
                elif performance == 'worst_week':
                    stock_performances.sort()
                
                # Keep only the top/bottom 10 performers
                top_performers = [s[1] for s in stock_performances[:10]]
                filtered_stocks = [stock for stock in filtered_stocks if stock['symbol'] in top_performers]
        
        # Fetch data for filtered stocks
        stocks = [fetch_stock_data_yahoo(stock['symbol']) for stock in filtered_stocks]
        stocks = [stock for stock in stocks if stock]  # Remove None values
    
    return render_template('uk_stocks.html', 
                         stocks=stocks, 
                         error_message=error_message,
                         sectors=sectors)
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
    # German stocks with sectors
    ge_stocks_data = [
        {'symbol': 'SAP.DE', 'name': 'SAP SE', 'sector': 'Technology'},
        {'symbol': 'BMW.DE', 'name': 'BMW AG', 'sector': 'Automotive'},
        {'symbol': 'VOW3.DE', 'name': 'Volkswagen AG', 'sector': 'Automotive'},
        {'symbol': 'ALV.DE', 'name': 'Allianz SE', 'sector': 'Finance'},
        {'symbol': 'DBK.DE', 'name': 'Deutsche Bank AG', 'sector': 'Finance'},
        {'symbol': 'BAS.DE', 'name': 'BASF SE', 'sector': 'Chemicals'},
        {'symbol': 'BAYN.DE', 'name': 'Bayer AG', 'sector': 'Pharmaceuticals'},
        {'symbol': 'DTE.DE', 'name': 'Deutsche Telekom AG', 'sector': 'Telecommunications'},
        {'symbol': 'RWE.DE', 'name': 'RWE AG', 'sector': 'Energy'},
        {'symbol': 'SIE.DE', 'name': 'Siemens AG', 'sector': 'Industrial'},
        {'symbol': 'ADS.DE', 'name': 'Adidas AG', 'sector': 'Consumer Goods'},
        {'symbol': 'FRE.DE', 'name': 'Fresenius SE & Co. KGaA', 'sector': 'Healthcare'},
        {'symbol': 'IFX.DE', 'name': 'Infineon Technologies AG', 'sector': 'Semiconductors'},
        {'symbol': 'HEN3.DE', 'name': 'Henkel AG & Co. KGaA', 'sector': 'Consumer Goods'},
        {'symbol': 'LIN.DE', 'name': 'Linde plc', 'sector': 'Chemicals'}
    ]
    
    stocks = []
    error_message = None
    sectors = sorted(list(set(stock['sector'] for stock in ge_stocks_data)))

    # Apply filters only when sector is selected
    if request.method == 'GET' and request.args.get('sector'):
        sector_filter = request.args.get('sector')
        price_range = request.args.get('price_range')
        performance = request.args.get('performance')
        
        # First filter by sector
        filtered_stocks = [stock for stock in ge_stocks_data if stock['sector'] == sector_filter]
        
        # Fetch data for sector-filtered stocks
        stocks = [fetch_stock_data_yahoo(stock['symbol']) for stock in filtered_stocks]
        stocks = [stock for stock in stocks if stock]  # Remove None values
        
        # Then apply price range filter if selected
        if price_range:
            filtered_by_price = []
            for stock in stocks:
                if stock and 'history' in stock and len(stock['history']) > 0:
                    price = stock['history'][-1]['close']
                    if price_range == '0-10' and 0 <= price <= 10:
                        filtered_by_price.append(stock)
                    elif price_range == '10-50' and 10 < price <= 50:
                        filtered_by_price.append(stock)
                    elif price_range == '50-100' and 50 < price <= 100:
                        filtered_by_price.append(stock)
                    elif price_range == '100-200' and 100 < price <= 200:
                        filtered_by_price.append(stock)
                    elif price_range == '200+' and price > 200:
                        filtered_by_price.append(stock)
            stocks = filtered_by_price
        
        # Then apply performance filter if selected
        if performance:
            if performance == 'gainers':
                stocks.sort(key=lambda x: ((x['history'][-1]['close'] - x['history'][0]['open']) / x['history'][0]['open'] * 100), reverse=True)
            elif performance == 'losers':
                stocks.sort(key=lambda x: ((x['history'][-1]['close'] - x['history'][0]['open']) / x['history'][0]['open'] * 100))
            elif performance == 'volume':
                stocks.sort(key=lambda x: x['history'][-1]['volume'], reverse=True)

    # Handle POST requests for search
    if request.method == 'POST':
        stock_symbol = request.form.get('stock_symbol', '').strip().upper()
        if stock_symbol:
            if not (stock_symbol.endswith('.DE') or stock_symbol.endswith('.F')):
                error_message = f"'{stock_symbol}' is not a German stock. Please search for stocks ending with .DE or .F"
            else:
                data = fetch_stock_data_yahoo(stock_symbol)
                if data:
                    if not any(stock['symbol'] == stock_symbol for stock in stocks):
                        stocks.insert(0, data)  # Add searched stock at the top
                else:
                    error_message = f"Stock symbol '{stock_symbol}' not found or data unavailable."

    # If no filters or search, show all stocks
    if not stocks and request.method != 'POST':
        stocks = [fetch_stock_data_yahoo(stock['symbol']) for stock in ge_stocks_data]
        stocks = [stock for stock in stocks if stock]  # Remove None values

    return render_template('ge_stocks.html', 
                         stocks=stocks, 
                         error_message=error_message,
                         sectors=sectors)

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Default to 10000 if PORT is not set
    app.run(host="0.0.0.0", port=port)