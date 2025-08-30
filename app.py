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
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a secret key for session management


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add login credentials
VALID_USERS = {
    'dev@gmail.com': 'dev2025',
    'admin1@gmail.com': 'admin1',
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
     'www.ft.com': {
        'actual_source': 'howtogeek.com',
        'name': 'ft',
        'link_replace': {
            'from': 'howtogeek.com',
            'to': 'www.ft.com'
        }
    },
    'www.wsj.com': {
        'actual_source': 'www.foxbusiness.com',
        'name': 'wsj',
        'link_replace': {
            'from': 'www.foxbusiness.com',
            'to': 'www.wsj.com'
        }
    },
    'www.usnews.com': {
        'actual_source': 'www.morningstar.com',
        'name': 'usnews',
        'link_replace': {
            'from': 'www.morningstar.com',
            'to': 'www.usnews.com'
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
        'name': 'apnews.com',
        'link_replace': {
            'from': 'businessinsider.com',
            'to': 'www.apnews.com'
        }
    },
    'www.foxnews.com': {
        'actual_source': 'businessinsider.com',
        'name': 'foxnews.com',
        'link_replace': {
            'from': 'businessinsider.com',
            'to': 'www.foxnews.com'
        }
    },
    'www.wired.com': {
        'actual_source': 'businessinsider.com',
        'name': 'wired.com',
        'link_replace': {
            'from': 'businessinsider.com',
            'to': 'www.wired.com'
        }
    },'www.theregister.com': {
        'actual_source': 'gizmodo.com',
        'name': 'theregister.com',
        'link_replace': {
            'from': 'gizmodo.com',
            'to': 'www.theregister.com'
        }
    },
    'www.computerweekly.com': {
        'actual_source': 'thenextweb.com',
        'name': 'computerweekly.com',
        'link_replace': {
            'from': 'thenextweb.com',
            'to': 'www.computerweekly.com'
        }
    }, 'www.semiconductors.org': {
        'actual_source': 'Macrumors.com',
        'name': 'semiconductors.org',
        'link_replace': {
            'from': 'Macrumors.com',
            'to': 'www.semiconductors.org'
        }
    },
    'www.semiconductor-today.com': {
        'actual_source': 'pcworld.com',
        'name': 'semiconductor-today.com',
        'link_replace': {
            'from': 'pcworld.com',
            'to': 'www.semiconductor-today.com'
        }
    },
    'www.electronicsweekly.com': { 
        'actual_source': 'techpout.com',
        'name': 'electronicsweekly.com',
        'link_replace': {
            'from': 'techpout.com',
            'to': 'www.electronicsweekly.com'
        }
    },
    'www.marketwatch.com': { 
        'actual_source': 'techmonitor.ai',
        'name': 'Associated Press',
        'link_replace': {
            'from': 'techmonitor.ai',
            'to': 'www.marketwatch.com'
        }
    },
     'www.bbc.co.uk': { 
        'actual_source': 'venturebeat.com',
        'name': 'bbc.co.uk',
        'link_replace': {
            'from': 'venturebeat.com',
            'to': 'www.bbc.co.uk/news/technology/'
        }
    },
 
    
}

SITE_SPECIFIC_SELECTORS = {
    'morningstar.com': {
        'article': '.mds-card, .article-item, .news-item, .card-story, .story-card, [data-testid="article"], .content-card, .featured-story',
        'title': '.mds-card__headline, .card-title, .story-headline, .article-title, h2, h3, .headline, a[data-testid="headline"]',
        'content': '.mds-card__summary, .card-description, .story-summary, .article-summary, .excerpt, .description',
        'link': 'a',
        'image': 'img, [data-testid="image"]',
        'date': '.date, .timestamp, time, .published-date'
    },
    'cnbc.com': {
        'article': '.Card-titleContainer, .InlineVideo-container, .LatestNews-item, .Card-standardBreakerCard, article, .story-card, .PromoTile, .CardBasic, .InlineViewable',
        'title': '.Card-title, .InlineVideo-headline, .headline, .title, h1, h2, h3, .story-headline, a[data-module="ArticleTitle"]',
        'content': '.Card-description, .desc, .summary, p, .card-text, .InlineVideo-container p',
        'link': 'a',
        'image': 'img, .Card-media img',
        'date': 'time, .time, .Card-time, .timestamp, .PublishDate'
    },
    'batimes.com': {
        'article': 'article, .article, .news-article, .card, .post, .story-item, .news-item, .content-item, .article-card',
        'title': 'h1, h2, h3, .article-title, .headline, .post-title, .story-title, .entry-title',
        'content': '.article-summary, .lead, p, .article-text, .excerpt, .story-summary, .post-excerpt',
        'link': 'a',
        'image': 'img, .featured-image img, .article-image img',
        'date': '.article-date, time, .published-date, .date, .post-date'
    },
    'buenosairesherald.com': {
        'article': '.article, .post, .news-item, .story, .card, .content-item, .entry, article',
        'title': '.article-title, .entry-title, .post-title, h1, h2, h3, .headline, .story-title',
        'content': '.article-excerpt, .entry-summary, .excerpt, .lead, p, .description',
        'link': 'a',
        'image': 'img, .featured-image img, .post-thumbnail img',
        'date': '.date, time, .published-date, .entry-date, .post-date'
    },
    'folha.uol.com.br': {
        'article': '.c-headline, .c-list-links, article, .c-news-item, .news-card, .story-item, .content-item',
        'title': '.c-headline__title, h1, h2, h3, .title, .headline, .story-title',
        'content': '.c-headline__summary, p, .summary, .content, .excerpt, .lead',
        'link': 'a',
        'image': 'img, .c-headline__image img',
        'date': '.c-headline__dateline, time, .date, .timestamp'
    },
    'france24.com': {
        'article': '.o-layout-list__item, article, .news-card, .m-item-list-article, .article-item, .story-card, .teaser',
        'title': '.article__title, h1, h2, h3, .title, .headline, .story-title, .teaser__title',
        'content': '.article__desc, .article__summary, p, .desc, .summary, .teaser__text',
        'link': 'a',
        'image': 'img, .article__image img, .teaser__image img',
        'date': '.article__date, time, .date, .timestamp, .published'
    },
    'dw.com': {
        'article': '.col1, .teaser, .news-teaser, article, .story-item, .content-item, .card',
        'title': '.teaser__title, h1, h2, h3, .headline, .story-title, .title',
        'content': '.teaser__text, .intro, p, .summary, .description',
        'link': 'a',
        'image': 'img, .teaser__image img',
        'date': '.date, time, .timestamp, .published-date'
    },
    'asia.nikkei.com': {
        'article': '.ezil__article, article, .article-card, .news-item, .story-card, .content-card, .teaser',
        'title': '.ezil__title, h1, h2, h3, .headline, .story-title, .article-title',
        'content': '.ezil__subtitle, .ezil__summary, p, .summary, .excerpt, .description',
        'link': 'a',
        'image': 'img, .ezil__image img',
        'date': '.ezil__date, time, .date, .timestamp'
    },
    'nhk.or.jp': {
        'article': '.p-article, article, .m-news-item, .news-card, .story-item, .content-card, .article-item',
        'title': '.p-article__title, h1, h2, h3, .title, .headline, .story-title',
        'content': '.p-article__text, p, .summary, .content, .description',
        'link': 'a',
        'image': 'img, .p-article__image img',
        'date': '.p-article__date, time, .date, .timestamp'
    },
    'channelnewsasia.com': {
        'article': '.teaser, .card, article, .story-card, .news-item, .content-card, .article-teaser',
        'title': '.teaser__title, .card__title, h1, h2, h3, .headline, .story-title',
        'content': '.teaser__summary, .card__description, p, .summary, .excerpt',
        'link': 'a',
        'image': 'img, .teaser__image img, .card__image img',
        'date': '.date, time, .timestamp, .published-date, .teaser__date'
    },
    # Keep existing selectors
    'msnbc.com': {
        'article': '.gs-c-promo, article, .article-body, .info-card, .content-card',
        'title': '.gs-c-promo-heading__title, h1, h2, h3, .headline, .card-headline',
        'content': '.gs-c-promo-summary, .article-body__content, .info-card__content, p, .dek',
        'link': 'a',
        'image': 'img',
        'date': 'time, .date, .timestamp, .published-date'
    },
   
}


def enhanced_generic_selectors():
    """Return comprehensive generic selectors for news extraction"""
    return {
        'article_selectors': [
            # Semantic HTML
            'article', 'main article', '[role="article"]',
            # Schema.org structured data
            '[itemtype="http://schema.org/NewsArticle"]', '[itemtype="http://schema.org/Article"]',
            # Common CSS classes
            '.article', '.post', '.story', '.news', '.card', '.teaser', '.item',
            '.article-item', '.news-item', '.story-item', '.post-item', '.content-item',
            '.article-card', '.news-card', '.story-card', '.post-card', '.content-card',
            '.article-teaser', '.news-teaser', '.story-teaser',
            # Layout specific
            '.content', '.main-content', '.entry', '.story-wrapper',
            # Grid/list items
            '.grid-item', '.list-item', '.feed-item', '.tile',
            # Component-based
            '.component', '.module', '.widget', '.block'
        ],
        'title_selectors': [
            # Headers in order of preference
            'h1', 'h2', 'h3',
            # Semantic title classes
            '.title', '.headline', '.heading',
            '.article-title', '.post-title', '.story-title', '.news-title',
            '.article-headline', '.post-headline', '.story-headline', '.news-headline',
            '.entry-title', '.content-title',
            # Card/component titles
            '.card-title', '.teaser-title', '.item-title',
            # Link-based titles
            'a[data-title]', 'a[title]'
        ],
        'content_selectors': [
            # Semantic content
            '.content', '.summary', '.excerpt', '.description', '.lead', '.intro',
            '.article-content', '.post-content', '.story-content',
            '.article-summary', '.post-summary', '.story-summary',
            '.article-excerpt', '.post-excerpt', '.story-excerpt',
            '.article-description', '.post-description', '.story-description',
            # Card/component content
            '.card-text', '.card-description', '.card-content',
            '.teaser-text', '.teaser-content',
            # Generic text
            'p', '.text', '.body'
        ],
        'link_selectors': [
            'a[href]', '.link', '.read-more'
        ],
        'image_selectors': [
            'img', '.image', '.photo', '.picture',
            '.featured-image img', '.article-image img', '.story-image img'
        ],
        'date_selectors': [
            'time', '.date', '.timestamp', '.published', '.published-date',
            '.article-date', '.post-date', '.story-date',
            '.datetime', '.time-stamp'
        ]
    }

def extract_articles_with_enhanced_logic(soup, source_domain, actual_url, max_articles=20):
    """Enhanced article extraction with multiple strategies"""
    articles = []
    generic_selectors = enhanced_generic_selectors()
    site_selectors = SITE_SPECIFIC_SELECTORS.get(source_domain, {})
    
    # Strategy 1: Site-specific selectors
    if site_selectors.get('article'):
        logger.info(f"Using site-specific selectors for {source_domain}")
        article_elements = []
        for selector in site_selectors['article'].split(', '):
            elements = soup.select(selector.strip())
            article_elements.extend(elements)
        articles = list(dict.fromkeys(article_elements))  # Remove duplicates while preserving order
    
    # Strategy 2: Generic selectors if site-specific didn't work well
    if len(articles) < 3:
        logger.info(f"Site-specific selectors found {len(articles)} articles, trying generic selectors")
        for selector in generic_selectors['article_selectors']:
            elements = soup.select(selector)
            if elements and len(elements) >= 3:
                articles = elements
                logger.info(f"Generic selector '{selector}' found {len(articles)} articles")
                break
    
    # Strategy 3: Aggressive generic search
    if len(articles) < 3:
        logger.info("Trying aggressive generic search")
        # Look for any element containing links with meaningful text
        potential_articles = []
        
        # Find divs/sections with multiple links
        containers = soup.find_all(['div', 'section', 'ul', 'ol'], class_=True)
        for container in containers:
            links = container.find_all('a', href=True)
            if len(links) >= 2:  # Container with multiple links likely has articles
                for link in links:
                    if link.get_text().strip() and len(link.get_text().strip()) > 20:
                        # Create pseudo-article element
                        pseudo_article = container if container not in potential_articles else link.parent
                        potential_articles.append(pseudo_article)
        
        if potential_articles:
            articles = potential_articles[:max_articles * 2]
            logger.info(f"Aggressive search found {len(articles)} potential articles")
    
    # Strategy 4: Last resort - find any links with substantial text
    if len(articles) < 2:
        logger.info("Last resort: finding substantial links")
        all_links = soup.find_all('a', href=True)
        substantial_links = []
        for link in all_links:
            text = link.get_text().strip()
            if len(text) > 30 and not is_generic_title(text):
                substantial_links.append(link.parent or link)
        articles = substantial_links[:max_articles]
        logger.info(f"Found {len(articles)} substantial links")
    
    logger.info(f"Final article count for processing: {len(articles[:max_articles * 2])}")
    return articles[:max_articles * 2]

def extract_title_with_enhanced_logic(article, site_selectors, generic_selectors, source_domain):
    """Enhanced title extraction with multiple fallback strategies"""
    title_candidates = []
    
    # Strategy 1: Site-specific selectors
    if site_selectors.get('title'):
        for selector in site_selectors['title'].split(', '):
            title_elem = article.select_one(selector.strip())
            if title_elem and title_elem.get_text().strip():
                candidate = clean_text(title_elem.get_text())
                if len(candidate) > 10 and not is_generic_title(candidate):
                    title_candidates.append(candidate)
    
    # Strategy 2: Generic title selectors
    for selector in generic_selectors['title_selectors']:
        title_elem = article.select_one(selector)
        if title_elem and title_elem.get_text().strip():
            candidate = clean_text(title_elem.get_text())
            if len(candidate) > 10 and not is_generic_title(candidate):
                title_candidates.append(candidate)
                break  # Take first good generic match
    
    # Strategy 3: Link text as title
    link_elem = article.find('a', href=True)
    if link_elem and link_elem.get_text().strip():
        candidate = clean_text(link_elem.get_text())
        if len(candidate) > 15 and not is_generic_title(candidate):
            title_candidates.append(candidate)
    
    # Strategy 4: Meta data from parent elements
    for attr in ['title', 'data-title', 'aria-label']:
        if article.has_attr(attr) and article[attr].strip():
            candidate = clean_text(article[attr])
            if len(candidate) > 10 and not is_generic_title(candidate):
                title_candidates.append(candidate)
    
    # Strategy 5: First substantial text content
    text_elements = article.find_all(text=True)
    for text in text_elements:
        text = text.strip()
        if len(text) > 20 and not is_generic_title(text):
            sentences = text.split('.')
            if sentences and len(sentences[0]) > 15:
                title_candidates.append(sentences[0].strip() + '.')
                break
    
    # Select best title
    if title_candidates:
        # Prefer titles that are not too long and not too short
        good_titles = [t for t in title_candidates if 20 <= len(t) <= 150]
        if good_titles:
            return good_titles[0]  # Return first good title
        else:
            return title_candidates[0]  # Return any title if no "good" ones
    
    return f"Latest from {source_domain.replace('www.', '').replace('.com', '').title()}"

def extract_content_with_enhanced_logic(article, title, site_selectors, generic_selectors):
    """Enhanced content extraction"""
    content_candidates = []
    
    # Strategy 1: Site-specific content selectors
    if site_selectors.get('content'):
        for selector in site_selectors['content'].split(', '):
            content_elem = article.select_one(selector.strip())
            if content_elem and content_elem.get_text().strip():
                candidate = clean_text(content_elem.get_text())
                if candidate != title and len(candidate) > 20:
                    content_candidates.append(candidate)
    
    # Strategy 2: Generic content selectors
    for selector in generic_selectors['content_selectors']:
        content_elem = article.select_one(selector)
        if content_elem and content_elem.get_text().strip():
            candidate = clean_text(content_elem.get_text())
            if candidate != title and len(candidate) > 20:
                content_candidates.append(candidate)
                break
    
    # Strategy 3: All paragraph text
    paragraphs = article.find_all('p')
    for p in paragraphs:
        text = clean_text(p.get_text())
        if text != title and len(text) > 30:
            content_candidates.append(text)
            break
    
    # Strategy 4: Any substantial text
    all_text = clean_text(article.get_text())
    if all_text != title and len(all_text) > 50:
        # Take first few sentences
        sentences = all_text.split('.')
        meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        if meaningful_sentences:
            content_candidates.append('. '.join(meaningful_sentences[:2]) + '.')
    
    if content_candidates:
        return content_candidates[0][:300] + "..." if len(content_candidates[0]) > 300 else content_candidates[0]
    
    return "Click to read the full article"
def scrape_article(url):
    """Enhanced article title extraction with multiple fallback strategies"""
    try:
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Multiple title extraction strategies
        title_candidates = []
        
        # Strategy 1: Meta tags (most reliable)
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            title_candidates.append(clean_text(meta_title['content']))
        
        meta_title_name = soup.find('meta', attrs={'name': 'title'})
        if meta_title_name and meta_title_name.get('content'):
            title_candidates.append(clean_text(meta_title_name['content']))
        
        # Strategy 2: HTML title tag
        html_title = soup.find('title')
        if html_title and html_title.get_text():
            # Clean up common title patterns (site name, separators)
            title_text = clean_text(html_title.get_text())
            # Remove common site name patterns
            for separator in [' - ', ' | ', ' :: ', ' — ', ' – ']:
                if separator in title_text:
                    parts = title_text.split(separator)
                    # Take the longest part (usually the article title)
                    title_text = max(parts, key=len).strip()
                    break
            title_candidates.append(title_text)
        
        # Strategy 3: Article-specific header tags
        header_selectors = [
            'h1.article-title', 'h1.headline', 'h1.entry-title',
            '.article-headline', '.story-headline', '.post-title',
            'header h1', 'article h1', '.content h1',
            'h1', 'h2.headline', 'h2.article-title'
        ]
        
        for selector in header_selectors:
            header = soup.select_one(selector)
            if header and header.get_text().strip():
                title_candidates.append(clean_text(header.get_text()))
        
        # Strategy 4: JSON-LD structured data
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('headline'):
                    title_candidates.append(clean_text(data['headline']))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('headline'):
                            title_candidates.append(clean_text(item['headline']))
            except:
                continue
        
        # Filter and select best title
        valid_titles = []
        for title in title_candidates:
            if title and len(title.strip()) > 10 and not is_generic_title(title):
                valid_titles.append(title.strip())
        
        if valid_titles:
            # Return the longest meaningful title (usually most descriptive)
            return max(valid_titles, key=len)
        
        # Fallback: Generate from URL and first paragraph
        return generate_smart_title_from_content(url, soup)
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return generate_title_from_url(url)

def is_generic_title(title):
    """Check if title is too generic"""
    generic_patterns = [
        'home', 'news', 'latest', 'breaking', 'today', 
        'page not found', '404', 'error', 'loading',
        'welcome', 'homepage'
    ]
    title_lower = title.lower()
    return any(pattern in title_lower for pattern in generic_patterns)

def generate_smart_title_from_content(url, soup):
    """Generate a smart title from page content when no proper title is found"""
    try:
        # Try to extract from first paragraph or lead text
        content_selectors = [
            '.article-lead', '.story-summary', '.article-intro',
            '.lead', '.summary', '.excerpt', '.deck',
            'article p:first-of-type', '.content p:first-of-type',
            'p'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element and element.get_text().strip():
                text = clean_text(element.get_text())
                if len(text) > 20:
                    # Take first sentence or first 80 characters
                    sentences = text.split('.')
                    if len(sentences[0]) > 20:
                        return sentences[0].strip() + ('.' if not sentences[0].endswith('.') else '')
                    elif len(text) > 80:
                        return text[:77] + "..."
                    else:
                        return text
        
        # Final fallback
        return generate_title_from_url(url)
        
    except:
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
    """Enhanced news fetching with improved extraction logic - NO FILTERING"""
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
    source_domain = urlparse(actual_url).netloc.lower().replace('www.', '').replace('www1.', '').replace('www3.', '')
    
    try:
        # Handle RSS feeds first
        if any(ext in actual_url.lower() for ext in ['rss', 'feed', 'xml']):
            return handle_rss_feed(actual_url, max_articles, region, source_domain, mapped_config)
        
        # Handle HTML pages
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        try:
            response = requests.get(actual_url, headers=headers, timeout=20, allow_redirects=True)
            response.raise_for_status()
            
            # Handle different encodings
            if response.encoding.lower() in ['iso-8859-1', 'windows-1252'] and 'charset' in response.headers.get('content-type', '').lower():
                response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
                
        except Exception as e:
            logger.error(f"Failed to fetch {actual_url}: {str(e)}")
            return []
        
        # Enhanced article extraction
        articles = extract_articles_with_enhanced_logic(soup, source_domain, actual_url, max_articles)
        logger.info(f"Extracted {len(articles)} articles for processing")
        
        if not articles:
            logger.warning(f"No articles found on {actual_url}")
            return []
        
        # Process articles with enhanced logic
        generic_selectors = enhanced_generic_selectors()
        site_selectors = SITE_SPECIFIC_SELECTORS.get(source_domain, {})
        
        for article in articles[:max_articles]:
            try:
                # Enhanced title extraction
                title = extract_title_with_enhanced_logic(article, site_selectors, generic_selectors, source_domain)
                
                # Enhanced content extraction
                content = extract_content_with_enhanced_logic(article, title, site_selectors, generic_selectors)
                
                # Extract link
                link = actual_url
                if site_selectors.get('link'):
                    link_elem = article.select_one(site_selectors['link'])
                else:
                    link_elem = article.find('a', href=True)
                
                if link_elem and 'href' in link_elem.attrs:
                    href = link_elem['href']
                    if href.startswith('/'):
                        link = urljoin(actual_url, href)
                    elif href.startswith('http'):
                        link = href
                
                # Extract image
                image = None
                if site_selectors.get('image'):
                    img_elem = article.select_one(site_selectors['image'])
                else:
                    img_elem = article.find('img')
                
                if img_elem:
                    for attr in ['src', 'data-src', 'data-original', 'data-lazy']:
                        if img_elem.has_attr(attr) and img_elem[attr]:
                            img_url = img_elem[attr]
                            if img_url.startswith('//'):
                                img_url = 'https:' + img_url
                            elif img_url.startswith('/'):
                                img_url = urljoin(actual_url, img_url)
                            image = img_url
                            break
                
                # Extract date
                date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if site_selectors.get('date'):
                    date_elem = article.select_one(site_selectors['date'])
                else:
                    date_elem = article.find('time') or article.find(class_=re.compile('date|time', re.I))
                
                if date_elem:
                    if date_elem.has_attr('datetime'):
                        date = clean_text(date_elem['datetime'])
                    elif date_elem.get_text().strip():
                        date = clean_text(date_elem.get_text())
                
                # Create news item with default values (NO FILTERING)
                news_item = {
                    'title': title or "No Title Available",  # Provide default instead of filtering
                    'content': content or "No Content Available",  # Provide default instead of filtering
                    'link': link,
                    'image': image or "/static/images/default_news.jpg",
                    'date': date,
                    'source': source_domain,
                    'read_more': link,
                    'category': assign_category((title or "") + " " + (content or ""), region)
                }
                
                # Add all items without filtering
                news_items.append(news_item)
                
            except Exception as e:
                logger.warning(f"Error processing article: {str(e)}")
                # Even on error, add a placeholder item to maintain count
                news_items.append({
                    'title': f"Error Processing Article #{len(news_items) + 1}",
                    'content': f"Failed to process article: {str(e)}",
                    'link': actual_url,
                    'image': "/static/images/default_news.jpg",
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'source': source_domain,
                    'read_more': actual_url,
                    'category': assign_category("", region)
                })
                continue
        
        # Apply domain mapping if needed
        if mapped_config:
            news_items = _apply_source_mapping(news_items, mapped_config)
        
        # Keep duplicate detection but remove other filtering
        final_items = []
        seen_titles = set()
        
        for item in news_items:
            # Skip duplicates only
            title_key = item['title'].lower().strip()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            
            final_items.append(item)
        
        logger.info(f"Returning {len(final_items)} processed articles from {actual_url} (duplicates removed, other filtering disabled)")
        return final_items[:max_articles]
    
    except Exception as e:
        logger.error(f"Error fetching news from {url}: {str(e)}", exc_info=True)
        return []

def handle_rss_feed(feed_url, max_articles, region, source_domain, mapped_config):
    """Handle RSS feed processing"""
    try:
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            logger.warning(f"No entries found in RSS feed: {feed_url}")
            return []
        
        news_items = []
        for entry in feed.entries[:max_articles * 2]:
            title = clean_text(entry.get('title', ''))
            if not title or len(title) < 10:
                # Generate title from description
                desc = entry.get('description', '') or entry.get('summary', '')
                if desc:
                    clean_desc = clean_text(BeautifulSoup(desc, 'html.parser').get_text())
                    sentences = clean_desc.split('.')
                    title = sentences[0].strip() + '.' if sentences and len(sentences[0]) > 15 else clean_desc[:80] + "..."
                else:
                    title = f"News from {source_domain}"
            
            content = clean_text(entry.get('description', '') or entry.get('summary', ''))
            if not content or len(content) < 20:
                content = "Click to read the full article"
            
            article = {
                'title': title,
                'content': content[:300] + "..." if len(content) > 300 else content,
                'link': entry.get('link', feed_url),
                'date': entry.get('published', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                'source': source_domain,
                'read_more': entry.get('link', feed_url),
                'category': assign_category(title + " " + content, region)
            }
            
            # Extract image from RSS
            if hasattr(entry, 'media_content') and entry.media_content:
                for media in entry.media_content:
                    if media.get('type', '').startswith('image'):
                        article['image'] = media['url']
                        break
            elif hasattr(entry, 'enclosures') and entry.enclosures:
                for enc in entry.enclosures:
                    if enc.get('type', '').startswith('image'):
                        article['image'] = enc.href
                        break
            
            if 'image' not in article:
                article['image'] = "/static/images/default_news.jpg"
            
            news_items.append(article)
        
        return news_items[:max_articles]
        
    except Exception as e:
        logger.error(f"Error processing RSS feed {feed_url}: {str(e)}")
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
    regions = [
        'world', 'north_america', 'south_america', 'europe', 
        'asia', 'africa', 'australia', 'mena'
    ]
    news_data = []
    error_messages = []
    urls_provided = False
    active_region = 'all'  # Default to 'all' tab
    
    if request.method == "POST":
        urls_provided = True
        
        # Determine which region was submitted by finding the first region with URLs
        active_region = 'all'  # Default if no URLs found
        for region in regions:
            urls = request.form.getlist(f"{region}_urls")
            if urls and any(url.strip() for url in urls):
                active_region = region
                break
        
        # Process each region's URLs
        for region in regions:
            urls = request.form.getlist(f"{region}_urls")
            if urls:
                for order_num, url in enumerate(urls, 1):
                    url = url.strip()
                    if not url:
                        continue
                    
                    try:
                        logger.info(f"Fetching news from {url} for region {region}")
                        source_news = fetch_top_news(url, max_articles=20)
                        
                        if source_news:
                            logger.info(f"Found {len(source_news)} articles at {url}")
                            for article in source_news:
                                article['source_order'] = order_num
                                article['source_url'] = url
                                article['category'] = region
                            news_data.extend(source_news)
                        else:
                            msg = f"Could not extract news from {url} (Region: {region})"
                            error_messages.append(msg)
                            logger.warning(msg)
                            
                    except Exception as e:
                        msg = f"Error processing {url} (Region: {region}): {str(e)}"
                        error_messages.append(msg)
                        logger.error(msg, exc_info=True)

    # Sort and categorize news data
    if news_data:
        news_data.sort(key=lambda x: (
            x.get('source_order', 0), 
            -x.get('timestamp', 0) if x.get('timestamp') else x.get('date', '')
        ))
        
        categorized_news = {region: [] for region in regions}
        categorized_news['all'] = news_data
        
        for item in news_data:
            category = item.get('category', 'world')
            if category in categorized_news:
                categorized_news[category].append(item)
    else:
        categorized_news = {region: [] for region in regions}
        categorized_news['all'] = []

    return render_template("current_affairs.html", 
                        news_data=categorized_news,
                        regions=regions,
                        error_messages=error_messages,
                        urls_provided=urls_provided,
                        active_region=active_region)

                    




@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in VALID_USERS and VALID_USERS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            return jsonify({'success': True, 'redirect': url_for('new_current')})
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'})
    
    if session.get('logged_in'):
        return redirect(url_for('new_current'))
    
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



@app.route("/new_current", methods=["GET", "POST"])
@login_required
def new_current():
    logger.info(f"New Current page accessed by {request.remote_addr}")
    
    # Initialize market regions
    markets = {
        'us': "North America",
        'uk': "South America",
        'ge': "Europe",
        'fr': "Asia",
        'china': "Africa",
        'europe': "Australia",
        'south_america': "MENA"
    }
    
    # FIXED: Use separate session key for current affairs
    market_urls = session.get('current_market_urls', {market: [] for market in markets})
    selected_market = request.args.get("market", "us")
    
    news_data = []
    error_messages = []
    urls_provided = False

    if request.method == "POST":
        logger.info("New Current form submitted")
        selected_market = request.form.get("market", selected_market)
        
        # Store URLs with their order numbers
        ordered_urls = {}
        market_inputs = request.form.getlist(f"{selected_market}_urls")
        
        # Process each URL in order
        for i, url in enumerate(market_inputs, start=1):
            url = url.strip()
            if url:
                ordered_urls[i] = url
        
        if ordered_urls:
            urls_provided = True
            logger.debug(f"URLs provided for {selected_market}: {ordered_urls}")

        if urls_provided:
            logger.info(f"Processing {len(ordered_urls)} URLs for market {selected_market}")
            
            # Clear existing URLs for this market before processing
            market_urls[selected_market] = []
            
            # Process URLs in their specified order
            for order_num, url in sorted(ordered_urls.items()):
                try:
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    
                    logger.info(f"Fetching market news from {url} for market {selected_market}")
                    
                    # Fetch news from this URL
                    source_news = fetch_top_news(url, max_articles=20, region=selected_market)
                    
                    if source_news:
                        logger.info(f"Found {len(source_news)} articles at {url}")
                        # Add market-specific metadata
                        for article in source_news:
                            article['market'] = markets[selected_market]
                            article['source_order'] = order_num  # Track the order number
                            article['source_url'] = url  # Track the source URL
                        news_data.extend(source_news)
                        
                        # Add URL to session after successful processing
                        market_urls[selected_market].append(url)
                    else:
                        msg = f"Could not extract news from {url} (Market: {selected_market})"
                        error_messages.append(msg)
                        logger.warning(msg)
                        
                except Exception as e:
                    msg = f"Error processing {url} (Market: {selected_market}): {str(e)}"
                    error_messages.append(msg)
                    logger.error(msg, exc_info=True)
            
            # FIXED: Update session with separate key for current affairs
            session['current_market_urls'] = market_urls

    # Sort news by source order (as specified in the form)
    # Then sort by date within each source (newest first)
    news_data.sort(key=lambda x: (x.get('source_order', 0), 
                                -x.get('timestamp', 0) if x.get('timestamp') else x.get('date', '')))

    return render_template("new_current.html", 
                         news_data=news_data,
                         market_urls=market_urls,
                         markets=markets,
                         selected_market=selected_market,
                         error_messages=error_messages,
                         urls_provided=urls_provided)

@app.route("/new_sector", methods=["GET", "POST"])
@login_required
def new_sector():
    logger.info(f"New Sector page accessed by {request.remote_addr}")
    
    # Initialize market regions with the new sectors
    markets = {
        'us': "Technology",
        'uk': "Health Care", 
        'ge': "Financials",
        'fr': "Retail",
        'china': "Energy",
        'europe': "Mining",
        'south_america': "Utilities",
        'asia': "Automotive"
    }
    
    # FIXED: Use separate session key for sector news
    market_urls = session.get('sector_market_urls', {market: [] for market in markets})
    selected_market = request.args.get("market", "us")
    
    news_data = []
    error_messages = []
    urls_provided = False

    if request.method == "POST":
        logger.info("New Sector form submitted")
        selected_market = request.form.get("market", selected_market)
        
        # Store URLs with their order numbers
        ordered_urls = {}
        market_inputs = request.form.getlist(f"{selected_market}_urls")
        
        # Process each URL in order
        for i, url in enumerate(market_inputs, start=1):
            url = url.strip()
            if url:
                ordered_urls[i] = url
        
        if ordered_urls:
            urls_provided = True
            logger.debug(f"URLs provided for {selected_market}: {ordered_urls}")

        if urls_provided:
            logger.info(f"Processing {len(ordered_urls)} URLs for market {selected_market}")
            
            # Clear existing URLs for this market before processing
            market_urls[selected_market] = []
            
            # Process URLs in their specified order
            for order_num, url in sorted(ordered_urls.items()):
                try:
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    
                    logger.info(f"Fetching market news from {url} for market {selected_market}")
                    
                    # Fetch news from this URL
                    source_news = fetch_top_news(url, max_articles=20, region=selected_market)
                    
                    if source_news:
                        logger.info(f"Found {len(source_news)} articles at {url}")
                        # Add market-specific metadata
                        for article in source_news:
                            article['market'] = markets[selected_market]
                            article['source_order'] = order_num  # Track the order number
                            article['source_url'] = url  # Track the source URL
                        news_data.extend(source_news)
                        
                        # Add URL to session after successful processing
                        market_urls[selected_market].append(url)
                    else:
                        msg = f"Could not extract news from {url} (Market: {selected_market})"
                        error_messages.append(msg)
                        logger.warning(msg)
                        
                except Exception as e:
                    msg = f"Error processing {url} (Market: {selected_market}): {str(e)}"
                    error_messages.append(msg)
                    logger.error(msg, exc_info=True)
            
            # FIXED: Update session with separate key for sector news
            session['sector_market_urls'] = market_urls

    # Sort news by source order (as specified in the form)
    # Then sort by date within each source (newest first)
    news_data.sort(key=lambda x: (x.get('source_order', 0), 
                                -x.get('timestamp', 0) if x.get('timestamp') else x.get('date', '')))

    return render_template("new_sector.html", 
                         news_data=news_data,
                         market_urls=market_urls,
                         markets=markets,
                         selected_market=selected_market,
                         error_messages=error_messages,
                         urls_provided=urls_provided)


@app.route("/new_market", methods=["GET", "POST"])
@login_required
def market_news():
    logger.info(f"Market News page accessed by {request.remote_addr}")
    
    # Initialize market regions
    markets = {
        'us': "Market 1",
        'uk': "Market 2",
        'ge': "Market 3",
        'fr': "Market 4",
        'china': "Market 5",
        'europe': "Market 6",
        'asia': "Market 7",
        'south_america': "Market 8"
    }
    
    # Get or initialize market URLs from session
    # In new_current route:
    market_urls = session.get('current_market_urls', {market: [] for market in markets})
# And when updating:
    session['current_market_urls'] = market_urls

# In new_sector route:
    market_urls = session.get('sector_market_urls', {market: [] for market in markets})
# And when updating:
    session['sector_market_urls'] = market_urls
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
        
        # Process each URL in order (including dynamically added ones)
        for i, url in enumerate(market_inputs, start=1):
            url = url.strip()
            if url:
                ordered_urls[i] = url
        
        if ordered_urls:
            urls_provided = True
            logger.debug(f"URLs provided for {selected_market}: {ordered_urls}")

        if urls_provided:
            logger.info(f"Processing {len(ordered_urls)} URLs for market {selected_market}")
            
            # Clear existing URLs for this market before processing
            market_urls[selected_market] = []
            
            # Process URLs in their specified order
            for order_num, url in sorted(ordered_urls.items()):
                try:
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    
                    logger.info(f"Fetching market news from {url} for market {selected_market}")
                    
                    # Fetch news from this URL
                    source_news = fetch_top_news(url, max_articles=20, region=selected_market)
                    
                    if source_news:
                        logger.info(f"Found {len(source_news)} articles at {url}")
                        # Add market-specific metadata
                        for article in source_news:
                            article['market'] = markets[selected_market]
                            article['source_order'] = order_num  # Track the order number
                            article['source_url'] = url  # Track the source URL
                        news_data.extend(source_news)
                        
                        # Add URL to session after successful processing
                        market_urls[selected_market].append(url)
                    else:
                        msg = f"Could not extract news from {url} (Market: {selected_market})"
                        error_messages.append(msg)
                        logger.warning(msg)
                        
                except Exception as e:
                    msg = f"Error processing {url} (Market: {selected_market}): {str(e)}"
                    error_messages.append(msg)
                    logger.error(msg, exc_info=True)
            
            # Update session with the latest URLs
            session['market_urls'] = market_urls

    # Sort news by source order (as specified in the form)
    # Then sort by date within each source (newest first)
    news_data.sort(key=lambda x: (x.get('source_order', 0), 
                                -x.get('timestamp', 0) if x.get('timestamp') else x.get('date', '')))

    return render_template("new_market.html", 
                         news_data=news_data,
                         market_urls=market_urls,
                         markets=markets,
                         selected_market=selected_market,
                         error_messages=error_messages,
                         urls_provided=urls_provided)
@app.route("/company_filter", methods=["GET", "POST"])
@login_required
def company_filter():
    logger.info(f"Company Filter page accessed by {request.remote_addr}")
    
    # Initialize company categories
    categories = {
        'tech': "Technology Companies",
        'healthcare': "Healthcare Companies", 
        'finance': "Financial Companies",
        'retail': "Retail Companies",
        'energy': "Energy Companies",
        'mining': "Mining Companies",
        'utilities': "Utilities Companies",
        'auto': "Automotive Companies"
    }
    
    # Use separate session key for company filter
    category_urls = session.get('company_filter_urls', {category: [] for category in categories})
    selected_category = request.args.get("category", "tech")
    
    news_data = []
    error_messages = []
    urls_provided = False
    company_name = ""

    if request.method == "POST":
        logger.info("Company Filter form submitted")
        selected_category = request.form.get("category", selected_category)
        company_name = request.form.get("company_name", "").strip().lower()
        
        # Store URLs with their order numbers
        ordered_urls = {}
        category_inputs = request.form.getlist(f"{selected_category}_urls")
        
        # Process each URL in order
        for i, url in enumerate(category_inputs, start=1):
            url = url.strip()
            if url:
                ordered_urls[i] = url
        
        if ordered_urls:
            urls_provided = True
            logger.debug(f"URLs provided for {selected_category}: {ordered_urls}")

        if urls_provided:
            logger.info(f"Processing {len(ordered_urls)} URLs for category {selected_category}")
            
            # Clear existing URLs for this category before processing
            category_urls[selected_category] = []
            
            # Process URLs in their specified order
            for order_num, url in sorted(ordered_urls.items()):
                try:
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    
                    logger.info(f"Fetching news from {url} for company: {company_name or 'All companies'}")
                    
                    # Fetch news from this URL
                    source_news = fetch_top_news(url, max_articles=50, region=None)  # Increased max articles for better filtering
                    
                    if source_news:
                        logger.info(f"Found {len(source_news)} articles at {url}")
                        
                        # Filter articles by company name if provided
                        filtered_news = []
                        for article in source_news:
                            # Combine all text fields for searching
                            article_text = f"{article.get('title', '')} {article.get('content', '')} {article.get('description', '')}".lower()
                            
                            if company_name:
                                # Check if company name appears in the article text
                                if company_name in article_text:
                                    article['category'] = categories[selected_category]
                                    article['source_order'] = order_num
                                    article['source_url'] = url
                                    article['company_match'] = company_name  # Track which company was matched
                                    filtered_news.append(article)
                            else:
                                # If no company name specified, include all articles
                                article['category'] = categories[selected_category]
                                article['source_order'] = order_num
                                article['source_url'] = url
                                filtered_news.append(article)
                        
                        if filtered_news:
                            if company_name:
                                logger.info(f"Filtered to {len(filtered_news)} articles about '{company_name}' from {url}")
                            else:
                                logger.info(f"Included {len(filtered_news)} articles from {url} (no filter)")
                            news_data.extend(filtered_news)
                        else:
                            if company_name:
                                logger.info(f"No articles about '{company_name}' found at {url}")
                        
                        # Add URL to session after successful processing
                        category_urls[selected_category].append(url)
                    else:
                        msg = f"Could not extract news from {url}"
                        error_messages.append(msg)
                        logger.warning(msg)
                        
                except Exception as e:
                    msg = f"Error processing {url}: {str(e)}"
                    error_messages.append(msg)
                    logger.error(msg, exc_info=True)
            
            # Update session with separate key for company filter
            session['company_filter_urls'] = category_urls

    # Sort news by source order (as specified in the form)
    # Then sort by date within each source (newest first)
    news_data.sort(key=lambda x: (x.get('source_order', 0), 
                                -x.get('timestamp', 0) if x.get('timestamp') else x.get('date', '')))

    return render_template("company_filter.html", 
                         news_data=news_data,
                         category_urls=category_urls,
                         categories=categories,
                         selected_category=selected_category,
                         error_messages=error_messages,
                         urls_provided=urls_provided,
                         company_name=company_name)
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
                source_news = fetch_top_news(url, max_articles=20)  # Get 3 articles per source
                
                if source_news:
                    logger.info(f"Found {len(source_news)} articles at {url}")
                    # Add source information to each article
                    for article in source_news:
                        if not article.get('title'):
                            continue  # Skip if no title
                        article['source_order'] = order_num
                        article['source_url'] = url
                        article['sector'] = selected_sector
                        # Extract domain name for display
                        domain = url.split('//')[-1].split('/')[0].replace('www.', '')
                        article['source_name'] = domain
                    sector_news.extend(source_news)
                else:
                    msg = f"No articles found at {url} (Sector: {selected_sector})"
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
        
        # Sort by source order first, then by date (newest first)
        sector_news.sort(key=lambda x: (
            x.get('source_order', 0),
            -x.get('timestamp', 0) if x.get('timestamp') else 
            (x.get('date', '') if isinstance(x.get('date'), str) else '')
        ))
        
        # Deduplicate news based on title
        unique_news = []
        seen_titles = set()
        for news in sector_news:
            title = news.get('title', '').strip().lower()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(news)
    else:
        logger.info(f"No news articles collected for {selected_sector}")
        unique_news = []

    return render_template("sector_news.html", 
                         selected_sector=selected_sector,
                         news_data=unique_news,
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
      {"symbol": "TEL", "name": "PLDT Inc.", "last_price": "1,482.50", "change": "-25.00", "change_pct": "-1.66%", "high": "1,495.00", "low": "1,480.00", "volume": "85,420", "sector": "Communication Services"},
    {"symbol": "SMC", "name": "San Miguel Corporation", "last_price": "108.90", "change": "+2.10", "change_pct": "+1.97%", "high": "109.50", "low": "107.00", "volume": "3,245,600", "sector": "Conglomerates"},
    {"symbol": "BPI", "name": "Bank of the Philippine Islands", "last_price": "112.75", "change": "+3.25", "change_pct": "+2.97%", "high": "113.00", "low": "110.50", "volume": "1,876,300", "sector": "Financial Services"},
    {"symbol": "URC", "name": "Universal Robina Corporation", "last_price": "134.50", "change": "-4.20", "change_pct": "-3.03%", "high": "138.00", "low": "133.50", "volume": "876,400", "sector": "Consumer Defensive"},
    {"symbol": "ICT", "name": "International Container Terminal Services", "last_price": "230.40", "change": "+7.60", "change_pct": "+3.41%", "high": "231.00", "low": "225.00", "volume": "542,100", "sector": "Industrials"},
    {"symbol": "MER", "name": "Manila Electric Company", "last_price": "389.00", "change": "+12.50", "change_pct": "+3.32%", "high": "390.50", "low": "380.00", "volume": "321,450", "sector": "Utilities"},
    {"symbol": "RRHI", "name": "Robinsons Retail Holdings Inc.", "last_price": "52.30", "change": "+1.80", "change_pct": "+3.56%", "high": "52.80", "low": "51.00", "volume": "1,245,700", "sector": "Consumer Cyclical"},
    {"symbol": "MPI", "name": "Metro Pacific Investments Corporation", "last_price": "5.18", "change": "+0.23", "change_pct": "+4.65%", "high": "5.20", "low": "5.00", "volume": "18,654,200", "sector": "Conglomerates"},
    {"symbol": "CEB", "name": "Cebu Air, Inc.", "last_price": "38.25", "change": "-1.75", "change_pct": "-4.38%", "high": "40.00", "low": "38.00", "volume": "1,987,500", "sector": "Industrials"},
    {"symbol": "AGI", "name": "Alliance Global Group, Inc.", "last_price": "11.40", "change": "+0.52", "change_pct": "+4.78%", "high": "11.50", "low": "11.00", "volume": "12,543,200", "sector": "Conglomerates"},
    {"symbol": "RLC", "name": "Robinsons Land Corporation", "last_price": "16.80", "change": "+0.75", "change_pct": "+4.67%", "high": "17.00", "low": "16.50", "volume": "5,432,100", "sector": "Real Estate"},
    {"symbol": "SECB", "name": "Security Bank Corporation", "last_price": "85.60", "change": "+2.40", "change_pct": "+2.88%", "high": "86.00", "low": "84.00", "volume": "876,300", "sector": "Financial Services"},
    {"symbol": "CNVRG", "name": "Converge ICT Solutions Inc.", "last_price": "12.75", "change": "-0.45", "change_pct": "-3.41%", "high": "13.00", "low": "12.50", "volume": "8,765,400", "sector": "Communication Services"},
    {"symbol": "DMW", "name": "DM Wenceslao & Associates, Inc.", "last_price": "5.85", "change": "+0.15", "change_pct": "+2.63%", "high": "5.90", "low": "5.70", "volume": "1,234,500", "sector": "Real Estate"},
    {"symbol": "FLI", "name": "Filinvest Land, Inc.", "last_price": "0.75", "change": "-0.02", "change_pct": "-2.60%", "high": "0.77", "low": "0.74", "volume": "15,432,100", "sector": "Real Estate"},
    {"symbol": "PSE", "name": "The Philippine Stock Exchange, Inc.", "last_price": "185.50", "change": "+3.50", "change_pct": "+1.92%", "high": "186.00", "low": "183.00", "volume": "45,320", "sector": "Financial Services"},
    {"symbol": "DMC", "name": "DMCI Holdings, Inc.", "last_price": "9.45", "change": "+0.35", "change_pct": "+3.85%", "high": "9.50", "low": "9.20", "volume": "7,654,300", "sector": "Conglomerates"},
    {"symbol": "LTG", "name": "LT Group, Inc.", "last_price": "9.80", "change": "+0.20", "change_pct": "+2.08%", "high": "9.85", "low": "9.60", "volume": "3,456,700", "sector": "Conglomerates"},
    {"symbol": "WLCON", "name": "Wilcon Depot, Inc.", "last_price": "22.40", "change": "+0.90", "change_pct": "+4.19%", "high": "22.50", "low": "21.80", "volume": "1,543,200", "sector": "Consumer Cyclical"},
    {"symbol": "CHIB", "name": "China Banking Corporation", "last_price": "32.75", "change": "+0.85", "change_pct": "+2.67%", "high": "32.90", "low": "32.00", "volume": "876,500", "sector": "Financial Services"},
    {"symbol": "PBB", "name": "Philippine Business Bank", "last_price": "12.30", "change": "-0.20", "change_pct": "-1.60%", "high": "12.50", "low": "12.20", "volume": "543,200", "sector": "Financial Services"},
    {"symbol": "SHNG", "name": "Shang Properties, Inc.", "last_price": "1.85", "change": "+0.05", "change_pct": "+2.78%", "high": "1.87", "low": "1.80", "volume": "2,345,600", "sector": "Real Estate"},
    {"symbol": "SSI", "name": "SSI Group, Inc.", "last_price": "2.15", "change": "-0.10", "change_pct": "-4.44%", "high": "2.20", "low": "2.12", "volume": "3,456,700", "sector": "Consumer Cyclical"},
    {"symbol": "ANS", "name": "A. Soriano Corporation", "last_price": "7.50", "change": "+0.25", "change_pct": "+3.45%", "high": "7.55", "low": "7.30", "volume": "765,400", "sector": "Industrials"},
    {"symbol": "CDC", "name": "Cityland Development Corporation", "last_price": "0.88", "change": "+0.03", "change_pct": "+3.53%", "high": "0.89", "low": "0.85", "volume": "4,321,500", "sector": "Real Estate"},
    {"symbol": "DFNN", "name": "DFNN, Inc.", "last_price": "5.25", "change": "-0.35", "change_pct": "-6.25%", "high": "5.50", "low": "5.20", "volume": "1,234,500", "sector": "Technology"},
    {"symbol": "DD", "name": "DoubleDragon Properties Corp.", "last_price": "8.90", "change": "+0.40", "change_pct": "+4.71%", "high": "9.00", "low": "8.70", "volume": "2,345,600", "sector": "Real Estate"},
    {"symbol": "FNI", "name": "Global Ferronickel Holdings, Inc.", "last_price": "2.05", "change": "+0.10", "change_pct": "+5.13%", "high": "2.08", "low": "2.00", "volume": "5,432,100", "sector": "Basic Materials"},
    {"symbol": "HVN", "name": "Golden MV Holdings, Inc.", "last_price": "420.00", "change": "+15.00", "change_pct": "+3.70%", "high": "425.00", "low": "415.00", "volume": "12,340", "sector": "Real Estate"},
    {"symbol": "MAC", "name": "Macay Holdings, Inc.", "last_price": "7.20", "change": "-0.30", "change_pct": "-4.00%", "high": "7.40", "low": "7.15", "volume": "543,200", "sector": "Consumer Defensive"},
    {"symbol": "MAXS", "name": "Max's Group, Inc.", "last_price": "14.50", "change": "+0.50", "change_pct": "+3.57%", "high": "14.60", "low": "14.20", "volume": "765,400", "sector": "Consumer Cyclical"},
    {"symbol": "NIKL", "name": "Nickel Asia Corporation", "last_price": "4.25", "change": "+0.15", "change_pct": "+3.66%", "high": "4.30", "low": "4.15", "volume": "8,765,400", "sector": "Basic Materials"},
    {"symbol": "PHA", "name": "Premiere Horizon Alliance Corporation", "last_price": "0.65", "change": "+0.02", "change_pct": "+3.17%", "high": "0.66", "low": "0.63", "volume": "12,345,600", "sector": "Real Estate"},
    {"symbol": "PIZZA", "name": "Shakey's Pizza Asia Ventures, Inc.", "last_price": "9.75", "change": "-0.25", "change_pct": "-2.50%", "high": "10.00", "low": "9.70", "volume": "1,234,500", "sector": "Consumer Cyclical"},
    {"symbol": "PRMX", "name": "Primex Corporation", "last_price": "2.30", "change": "+0.10", "change_pct": "+4.55%", "high": "2.35", "low": "2.25", "volume": "3,456,700", "sector": "Real Estate"},
    {"symbol": "ROCK", "name": "Rockwell Land Corporation", "last_price": "1.15", "change": "+0.05", "change_pct": "+4.55%", "high": "1.16", "low": "1.12", "volume": "5,432,100", "sector": "Real Estate"},
    {"symbol": "SCC", "name": "Semirara Mining and Power Corporation", "last_price": "32.50", "change": "+1.50", "change_pct": "+4.84%", "high": "32.80", "low": "31.50", "volume": "3,456,700", "sector": "Energy"},
    {"symbol": "SLF", "name": "Sun Life Financial, Inc.", "last_price": "2,450.00", "change": "+75.00", "change_pct": "+3.16%", "high": "2,460.00", "low": "2,400.00", "volume": "12,340", "sector": "Financial Services"},
    {"symbol": "STI", "name": "STI Education Systems Holdings, Inc.", "last_price": "0.95", "change": "+0.03", "change_pct": "+3.26%", "high": "0.96", "low": "0.93", "volume": "4,321,500", "sector": "Consumer Defensive"},
    {"symbol": "TBGI", "name": "Transpacific Broadband Group Int'l Inc.", "last_price": "0.48", "change": "+0.01", "change_pct": "+2.13%", "high": "0.49", "low": "0.47", "volume": "12,345,600", "sector": "Communication Services"},
    {"symbol": "VITA", "name": "Vitarich Corporation", "last_price": "0.72", "change": "+0.02", "change_pct": "+2.86%", "high": "0.73", "low": "0.70", "volume": "5,432,100", "sector": "Consumer Defensive"},
    {"symbol": "WEB", "name": "PhilWeb Corporation", "last_price": "2.85", "change": "-0.15", "change_pct": "-5.00%", "high": "2.90", "low": "2.80", "volume": "1,234,500", "sector": "Technology"},
    {"symbol": "X", "name": "Xurpas, Inc.", "last_price": "0.32", "change": "+0.01", "change_pct": "+3.23%", "high": "0.33", "low": "0.31", "volume": "21,543,200", "sector": "Technology"},
    {"symbol": "ATN", "name": "ATN Holdings, Inc.", "last_price": "0.95", "change": "+0.02", "change_pct": "+2.15%", "high": "0.96", "low": "0.93", "volume": "3,456,700", "sector": "Real Estate"},
    {"symbol": "COSCO", "name": "Cosco Capital, Inc.", "last_price": "5.20", "change": "+0.15", "change_pct": "+2.97%", "high": "5.25", "low": "5.10", "volume": "8,765,400", "sector": "Consumer Defensive"},
    {"symbol": "CPG", "name": "Century Properties Group, Inc.", "last_price": "0.38", "change": "+0.01", "change_pct": "+2.70%", "high": "0.39", "low": "0.37", "volume": "21,543,200", "sector": "Real Estate"},
    {"symbol": "CPM", "name": "Century Peak Metals Holdings Corporation", "last_price": "2.15", "change": "+0.05", "change_pct": "+2.38%", "high": "2.18", "low": "2.10", "volume": "3,456,700", "sector": "Basic Materials"},
    {"symbol": "FEU", "name": "Far Eastern University, Inc.", "last_price": "650.00", "change": "+20.00", "change_pct": "+3.17%", "high": "655.00", "low": "635.00", "volume": "1,230", "sector": "Consumer Defensive"},
    {"symbol": "FPI", "name": "Forum Pacific, Inc.", "last_price": "0.55", "change": "+0.01", "change_pct": "+1.85%", "high": "0.56", "low": "0.54", "volume": "12,345,600", "sector": "Financial Services"},
    {"symbol": "GMA7", "name": "GMA Network, Inc.", "last_price": "7.85", "change": "-0.25", "change_pct": "-3.09%", "high": "8.00", "low": "7.80", "volume": "3,456,700", "sector": "Communication Services"},
    {"symbol": "HOUSE", "name": "8990 Holdings, Inc.", "last_price": "8.25", "change": "+0.35", "change_pct": "+4.43%", "high": "8.30", "low": "8.00", "volume": "5,432,100", "sector": "Real Estate"},
    {"symbol": "IMI", "name": "Integrated Micro-Electronics, Inc.", "last_price": "5.50", "change": "+0.20", "change_pct": "+3.77%", "high": "5.55", "low": "5.40", "volume": "876,500", "sector": "Technology"},
    {"symbol": "ION", "name": "IONICS, Inc.", "last_price": "1.85", "change": "+0.05", "change_pct": "+2.78%", "high": "1.87", "low": "1.80", "volume": "543,200", "sector": "Technology"},
    {"symbol": "IRC", "name": "IRC Properties, Inc.", "last_price": "0.95", "change": "+0.02", "change_pct": "+2.15%", "high": "0.96", "low": "0.93", "volume": "3,456,700", "sector": "Real Estate"},
    {"symbol": "KPPI", "name": "Kapamilya Online Inc.", "last_price": "0.45", "change": "+0.01", "change_pct": "+2.27%", "high": "0.46", "low": "0.44", "volume": "21,543,200", "sector": "Communication Services"},
    {"symbol": "LFM", "name": "Liberty Flour Mills, Inc.", "last_price": "25.50", "change": "+0.75", "change_pct": "+3.03%", "high": "25.75", "low": "25.00", "volume": "12,340", "sector": "Consumer Defensive"},
    {"symbol": "LR", "name": "Lepanto Consolidated Mining Company", "last_price": "0.185", "change": "+0.005", "change_pct": "+2.78%", "high": "0.186", "low": "0.180", "volume": "32,154,300", "sector": "Basic Materials"},
    {"symbol": "MAB", "name": "Manila Bulletin Publishing Corporation", "last_price": "0.85", "change": "+0.02", "change_pct": "+2.41%", "high": "0.86", "low": "0.83", "volume": "3,456,700", "sector": "Communication Services"},
    {"symbol": "MED", "name": "Medco Holdings, Inc.", "last_price": "0.65", "change": "+0.01", "change_pct": "+1.56%", "high": "0.66", "low": "0.64", "volume": "12,345,600", "sector": "Financial Services"},
    {"symbol": "MHC", "name": "Mabuhay Holdings Corporation", "last_price": "0.48", "change": "+0.01", "change_pct": "+2.13%", "high": "0.49", "low": "0.47", "volume": "21,543,200", "sector": "Holding Firms"},
    {"symbol": "MJIC", "name": "Manila Jockey Club, Inc.", "last_price": "1.85", "change": "+0.05", "change_pct": "+2.78%", "high": "1.87", "low": "1.80", "volume": "543,200", "sector": "Consumer Cyclical"},
    {"symbol": "OPM", "name": "Oroport Mining Corporation", "last_price": "0.95", "change": "+0.02", "change_pct": "+2.15%", "high": "0.96", "low": "0.93", "volume": "3,456,700", "sector": "Basic Materials"},
    {"symbol": "ORE", "name": "Oriental Peninsula Resources Group Inc.", "last_price": "1.15", "change": "+0.03", "change_pct": "+2.68%", "high": "1.16", "low": "1.12", "volume": "5,432,100", "sector": "Basic Materials"},
    {"symbol": "PBC", "name": "Philippine Bank of Communications", "last_price": "12.50", "change": "+0.30", "change_pct": "+2.46%", "high": "12.60", "low": "12.30", "volume": "876,500", "sector": "Financial Services"},
    {"symbol": "PCP", "name": "PICOP Resources, Inc.", "last_price": "3.25", "change": "+0.10", "change_pct": "+3.17%", "high": "3.30", "low": "3.20", "volume": "1,234,500", "sector": "Basic Materials"},
    {"symbol": "PERC", "name": "Pacific Online Systems Corporation", "last_price": "4.85", "change": "+0.15", "change_pct": "+3.19%", "high": "4.90", "low": "4.80", "volume": "543,200", "sector": "Technology"},
    {"symbol": "PHR", "name": "PH Resorts Group Holdings, Inc.", "last_price": "1.45", "change": "+0.05", "change_pct": "+3.57%", "high": "1.47", "low": "1.42", "volume": "3,456,700", "sector": "Consumer Cyclical"},
    {"symbol": "PLC", "name": "Premium Leisure Corporation", "last_price": "0.85", "change": "+0.02", "change_pct": "+2.41%", "high": "0.86", "low": "0.83", "volume": "12,345,600", "sector": "Consumer Cyclical"},
    {"symbol": "PMPC", "name": "PMPC Corporation", "last_price": "5.25", "change": "+0.15", "change_pct": "+2.94%", "high": "5.30", "low": "5.20", "volume": "876,500", "sector": "Industrials"},
    {"symbol": "PNX", "name": "Phoenix Petroleum Philippines, Inc.", "last_price": "12.75", "change": "+0.35", "change_pct": "+2.82%", "high": "12.80", "low": "12.50", "volume": "1,234,500", "sector": "Energy"},
    {"symbol": "PPC", "name": "Pioneer Premium Brands, Inc.", "last_price": "3.50", "change": "+0.10", "change_pct": "+2.94%", "high": "3.55", "low": "3.45", "volume": "543,200", "sector": "Consumer Defensive"},
    {"symbol": "PSE", "name": "The Philippine Stock Exchange, Inc.", "last_price": "185.50", "change": "+3.50", "change_pct": "+1.92%", "high": "186.00", "low": "183.00", "volume": "45,320", "sector": "Financial Services"},
    {"symbol": "PX", "name": "Philex Mining Corporation", "last_price": "6.30", "change": "+0.55", "change_pct": "+9.57%", "high": "6.45", "low": "6.15", "volume": "16,543,200", "sector": "Basic Materials"},
    {"symbol": "BDO", "name": "BDO Unibank, Inc.", "last_price": "173.80", "change": "+4.30", "change_pct": "+2.54%", "high": "174.50", "low": "171.50", "volume": "4,876,500", "sector": "Financial Services"},
    {"symbol": "AC", "name": "Ayala Corporation", "last_price": "768.50", "change": "-9.50", "change_pct": "-1.22%", "high": "775.00", "low": "765.00", "volume": "245,600", "sector": "Conglomerates"},
    {"symbol": "AP", "name": "Aboitiz Power Corporation", "last_price": "45.20", "change": "+1.50", "change_pct": "+3.43%", "high": "45.50", "low": "44.50", "volume": "1,087,600", "sector": "Utilities"},
    {"symbol": "NOW", "name": "NOW Corporation", "last_price": "2.25", "change": "-0.25", "change_pct": "-10.00%", "high": "2.30", "low": "2.20", "volume": "12,654,300", "sector": "Technology"},
    {"symbol": "GLO", "name": "Globe Telecom, Inc.", "last_price": "2,325.00", "change": "+60.75", "change_pct": "+2.68%", "high": "2,330.00", "low": "2,295.00", "volume": "56,420", "sector": "Communication Services"},
    {"symbol": "GTCAP", "name": "GT Capital Holdings, Inc.", "last_price": "540.50", "change": "+20.00", "change_pct": "+3.84%", "high": "542.00", "low": "530.00", "volume": "56,780", "sector": "Conglomerates"},
    {"symbol": "SMPH", "name": "SM Prime Holdings, Inc.", "last_price": "26.25", "change": "+1.65", "change_pct": "+6.71%", "high": "26.50", "low": "25.80", "volume": "15,876,500", "sector": "Real Estate"},
    {"symbol": "VLL", "name": "Vista Land & Lifescapes, Inc.", "last_price": "1.90", "change": "-0.23", "change_pct": "-10.80%", "high": "2.00", "low": "1.85", "volume": "6,543,200", "sector": "Real Estate"},
    {"symbol": "JFC", "name": "Jollibee Foods Corporation", "last_price": "290.50", "change": "+15.70", "change_pct": "+5.71%", "high": "292.00", "low": "280.00", "volume": "1,543,200", "sector": "Consumer Cyclical"},
    {"symbol": "MBT", "name": "Metropolitan Bank & Trust Company", "last_price": "64.25", "change": "+1.75", "change_pct": "+2.80%", "high": "64.50", "low": "63.00", "volume": "2,654,300", "sector": "Financial Services"},
    {"symbol": "PGOLD", "name": "Puregold Price Club, Inc.", "last_price": "33.00", "change": "-1.00", "change_pct": "-2.94%", "high": "34.00", "low": "32.50", "volume": "4,321,500", "sector": "Consumer Defensive"},
    {"symbol": "ALI", "name": "Ayala Land, Inc.", "last_price": "35.25", "change": "+2.40", "change_pct": "+7.31%", "high": "35.50", "low": "34.00", "volume": "10,543,200", "sector": "Real Estate"},
    {"symbol": "MEG", "name": "Megaworld Corporation", "last_price": "2.65", "change": "+0.48", "change_pct": "+22.12%", "high": "2.70", "low": "2.50", "volume": "23,654,300", "sector": "Real Estate"},
    {"symbol": "DITO", "name": "DITO CME Holdings Corp.", "last_price": "1.95", "change": "-0.33", "change_pct": "-14.47%", "high": "2.20", "low": "1.85", "volume": "35,432,100", "sector": "Communication Services"},
    {"symbol": "FGEN", "name": "First Gen Corporation", "last_price": "19.80", "change": "-0.37", "change_pct": "-1.83%", "high": "20.20", "low": "19.50", "volume": "3,543,200", "sector": "Utilities"},
    {"symbol": "AEV", "name": "Aboitiz Equity Ventures, Inc.", "last_price": "50.75", "change": "+1.25", "change_pct": "+2.53%", "high": "51.00", "low": "49.50", "volume": "2,345,600", "sector": "Conglomerates"},
    {"symbol": "BEL", "name": "Bell Telecommunication Philippines, Inc.", "last_price": "1.85", "change": "+0.05", "change_pct": "+2.78%", "high": "1.87", "low": "1.80", "volume": "3,456,700", "sector": "Communication Services"},
    {"symbol": "BHI", "name": "Boulevard Holdings, Inc.", "last_price": "0.095", "change": "+0.005", "change_pct": "+5.56%", "high": "0.096", "low": "0.090", "volume": "21,543,200", "sector": "Consumer Cyclical"},
    {"symbol": "BRN", "name": "A Brown Company, Inc.", "last_price": "0.75", "change": "+0.02", "change_pct": "+2.74%", "high": "0.76", "low": "0.73", "volume": "5,432,100", "sector": "Real Estate"},
    {"symbol": "CEU", "name": "Centro Escolar University", "last_price": "12.50", "change": "+0.30", "change_pct": "+2.46%", "high": "12.60", "low": "12.30", "volume": "876,500", "sector": "Consumer Defensive"},
    {"symbol": "COL", "name": "COL Financial Group, Inc.", "last_price": "16.80", "change": "+0.50", "change_pct": "+3.07%", "high": "17.00", "low": "16.50", "volume": "1,234,500", "sector": "Financial Services"},
    {"symbol": "EEI", "name": "EEI Corporation", "last_price": "5.75", "change": "+0.15", "change_pct": "+2.68%", "high": "5.80", "low": "5.60", "volume": "2,345,600", "sector": "Industrials"},
    {"symbol": "EW", "name": "East West Banking Corporation", "last_price": "9.85", "change": "+0.25", "change_pct": "+2.60%", "high": "9.90", "low": "9.60", "volume": "3,456,700", "sector": "Financial Services"},
    {"symbol": "FERRO", "name": "Ferronickel Holdings, Inc.", "last_price": "1.95", "change": "+0.05", "change_pct": "+2.63%", "high": "2.00", "low": "1.90", "volume": "5,432,100", "sector": "Basic Materials"},
    {"symbol": "GPH", "name": "Grand Plaza Hotel Corporation", "last_price": "8.50", "change": "+0.20", "change_pct": "+2.41%", "high": "8.60", "low": "8.30", "volume": "543,200", "sector": "Consumer Cyclical"},
    {"symbol": "IDC", "name": "Italpinas Development Corporation", "last_price": "1.45", "change": "+0.05", "change_pct": "+3.57%", "high": "1.47", "low": "1.42", "volume": "3,456,700", "sector": "Real Estate"},
    {"symbol": "IPO", "name": "iPeople, Inc.", "last_price": "6.25", "change": "+0.15", "change_pct": "+2.46%", "high": "6.30", "low": "6.10", "volume": "876,500", "sector": "Consumer Defensive"},
    {"symbol": "ISM", "name": "ISM Communications Corporation", "last_price": "0.35", "change": "+0.01", "change_pct": "+2.94%", "high": "0.36", "low": "0.34", "volume": "12,345,600", "sector": "Communication Services"},
    {"symbol": "KEEPR", "name": "Keepers Holdings, Inc.", "last_price": "1.85", "change": "+0.05", "change_pct": "+2.78%", "high": "1.87", "low": "1.80", "volume": "5,432,100", "sector": "Consumer Defensive"},
    {"symbol": "LBC", "name": "LBC Express Holdings, Inc.", "last_price": "15.75", "change": "+0.35", "change_pct": "+2.27%", "high": "15.80", "low": "15.50", "volume": "876,500", "sector": "Industrials"},
    {"symbol": "LMG", "name": "LMG Chemicals Corporation", "last_price": "2.85", "change": "+0.10", "change_pct": "+3.64%", "high": "2.90", "low": "2.80", "volume": "3,456,700", "sector": "Basic Materials"},
    {"symbol": "LPZ", "name": "Lopez Holdings Corporation", "last_price": "5.25", "change": "+0.15", "change_pct": "+2.94%", "high": "5.30", "low": "5.20", "volume": "1,234,500", "sector": "Communication Services"},
    {"symbol": "MA", "name": "Manila Mining Corporation", "last_price": "0.0125", "change": "+0.0005", "change_pct": "+4.17%", "high": "0.0130", "low": "0.0120", "volume": "45,432,100", "sector": "Basic Materials"},
    {"symbol": "MG", "name": "Millennium Global Holdings, Inc.", "last_price": "0.65", "change": "+0.02", "change_pct": "+3.17%", "high": "0.66", "low": "0.63", "volume": "12,345,600", "sector": "Consumer Defensive"},
    {"symbol": "MM", "name": "Metro Retail Stores Group, Inc.", "last_price": "1.45", "change": "+0.05", "change_pct": "+3.57%", "high": "1.47", "low": "1.42", "volume": "5,432,100", "sector": "Consumer Cyclical"},
    {"symbol": "NRCP", "name": "National Reinsurance Corporation of the Philippines", "last_price": "1.25", "change": "+0.03", "change_pct": "+2.46%", "high": "1.26", "low": "1.22", "volume": "3,456,700", "sector": "Financial Services"},
    {"symbol": "OM", "name": "Omico Corporation", "last_price": "0.85", "change": "+0.02", "change_pct": "+2.41%", "high": "0.86", "low": "0.83", "volume": "12,345,600", "sector": "Real Estate"},
    {"symbol": "PA", "name": "Pacifica Holdings, Inc.", "last_price": "0.55", "change": "+0.01", "change_pct": "+1.85%", "high": "0.56", "low": "0.54", "volume": "21,543,200", "sector": "Basic Materials"},
    {"symbol": "PAL", "name": "PAL Holdings, Inc.", "last_price": "8.75", "change": "+0.25", "change_pct": "+2.94%", "high": "8.80", "low": "8.60", "volume": "3,456,700", "sector": "Industrials"},
    {"symbol": "PHA", "name": "Premiere Horizon Alliance Corporation", "last_price": "0.65", "change": "+0.02", "change_pct": "+3.17%", "high": "0.66", "low": "0.63", "volume": "12,345,600", "sector": "Real Estate"},
    {"symbol": "PIZZA", "name": "Shakey's Pizza Asia Ventures, Inc.", "last_price": "9.75", "change": "-0.25", "change_pct": "-2.50%", "high": "10.00", "low": "9.70", "volume": "1,234,500", "sector": "Consumer Cyclical"},
    {"symbol": "PRMX", "name": "Primex Corporation", "last_price": "2.30", "change": "+0.10", "change_pct": "+4.55%", "high": "2.35", "low": "2.25", "volume": "3,456,700", "sector": "Real Estate"},
    {"symbol": "PSE", "name": "The Philippine Stock Exchange, Inc.", "last_price": "185.50", "change": "+3.50", "change_pct": "+1.92%", "high": "186.00", "low": "183.00", "volume": "45,320", "sector": "Financial Services"}
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
    # Sample UK stock data (manually entered)
    sample_stocks = [
       {"symbol": "AZN.L", "name": "AstraZeneca", "last_price": "10,420.00", "change": "+185.00", "change_pct": "+1.81%", "high": "10,450.00", "low": "10,380.00", "volume": "1,056,800", "sector": "Pharmaceuticals"},
    {"symbol": "SHEL.L", "name": "Shell", "last_price": "2,680.50", "change": "-32.50", "change_pct": "-1.20%", "high": "2,695.00", "low": "2,670.00", "volume": "4,125,600", "sector": "Energy"},
    {"symbol": "HSBA.L", "name": "HSBC Holdings", "last_price": "632.40", "change": "+8.20", "change_pct": "+1.31%", "high": "634.00", "low": "628.50", "volume": "9,876,500", "sector": "Banking"},
    {"symbol": "ULVR.L", "name": "Unilever", "last_price": "4,180.00", "change": "-42.00", "change_pct": "-1.00%", "high": "4,195.00", "low": "4,165.00", "volume": "1,543,200", "sector": "Consumer Goods"},
    {"symbol": "DGE.L", "name": "Diageo", "last_price": "3,512.00", "change": "+28.50", "change_pct": "+0.82%", "high": "3,520.00", "low": "3,500.00", "volume": "987,650", "sector": "Beverages"},
    {"symbol": "BP.L", "name": "BP", "last_price": "515.80", "change": "-6.20", "change_pct": "-1.19%", "high": "518.00", "low": "514.50", "volume": "18,765,400", "sector": "Energy"},
    {"symbol": "GSK.L", "name": "GSK", "last_price": "1,625.50", "change": "+22.50", "change_pct": "+1.40%", "high": "1,630.00", "low": "1,615.00", "volume": "5,432,100", "sector": "Pharmaceuticals"},
    {"symbol": "RIO.L", "name": "Rio Tinto", "last_price": "5,680.00", "change": "+95.00", "change_pct": "+1.70%", "high": "5,700.00", "low": "5,650.00", "volume": "1,345,600", "sector": "Mining"},
    {"symbol": "BATS.L", "name": "British American Tobacco", "last_price": "2,480.00", "change": "-32.00", "change_pct": "-1.27%", "high": "2,490.00", "low": "2,475.00", "volume": "2,345,600", "sector": "Tobacco"},
    {"symbol": "GLEN.L", "name": "Glencore", "last_price": "440.25", "change": "+7.75", "change_pct": "+1.79%", "high": "442.00", "low": "438.50", "volume": "10,987,600", "sector": "Mining"},
    {"symbol": "REL.L", "name": "RELX", "last_price": "3,025.00", "change": "+18.00", "change_pct": "+0.60%", "high": "3,030.00", "low": "3,015.00", "volume": "654,320", "sector": "Media"},
    {"symbol": "PRU.L", "name": "Prudential", "last_price": "1,120.50", "change": "+15.50", "change_pct": "+1.40%", "high": "1,125.00", "low": "1,115.00", "volume": "2,345,600", "sector": "Insurance"},
    {"symbol": "NG.L", "name": "National Grid", "last_price": "1,082.00", "change": "+4.50", "change_pct": "+0.42%", "high": "1,085.00", "low": "1,080.00", "volume": "3,456,700", "sector": "Utilities"},
    {"symbol": "VOD.L", "name": "Vodafone Group", "last_price": "72.15", "change": "-1.85", "change_pct": "-2.50%", "high": "73.50", "low": "72.00", "volume": "45,678,900", "sector": "Telecommunications"},
    {"symbol": "LLOY.L", "name": "Lloyds Banking Group", "last_price": "48.90", "change": "+0.95", "change_pct": "+1.98%", "high": "49.10", "low": "48.50", "volume": "56,789,000", "sector": "Banking"},
    {"symbol": "BARC.L", "name": "Barclays", "last_price": "185.40", "change": "+3.20", "change_pct": "+1.76%", "high": "186.00", "low": "184.00", "volume": "15,678,200", "sector": "Banking"},
    {"symbol": "TSCO.L", "name": "Tesco", "last_price": "285.60", "change": "+3.40", "change_pct": "+1.20%", "high": "286.50", "low": "284.00", "volume": "25,678,900", "sector": "Retail"},
    {"symbol": "AAL.L", "name": "Anglo American", "last_price": "2,280.00", "change": "-42.00", "change_pct": "-1.81%", "high": "2,295.00", "low": "2,275.00", "volume": "1,876,500", "sector": "Mining"},
    {"symbol": "IMB.L", "name": "Imperial Brands", "last_price": "1,780.00", "change": "-15.00", "change_pct": "-0.84%", "high": "1,785.00", "low": "1,775.00", "volume": "1,543,200", "sector": "Tobacco"},
    {"symbol": "LGEN.L", "name": "Legal & General", "last_price": "238.40", "change": "+1.60", "change_pct": "+0.68%", "high": "239.00", "low": "237.50", "volume": "4,567,800", "sector": "Financial Services"},
    {"symbol": "STAN.L", "name": "Standard Chartered", "last_price": "725.50", "change": "+12.50", "change_pct": "+1.75%", "high": "728.00", "low": "723.00", "volume": "3,456,700", "sector": "Banking"},
    {"symbol": "CRDA.L", "name": "Croda International", "last_price": "5,240.00", "change": "+65.00", "change_pct": "+1.26%", "high": "5,250.00", "low": "5,230.00", "volume": "345,670", "sector": "Chemicals"},
    {"symbol": "SPX.L", "name": "Spirax-Sarco Engineering", "last_price": "10,250.00", "change": "+125.00", "change_pct": "+1.23%", "high": "10,275.00", "low": "10,200.00", "volume": "123,450", "sector": "Industrials"},
    {"symbol": "EXPN.L", "name": "Experian", "last_price": "2,850.00", "change": "+32.00", "change_pct": "+1.14%", "high": "2,860.00", "low": "2,840.00", "volume": "876,540", "sector": "Information Services"},
    {"symbol": "SMDS.L", "name": "Smiths Group", "last_price": "1,680.00", "change": "+18.00", "change_pct": "+1.08%", "high": "1,685.00", "low": "1,675.00", "volume": "543,210", "sector": "Industrials"},
    {"symbol": "SGRO.L", "name": "Segro", "last_price": "825.50", "change": "-7.50", "change_pct": "-0.90%", "high": "830.00", "low": "824.00", "volume": "2,345,600", "sector": "Real Estate"},
    {"symbol": "LAND.L", "name": "Land Securities Group", "last_price": "680.40", "change": "+3.60", "change_pct": "+0.53%", "high": "682.00", "low": "678.00", "volume": "1,987,600", "sector": "Real Estate"},
    {"symbol": "RTO.L", "name": "Rentokil Initial", "last_price": "545.00", "change": "+8.00", "change_pct": "+1.49%", "high": "546.50", "low": "543.00", "volume": "3,456,700", "sector": "Business Services"},
    {"symbol": "ICP.L", "name": "Intermediate Capital Group", "last_price": "1,720.00", "change": "+25.00", "change_pct": "+1.47%", "high": "1,725.00", "low": "1,715.00", "volume": "876,540", "sector": "Financial Services"},
    {"symbol": "MNDI.L", "name": "Mondi", "last_price": "1,450.00", "change": "-22.00", "change_pct": "-1.49%", "high": "1,460.00", "low": "1,445.00", "volume": "1,234,500", "sector": "Packaging"},
    {"symbol": "WTB.L", "name": "Whitbread", "last_price": "3,280.00", "change": "+42.00", "change_pct": "+1.30%", "high": "3,285.00", "low": "3,270.00", "volume": "543,210", "sector": "Hospitality"},
    {"symbol": "ANTO.L", "name": "Antofagasta", "last_price": "1,520.00", "change": "-18.00", "change_pct": "-1.17%", "high": "1,525.00", "low": "1,515.00", "volume": "1,543,200", "sector": "Mining"},
    {"symbol": "PSN.L", "name": "Persimmon", "last_price": "1,280.50", "change": "+15.50", "change_pct": "+1.23%", "high": "1,285.00", "low": "1,275.00", "volume": "876,540", "sector": "Housebuilding"},
    {"symbol": "KGF.L", "name": "Kingfisher", "last_price": "240.60", "change": "+2.10", "change_pct": "+0.88%", "high": "241.00", "low": "239.50", "volume": "4,567,800", "sector": "Retail"},
    {"symbol": "MKS.L", "name": "Marks & Spencer", "last_price": "260.40", "change": "+3.60", "change_pct": "+1.40%", "high": "261.00", "low": "259.00", "volume": "5,432,100", "sector": "Retail"},
    {"symbol": "CCH.L", "name": "Coca-Cola HBC", "last_price": "2,350.00", "change": "+18.00", "change_pct": "+0.77%", "high": "2,355.00", "low": "2,345.00", "volume": "654,320", "sector": "Beverages"},
    {"symbol": "SVT.L", "name": "Severn Trent", "last_price": "2,680.00", "change": "+12.00", "change_pct": "+0.45%", "high": "2,685.00", "low": "2,675.00", "volume": "543,210", "sector": "Utilities"},
    {"symbol": "UU.L", "name": "United Utilities", "last_price": "1,025.00", "change": "+3.00", "change_pct": "+0.29%", "high": "1,027.00", "low": "1,023.00", "volume": "876,540", "sector": "Utilities"},
    {"symbol": "BA.L", "name": "BAE Systems", "last_price": "1,050.50", "change": "+8.50", "change_pct": "+0.82%", "high": "1,052.00", "low": "1,048.00", "volume": "2,345,600", "sector": "Aerospace & Defense"},
    {"symbol": "RR.L", "name": "Rolls-Royce", "last_price": "230.40", "change": "+3.60", "change_pct": "+1.59%", "high": "231.50", "low": "229.00", "volume": "15,678,200", "sector": "Aerospace & Defense"},
    {"symbol": "AHT.L", "name": "Ashtead Group", "last_price": "5,250.00", "change": "+75.00", "change_pct": "+1.45%", "high": "5,260.00", "low": "5,240.00", "volume": "345,670", "sector": "Industrial Services"},
    {"symbol": "RMV.L", "name": "Rightmove", "last_price": "580.50", "change": "-4.50", "change_pct": "-0.77%", "high": "582.00", "low": "579.00", "volume": "1,234,500", "sector": "Property Portal"},
    {"symbol": "OCDO.L", "name": "Ocado", "last_price": "680.00", "change": "-12.00", "change_pct": "-1.73%", "high": "685.00", "low": "678.00", "volume": "2,345,600", "sector": "Retail"},
    {"symbol": "III.L", "name": "3i Group", "last_price": "2,150.00", "change": "+32.00", "change_pct": "+1.51%", "high": "2,155.00", "low": "2,145.00", "volume": "876,540", "sector": "Private Equity"},
    {"symbol": "ABDN.L", "name": "abrdn", "last_price": "185.60", "change": "+1.60", "change_pct": "+0.87%", "high": "186.00", "low": "185.00", "volume": "3,456,700", "sector": "Asset Management"},
    {"symbol": "AV.L", "name": "Aviva", "last_price": "420.50", "change": "+3.50", "change_pct": "+0.84%", "high": "421.00", "low": "419.00", "volume": "5,432,100", "sector": "Insurance"},
    {"symbol": "BNZL.L", "name": "Bunzl", "last_price": "2,850.00", "change": "+18.00", "change_pct": "+0.64%", "high": "2,855.00", "low": "2,845.00", "volume": "543,210", "sector": "Distribution"},
    {"symbol": "FRES.L", "name": "Fresnillo", "last_price": "680.00", "change": "-8.00", "change_pct": "-1.16%", "high": "685.00", "low": "678.00", "volume": "1,543,200", "sector": "Mining"},
    {"symbol": "ITRK.L", "name": "Intertek", "last_price": "4,250.00", "change": "+32.00", "change_pct": "+0.76%", "high": "4,255.00", "low": "4,245.00", "volume": "345,670", "sector": "Testing & Inspection"},
    {"symbol": "SDR.L", "name": "Schroders", "last_price": "450.50", "change": "+2.50", "change_pct": "+0.56%", "high": "451.00", "low": "449.00", "volume": "876,540", "sector": "Asset Management"},
    {"symbol": "WEIR.L", "name": "Weir Group", "last_price": "1,850.00", "change": "+15.00", "change_pct": "+0.82%", "high": "1,855.00", "low": "1,845.00", "volume": "543,210", "sector": "Engineering"}
    ]

    # Get all unique sectors for the filter dropdown
    all_sectors = sorted(list({stock["sector"] for stock in sample_stocks}))
    error_message = None
    symbols = []
    
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
                if performance_filter == "most_active" and float(stock["volume"].replace(',', '')) < 2000000:  # Adjusted threshold for UK stocks
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
        "uk_stocks.html", 
        stocks_data=stocks_data, 
        symbols=symbols, 
        error_message=error_message,
        all_sectors=all_sectors,
        current_sector=request.form.get("sector", "") if request.method == "POST" else "",
        current_price_min=request.form.get("price_min", "") if request.method == "POST" else "",
        current_price_max=request.form.get("price_max", "") if request.method == "POST" else "",
        current_performance=request.form.get("performance", "") if request.method == "POST" else ""
    )

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
    # Sample German stock data (manually entered)
    sample_stocks = [
       {"symbol": "SAP.DE", "name": "SAP SE", "last_price": "178.20", "change": "+2.70", "change_pct": "+1.54%", "high": "179.00", "low": "176.50", "volume": "1,345,600", "sector": "Technology"},
    {"symbol": "DTE.DE", "name": "Deutsche Telekom AG", "last_price": "23.15", "change": "+0.40", "change_pct": "+1.76%", "high": "23.30", "low": "22.90", "volume": "6,789,000", "sector": "Telecommunications"},
    {"symbol": "ALV.DE", "name": "Allianz SE", "last_price": "268.50", "change": "+3.10", "change_pct": "+1.17%", "high": "269.80", "low": "266.20", "volume": "654,320", "sector": "Insurance"},
    {"symbol": "LIN.DE", "name": "Linde plc", "last_price": "430.25", "change": "+4.75", "change_pct": "+1.12%", "high": "431.50", "low": "428.00", "volume": "456,780", "sector": "Chemicals"},
    {"symbol": "VOW3.DE", "name": "Volkswagen AG", "last_price": "128.40", "change": "+2.60", "change_pct": "+2.07%", "high": "129.00", "low": "126.80", "volume": "1,654,300", "sector": "Automotive"},
    {"symbol": "BMW.DE", "name": "BMW AG", "last_price": "107.80", "change": "+2.55", "change_pct": "+2.42%", "high": "108.20", "low": "106.50", "volume": "1,023,400", "sector": "Automotive"},
    {"symbol": "SIE.DE", "name": "Siemens AG", "last_price": "187.50", "change": "+2.25", "change_pct": "+1.21%", "high": "188.00", "low": "186.00", "volume": "987,650", "sector": "Industrial"},
    {"symbol": "DB1.DE", "name": "Deutsche Börse AG", "last_price": "185.40", "change": "+1.40", "change_pct": "+0.76%", "high": "186.00", "low": "184.50", "volume": "345,670", "sector": "Financial Services"},
    {"symbol": "BAYN.DE", "name": "Bayer AG", "last_price": "31.20", "change": "-1.25", "change_pct": "-3.85%", "high": "32.50", "low": "31.00", "volume": "4,567,800", "sector": "Pharmaceuticals"},
    {"symbol": "BAS.DE", "name": "BASF SE", "last_price": "47.85", "change": "-1.05", "change_pct": "-2.15%", "high": "48.50", "low": "47.60", "volume": "2,456,700", "sector": "Chemicals"},
    {"symbol": "RWE.DE", "name": "RWE AG", "last_price": "43.60", "change": "+1.30", "change_pct": "+3.07%", "high": "43.90", "low": "42.80", "volume": "2,187,600", "sector": "Energy"},
    {"symbol": "MRK.DE", "name": "Merck KGaA", "last_price": "178.20", "change": "+2.40", "change_pct": "+1.37%", "high": "178.80", "low": "176.50", "volume": "567,890", "sector": "Pharmaceuticals"},
    {"symbol": "ADS.DE", "name": "Adidas AG", "last_price": "220.40", "change": "+4.80", "change_pct": "+2.23%", "high": "221.50", "low": "218.00", "volume": "1,345,600", "sector": "Consumer Goods"},
    {"symbol": "FRE.DE", "name": "Fresenius SE & Co. KGaA", "last_price": "27.80", "change": "-1.10", "change_pct": "-3.81%", "high": "28.50", "low": "27.60", "volume": "1,654,300", "sector": "Healthcare"},
    {"symbol": "IFX.DE", "name": "Infineon Technologies AG", "last_price": "40.25", "change": "+1.50", "change_pct": "+3.87%", "high": "40.50", "low": "39.50", "volume": "4,567,800", "sector": "Semiconductors"},
    {"symbol": "HEN3.DE", "name": "Henkel AG & Co. KGaA", "last_price": "79.60", "change": "+1.20", "change_pct": "+1.53%", "high": "79.90", "low": "78.80", "volume": "654,320", "sector": "Consumer Goods"},
    {"symbol": "DBK.DE", "name": "Deutsche Bank AG", "last_price": "15.20", "change": "+0.35", "change_pct": "+2.36%", "high": "15.30", "low": "14.90", "volume": "9,876,500", "sector": "Banking"},
    {"symbol": "CON.DE", "name": "Continental AG", "last_price": "70.40", "change": "+1.50", "change_pct": "+2.18%", "high": "70.80", "low": "69.50", "volume": "1,234,500", "sector": "Automotive"},
    {"symbol": "DPW.DE", "name": "Deutsche Post AG", "last_price": "43.25", "change": "+1.10", "change_pct": "+2.61%", "high": "43.50", "low": "42.80", "volume": "1,345,600", "sector": "Logistics"},
    {"symbol": "EOAN.DE", "name": "E.ON SE", "last_price": "12.80", "change": "+0.35", "change_pct": "+2.81%", "high": "12.90", "low": "12.60", "volume": "5,678,900", "sector": "Energy"},
    {"symbol": "LHA.DE", "name": "Deutsche Lufthansa AG", "last_price": "9.05", "change": "+0.30", "change_pct": "+3.43%", "high": "9.10", "low": "8.90", "volume": "6,789,000", "sector": "Airlines"},
    {"symbol": "ZAL.DE", "name": "Zalando SE", "last_price": "28.75", "change": "-1.25", "change_pct": "-4.17%", "high": "29.50", "low": "28.60", "volume": "1,543,200", "sector": "E-Commerce"},
    {"symbol": "SHL.DE", "name": "Siemens Healthineers AG", "last_price": "52.40", "change": "+0.90", "change_pct": "+1.75%", "high": "52.80", "low": "52.00", "volume": "1,234,500", "sector": "Healthcare"},
    {"symbol": "MTX.DE", "name": "MTU Aero Engines AG", "last_price": "245.60", "change": "+3.60", "change_pct": "+1.49%", "high": "246.50", "low": "243.50", "volume": "345,670", "sector": "Aerospace"},
    {"symbol": "1COV.DE", "name": "Covestro AG", "last_price": "48.90", "change": "+1.40", "change_pct": "+2.95%", "high": "49.20", "low": "48.00", "volume": "1,654,300", "sector": "Chemicals"},
    {"symbol": "BEI.DE", "name": "Beiersdorf AG", "last_price": "125.40", "change": "+1.40", "change_pct": "+1.13%", "high": "125.80", "low": "124.50", "volume": "456,780", "sector": "Consumer Goods"},
    {"symbol": "SY1.DE", "name": "Symrise AG", "last_price": "98.75", "change": "-1.25", "change_pct": "-1.25%", "high": "99.50", "low": "98.50", "volume": "345,670", "sector": "Chemicals"},
    {"symbol": "PUM.DE", "name": "Puma SE", "last_price": "62.40", "change": "+1.40", "change_pct": "+2.30%", "high": "62.80", "low": "61.50", "volume": "987,650", "sector": "Consumer Goods"},
    {"symbol": "HFG.DE", "name": "HelloFresh SE", "last_price": "18.20", "change": "-0.80", "change_pct": "-4.21%", "high": "18.80", "low": "18.10", "volume": "1,543,200", "sector": "Food Delivery"},
    {"symbol": "BNR.DE", "name": "Brenntag SE", "last_price": "82.50", "change": "+1.50", "change_pct": "+1.85%", "high": "82.90", "low": "81.80", "volume": "654,320", "sector": "Chemicals"},
    {"symbol": "DHL.DE", "name": "DHL Group", "last_price": "42.80", "change": "+0.80", "change_pct": "+1.90%", "high": "43.00", "low": "42.50", "volume": "1,234,500", "sector": "Logistics"},
    {"symbol": "FME.DE", "name": "Fresenius Medical Care AG", "last_price": "32.45", "change": "-0.85", "change_pct": "-2.55%", "high": "33.00", "low": "32.30", "volume": "2,345,600", "sector": "Healthcare"},
    {"symbol": "TKA.DE", "name": "Thyssenkrupp AG", "last_price": "6.85", "change": "+0.15", "change_pct": "+2.24%", "high": "6.90", "low": "6.75", "volume": "5,678,900", "sector": "Industrial"},
    {"symbol": "EVK.DE", "name": "Evonik Industries AG", "last_price": "19.40", "change": "-0.30", "change_pct": "-1.52%", "high": "19.70", "low": "19.30", "volume": "1,654,300", "sector": "Chemicals"},
    {"symbol": "NDA.DE", "name": "Nordex SE", "last_price": "12.35", "change": "+0.45", "change_pct": "+3.78%", "high": "12.50", "low": "12.20", "volume": "2,345,600", "sector": "Renewable Energy"},
    {"symbol": "SDF.DE", "name": "K+S AG", "last_price": "14.80", "change": "+0.30", "change_pct": "+2.07%", "high": "14.90", "low": "14.60", "volume": "1,543,200", "sector": "Chemicals"},
    {"symbol": "GXI.DE", "name": "Gerresheimer AG", "last_price": "98.50", "change": "+1.50", "change_pct": "+1.55%", "high": "98.90", "low": "97.80", "volume": "345,670", "sector": "Pharmaceuticals"},
    {"symbol": "SAZ.DE", "name": "Strabag SE", "last_price": "42.15", "change": "+0.65", "change_pct": "+1.57%", "high": "42.30", "low": "41.80", "volume": "654,320", "sector": "Construction"},
    {"symbol": "HNR1.DE", "name": "Hannover Rück SE", "last_price": "215.60", "change": "+2.60", "change_pct": "+1.22%", "high": "216.00", "low": "214.00", "volume": "456,780", "sector": "Insurance"},
    {"symbol": "BOSS.DE", "name": "Hugo Boss AG", "last_price": "58.90", "change": "+1.10", "change_pct": "+1.90%", "high": "59.20", "low": "58.50", "volume": "987,650", "sector": "Apparel"},
    {"symbol": "UN01.DE", "name": "Uniper SE", "last_price": "14.25", "change": "+0.35", "change_pct": "+2.52%", "high": "14.30", "low": "14.00", "volume": "3,456,700", "sector": "Energy"},
    {"symbol": "AFX.DE", "name": "Carl Zeiss Meditec AG", "last_price": "125.40", "change": "-1.60", "change_pct": "-1.26%", "high": "126.50", "low": "125.00", "volume": "345,670", "sector": "Healthcare"},
    {"symbol": "OSR.DE", "name": "OSRAM Licht AG", "last_price": "52.30", "change": "+0.80", "change_pct": "+1.55%", "high": "52.50", "low": "52.00", "volume": "1,234,500", "sector": "Technology"},
    {"symbol": "PFV.DE", "name": "Pfeiffer Vacuum Technology AG", "last_price": "145.60", "change": "+2.60", "change_pct": "+1.82%", "high": "146.00", "low": "144.50", "volume": "54,320", "sector": "Industrial"},
    {"symbol": "FNTN.DE", "name": "Freenet AG", "last_price": "26.80", "change": "-0.40", "change_pct": "-1.47%", "high": "27.00", "low": "26.70", "volume": "654,320", "sector": "Telecommunications"},
    {"symbol": "JUN3.DE", "name": "Jungheinrich AG", "last_price": "32.45", "change": "+0.45", "change_pct": "+1.41%", "high": "32.50", "low": "32.20", "volume": "345,670", "sector": "Industrial"},
    {"symbol": "KRN.DE", "name": "Krones AG", "last_price": "125.40", "change": "+1.40", "change_pct": "+1.13%", "high": "125.80", "low": "124.50", "volume": "456,780", "sector": "Industrial"},
    {"symbol": "LEG.DE", "name": "LEG Immobilien SE", "last_price": "78.90", "change": "-0.60", "change_pct": "-0.75%", "high": "79.20", "low": "78.80", "volume": "987,650", "sector": "Real Estate"},
    {"symbol": "RHK.DE", "name": "Rhön-Klinikum AG", "last_price": "22.45", "change": "+0.25", "change_pct": "+1.13%", "high": "22.50", "low": "22.30", "volume": "345,670", "sector": "Healthcare"},
    {"symbol": "VNA.DE", "name": "Vonovia SE", "last_price": "28.75", "change": "+0.45", "change_pct": "+1.59%", "high": "28.90", "low": "28.50", "volume": "2,345,600", "sector": "Real Estate"},
    {"symbol": "WCH.DE", "name": "Wacker Chemie AG", "last_price": "115.60", "change": "+1.60", "change_pct": "+1.40%", "high": "115.90", "low": "114.80", "volume": "654,320", "sector": "Chemicals"}
    ]

    # Get all unique sectors for the filter dropdown
    all_sectors = sorted(list({stock["sector"] for stock in sample_stocks}))
    error_message = None
    symbols = []
    
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
                if performance_filter == "most_active" and float(stock["volume"].replace(',', '')) < 1000000:  # Adjusted threshold for German stocks
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
        "ge_stocks.html", 
        stocks_data=stocks_data, 
        symbols=symbols, 
        error_message=error_message,
        all_sectors=all_sectors,
        current_sector=request.form.get("sector", "") if request.method == "POST" else "",
        current_price_min=request.form.get("price_min", "") if request.method == "POST" else "",
        current_price_max=request.form.get("price_max", "") if request.method == "POST" else "",
        current_performance=request.form.get("performance", "") if request.method == "POST" else ""
    )
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
        {"url": "https://apnews.com/hub/apf-topnews", "name": "/apnews.com", "type": "html"}
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