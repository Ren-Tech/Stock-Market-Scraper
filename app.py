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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import yfinance as yf
from urllib.parse import urlparse, urljoin
from flask import url_for
import logging
from flask import session, flash
from functools import wraps
from newspaper import Article

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a secret key for session management


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add login credentials
VALID_USERS = {
    'developertest@gmail.com': 'solutions2025',
    'admin1@gmail.com': 'admin/2002',
    'admin2@gmail.com': 'admin2',
}



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

# Configure request headers with multiple user agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Mobile/15E148 Safari/604.1'
]

NEWS_SOURCE_MAPPING = {
    'www.msnbc.com': {
        'actual_source': 'pressgazette.co.uk',
        'name': 'MSNBC',
        'link_replace': {
            'from': 'pressgazette.co.uk',
            'to': 'www.msnbc.com'
        }
    },
    'www.cnbc.com': {
        'actual_source': 'foxnews.com',
        'name': 'CNBC',
        'link_replace': {
            'from': 'foxnews.com',
            'to': 'www.cnbc.com'
        }
    },
    'www.batimes.com': {
        'actual_source': 'newsweek.com',
        'name': 'Buenos Aires Times',
        'link_replace': {
            'from': 'newsweek.com',
            'to': 'www.batimes.com'
        }
    },
    'www.apnews.com': {
        'actual_source': 'businessinsider.com',
        'name': 'Associated Press',
        'link_replace': {
            'from': 'businessinsider.com',
            'to': 'www.apnews.com'
        }
    },
    'www.foxnews.com': {
        'actual_source': 'businessinsider.com',
        'name': 'Associated Press',
        'link_replace': {
            'from': 'businessinsider.com',
            'to': 'www.foxnews.com'
        }
    },
    'www.wired.com': {
        'actual_source': 'businessinsider.com',
        'name': 'Associated Press',
        'link_replace': {
            'from': 'businessinsider.com',
            'to': 'www.wired.com'
        }
    },'www.theregister.com': {
        'actual_source': 'gizmodo.com',
        'name': 'Associated Press',
        'link_replace': {
            'from': 'gizmodo.com',
            'to': 'www.theregister.com'
        }
    },
    'www.computerweekly.com': {
        'actual_source': 'techradar.com',
        'name': 'Associated Press',
        'link_replace': {
            'from': 'techradar.com',
            'to': 'www.computerweekly.com'
        }
    }, 'www.semiconductors.org': {
        'actual_source': 'Macrumors.com',
        'name': 'Associated Press',
        'link_replace': {
            'from': 'Macrumors.com',
            'to': 'www.semiconductors.org'
        }
    }
}

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
        'article': 'article, div.container__item, div.card, .card--section, .el__storyelement--standard, .cnn-search__result, .cd__content',
        'title': 'span.container__headline-text, h3.card__headline, .headline, h1, h2, h3, .cd__headline-text, .cnn-search__result-headline',
        'content': 'div.container__description, div.card__description, .description, p, .cd__description, .cnn-search__result-body',
        'link': 'a',
        'image': 'img',
        'date': '.timestamp, time, .date, .cd__timestamp, .cnn-search__result-publish-date'
    }
}
def scrape_article(url):
    try:
        # Special handling for CNN
        if 'cnn.com' in url:
            try:
                response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                soup = BeautifulSoup(response.text, 'html.parser')
                title = (
                    soup.find('h1', class_='headline__text') or 
                    soup.find('meta', property='og:title') or
                    soup.find('title')
                )
                if title:
                    title_text = title.get_text().strip()
                    return title_text if title_text else generate_title_from_url(url)
                return generate_title_from_url(url)
            except:
                return generate_title_from_url(url)
        
        # Default handling for other sites
        try:
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = (
                soup.find('meta', property='og:title') or
                soup.find('title') or
                soup.find('h1')
            )
            return title.get_text().strip() if title else generate_title_from_url(url)
        except:
            return generate_title_from_url(url)
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return generate_title_from_url(url)

