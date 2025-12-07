# 📰 NewsData.io - Quick Reference Card

## 🔑 Your API Key
```
pub_351be3c902b4478180538c1f6c2c33d3
```
**Status:** ✅ Pre-configured in code (no setup needed)

---

## 🚀 Quick Commands

### Test News Integration
```bash
# Quick test
./test_news.sh

# Or run Python directly
python3 test_newsdata.py
```

### Launch Beginner GUI (with news)
```bash
python3 app/beginner_mode_gui.py
```

### Check API Usage
Dashboard: https://newsdata.io/dashboard

---

## 💻 Code Examples

### Basic Usage
```python
from backend.news_sentiment import NewsSentimentAnalyzer

analyzer = NewsSentimentAnalyzer()  # API key already set
result = analyzer.get_sentiment_signal('RELIANCE.NS')

print(result['sentiment']['label'])   # POSITIVE/NEGATIVE/NEUTRAL
print(result['sentiment']['score'])   # -1.0 to +1.0
print(result['sentiment']['emoji'])   # 😊/😐/😟
```

### Get Latest Headlines
```python
result = analyzer.get_sentiment_signal('AAPL', days=3)

for article in result['articles'][:5]:
    print(f"{article['title']}")
    print(f"Source: {article['source']}")
```

### Combine with Trading Signal
```python
# Technical signal
signals = strategy.generate_signals(df)
tech_signal = signals.iloc[-1]['signal']

# News sentiment
news = analyzer.get_sentiment_signal('RELIANCE.NS')
sentiment = news['sentiment']['score']

# Combined decision
if tech_signal == 1 and sentiment > 0.3:
    action = "STRONG BUY"
elif tech_signal == 1 and sentiment < -0.3:
    action = "CAUTION"
```

---

## 📊 Sentiment Guide

| Score | Label | Emoji | Meaning |
|-------|-------|-------|---------|
| > 0.2 | POSITIVE | 😊 | Bullish news |
| -0.2 to 0.2 | NEUTRAL | 😐 | Mixed/No clear direction |
| < -0.2 | NEGATIVE | 😟 | Bearish news |

**Confidence:** How strong the sentiment is (0-1)
- High (>0.5): Clear positive/negative
- Medium (0.3-0.5): Moderate sentiment
- Low (<0.3): Weak or mixed

---

## 🎯 Best Stocks

### Indian Stocks
- RELIANCE.NS (Reliance Industries)
- TCS.NS (Tata Consultancy)
- INFY.NS (Infosys)
- HDFCBANK.NS (HDFC Bank)

### US Stocks
- AAPL (Apple)
- MSFT (Microsoft)
- GOOGL (Google)
- TSLA (Tesla)

---

## 🔄 Fallback System

1. **NewsData.io** (Your API) - Primary ✅
2. **NewsAPI.org** (If you add key) - Backup
3. **Google News RSS** (Free) - Last resort

System automatically tries next source if one fails.

---

## 🛠️ Quick Fixes

### No articles found?
- Try major stocks (AAPL, RELIANCE.NS)
- Check API limits at dashboard
- Wait for Google News fallback

### Need TextBlob?
```bash
pip3 install textblob
python3 -m textblob.download_corpora
```

### Want to change API key?
Edit: `backend/news_sentiment.py` line 32

---

## 📚 Full Documentation

- **Complete Guide:** `NEWSDATA_SETUP.md`
- **Integration Summary:** `NEWSDATA_INTEGRATION_SUMMARY.md`
- **All Features:** `NEW_FEATURES_README.md`

---

## ⚡ Pro Tips

1. **Combine with technicals** - Use news as confirmation
2. **Check recent articles** - Look at titles manually
3. **Monitor dashboard** - Track API usage
4. **Test regularly** - Run `test_newsdata.py` weekly
5. **Try multiple stocks** - News coverage varies

---

**Status:** ✅ Ready to use - No configuration needed!

**Next:** Run `./test_news.sh` to verify it works
