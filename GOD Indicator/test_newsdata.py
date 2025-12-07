#!/usr/bin/env python3
"""
Quick test for NewsData.io integration
Tests news fetching and sentiment analysis with your API key
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.news_sentiment import NewsSentimentAnalyzer


def test_news_fetch():
    """Test news fetching from NewsData.io"""
    print("\n" + "="*70)
    print("📰 TESTING NEWSDATA.IO INTEGRATION")
    print("="*70)
    
    # Initialize with your API key (already set as default)
    analyzer = NewsSentimentAnalyzer()
    
    # Test with Indian stocks (best for NewsData.io)
    test_symbols = [
        ('RELIANCE.NS', 'Reliance Industries'),
        ('TCS.NS', 'Tata Consultancy'),
        ('INFY.NS', 'Infosys')
    ]
    
    for symbol, name in test_symbols:
        print(f"\n{'─'*70}")
        print(f"📊 {name} ({symbol})")
        print('─'*70)
        
        try:
            # Get news and sentiment
            result = analyzer.get_sentiment_signal(symbol, days=7)
            
            # Display sentiment
            sentiment = result['sentiment']
            print(f"\n{sentiment['emoji']} Sentiment: {sentiment['label']}")
            print(f"   Score: {sentiment['score']:.3f}")
            print(f"   Confidence: {sentiment['confidence']:.3f}")
            print(f"   Summary: {sentiment['summary']}")
            
            # Display articles
            articles = result['articles']
            print(f"\n📰 Latest News ({len(articles)} articles):")
            
            for i, article in enumerate(articles[:5], 1):
                print(f"\n   {i}. {article['title']}")
                print(f"      Source: {article['source']}")
                print(f"      Published: {article['published_at']}")
                if article.get('description'):
                    desc = article['description'][:100]
                    print(f"      {desc}...")
            
            if not articles:
                print("   ⚠️  No articles found (try US stocks like AAPL)")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("✅ Test Complete!")
    print("="*70)
    print("\n💡 Tips:")
    print("   - NewsData.io works best with major stocks")
    print("   - Try US stocks (AAPL, MSFT, GOOGL) if Indian stocks have no news")
    print("   - API updates every 15 minutes")
    print("   - Free tier: Check your usage at https://newsdata.io/dashboard")
    print()


if __name__ == '__main__':
    test_news_fetch()