def generate_title_from_url(url):
    """Generate a reasonable title from the URL when no title can be scraped"""
    try:
        domain = urlparse(url).netloc.replace('www.', '').replace('.com', '').title()
        path = urlparse(url).path
        if path:
            # Take the last part of the path and clean it up
            last_part = path.split('/')[-1]
            if last_part:
                return f"{domain}: {last_part.replace('-', ' ').replace('_', ' ').title()}"
        return f"{domain} News Update"
    except:
        return "Latest News Update"
def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)  # Replace multiple whitespace with single space
    return text.strip()

def assign_category(text, region=None):
    """Assign a news category based on text content with region override"""
    if region:
        return region.lower()
    
    text = text.lower()
    
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
        return 'world'

def _apply_source_mapping(news_items, mapping):
    """Apply domain mapping to news items with comprehensive replacements"""
    mapped_items = []
    
    for item in news_items:
        try:
            mapped_item = item.copy()
            
            # Replace the source domain in links
            if 'link' in mapped_item:
                mapped_item['link'] = re.sub(
                    rf'(https?://)?(www\.)?{re.escape(mapping["link_replace"]["from"])}',
                    f'https://{mapping["link_replace"]["to"]}',
                    mapped_item['link'],
                    flags=re.IGNORECASE
                )
            
            # Replace the source name
            mapped_item['source'] = mapping['name']
            
            # Replace read_more link if it exists
            if 'read_more' in mapped_item:
                mapped_item['read_more'] = re.sub(
                    rf'(https?://)?(www\.)?{re.escape(mapping["link_replace"]["from"])}',
                    f'https://{mapping["link_replace"]["to"]}',
                    mapped_item['read_more'],
                    flags=re.IGNORECASE
                )
            
            # Also replace any occurrences in content
            if 'content' in mapped_item:
                mapped_item['content'] = re.sub(
                    rf'(https?://)?(www\.)?{re.escape(mapping["link_replace"]["from"])}',
                    f'https://{mapping["link_replace"]["to"]}',
                    mapped_item['content'],
                    flags=re.IGNORECASE
                )
            
            mapped_items.append(mapped_item)
        except Exception as e:
            logger.error(f"Error applying source mapping to item: {str(e)}")
            continue
    
    return mapped_items

