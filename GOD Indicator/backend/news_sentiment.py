"""
News & Sentiment Analysis for Stocks
Fetches financial news and analyzes sentiment to aid trading decisions
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logging.warning("TextBlob not available. Install with: pip install textblob")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsSentimentAnalyzer:
    """
    Fetch and analyze financial news sentiment for stocks
    
    Supports:
    - NewsData.io (primary source with your API key)
    - NewsAPI.org (alternative source)
    - Google News RSS feeds (fallback)
    """
    
    def __init__(self, newsdata_key: str = "pub_351be3c902b4478180538c1f6c2c33d3", newsapi_key: str = None):
        """
        Initialize news sentiment analyzer
        
        Args:
            newsdata_key: NewsData.io API key (default provided)
            newsapi_key: NewsAPI.org API key (optional)
        """
        self.newsdata_key = newsdata_key
        self.newsapi_key = newsapi_key
        self.newsdata_url = "https://newsdata.io/api/1/news"
        self.newsapi_url = "https://newsapi.org/v2/everything"
    
    def get_stock_news(self, symbol: str, days: int = 7, max_articles: int = 10) -> List[Dict]:
        """
        Fetch recent news articles for a stock
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS', 'AAPL')
            days: Number of days to look back
            max_articles: Maximum number of articles to return
            
        Returns:
            List of news articles with title, description, source, etc.
        """
        # Clean symbol for search
        search_term = symbol.replace('.NS', '').replace('.BSE', '').replace('.BO', '')
        
        # Add company keywords for better results
        company_keywords = {
            'RELIANCE': 'Reliance Industries',
            'TCS': 'Tata Consultancy Services',
            'INFY': 'Infosys',
            'HDFC': 'HDFC Bank',
            'ICICI': 'ICICI Bank',
            'ITC': 'ITC Limited',
            'AAPL': 'Apple Inc',
            'MSFT': 'Microsoft',
            'GOOGL': 'Google',
            'TSLA': 'Tesla'
        }
        
        search_query = company_keywords.get(search_term, search_term)
        
        articles = []
        
        # Try NewsData.io first (primary source)
        if self.newsdata_key:
            try:
                articles = self._fetch_from_newsdata(search_query, max_articles)
                logger.info(f"Fetched {len(articles)} articles from NewsData.io")
            except Exception as e:
                logger.warning(f"NewsData.io failed: {e}")
        
        # Fallback 1: Try NewsAPI.org
        if not articles and self.newsapi_key:
            try:
                articles = self._fetch_from_newsapi(search_query, days, max_articles)
                logger.info(f"Fetched {len(articles)} articles from NewsAPI.org")
            except Exception as e:
                logger.warning(f"NewsAPI failed: {e}")
        
        # Fallback 2: Try Google News RSS
        if not articles:
            try:
                articles = self._fetch_from_google_news(search_query, max_articles)
                logger.info(f"Fetched {len(articles)} articles from Google News")
            except Exception as e:
                logger.warning(f"Google News failed: {e}")
        
        return articles
    
    def _fetch_from_newsdata(self, query: str, max_articles: int) -> List[Dict]:
        """Fetch news from NewsData.io (primary source)"""
        params = {
            'apikey': self.newsdata_key,
            'q': query,
            'language': 'en',
            'category': 'business',
            'size': max_articles
        }
        
        response = requests.get(self.newsdata_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') != 'success':
            raise Exception(f"NewsData.io error: {data.get('message', 'Unknown error')}")
        
        articles = data.get('results', [])
        
        return [{
            'title': a.get('title', ''),
            'description': a.get('description', ''),
            'source': a.get('source_id', 'Unknown'),
            'published_at': a.get('pubDate', ''),
            'url': a.get('link', ''),
            'author': ', '.join(a.get('creator', [])) if a.get('creator') else 'Unknown',
            'country': a.get('country', ['unknown'])[0] if a.get('country') else 'unknown',
            'category': ', '.join(a.get('category', [])) if a.get('category') else 'business'
        } for a in articles if a.get('title')]
    
    def _fetch_from_newsapi(self, query: str, days: int, max_articles: int) -> List[Dict]:
        """Fetch news from NewsAPI.org (fallback)"""
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        params = {
            'q': query,
            'apiKey': self.newsapi_key,
            'language': 'en',
            'sortBy': 'publishedAt',
            'from': from_date,
            'pageSize': max_articles
        }
        
        response = requests.get(self.newsapi_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get('articles', [])
        
        return [{
            'title': a.get('title', ''),
            'description': a.get('description', ''),
            'source': a.get('source', {}).get('name', 'Unknown'),
            'published_at': a.get('publishedAt', ''),
            'url': a.get('url', ''),
            'author': a.get('author', 'Unknown')
        } for a in articles if a.get('title')]
    
    def _fetch_from_google_news(self, query: str, max_articles: int) -> List[Dict]:
        """Fetch news from Google News RSS (fallback)"""
        # Google News RSS feed
        import feedparser
        
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        try:
            feed = feedparser.parse(url)
            articles = []
            
            for entry in feed.entries[:max_articles]:
                articles.append({
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', ''),
                    'source': entry.get('source', {}).get('title', 'Google News'),
                    'published_at': entry.get('published', ''),
                    'url': entry.get('link', ''),
                    'author': 'Google News'
                })
            
            return articles
        except:
            # Return empty if feedparser not available
            return []
    
    def analyze_sentiment(self, articles: List[Dict]) -> Dict:
        """
        Analyze sentiment of news articles
        
        Args:
            articles: List of news articles from get_stock_news()
            
        Returns:
            Dict with:
            - score: -1.0 (very negative) to +1.0 (very positive)
            - label: 'POSITIVE', 'NEGATIVE', or 'NEUTRAL'
            - emoji: Visual representation
            - confidence: How confident the sentiment is (0-1)
            - summary: Human-readable summary
            - article_count: Number of articles analyzed
        """
        if not articles:
            return {
                'score': 0.0,
                'label': 'NEUTRAL',
                'emoji': '😐',
                'confidence': 0.0,
                'summary': 'No recent news available',
                'article_count': 0
            }
        
        if not TEXTBLOB_AVAILABLE:
            return {
                'score': 0.0,
                'label': 'UNKNOWN',
                'emoji': '❓',
                'confidence': 0.0,
                'summary': 'Sentiment analysis unavailable (install textblob)',
                'article_count': len(articles)
            }
        
        # Analyze each article
        sentiments = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            
            # Skip empty articles
            if not text.strip():
                continue
            
            try:
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity
                sentiments.append(polarity)
            except Exception as e:
                logger.warning(f"Sentiment analysis failed for article: {e}")
                continue
        
        if not sentiments:
            return {
                'score': 0.0,
                'label': 'NEUTRAL',
                'emoji': '😐',
                'confidence': 0.0,
                'summary': 'Unable to analyze sentiment',
                'article_count': len(articles)
            }
        
        # Calculate aggregate sentiment
        avg_score = sum(sentiments) / len(sentiments)
        confidence = abs(avg_score)
        
        # Classify sentiment
        if avg_score > 0.2:
            label = 'POSITIVE'
            emoji = '😊'
            color = '#2ecc71'
        elif avg_score < -0.2:
            label = 'NEGATIVE'
            emoji = '😟'
            color = '#e74c3c'
        else:
            label = 'NEUTRAL'
            emoji = '😐'
            color = '#95a5a6'
        
        # Generate summary
        percentage = int((avg_score + 1) / 2 * 100)  # Convert -1,1 to 0,100
        summary = f"{label} sentiment ({percentage}%) from {len(articles)} articles"
        
        return {
            'score': round(avg_score, 3),
            'label': label,
            'emoji': emoji,
            'color': color,
            'confidence': round(confidence, 3),
            'summary': summary,
            'article_count': len(articles),
            'percentage': percentage
        }
    
    def get_sentiment_signal(self, symbol: str, days: int = 7) -> Dict:
        """
        Get complete sentiment analysis for a stock (convenience method)
        
        Args:
            symbol: Stock symbol
            days: Days to look back for news
            
        Returns:
            Dict with news articles and sentiment analysis
        """
        articles = self.get_stock_news(symbol, days=days)
        sentiment = self.analyze_sentiment(articles)
        
        return {
            'symbol': symbol,
            'articles': articles,
            'sentiment': sentiment,
            'timestamp': datetime.now().isoformat()
        }


# Example usage
if __name__ == '__main__':
    print("\n📰 Testing News Sentiment Analyzer\n")
    
    # Test with demo key (limited functionality)
    analyzer = NewsSentimentAnalyzer()
    
    # Test stocks
    test_symbols = ['RELIANCE.NS', 'TCS.NS', 'AAPL']
    
    for symbol in test_symbols:
        print(f"\n{'='*60}")
        print(f"📊 Analyzing: {symbol}")
        print('='*60)
        
        try:
            result = analyzer.get_sentiment_signal(symbol, days=7)
            
            sentiment = result['sentiment']
            print(f"\n{sentiment['emoji']} Sentiment: {sentiment['label']}")
            print(f"Score: {sentiment['score']:.3f} (confidence: {sentiment['confidence']:.3f})")
            print(f"Summary: {sentiment['summary']}")
            
            print(f"\nLatest News:")
            for i, article in enumerate(result['articles'][:3], 1):
                print(f"{i}. {article['title']}")
                print(f"   Source: {article['source']}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "="*60)
    print("\n✅ Using NewsData.io API (included)")
    print("💡 Optional: Get additional API key from https://newsapi.org for more coverage")
