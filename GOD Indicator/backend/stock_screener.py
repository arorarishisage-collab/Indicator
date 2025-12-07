"""Professional Stock Screener supporting Discord alerts per signal."""

import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

import pandas as pd

from backend.news_sentiment import NewsSentimentAnalyzer
from backend.tradingview_webhook import TradingViewWebhook, WebhookConfig

logger = logging.getLogger(__name__)


class StockScreener:
    """
    Professional stock screener that scans markets for trading opportunities
    """
    
    # NSE Top 200 stocks
    NSE_STOCKS = [
        'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 'ITC', 'SBIN',
        'BHARTIARTL', 'KOTAKBANK', 'LT', 'AXISBANK', 'ASIANPAINT', 'BAJFINANCE', 'MARUTI',
        'TITAN', 'NESTLEIND', 'ULTRACEMCO', 'SUNPHARMA', 'WIPRO', 'TECHM', 'ONGC', 'POWERGRID',
        'NTPC', 'TATAMOTORS', 'TATASTEEL', 'ADANIGREEN', 'ADANIPORTS', 'COALINDIA', 'M&M',
        'BAJAJFINSV', 'HCLTECH', 'DRREDDY', 'DIVISLAB', 'JSWSTEEL', 'INDUSINDBK', 'GRASIM',
        'BRITANNIA', 'EICHERMOT', 'SHREECEM', 'CIPLA', 'APOLLOHOSP', 'BPCL', 'UPL', 'HINDALCO',
        'TATACONSUM', 'ADANIENT', 'HEROMOTOCO', 'BAJAJ-AUTO', 'ICICIGI', 'VEDL', 'SBILIFE',
        'DABUR', 'IOC', 'HDFCLIFE', 'PIDILITIND', 'GODREJCP', 'DLF', 'BANDHANBNK', 'GAIL',
        'AMBUJACEM', 'BERGEPAINT', 'MARICO', 'SIEMENS', 'LUPIN', 'HAVELLS', 'COLPAL',
        'DMART', 'INDIGO', 'ADANIPOWER', 'BANKBARODA', 'BOSCHLTD', 'ZOMATO', 'TORNTPHARM',
        'MCDOWELL-N', 'PNB', 'BAJAJHLDNG', 'BIOCON', 'INDHOTEL', 'NAUKRI', 'TATAPOWER',
        'TRENT', 'SAIL', 'MOTHERSON', 'CANBK', 'PAGEIND', 'ACC', 'IRCTC', 'APOLLOTYRE',
        'PGHH', 'CONCOR', 'JINDALSTEL', 'MPHASIS', 'JUBLFOOD', 'NMDC', 'ZEEL', 'PETRONET',
        'GODREJPROP', 'PERSISTENT', 'VOLTAS', 'LICI', 'PFC', 'RECLTD', 'LTIM', 'OFSS',
        'IPCALAB', 'SBICARD', 'MRF', 'HDFCAMC', 'ABCAPITAL', 'L&TFH', 'INDUSTOWER',
        'SUPREMEIND', 'CROMPTON', 'DIXON', 'POLYCAB', 'TATACOMM', 'ALKEM', 'INDIAMART',
        'CHOLAFIN', 'MUTHOOTFIN', 'AUBANK', 'LICHSGFIN', 'MFSL', 'MANAPPURAM', 'CENTRALBK',
        'UNIONBANK', 'FEDERALBNK', 'IDFCFIRSTB', 'PEL', 'KPITTECH', 'COFORGE', 'LTTS',
        'ANGELONE', 'PAYTM', 'POLICYBZR', 'DELHIVERY', 'ASTRAL', 'APLAPOLLO', 'CUMMINSIND',
        'ESCORTS', 'EXIDEIND', 'TVSMOTOR', 'BALKRISIND', 'MGL', 'IGL', 'PIIND', 'SYNGENE',
        'LAURUSLABS', 'GRANULES', 'NATCOPHARM', 'SUNPHARMA', 'AUROPHARMA', 'TORNTPOWER',
        'CESC', 'ADANITRANS', 'JSW', 'JSWENERGY', 'NHPC', 'SJVN', 'IRFC', 'RVNL',
        'GMRINFRA', 'IDEA', 'YESBANK', 'SUZLON', 'RPOWER', 'UCOBANK', 'RBLBANK'
    ]
    
    # US Top 100 stocks
    US_STOCKS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'LLY', 'AVGO',
        'V', 'JPM', 'WMT', 'XOM', 'UNH', 'MA', 'PG', 'JNJ', 'HD', 'COST', 'ABBV', 'ORCL',
        'MRK', 'CVX', 'KO', 'BAC', 'PEP', 'AMD', 'CRM', 'NFLX', 'ADBE', 'TMO', 'MCD',
        'CSCO', 'ACN', 'LIN', 'ABT', 'DIS', 'WFC', 'DHR', 'INTC', 'VZ', 'TXN', 'CMCSA',
        'QCOM', 'INTU', 'PM', 'UBER', 'AMGN', 'COP', 'NKE', 'IBM', 'RTX', 'UNP', 'HON',
        'NEE', 'LOW', 'SPGI', 'CAT', 'BA', 'GE', 'UPS', 'DE', 'AMAT', 'ELV', 'PLD', 'BLK',
        'MDT', 'SYK', 'GILD', 'SBUX', 'BKNG', 'ADP', 'ADI', 'MMC', 'MDLZ', 'CI', 'VRTX',
        'ISRG', 'LRCX', 'CB', 'TJX', 'PGR', 'SO', 'REGN', 'NOC', 'BSX', 'SCHW', 'DUK',
        'MO', 'FI', 'ETN', 'PANW', 'CME', 'EOG', 'ZTS', 'PYPL', 'SLB', 'ITW', 'BMY'
    ]
    
    # Forex and Commodities (via ETFs)
    FOREX_COMMODITIES = {
        'Gold': 'GLD',          # SPDR Gold Shares
        'Silver': 'SLV',        # iShares Silver Trust
        'Oil': 'USO',           # US Oil Fund
        'Gold Miners': 'GDX',   # VanEck Gold Miners ETF
        'EUR/USD': 'FXE',       # Euro Currency Trust
        'GBP/USD': 'FXB',       # British Pound ETF
        'JPY/USD': 'FXY',       # Japanese Yen ETF
        'Crude Oil': 'USO',     # US Oil
        'Natural Gas': 'UNG',   # US Natural Gas
        'Copper': 'CPER',       # Copper ETF
    }
    
    def __init__(
        self,
        data_fetcher,
        webhook_config: Optional[WebhookConfig] = None,
        webhook_channels: Optional[Sequence[str]] = None,
        news_analyzer: Optional[NewsSentimentAnalyzer] = None,
    ):
        """Initialize screener with optional Discord alert and enrichment support."""
        self.data_fetcher = data_fetcher
        self.cache = {}
        self.webhook_config = webhook_config
        self.webhook_channels = list(webhook_channels or [])
        self._webhook_cache: Dict[str, Optional[TradingViewWebhook]] = {}

        if news_analyzer:
            self.news_analyzer = news_analyzer
        else:
            news_key = os.getenv('NEWSDATA_API_KEY')
            self.news_analyzer = NewsSentimentAnalyzer(newsdata_key=news_key) if news_key else NewsSentimentAnalyzer()
        self._fundamental_cache: Dict[str, Dict] = {}
        self._news_cache: Dict[str, Dict] = {}
    
    def get_all_symbols(self, market: str = 'ALL') -> List[Dict]:
        """
        Get all available symbols with metadata
        
        Args:
            market: 'NSE', 'US', 'FOREX', or 'ALL'
        
        Returns:
            List of dicts with symbol info
        """
        symbols = []
        
        if market in ['NSE', 'ALL']:
            for symbol in self.NSE_STOCKS:
                symbols.append({
                    'symbol': symbol,
                    'name': symbol,
                    'exchange': 'NSE',
                    'type': 'Stock'
                })
        
        if market in ['US', 'ALL']:
            for symbol in self.US_STOCKS:
                symbols.append({
                    'symbol': symbol,
                    'name': symbol,
                    'exchange': 'US',
                    'type': 'Stock'
                })
        
        if market in ['FOREX', 'ALL']:
            for name, symbol in self.FOREX_COMMODITIES.items():
                symbols.append({
                    'symbol': symbol,
                    'name': name,
                    'exchange': 'US',
                    'type': 'Commodity/Forex'
                })
        
        return symbols
    
    def screen_by_strategy(
        self,
        strategy,
        market: str = 'NSE',
        min_signal_strength: float = 6.0,
        max_stocks: int = 50,
        days: int = 180
    ) -> List[Dict]:
        """
        Screen stocks by strategy criteria
        
        Args:
            strategy: Trading strategy instance
            market: 'NSE', 'US', 'FOREX', or 'ALL'
            min_signal_strength: Minimum signal strength (0-10)
            max_stocks: Maximum results to return
            days: Historical data days
        
        Returns:
            List of stocks matching criteria with signals
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"SCREENING: {market} market, min_strength={min_signal_strength}")
        logger.info(f"Strategy: {strategy.__class__.__name__}")
        logger.info(f"{'='*60}\n")
        
        # Get symbol universe
        all_symbols = self.get_all_symbols(market)
        logger.info(f"Symbol universe: {len(all_symbols)} stocks")
        
        # FIXED: Screen ALL symbols, not just 2x max_stocks
        symbols_to_scan = all_symbols[:min(len(all_symbols), 100)]  # Cap at 100 for speed
        logger.info(f"Scanning: {len(symbols_to_scan)} stocks\n")
        
        # Fetch and analyze in parallel
        results = []
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        completed_count = 0
        error_count = 0
        
        with ThreadPoolExecutor(max_workers=5) as executor:  # Reduced workers for stability
            futures = {}
            
            for symbol_info in symbols_to_scan:
                symbol = symbol_info['symbol']
                exchange = symbol_info['exchange']
                
                future = executor.submit(
                    self._analyze_symbol,
                    symbol,
                    exchange,
                    strategy,
                    from_date,
                    to_date,
                    min_signal_strength
                )
                futures[future] = symbol_info
            
            # Collect results with progress tracking
            for future in as_completed(futures):
                symbol_info = futures[future]
                completed_count += 1
                
                try:
                    result = future.result(timeout=15)  # Increased timeout
                    if result:
                        result['name'] = symbol_info['name']
                        result['type'] = symbol_info['type']
                        results.append(result)
                        logger.info(f"Progress: {completed_count}/{len(symbols_to_scan)} | Found: {len(results)}")
                
                except Exception as e:
                    error_count += 1
                    logger.warning(f"❌ {symbol_info['symbol']}: {str(e)[:50]}")
        
        # Sort by signal strength
        results.sort(key=lambda x: x.get('signal_strength', 0), reverse=True)
        selected = results[:max_stocks]

        # Enrich final signals with fundamentals/news for alerts
        self._enrich_signals(selected, strategy)

        logger.info(f"\n{'='*60}")
        logger.info("SCAN COMPLETE")
        logger.info(f"Scanned: {completed_count} stocks")
        logger.info(f"Matches: {len(results)} stocks")
        logger.info(f"Errors: {error_count}")
        logger.info(f"{'='*60}\n")

        # Emit Discord alerts for the shortlisted signals
        self._emit_alerts(selected, strategy)

        return selected
    
    def _analyze_symbol(
        self,
        symbol: str,
        exchange: str,
        strategy,
        from_date,
        to_date,
        min_signal_strength: float
    ) -> Dict:
        """Analyze single symbol (internal helper)"""
        try:
            # Fetch data
            df = self.data_fetcher.fetch_historical_data(
                symbol, 'D', from_date, to_date, exchange
            )
            
            if df is None or len(df) < 50:
                logger.debug(f"{symbol}: Insufficient data ({len(df) if df is not None else 0} bars)")
                return None
            
            # Generate signals - FIXED: Better error handling
            try:
                signals = strategy.generate_signals(df)
                if signals is None or signals.empty:
                    logger.debug(f"{symbol}: Strategy returned no signals")
                    return None
            except Exception as e:
                logger.warning(f"{symbol}: Strategy failed - {e}")
                return None
            
            # FIXED: Look at ALL signals, not just last 5
            buy_signals = signals[signals['Signal'] == 1]
            
            if buy_signals.empty:
                logger.debug(f"{symbol}: No buy signals found")
                return None
            
            # Get latest signal
            latest = buy_signals.iloc[-1]
            
            # FIXED: Calculate signal strength properly
            # If strategy doesn't provide Signal_Strength, calculate it
            if 'Signal_Strength' not in latest.index:
                # Use proximity to signal as strength indicator
                days_since_signal = len(signals) - signals.index.get_loc(latest.name) - 1
                signal_strength = max(5.0, 10.0 - (days_since_signal * 0.2))
            else:
                signal_strength = float(latest['Signal_Strength'])
            
            if signal_strength < min_signal_strength:
                logger.debug(f"{symbol}: Signal strength {signal_strength:.1f} < {min_signal_strength}")
                return None
            
            # Get current price
            current_price = df['Close'].iloc[-1]
            
            logger.info(f"✅ {symbol}: MATCH! Strength={signal_strength:.1f}, Price={current_price:.2f}")
            
            stop_loss = None
            take_profit = None
            if 'Stop_Loss' in latest.index and pd.notna(latest['Stop_Loss']):
                stop_loss = float(latest['Stop_Loss'])
            if 'Take_Profit' in latest.index and pd.notna(latest['Take_Profit']):
                take_profit = float(latest['Take_Profit'])

            return {
                'symbol': symbol,
                'exchange': exchange,
                'current_price': current_price,
                'signal_strength': signal_strength,
                'signal_date': latest.name,
                'volume': df['Volume'].iloc[-1],
                'direction': 'BUY',
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'timeframe': '1D',
                'data': df
            }
        
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {e}")
            return None

    # ------------------------------------------------------------------
    # Discord alert helpers
    # ------------------------------------------------------------------
    def _enrich_signals(self, signals: List[Dict], strategy) -> None:
        """Augment shortlisted signals with fundamentals and sentiment."""
        if not signals:
            return

        for signal in signals:
            symbol = signal['symbol']
            exchange = signal['exchange']

            fundamentals = self._fetch_fundamentals(symbol, exchange)
            if fundamentals:
                signal['fundamentals'] = fundamentals

            sentiment_bundle = self._fetch_sentiment(symbol)
            if sentiment_bundle:
                signal.update(sentiment_bundle)

    def _fetch_fundamentals(self, symbol: str, exchange: str) -> Dict:
        cache_key = f"{symbol}:{exchange}"
        if cache_key in self._fundamental_cache:
            return self._fundamental_cache[cache_key]

        finnhub = getattr(self.data_fetcher, 'finnhub', None)
        if not finnhub:
            return {}

        try:
            profile = finnhub.get_company_profile(symbol, exchange) or {}
            metrics = finnhub.get_key_metrics(symbol, exchange) or {}
            fundamentals = {**profile, 'metrics': metrics}
            self._fundamental_cache[cache_key] = fundamentals
            return fundamentals
        except Exception as exc:
            logger.debug(f"Fundamental enrichment failed for {symbol}: {exc}")
            return {}

    def _fetch_sentiment(self, symbol: str) -> Dict:
        if not self.news_analyzer:
            return {}

        if symbol in self._news_cache:
            return self._news_cache[symbol]

        try:
            articles = self.news_analyzer.get_stock_news(symbol, days=3, max_articles=6)
            sentiment = self.news_analyzer.analyze_sentiment(articles) if articles else {}
            news_headlines = [article.get('title', '') for article in articles[:3] if article.get('title')]
            bundle = {
                'sentiment': sentiment,
                'news_headlines': news_headlines,
                'news_articles': articles,
            }
            self._news_cache[symbol] = bundle
            return bundle
        except Exception as exc:
            logger.debug(f"News enrichment failed for {symbol}: {exc}")
            return {}

    def _emit_alerts(self, signals: List[Dict], strategy) -> None:
        """Send Discord alerts for shortlisted signals."""
        if not self.webhook_config or not self.webhook_channels or not signals:
            return

        strategy_name = getattr(strategy, 'name', strategy.__class__.__name__)

        for signal in signals:
            for channel in self.webhook_channels:
                webhook = self._get_webhook(channel)
                if not webhook:
                    logger.warning(f"Webhook '{channel}' unavailable; skipping alert for {signal['symbol']}")
                    continue

                try:
                    webhook.send_signal(
                        symbol=signal['symbol'],
                        direction=signal.get('direction', 'BUY'),
                        strategy=strategy_name,
                        entry_price=signal['current_price'],
                        signal_strength=signal.get('signal_strength', 0),
                        stop_loss=signal.get('stop_loss'),
                        take_profit=signal.get('take_profit'),
                        timeframe=signal.get('timeframe', '1D'),
                        extra_fields=self._format_fundamental_fields(signal),
                        news_headlines=signal.get('news_headlines')
                    )
                    logger.info(f"📣 Discord alert sent for {signal['symbol']} via {channel}")
                except Exception as alert_error:
                    logger.error(f"❌ Failed to send Discord alert for {signal['symbol']} ({channel}): {alert_error}")

    def _get_webhook(self, channel: str) -> Optional[TradingViewWebhook]:
        if channel not in self._webhook_cache:
            self._webhook_cache[channel] = (
                self.webhook_config.get_webhook(channel) if self.webhook_config else None
            )
        return self._webhook_cache[channel]

    def _format_fundamental_fields(self, signal: Dict) -> Optional[Dict[str, str]]:
        fundamentals = signal.get('fundamentals') or {}
        metrics = fundamentals.get('metrics') or {}
        sentiment = signal.get('sentiment') or {}

        fields: Dict[str, str] = {}

        market_cap = fundamentals.get('market_cap')
        try:
            if market_cap:
                cap_val = float(market_cap)
                value = cap_val / 1e3
                fields['Market Cap'] = f"${value:.1f}B" if value >= 1 else f"${cap_val:.0f}M"
        except (TypeError, ValueError):
            pass

        pe_ratio = metrics.get('pe_ratio')
        if isinstance(pe_ratio, (int, float)) and pe_ratio:
            fields['P/E'] = f"{pe_ratio:.1f}"

        roe = metrics.get('return_on_equity')
        if isinstance(roe, (int, float)) and roe:
            fields['ROE'] = f"{roe*100:.1f}%"

        revenue_growth = metrics.get('revenue_growth')
        if isinstance(revenue_growth, (int, float)) and revenue_growth:
            fields['Revenue Growth'] = f"{revenue_growth*100:.1f}%"
        if sentiment.get('label'):
            score = sentiment.get('score', 0)
            fields['News Sentiment'] = f"{sentiment['label']} ({score:+.2f})"

        return fields or None
    
    def quick_scan_top_movers(self, market: str = 'NSE', top_n: int = 20) -> List[Dict]:
        """
        Quick scan for top movers (volume + price change)
        
        Args:
            market: Market to scan
            top_n: Number of top stocks
        
        Returns:
            List of top moving stocks
        """
        symbols = self.get_all_symbols(market)[:100]  # Top 100
        results = []
        
        to_date = datetime.now()
        from_date = to_date - timedelta(days=5)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {}
            
            for symbol_info in symbols:
                future = executor.submit(
                    self._get_mover_data,
                    symbol_info['symbol'],
                    symbol_info['exchange'],
                    from_date,
                    to_date
                )
                futures[future] = symbol_info
            
            for future in as_completed(futures):
                symbol_info = futures[future]
                try:
                    result = future.result(timeout=5)
                    if result:
                        result['name'] = symbol_info['name']
                        results.append(result)
                except:
                    pass
        
        # Sort by momentum score
        results.sort(key=lambda x: x.get('momentum_score', 0), reverse=True)
        return results[:top_n]
    
    def _get_mover_data(self, symbol: str, exchange: str, from_date, to_date) -> Dict:
        """Get price movement data"""
        try:
            df = self.data_fetcher.fetch_historical_data(
                symbol, 'D', from_date, to_date, exchange
            )
            
            if df is None or len(df) < 2:
                return None
            
            # Calculate metrics
            price_change_pct = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100
            avg_volume = df['Volume'].mean()
            volume_spike = df['Volume'].iloc[-1] / avg_volume if avg_volume > 0 else 1
            
            # Momentum score
            momentum_score = abs(price_change_pct) * volume_spike
            
            return {
                'symbol': symbol,
                'exchange': exchange,
                'current_price': df['Close'].iloc[-1],
                'price_change_pct': price_change_pct,
                'volume_spike': volume_spike,
                'momentum_score': momentum_score
            }
        except:
            return None