def fetch_top_news(url, max_articles=20, region=None):
    """
    Fetch top news articles from a given URL with source mapping functionality.
    """
    parsed_url = urlparse(url)
    input_domain = parsed_url.netloc.lower()
    
    # Check for domain mapping
    mapped_config = None
    for display_domain, config in NEWS_SOURCE_MAPPING.items():
        display_domain_clean = display_domain.replace('www.', '').lower()
        input_domain_clean = input_domain.replace('www.', '').lower()
        
        if display_domain_clean == input_domain_clean:
            mapped_config = config
            break
    
    # Determine actual URL to fetch
    if mapped_config:
        actual_domain = mapped_config['actual_source']
        actual_url = url.replace(input_domain, actual_domain)
        logger.info(f"Domain mapping active: {input_domain} → {actual_domain}")
    else:
        actual_url = url
    
    news_items = []
    source_domain = urlparse(actual_url).netloc.lower()
    
    try:
        # Handle RSS feeds
        if any(ext in actual_url.lower() for ext in ['rss', 'feed', 'xml']):
            logger.info(f"Processing as RSS feed: {actual_url}")
            feed = feedparser.parse(actual_url)
            
            if not feed.entries:
                logger.warning(f"No entries found in feed: {actual_url}")
                return []
                
            for entry in feed.entries[:max_articles*2]:  # Get more entries to account for filtering
                article = {
                    'title': clean_text(entry.get('title', 'No title')),
                    'content': clean_text(entry.get('description', 'No content')),
                    'link': entry.get('link', actual_url),
                    'date': entry.get('published', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    'source': source_domain,
                    'read_more': entry.get('link', actual_url),
                    'category': assign_category(entry.get('title', '') + " " + entry.get('description', ''), region)
                }
                
                # Extract image
                if 'media_content' in entry and entry.media_content:
                    for media in entry.media_content:
                        if media.get('type', '').startswith('image'):
                            article['image'] = media['url']
                            break
                elif 'enclosures' in entry and entry.enclosures:
                    for enc in entry.enclosures:
                        if enc.get('type', '').startswith('image'):
                            article['image'] = enc.href
                            break
                
                news_items.append(article)
        
        # Handle HTML pages
        else:
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            # Try with requests first
            try:
                response = requests.get(actual_url, headers=headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                logger.warning(f"Requests failed, trying Selenium: {str(e)}")
                try:
                    options = Options()
                    options.headless = True
                    driver = webdriver.Chrome(options=options)
                    driver.get(actual_url)
                    time.sleep(3)  # Wait for JavaScript to load
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    driver.quit()
                except Exception as e:
                    logger.error(f"Selenium also failed: {str(e)}")
                    return []
            
            # Try site-specific selectors first
            site_selectors = SITE_SPECIFIC_SELECTORS.get(source_domain, {})
            articles = []
            
            if site_selectors.get('article'):
                articles = soup.select(site_selectors['article'])[:max_articles*3]  # Get more articles for filtering
            
            # Fallback to generic detection
            if not articles:
                article_selectors = [
                    'article', '[itemtype="http://schema.org/NewsArticle"]',
                    '.article', '.story', '.post', '.card', '.teaser', '.list__item'
                ]
                for selector in article_selectors:
                    articles = soup.select(selector)
                    if articles:
                        articles = articles[:max_articles*3]
                        break
            
            logger.info(f"Found {len(articles)} potential articles before filtering")
            
            # Process articles
            for article in articles[:max_articles*2]:  # Process more to account for filtering
                try:
                    # Extract title
                    title = None
                    if site_selectors.get('title'):
                        title_elem = article.select_one(site_selectors['title'])
                    else:
                        for tag in ['h1', 'h2', 'h3']:
                            title_elem = article.find(tag)
                            if title_elem:
                                break
                    title = clean_text(title_elem.get_text()) if title_elem else 'No title'
                    
                    # Extract content
                    content = None
                    if site_selectors.get('content'):
                        content_elem = article.select_one(site_selectors['content'])
                    else:
                        content_elem = article.find('p') or article.find(class_=re.compile('content|summary', re.I))
                    content = clean_text(content_elem.get_text()) if content_elem else title
                    
                    # Extract link
                    if site_selectors.get('link'):
                        link_elem = article.select_one(site_selectors['link'])
                    else:
                        link_elem = article.find('a', href=True)
                    link = urljoin(actual_url, link_elem['href']) if link_elem and 'href' in link_elem.attrs else actual_url
                    
                    # Extract image
                    if site_selectors.get('image'):
                        img_elem = article.select_one(site_selectors['image'])
                    else:
                        img_elem = article.find('img')
                    image = None
                    if img_elem:
                        for attr in ['src', 'data-src', 'data-original']:
                            if img_elem.has_attr(attr):
                                image = urljoin(actual_url, img_elem[attr])
                                break
                    
                    # Extract date
                    if site_selectors.get('date'):
                        date_elem = article.select_one(site_selectors['date'])
                    else:
                        date_elem = article.find('time') or article.find(class_=re.compile('date|time', re.I))
                    date = clean_text(date_elem['datetime']) if date_elem and date_elem.has_attr('datetime') else \
                          clean_text(date_elem.get_text()) if date_elem else \
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    news_items.append({
                        'title': title,
                        'content': content[:200] + "..." if len(content) > 200 else content,
                        'link': link,
                        'image': image or "/static/images/default_news.jpg",
                        'date': date,
                        'source': source_domain,
                        'read_more': link,
                        'category': assign_category(title + " " + content, region)
                    })
                except Exception as e:
                    logger.warning(f"Error processing article: {str(e)}")
        
        # Apply domain mapping if needed
        if mapped_config:
            news_items = _apply_source_mapping(news_items, mapped_config)
        
        # Remove duplicates and ensure proper fields
        seen = set()
        final_items = []
        
        for item in news_items:
            # Validate required fields
            if not all(k in item for k in ['title', 'link', 'content']):
                continue
            
            # Deduplicate based on title and URL
            key = (item['title'].lower().strip(), item['link'].lower().strip())
            if key in seen:
                continue
            seen.add(key)
            
            # Ensure defaults
            item.setdefault('image', "/static/images/default_news.jpg")
            item.setdefault('date', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            item.setdefault('source', input_domain)
            item.setdefault('read_more', item['link'])
            
            # Ensure category is set
            if 'category' not in item:
                item['category'] = assign_category(item.get('title', '') + " " + item.get('content', ''), region)
            
            final_items.append(item)
        
        logger.info(f"After processing, returning {len(final_items[:max_articles])} articles")
        return final_items[:max_articles]
    
    except Exception as e:
        logger.error(f"Error fetching news from {url}: {str(e)}", exc_info=True)
        return []
    
def get_news_from_url(url, sector):
    """
    Extract news articles from a given URL and categorize them by sector.
    
    Args:
        url (str): The URL to scrape news from
        sector (str): The sector/category for these news articles
        
    Returns:
        list: A list of dictionaries containing news article data
    """
    articles = []
    
    try:
        # Check if URL is a news article directly
        if is_article_url(url):
            article_data = process_single_article(url, sector)
            if article_data:
                articles.append(article_data)
        else:
            # Otherwise, treat as a news portal/page with multiple articles
            articles = scrape_news_portal(url, sector)
            
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")
    
    return articles

def is_article_url(url):
    """
    Heuristic to determine if a URL points directly to a news article.
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Common patterns in article URLs
    article_patterns = [
        '/article/', '/story/', '/news/', '/post/',
        '/blog/', '/entry/', '/20', '/19'  # Dates in path
    ]
    
    return any(pattern in path for pattern in article_patterns)

def process_single_article(url, sector):
    """
    Process a single news article URL using newspaper3k.
    """
    try:
        article = Article(url)
        article.download()
        article.parse()
        
        # Basic validation - skip if no meaningful content
        if not article.text or len(article.text.strip()) < 200:
            return None
            
        return {
            'title': article.title,
            'url': url,
            'source': article.source_url,
            'summary': article.meta_description or article.text[:200] + "...",
            'content': article.text,
            'published_date': str(article.publish_date) if article.publish_date else str(datetime.datetime.now()),
            'image_url': article.top_image,
            'sector': sector,
            'authors': article.authors
        }
    except Exception as e:
        print(f"Error processing article {url}: {str(e)}")
        return None

def scrape_news_portal(url, sector):
    """
    Scrape a news portal homepage for article links, then process each article.
    """
    articles = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find potential article links - these selectors might need adjustment
        potential_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            
            # Make relative URLs absolute
            if href.startswith('/'):
                parsed = urlparse(url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            
            # Filter out non-article links
            if is_article_url(href) and href not in potential_links:
                potential_links.append(href)
        
        # Process each article link (with limit to avoid too many requests)
        for article_url in potential_links[:20]:  # Limit to 20 articles per portal
            try:
                article_data = process_single_article(article_url, sector)
                if article_data:
                    articles.append(article_data)
            except Exception as e:
                print(f"Error processing {article_url}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error scraping portal {url}: {str(e)}")
    
    return articles

@app.route("/current_affairs", methods=["GET", "POST"])
def current_affairs():
    logger.info(f"Current Affairs page accessed by {request.remote_addr}")
    
    regions = {
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
        
        # Dictionary to store URLs with their order
        ordered_urls = {region: {} for region in regions.keys()}
        
        for region in regions.keys():
            # Get URLs with their order numbers
            region_inputs = request.form.getlist(f"{region}_urls")
            for i, url in enumerate(region_inputs, start=1):
                url = url.strip()
                if url:
                    ordered_urls[region][i] = url
                    regions[region].append(url)
            
            if ordered_urls[region]:
                urls_provided = True
                logger.debug(f"URLs provided for {region}: {ordered_urls[region]}")

        if urls_provided:
            logger.info(f"Processing {sum(len(regions[r]) for r in regions)} URLs across all regions")
            
            for region, url_dict in ordered_urls.items():
                if not url_dict:
                    continue
                    
                logger.info(f"Processing {len(url_dict)} URLs for {region}")
                
                # Process URLs in their specified order
                for order_num, url in sorted(url_dict.items()):
                    try:
                        if not url.startswith(('http://', 'https://')):
                            url = 'https://' + url
                            logger.debug(f"Added protocol to URL: {url}")
                        
                        logger.info(f"Fetching news from {url} for region {region}")
                        source_news = fetch_top_news(url, max_articles=20)
                        
                        if source_news:
                            logger.info(f"Found {len(source_news)} articles at {url}")
                            # Add source order, URL, and category to each article
                            for article in source_news:
                                article['source_order'] = order_num
                                article['source_url'] = url
                                article['category'] = region  # Set category to the region it was submitted under
                            news_data.extend(source_news)
                        else:
                            msg = f"Could not extract news from {url} (Region: {region})"
                            error_messages.append(msg)
                            logger.warning(msg)
                            
                    except requests.exceptions.Timeout:
                        msg = f"Timeout when trying to access {url}"
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

    if news_data:
        logger.info(f"Total articles collected: {len(news_data)}")
        
        # First sort by source order (as specified in the form)
        # Then sort by date within each source (newest first)
        news_data.sort(key=lambda x: (x.get('source_order', 0), 
                                    -x.get('timestamp', 0) if x.get('timestamp') else x.get('date', '')))
        
        # Categorize news for template display while preserving order
        categorized_news = {region: [] for region in regions}
        
        # Add all news to the 'all' category
        categorized_news['all'] = news_data
        
        # Categorize news by their region
        for item in news_data:
            category = item.get('category', 'world')
            if category in categorized_news:
                categorized_news[category].append(item)
        
        for region, items in categorized_news.items():
            logger.debug(f"Category {region} has {len(items)} articles")
    else:
        logger.info("No news articles collected in this request")
        categorized_news = {region: [] for region in regions}
        categorized_news['all'] = []

    if error_messages:
        logger.warning(f"Encountered {len(error_messages)} errors during processing")

    return render_template("current_affairs.html", 
                        news_data=categorized_news,
                        regions=regions,
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
    return decorated_function
    return decorated_function@app.route("/current_affairs", methods=["GET", "POST"])


@app.route("/market_news", methods=["GET", "POST"])
@login_required
def market_news():
    logger.info(f"Market News page accessed by {request.remote_addr}")
    
    # Initialize market regions with the same structure as current affairs
    markets = {
        'us': "United States",
        'uk': "United Kingdom",
        'ge': "Germany",
        'fr': "France",
        'china': "China",
        'europe': "Europe",
        'asia': "Asia",
        'south_america': "South America"
    }
    
    # Get or initialize market URLs from session
    market_urls = session.get('market_urls', {market: [] for market in markets})
    selected_market = request.args.get("market", "us")
    
    news_data = []
    error_messages = []
    urls_provided = False

    if request.method == "POST":
        logger.info("Market News form submitted")
        selected_market = request.form.get("market", selected_market)
        
        # Store URLs with their order numbers
        ordered_urls = {}
        market_inputs = request.form.getlist(f"{selected_market}_urls")
        
        # DEBUG: Log the form inputs
        logger.debug(f"Form inputs for {selected_market}: {market_inputs}")
        
        for i, url in enumerate(market_inputs, start=1):
            url = url.strip()
            if url:
                ordered_urls[i] = url
                # FIX: Don't append to session list here, do it after processing
                # market_urls[selected_market].append(url)
        
        if ordered_urls:
            urls_provided = True
            logger.debug(f"URLs provided for {selected_market}: {ordered_urls}")

        if urls_provided:
            logger.info(f"Processing {len(ordered_urls)} URLs for market {selected_market}")
            
            # FIX: Clear existing URLs for this market before processing
            market_urls[selected_market] = []
            
            # Process URLs in their specified order
            for order_num, url in sorted(ordered_urls.items()):
                try:
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                        logger.debug(f"Added protocol to URL: {url}")
                    
                    logger.info(f"Fetching market news from {url} for market {selected_market}")
                    
                    # Use the same fetch_top_news function as current affairs
                    source_news = fetch_top_news(url, max_articles=20, region=selected_market)
                    
                    if source_news:
                        logger.info(f"Found {len(source_news)} articles at {url}")
                        # Add market-specific metadata
                        for article in source_news:
                            article['market'] = markets[selected_market]
                            article['source_order'] = order_num
                            article['source_url'] = url
                        news_data.extend(source_news)
                        
                        # FIX: Add URL to session only after successful processing
                        market_urls[selected_market].append(url)
                    else:
                        msg = f"Could not extract news from {url} (Market: {selected_market})"
                        error_messages.append(msg)
                        logger.warning(msg)
                        
                except requests.exceptions.Timeout:
                    msg = f"Timeout when trying to access {url}"
                    error_messages.append(msg)
                    logger.error(msg)
                except Exception as e:
                    msg = f"Error processing {url} (Market: {selected_market}): {str(e)}"
                    error_messages.append(msg)
                    logger.error(msg, exc_info=True)
            
            # Update session with the latest URLs
            session['market_urls'] = market_urls
        else:
            msg = "No URLs provided to fetch market news"
            error_messages.append(msg)
            logger.warning(msg)

    # DEBUG: Log what we're about to pass to template
    logger.info(f"Passing to template: {len(news_data)} articles, selected_market: {selected_market}")
    logger.info(f"Market URLs in session: {market_urls}")
    logger.debug(f"Sample news data: {news_data[:2] if news_data else 'None'}")

    if news_data:
        logger.info(f"Total market articles collected: {len(news_data)}")
        
        # Sort by source order (as specified in the form)
        # Then sort by date within each source (newest first)
        news_data.sort(key=lambda x: (x.get('source_order', 0), 
                                    -x.get('timestamp', 0) if x.get('timestamp') else x.get('date', '')))
    else:
        logger.info("No market news articles collected in this request")

    if error_messages:
        logger.warning(f"Encountered {len(error_messages)} errors during processing")

    return render_template("market_news.html", 
                         news_data=news_data,
                         market_urls=market_urls,
                         markets=markets,
                         selected_market=selected_market,
                         error_messages=error_messages,
                         urls_provided=urls_provided)

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


    
    
@app.route("/sector_news", methods=["GET", "POST"])
def sector_news():
    logger.info(f"Sector News page accessed by {request.remote_addr}")
    
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
    error_messages = []
    sector_urls = urls.get(selected_sector, [])
    urls_provided = bool(sector_urls)
    
    # Only fetch news if URLs are provided for the selected sector
    if sector_urls:
        logger.info(f"Processing {len(sector_urls)} URLs for {selected_sector}")
        
        for order_num, url in enumerate(sector_urls, start=1):
            try:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                    logger.debug(f"Added protocol to URL: {url}")
                
                logger.info(f"Fetching news from {url} for sector {selected_sector}")
                source_news = fetch_top_news(url, max_articles=20)
                
                if source_news:
                    logger.info(f"Found {len(source_news)} articles at {url}")
                    # Add source order, URL, and sector to each article
                    for article in source_news:
                        article['source_order'] = order_num
                        article['source_url'] = url
                        article['sector'] = selected_sector
                    sector_news.extend(source_news)
                else:
                    msg = f"Could not extract news from {url} (Sector: {selected_sector})"
                    error_messages.append(msg)
                    logger.warning(msg)
                    
            except requests.exceptions.Timeout:
                msg = f"Timeout when trying to access {url}"
                error_messages.append(msg)
                logger.error(msg)
            except Exception as e:
                msg = f"Error processing {url} (Sector: {selected_sector}): {str(e)}"
                error_messages.append(msg)
                logger.error(msg, exc_info=True)

    if sector_news:
        logger.info(f"Total articles collected for {selected_sector}: {len(sector_news)}")
        
        # First sort by source order (as specified in the form)
        # Then sort by date within each source (newest first)
        sector_news.sort(key=lambda x: (x.get('source_order', 0), 
                                      -x.get('timestamp', 0) if x.get('timestamp') else x.get('date', '')))
        
        # Deduplicate news
        unique_news = []
        seen_titles = set()
        for news in sector_news:
            if isinstance(news, dict) and "title" in news and news["title"] not in seen_titles:
                seen_titles.add(news["title"])
                unique_news.append(news)
    else:
        logger.info(f"No news articles collected for {selected_sector}")
        unique_news = []

    if error_messages:
        logger.warning(f"Encountered {len(error_messages)} errors during processing")

    return render_template("sector_news.html", 
                         selected_sector=selected_sector,
                         news_data=unique_news[:20],
                         urls=urls,
                         sectors=SECTORS.keys(),
                         error_messages=error_messages,
                         urls_provided=urls_provided)

                         

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

@app.route("/latest_news", methods=["GET"])
def latest_news():
    """Display latest news from major news sources with improved scraping"""
    logger.info("Latest News page accessed")
    
    # Define our target news sources with specific section URLs that work better for scraping
    news_sources = [
        {"url": "https://www.msnbc.com/latest", "name": "MSNBC", "type": "html"},
        {"url": "https://www.cnbc.com/world/?region=world", "name": "CNBC", "type": "html"},
        {"url": "https://www.batimes.com.ar/feed/", "name": "Buenos Aires Times", "type": "rss"},
        {"url": "https://apnews.com/hub/apf-topnews", "name": "Associated Press", "type": "html"}
    ]
    
    news_data = []
    error_messages = []
    
    # Fetch news from each source
    for source in news_sources:
        try:
            logger.info(f"Fetching news from {source['name']} ({source['url']})")
            
            if source['type'] == 'rss':
                # Special handling for RSS feeds
                articles = fetch_rss_feed(source['url'], source['name'])
            else:
                # Use Selenium for JavaScript-heavy sites
                articles = fetch_with_selenium(source['url'], source['name']) # type: ignore
                
            if articles:
                logger.info(f"Found {len(articles)} articles from {source['name']}")
                news_data.extend(articles)
            else:
                msg = f"No articles found from {source['name']}"
                error_messages.append(msg)
                logger.warning(msg)
                
        except Exception as e:
            msg = f"Error fetching from {source['name']}: {str(e)}"
            error_messages.append(msg)
            logger.error(msg, exc_info=True)
    
    # Sort all articles by date (newest first)
    news_data = sorted(news_data, key=lambda x: x.get('date', ''), reverse=True)
    
    # Group by source for better display
    news_by_source = {}
    for article in news_data:
        source = article['source_name']
        if source not in news_by_source:
            news_by_source[source] = []
        news_by_source[source].append(article)
    
    return render_template("latest_news.html",
                         news_by_source=news_by_source,
                         error_messages=error_messages)

def fetch_rss_feed(url, source_name):
    """Fetch and parse RSS feed"""
    feed = feedparser.parse(url)
    articles = []
    
    for entry in feed.entries[:5]:  # Limit to 5 articles
        articles.append({
            'title': clean_text(entry.get('title', 'No title')),
            'content': clean_text(entry.get('description', 'No content')),
            'link': entry.get('link', url),
            'date': entry.get('published', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            'source_name': source_name,
            'image': find_image_in_rss_entry(entry)
        })
    
    return articles

def find_image_in_rss_entry(entry):
    """Extract image URL from RSS entry"""
    if 'media_content' in entry and entry.media_content:
        for media in entry.media_content:
            if media.get('type', '').startswith('image'):
                return media['url']
    elif 'enclosures' in entry and entry.enclosures:
        for enclosure in entry.enclosures:
            if enclosure.get('type', '').startswith('image'):
                return enclosure.href
    return "/static/images/default_news.jpg"


# Site-specific extraction functions
def extract_msnbc_articles(soup, source_name):
    articles = []
    for article in soup.select('.wide-tease-item, .sm-tease-item')[:5]:
        try:
            title_elem = article.select_one('.tease-title')
            content_elem = article.select_one('.tease-card__description')
            link_elem = article.find('a', href=True)
            image_elem = article.find('img')
            date_elem = article.select_one('.datetime')
            
            if not title_elem or not link_elem:
                continue
                
            articles.append({
                'title': clean_text(title_elem.get_text()),
                'content': clean_text(content_elem.get_text()) if content_elem else '',
                'link': urljoin("https://www.msnbc.com", link_elem['href']),
                'image': image_elem['src'] if image_elem and 'src' in image_elem.attrs else '',
                'date': clean_text(date_elem.get_text()) if date_elem else datetime.now().strftime("%Y-%m-%d"),
                'source_name': source_name
            })
        except Exception as e:
            logger.warning(f"Error processing MSNBC article: {str(e)}")
    return articles

def extract_cnbc_articles(soup, source_name):
    articles = []
    for article in soup.select('.Card-titleContainer, .LatestNews-item')[:5]:
        try:
            title_elem = article.select_one('.Card-title')
            content_elem = article.select_one('.Card-description')
            link_elem = article.find('a', href=True)
            image_elem = article.find('img')
            date_elem = article.select_one('.Card-time')
            
            if not title_elem or not link_elem:
                continue
                
            articles.append({
                'title': clean_text(title_elem.get_text()),
                'content': clean_text(content_elem.get_text()) if content_elem else '',
                'link': urljoin("https://www.cnbc.com", link_elem['href']),
                'image': image_elem['src'] if image_elem and 'src' in image_elem.attrs else '',
                'date': clean_text(date_elem.get_text()) if date_elem else datetime.now().strftime("%Y-%m-%d"),
                'source_name': source_name
            })
        except Exception as e:
            logger.warning(f"Error processing CNBC article: {str(e)}")
    return articles

def extract_apnews_articles(soup, source_name):
    articles = []
    for article in soup.select('.FeedCard, .CardHeadline')[:5]:
        try:
            title_elem = article.select_one('.CardHeadline-headlineText')
            content_elem = article.select_one('.CardHeadline-description')
            link_elem = article.find('a', href=True)
            image_elem = article.find('img')
            date_elem = article.select_one('.Timestamp')
            
            if not title_elem or not link_elem:
                continue
                
            articles.append({
                'title': clean_text(title_elem.get_text()),
                'content': clean_text(content_elem.get_text()) if content_elem else '',
                'link': urljoin("https://apnews.com", link_elem['href']),
                'image': image_elem['src'] if image_elem and 'src' in image_elem.attrs else '',
                'date': clean_text(date_elem.get_text()) if date_elem else datetime.now().strftime("%Y-%m-%d"),
                'source_name': source_name
            })
        except Exception as e:
            logger.warning(f"Error processing AP News article: {str(e)}")
    return articles

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Default to 10000 if PORT is not set
    app.run(host="0.0.0.0", port=port)