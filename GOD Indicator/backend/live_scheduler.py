"""
24/7 Live Trading Scheduler/Daemon
Continuously fetches live market data, generates signals, and manages dummy trades
Runs independently in background on Mac
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import schedule
import time
import threading
import logging
import json
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None
from typing import Optional, Dict, Any, Iterable, Tuple

import pandas as pd

from backend.data_manager import DataManager
from backend.strategy_profile import StrategyProfile
from backend.ema_strategy import EMA30Strategy
from backend.ict_strategy import ICTStrategy
from backend.vcp_strategy import VCPStrategy
from backend.market_regime_detector import MarketRegimeDetector, MarketRegime
from backend.advanced_risk_manager import AdvancedRiskManager
from backend.correlation_manager import CorrelationManager
from backend.multi_timeframe_analyzer import MultiTimeframeAnalyzer

# RL System imports (optional - requires PyTorch)
try:
    from backend.advanced_rl_trading_system import TradingEnvironment, PPOAgent
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False
    TradingEnvironment = None
    PPOAgent = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

STRATEGY_MAP = {
    'EMA30Strategy': EMA30Strategy,
    'ICTStrategy': ICTStrategy,
    'VCPStrategy': VCPStrategy,
}


class LiveTradingScheduler:
    """
    24/7 scheduler for continuous trading signal generation and dummy trading
    """
    
    def __init__(self, symbols=['XAUUSD', 'BTC'], 
                 check_interval_minutes=60,
                 data_fetcher_class=None,
                 strategy_classes=None,
                 webhook_config=None,
                 dummy_trader=None,
                 strategy_profiles: Optional[Iterable[Any]] = None,
                 now_provider=None):
        """
        Initialize live trading scheduler
        
        Args:
            symbols (list): Symbols to monitor
            check_interval_minutes (int): Check interval in minutes
            data_fetcher_class: Data fetcher class (YFinanceDataFetcher)
            strategy_classes (dict): {strategy_name: strategy_class}
            webhook_config: WebhookConfig instance
            dummy_trader: LiveDummyTrader instance
        """
        self.symbols = symbols
        self.check_interval_minutes = check_interval_minutes
        self.data_fetcher = data_fetcher_class() if data_fetcher_class else None
        self.data_manager = DataManager()
        self.strategy_classes = strategy_classes or {}
        self.webhook_config = webhook_config
        self.dummy_trader = dummy_trader
        self.strategy_profiles: Dict[str, Dict[str, Any]] = {}
        self.profile_state: Dict[str, Dict[str, Any]] = {}
        self._now_provider = now_provider
        
        # Initialize advanced components
        self.regime_detector = MarketRegimeDetector()
        self.risk_manager = AdvancedRiskManager(
            base_risk_pct=0.01,
            max_risk_pct=0.03,
            kelly_fraction=0.25
        )
        self.correlation_manager = CorrelationManager(
            data_fetcher=data_fetcher_class() if data_fetcher_class else None,
            high_correlation_threshold=0.7,
            max_correlated_positions=2
        ) if data_fetcher_class else None
        
        # Multi-timeframe analyzer (optional - can be enabled per profile)
        self.mtf_analyzer = None  # Will be created per strategy profile
        self.use_mtf_confirmation = False  # Toggle via config
        
        # RL Agent (optional - requires PyTorch and trained model)
        self.rl_agent = None
        self.use_rl_decisions = False  # Toggle via config
        self.rl_confidence_threshold = 0.6  # Minimum confidence for RL decisions
        if RL_AVAILABLE:
            logger.info("✅ RL System available (PyTorch detected)")
        else:
            logger.info("⚠️ RL System unavailable (install PyTorch: pip install torch)")
        
        if strategy_profiles:
            self.load_profiles(strategy_profiles)
        
        self.is_running = False
        self.scheduler_thread = None
        self.last_run_time = {}
        self.signal_history = {}
        self.config_file = 'config/scheduler_config.json'
        self.rl_agents: Dict[str, Optional['PPOAgent']] = {}
        self.rl_training_jobs: Dict[str, Dict[str, Any]] = {
            'EMA30Strategy': {
                'enabled': True,
                'time': '03:30',
                'episodes': 500,
                'symbol': 'GC=F',
                'symbols': ['GC=F', 'GLD', 'SLV', 'SI=F', 'HG=F'],
                'min_feedback_signal': 6.0,
                'auto_reload': True
            },
            'ICTStrategy': {
                'enabled': True,
                'time': '03:45',
                'episodes': 500,
                'symbol': 'GC=F',
                'symbols': ['GC=F', 'CL=F', 'ES=F', 'NQ=F'],
                'min_feedback_signal': 7.0,
                'auto_reload': True
            },
            'VCPStrategy': {
                'enabled': True,
                'time': '04:00',
                'episodes': 400,
                'symbol': 'GC=F',
                'symbols': ['GC=F', 'GLD', 'RELIANCE.NS', 'HDFCBANK.NS', 'TCS.NS', 'AAPL', 'MSFT'],
                'min_feedback_signal': 7.5,
                'auto_reload': True
            }
        }
        self.last_rl_training_summary: Dict[str, Any] = {}
        
        # Load configuration
        self.load_config()

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    def load_profiles(self, profile_specs: Iterable[Any]):
        """Load strategy profiles from names/paths/instances."""
        loaded_any = False
        for spec in profile_specs:
            try:
                if isinstance(spec, StrategyProfile):
                    profile = spec
                elif isinstance(spec, dict):
                    if 'path' in spec:
                        profile = StrategyProfile.load(spec['path'], base_dir='')
                    elif 'name' in spec:
                        profile = StrategyProfile.load(spec['name'])
                    else:
                        logger.error(f"Profile dict missing 'name' or 'path': {spec}")
                        continue
                else:
                    profile = StrategyProfile.load(spec)
            except Exception as exc:
                logger.error(f"Failed to load profile {spec}: {exc}")
                continue

            live_settings = profile.live or {}
            symbol = (profile.data_source.get('symbol') or live_settings.get('symbol'))
            if not symbol:
                logger.error(f"Profile {profile.name} missing symbol (data_source.symbol or live.symbol)")
                continue

            strategy_class = self._resolve_strategy_class(profile.strategy.get('class'))
            if not strategy_class:
                continue

            poll_seconds = int(live_settings.get('poll_interval_seconds') or self.check_interval_minutes * 60)
            min_poll = int(live_settings.get('min_poll_seconds', poll_seconds))
            max_poll = int(live_settings.get('max_poll_seconds', poll_seconds * 8))

            self.strategy_profiles[profile.name] = {
                'profile': profile,
                'symbol': symbol,
                'strategy_class': strategy_class,
                'strategy_params': profile.strategy.get('params', {}).copy(),
                'poll_interval_seconds': poll_seconds,
                'schedule_interval_seconds': max(5, min_poll),
            }
            self.profile_state[profile.name] = {
                'base_interval': poll_seconds,
                'current_interval': poll_seconds,
                'min_interval': max(5, min_poll),
                'max_interval': max_poll,
                'backoff': 1.0,
                'next_run': None,
                'last_signal_time': None,
                'last_signal_direction': None,
            }
            loaded_any = True

        if loaded_any:
            self.symbols = [cfg['symbol'] for cfg in self.strategy_profiles.values()]

    def _resolve_strategy_class(self, class_name: Optional[str]):
        if not class_name:
            logger.error("Strategy class not specified in profile")
            return None
        strategy_class = STRATEGY_MAP.get(class_name)
        if not strategy_class:
            logger.error(f"Strategy '{class_name}' not registered. Available: {', '.join(STRATEGY_MAP)}")
        return strategy_class

    def _should_run_profile(self, profile_name: str) -> bool:
        state = self.profile_state.get(profile_name)
        if not state:
            return True
        next_run = state.get('next_run')
        if not next_run:
            return True
        if datetime.now() >= next_run:
            return True
        return False

    def _mark_profile_success(self, profile_name: str):
        state = self.profile_state.get(profile_name)
        if not state:
            return
        state['backoff'] = 1.0
        state['current_interval'] = state['base_interval']
        state['next_run'] = datetime.now() + timedelta(seconds=state['current_interval'])

    def _mark_profile_failure(self, profile_name: str):
        state = self.profile_state.get(profile_name)
        if not state:
            return
        state['backoff'] = min(state.get('backoff', 1.0) * 2, 8.0)
        interval = min(state['base_interval'] * state['backoff'], state['max_interval'])
        state['current_interval'] = interval
        state['next_run'] = datetime.now() + timedelta(seconds=interval)

    def set_now_provider(self, provider):
        """Inject custom now-provider (useful for testing)."""
        self._now_provider = provider

    def _profile_now(self, profile: StrategyProfile) -> datetime:
        if self._now_provider:
            try:
                return self._now_provider(profile)
            except Exception as exc:
                logger.warning(f"Custom now_provider failed for {profile.name}: {exc}")
        tz_name = (
            (profile.data_source or {}).get('timezone')
            or (profile.live or {}).get('timezone')
            or 'UTC'
        )
        if ZoneInfo:
            try:
                return datetime.now(ZoneInfo(tz_name))
            except Exception:
                pass
        return datetime.utcnow()

    @staticmethod
    def _time_in_window(current_time, start_time, end_time) -> bool:
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        return current_time >= start_time or current_time <= end_time

    def _is_within_live_session(self, profile: StrategyProfile) -> bool:
        sessions = (
            (profile.live or {}).get('session_hours')
            or (profile.filters or {}).get('session_hours')
            or []
        )
        if not sessions:
            return True

        now_local = self._profile_now(profile)
        now_time = now_local.time()

        for window in sessions:
            try:
                start_str, end_str = [part.strip() for part in window.split('-')]
                start_time = datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.strptime(end_str, "%H:%M").time()
            except ValueError:
                logger.warning(f"Invalid session window '{window}' for profile {profile.name}")
                continue

            if self._time_in_window(now_time, start_time, end_time):
                return True

        return False

    def _is_in_cooldown(self, profile_name: str, cooldown_minutes: float) -> Tuple[bool, float]:
        if not cooldown_minutes:
            return (False, 0.0)
        state = self.profile_state.get(profile_name)
        if not state:
            return (False, 0.0)
        last_signal = state.get('last_signal_time')
        if not last_signal:
            return (False, 0.0)
        elapsed = datetime.utcnow() - last_signal
        remaining = cooldown_minutes - (elapsed.total_seconds() / 60.0)
        return (remaining > 0, max(0.0, remaining))

    def _get_open_trades_for_profile(self, profile_name: str, symbol: str):
        if not self.dummy_trader:
            return []
        if hasattr(self.dummy_trader, 'get_open_trades'):
            return self.dummy_trader.get_open_trades(symbol=symbol, profile=profile_name)
        trades = []
        for trade_data in getattr(self.dummy_trader, 'open_trades', {}).values():
            if trade_data.get('symbol') != symbol:
                continue
            trades.append(trade_data)
        return trades

    def _passes_quality_filters(self, profile: StrategyProfile, signal_data: dict) -> Tuple[bool, Optional[str]]:
        """Apply additional quality gates to improve expected win rate."""
        min_strength = (profile.live or {}).get('confidence_threshold')
        if not min_strength:
            min_strength = (profile.filters or {}).get('min_signal_strength')
        if min_strength and signal_data.get('signal_strength', 0) < float(min_strength):
            return False, (
                f"Signal strength {signal_data.get('signal_strength', 0):.1f} below "
                f"minimum {float(min_strength):.1f}"
            )

        regime = signal_data.get('regime')
        if regime in {MarketRegime.CHOPPY, MarketRegime.UNKNOWN, MarketRegime.RANGING}:
            return False, f"Market regime {regime} not tradable"

        regime_metrics = signal_data.get('regime_metrics') or {}
        volatility_score = regime_metrics.get('volatility_score')
        if isinstance(volatility_score, (int, float)) and volatility_score > 0.8:
            return False, f"Volatility score {volatility_score:.2f} exceeds safe threshold"

        return True, None

    def _passes_risk_checks(self, profile_name: str, profile: StrategyProfile, signal_data: dict):
        """Enhanced risk checks including correlation and advanced position sizing"""
        live_settings = profile.live or {}
        max_concurrent = live_settings.get('max_concurrent_trades')
        max_exposure = live_settings.get('max_exposure_percent')

        if not self.dummy_trader or (max_concurrent is None and max_exposure is None):
            return True, None, {'open_trades': 0, 'exposure_percent': 0.0}

        open_trades = self._get_open_trades_for_profile(profile_name, signal_data['symbol'])
        open_count = len(open_trades)

        # ============ CORRELATION CHECK ============
        if self.correlation_manager:
            try:
                # Get all open positions
                all_open_positions = []
                for trade in open_trades:
                    all_open_positions.append({
                        'symbol': trade.get('symbol', signal_data['symbol']),
                        'direction': trade.get('direction', 0),
                        'risk_pct': trade.get('risk_percent', 0)
                    })
                
                # Check correlation limits
                new_direction = 1 if signal_data['direction'] == 'BUY' else -1
                corr_allowed, corr_reason = self.correlation_manager.check_correlation_limit(
                    new_symbol=signal_data['symbol'],
                    new_direction=new_direction,
                    new_risk_pct=signal_data.get('risk_percent', 0),
                    open_positions=all_open_positions
                )
                
                if not corr_allowed:
                    logger.warning(f"   🚫 Correlation check failed: {corr_reason}")
                    return False, f"Correlation limit: {corr_reason}", {
                        'open_trades': open_count,
                        'correlation_check': 'failed'
                    }
                else:
                    logger.info(f"   ✓ Correlation check passed: {corr_reason}")
            except Exception as e:
                logger.warning(f"   ⚠️ Correlation check error: {e}")
        
        # ============ CONCURRENT TRADES CHECK ============
        if max_concurrent is not None and open_count >= max_concurrent:
            return False, f"max concurrent trades reached ({open_count}/{max_concurrent})", {
                'open_trades': open_count
            }

        # ============ EXPOSURE CHECK ============
        exposure = None
        if max_exposure is not None:
            base_exposure = 0.0
            if hasattr(self.dummy_trader, 'get_open_exposure_percent'):
                base_exposure = self.dummy_trader.get_open_exposure_percent(
                    symbol=signal_data['symbol'],
                    profile=profile_name
                )
            else:
                base_exposure = open_count * getattr(self.dummy_trader, 'risk_percent', 0)

            trade_risk = signal_data.get('risk_percent') or getattr(self.dummy_trader, 'risk_percent', 0)
            exposure = base_exposure
            prospective = base_exposure + trade_risk
            if prospective > max_exposure:
                return False, (
                    f"exposure {prospective:.2f}% (incl new {trade_risk:.2f}%) exceeds cap {max_exposure}%"
                ), {
                    'open_trades': open_count,
                    'exposure_percent': base_exposure,
                    'prospective_exposure': prospective
                }

        return True, None, {
            'open_trades': open_count,
            'exposure_percent': exposure
        }

    def _record_signal_execution(self, profile_name: str, signal_data: dict):
        state = self.profile_state.get(profile_name)
        if not state:
            return
        state['last_signal_time'] = datetime.utcnow()
        state['last_signal_direction'] = signal_data.get('direction')
        state['last_signal_strength'] = signal_data.get('signal_strength')
    
    def start(self):
        """Start the 24/7 scheduler"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        self.is_running = True
        
        scheduled_jobs = 0

        if self.strategy_profiles:
            for profile_name, cfg in self.strategy_profiles.items():
                interval_seconds = cfg.get('schedule_interval_seconds', self.check_interval_minutes * 60)
                schedule.every(interval_seconds).seconds.do(
                    self._run_profile_job,
                    profile_name=profile_name
                )
                logger.info(
                    f"   • Profile {profile_name} ({cfg['symbol']}) every {interval_seconds}s"
                )
                scheduled_jobs += 1
        elif self.symbols and self.strategy_classes:
            for symbol in self.symbols:
                schedule.every(self.check_interval_minutes).minutes.do(
                    self.check_and_generate_signals,
                    symbol=symbol
                )
                scheduled_jobs += 1
        else:
            logger.error("No strategies configured for scheduler")
            return
        
        # Schedule optimization job (daily at 2 AM)
        schedule.every().day.at("02:00").do(self.run_parameter_optimization)
        
        # Schedule performance report (daily at 9 AM)
        schedule.every().day.at("09:00").do(self.generate_performance_report)

        for strategy_name, job_cfg in self.rl_training_jobs.items():
            if not job_cfg.get('enabled', True):
                continue
            job_time = job_cfg.get('time', '03:30')
            try:
                schedule.every().day.at(job_time).do(
                    self.run_rl_training_job,
                    strategy_name=strategy_name
                )
                logger.info(
                    "   • RL retraining for %s daily at %s (%s episodes)",
                    strategy_name,
                    job_time,
                    job_cfg.get('episodes', 500)
                )
            except Exception as rl_schedule_error:
                logger.error(
                    f"Failed to schedule RL retraining for {strategy_name}: {rl_schedule_error}"
                )
        
        # Start scheduler in background thread
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name='TradingScheduler'
        )
        self.scheduler_thread.start()
        
        logger.info("🚀 Live Trading Scheduler started!")
        if self.strategy_profiles:
            logger.info(f"   Active profiles: {', '.join(self.strategy_profiles.keys())}")
        else:
            logger.info(f"   Monitoring: {', '.join(self.symbols)}")
            logger.info(f"   Check interval: {self.check_interval_minutes} minutes")
    
    def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        schedule.clear()
        logger.info("⏹️  Live Trading Scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def check_and_generate_signals(self, symbol: str):
        """
        Check symbol and generate trading signals
        
        Args:
            symbol (str): Trading symbol to check
        """
        try:
            logger.info(f"\n{'='*70}")
            logger.info(f"📊 Checking signals for {symbol} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info('='*70)
            
            # Fetch latest hourly candle
            if not self.data_fetcher:
                logger.warning("Data fetcher not initialized")
                return
            
            try:
                df = self.data_fetcher.fetch_historical_data(
                    symbol,
                    period='1y',
                    interval='1h'
                )
            except Exception as e:
                logger.error(f"Error fetching data: {e}")
                return
            
            # Generate signals from all configured strategies
            signals_generated = []
            
            for strategy_name, strategy_class in self.strategy_classes.items():
                try:
                    logger.info(f"\n  🤖 Running {strategy_name}...")
                    
                    strategy = strategy_class()
                    df_signals = strategy.generate_signals(df.copy())
                    
                    # Get latest signal
                    latest_signal = df_signals.iloc[-1]
                    
                    if latest_signal.get('Signal', 0) != 0:
                        stop_loss = latest_signal.get('Stop_Loss')
                        if pd.notna(stop_loss):
                            stop_loss = float(stop_loss)
                        else:
                            stop_loss = None
                        take_profit = latest_signal.get('Take_Profit')
                        if pd.notna(take_profit):
                            take_profit = float(take_profit)
                        else:
                            take_profit = None
                        signal_data = {
                            'timestamp': datetime.now().isoformat(),
                            'symbol': symbol,
                            'strategy': strategy_name,
                            'direction': 'BUY' if latest_signal['Signal'] == 1 else 'SELL',
                            'entry_price': float(latest_signal['Close']),
                            'signal_strength': float(latest_signal.get('Signal_Strength', 5)),
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'timeframe': '1H',
                            'channels': ['main'],
                        }
                        
                        logger.info(f"     ✓ Signal: {signal_data['direction']} @ {signal_data['price']:.2f}")
                        logger.info(f"     ✓ Strength: {signal_data['signal_strength']:.1f}/10")
                        
                        signals_generated.append(signal_data)
                        
                        # Send to webhook if configured
                        self._send_webhook_signal(signal_data)
                        
                        # Execute dummy trade
                        if self.dummy_trader:
                            self._execute_dummy_trade(signal_data)
                    else:
                        logger.info(f"     - No signal")
                        
                except Exception as e:
                    logger.error(f"  ❌ Error running {strategy_name}: {e}")
                    continue
            
            # Store signal history
            self.signal_history[symbol] = {
                'timestamp': datetime.now().isoformat(),
                'signals': signals_generated
            }
            
            # Save to file
            self._save_signal_history()
            
            self.last_run_time[symbol] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error in check_and_generate_signals: {e}")

    def _run_profile_job(self, profile_name: str):
        """Execute scheduled job for a strategy profile."""
        if not self._should_run_profile(profile_name):
            return

        cfg = self.strategy_profiles.get(profile_name)
        if not cfg:
            logger.error(f"Profile {profile_name} not loaded")
            return

        profile = cfg['profile']
        symbol = cfg['symbol']
        strategy_class = cfg['strategy_class']
        params = cfg.get('strategy_params', {})
        live_settings = profile.live or {}
        confidence_threshold = live_settings.get('confidence_threshold', 0)
        timeframe = profile.data_source.get('interval', '1h')
        channels = live_settings.get('alert_channels', ['main'])
        cooldown_minutes = live_settings.get('cooldown_minutes', 0) or 0
        cooldown_minutes = float(cooldown_minutes)
        trade_risk_percent = live_settings.get('risk_per_trade_percent')
        if trade_risk_percent is None and self.dummy_trader:
            trade_risk_percent = getattr(self.dummy_trader, 'risk_percent', 0.0)
        if trade_risk_percent is None:
            trade_risk_percent = 0.0
        trade_risk_percent = float(trade_risk_percent)
        strategy_name = profile.strategy.get('class') or strategy_class.__name__

        if not self._is_within_live_session(profile):
            logger.info(f"[{profile_name}] Outside live session window — skipping run")
            self._mark_profile_success(profile_name)
            return

        in_cooldown, remaining = self._is_in_cooldown(profile_name, cooldown_minutes)
        if in_cooldown:
            logger.info(f"[{profile_name}] In cooldown for another {remaining:.1f} minutes")
            self._mark_profile_success(profile_name)
            return

        try:
            df = self.data_manager.load_source(profile.data_source)
            if df.empty:
                logger.warning(f"[{profile_name}] Data source returned no rows")
                self._mark_profile_failure(profile_name)
                return
        except Exception as exc:
            logger.error(f"[{profile_name}] Data load failed: {exc}")
            self._mark_profile_failure(profile_name)
            return

        try:
            strategy = strategy_class(**params)
            df_signals = strategy.generate_signals(df.copy())
            if df_signals.empty:
                logger.warning(f"[{profile_name}] Strategy returned no data (rows={len(df)})")
                self._mark_profile_failure(profile_name)
                return
        except Exception as exc:
            logger.error(f"[{profile_name}] Strategy error: {exc}")
            self._mark_profile_failure(profile_name)
            return

        latest = df_signals.iloc[-1]
        signal_value = latest.get('Signal', 0)
        signal_strength = float(latest.get('Signal_Strength', 0.0))

        logger.info("\n" + '=' * 70)
        logger.info(f"📊 Profile: {profile_name}")
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Strategy: {strategy_class.__name__}")
        logger.info(f"   Data rows: {len(df_signals)}")
        logger.info(f"   Latest price: ${float(latest['Close']):.2f}")
        logger.info(f"   Signal value: {signal_value} (0=none, 1=buy, -1=sell)")
        logger.info(f"   Signal strength: {signal_strength:.1f}/10")
        logger.info(f"   Confidence threshold: {confidence_threshold}")
        logger.info('=' * 70)

        signals_generated = []

        if signal_value != 0 and signal_strength >= confidence_threshold:
            # ============ REGIME DETECTION CHECK ============
            regime, regime_metrics = self.regime_detector.detect_regime(df_signals, verbose=False)
            should_trade_regime, regime_reason = self.regime_detector.should_trade(regime, 'trend_following')
            
            logger.info(f"   🎨 Market Regime: {regime}")
            logger.info(f"   🎨 Regime Check: {regime_reason}")
            
            if not should_trade_regime:
                logger.warning(f"     ⚠️ Signal BLOCKED by regime filter: {regime}")
                logger.warning(f"     {regime_reason}")
                signal_data = {
                    'timestamp': datetime.now().isoformat(),
                    'profile': profile_name,
                    'symbol': symbol,
                    'status': 'blocked',
                    'blocked_reason': f"Unfavorable regime: {regime}",
                    'regime': regime,
                    'regime_metrics': regime_metrics
                }
                signals_generated.append(signal_data)
                self.signal_history[profile_name] = {
                    'timestamp': datetime.now().isoformat(),
                    'signals': signals_generated
                }
                self.last_run_time[profile_name] = datetime.now()
                self._save_signal_history()
                self._mark_profile_success(profile_name)
                return
            
            # ============ MULTI-TIMEFRAME CONFIRMATION CHECK ============
            if self.use_mtf_confirmation and self.mtf_analyzer:
                try:
                    # Update analyzer with current strategy
                    self.mtf_analyzer.strategy = strategy
                    
                    logger.info(f"   ⏰ Running Multi-Timeframe Analysis...")
                    mtf_signal = self.mtf_analyzer.analyze_multi_timeframe(symbol)
                    should_trade_mtf, mtf_reason = self.mtf_analyzer.get_trading_recommendation(mtf_signal)
                    
                    logger.info(f"   ⏰ MTF Signal: {mtf_signal['final_signal']}")
                    logger.info(f"   ⏰ MTF Strength: {mtf_signal['final_strength']:.1f}/10")
                    logger.info(f"   ⏰ MTF Check: {mtf_reason}")
                    
                    # Verify MTF agrees with current signal direction
                    mtf_direction = mtf_signal['final_signal']
                    current_direction = 'BUY' if signal_value == 1 else 'SELL'
                    
                    if not should_trade_mtf or mtf_direction != current_direction:
                        logger.warning(f"     ⚠️ Signal BLOCKED by MTF filter")
                        logger.warning(f"     Current: {current_direction}, MTF: {mtf_direction}")
                        logger.warning(f"     {mtf_reason}")
                        signal_data = {
                            'timestamp': datetime.now().isoformat(),
                            'profile': profile_name,
                            'symbol': symbol,
                            'status': 'blocked',
                            'blocked_reason': f"MTF mismatch: {mtf_reason}",
                            'regime': regime,
                            'mtf_signal': mtf_signal
                        }
                        signals_generated.append(signal_data)
                        self.signal_history[profile_name] = {
                            'timestamp': datetime.now().isoformat(),
                            'signals': signals_generated
                        }
                        self.last_run_time[profile_name] = datetime.now()
                        self._save_signal_history()
                        self._mark_profile_success(profile_name)
                        return
                    
                    logger.info(f"     ✓ MTF confirmation passed: All timeframes aligned")
                    
                except Exception as mtf_error:
                    logger.warning(f"     ⚠️ MTF analysis failed: {mtf_error}")
                    # Don't block signal on MTF error - just log and continue
            
            direction = 'BUY' if signal_value == 1 else 'SELL'
            entry_price = float(latest['Close'])
            stop_loss = float(latest['Stop_Loss']) if 'Stop_Loss' in latest and not pd.isna(latest['Stop_Loss']) else None
            take_profit = float(latest['Take_Profit']) if 'Take_Profit' in latest and not pd.isna(latest['Take_Profit']) else None

            signal_data = {
                'timestamp': datetime.now().isoformat(),
                'profile': profile_name,
                'symbol': symbol,
                'strategy': strategy_name,
                'direction': direction,
                'entry_price': entry_price,
                'signal_strength': signal_strength,
                'timeframe': timeframe,
                'channels': channels,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_percent': trade_risk_percent,
                'regime': regime,
                'regime_metrics': regime_metrics,
                'bar_timestamp': self._serialize_for_rl(latest.name),
                'feature_snapshot': self._extract_feature_snapshot(latest)
            }

            quality_ok, quality_reason = self._passes_quality_filters(profile, signal_data)
            if not quality_ok:
                logger.warning(f"     ⚠️ Signal BLOCKED by quality filters: {quality_reason}")
                blocked_data = signal_data.copy()
                blocked_data['status'] = 'blocked'
                blocked_data['blocked_reason'] = quality_reason
                signals_generated.append(blocked_data)
                self.signal_history[profile_name] = {
                    'timestamp': datetime.now().isoformat(),
                    'signals': signals_generated
                }
                self.last_run_time[profile_name] = datetime.now()
                self._save_signal_history()
                self._mark_profile_success(profile_name)
                return

            # ============ RL AGENT DECISION CHECK ============
            if self.use_rl_decisions:
                try:
                    logger.info(f"   🤖 Querying RL Agent for decision...")

                    should_execute_rl, rl_reason, rl_confidence = self._should_execute_with_rl(
                        signal_data,
                        df_signals
                    )
                    
                    logger.info(f"   🤖 RL Decision: {'EXECUTE' if should_execute_rl else 'BLOCK'}")
                    logger.info(f"   🤖 RL Reason: {rl_reason}")
                    logger.info(f"   🤖 RL Confidence: {rl_confidence:.2%}")
                    
                    if not should_execute_rl:
                        logger.warning(f"     ⚠️ Signal BLOCKED by RL Agent")
                        logger.warning(f"     {rl_reason}")
                        blocked_data = signal_data.copy()
                        blocked_data['status'] = 'blocked'
                        blocked_data['blocked_reason'] = f"RL Agent: {rl_reason}"
                        blocked_data['rl_confidence'] = rl_confidence
                        blocked_data['rl_reason'] = rl_reason
                        signals_generated.append(blocked_data)
                        self.signal_history[profile_name] = {
                            'timestamp': datetime.now().isoformat(),
                            'signals': signals_generated
                        }
                        self.last_run_time[profile_name] = datetime.now()
                        self._save_signal_history()
                        self._mark_profile_success(profile_name)
                        return
                    
                    logger.info(f"     ✓ RL Agent confirmed signal execution")
                    
                except Exception as rl_error:
                    logger.warning(f"     ⚠️ RL decision failed: {rl_error}")
                    # Don't block signal on RL error - just log and continue
            
            # ============ PROCEED WITH SIGNAL ============
            logger.info(
                f"     ✓ Signal {signal_data['direction']} @ {signal_data['entry_price']:.2f} "
                f"(strength {signal_data['signal_strength']:.1f}/10)"
            )
            allowed, block_reason, risk_meta = self._passes_risk_checks(profile_name, profile, signal_data)

            if allowed:
                signal_data['status'] = 'executed'
                signal_data['risk'] = risk_meta
                signals_generated.append(signal_data)
                self._send_webhook_signal(signal_data)
                self._execute_dummy_trade(signal_data)
                self._record_signal_execution(profile_name, signal_data)
            else:
                signal_data['status'] = 'blocked'
                signal_data['blocked_reason'] = block_reason
                signal_data['risk'] = risk_meta
                signals_generated.append(signal_data)
                logger.info(f"     - Signal blocked: {block_reason}")
        else:
            reason = "no signal" if signal_value == 0 else f"strength {signal_strength:.1f} below threshold {confidence_threshold}"
            logger.info(f"     - No actionable signal ({reason})")

        self.signal_history[profile_name] = {
            'timestamp': datetime.now().isoformat(),
            'signals': signals_generated
        }
        self.last_run_time[profile_name] = datetime.now()
        self._save_signal_history()
        self._mark_profile_success(profile_name)
    
    def _send_webhook_signal(self, signal_data: dict):
        """Send signal to configured webhooks"""
        if not self.webhook_config:
            logger.warning("No webhook config - signals will not be sent to Discord")
            return
        
        channels = signal_data.get('channels') or ['main']
        timeframe = signal_data.get('timeframe', '1H')
        
        logger.info(f"📤 Sending webhook to channels: {channels}")
        
        for channel in channels:
            try:
                webhook = self.webhook_config.get_webhook(channel)
                if not webhook:
                    logger.warning(f"Webhook '{channel}' not found or disabled")
                    continue
                
                logger.info(f"   → Sending to {channel}...")
                
                webhook.send_signal(
                    symbol=signal_data['symbol'],
                    direction=signal_data['direction'],
                    strategy=signal_data['strategy'],
                    entry_price=signal_data['entry_price'],
                    signal_strength=signal_data['signal_strength'],
                    stop_loss=signal_data.get('stop_loss'),
                    take_profit=signal_data.get('take_profit'),
                    timeframe=timeframe,
                    risk_percent=signal_data.get('risk_percent'),
                    exposure_percent=signal_data.get('risk', {}).get('exposure_percent'),
                    open_trades=signal_data.get('risk', {}).get('open_trades')
                )
                
                logger.info(f"   ✓ Sent to Discord via {channel}")
                
            except Exception as e:
                logger.error(f"   ✗ Error sending webhook to {channel}: {e}")
                import traceback
                traceback.print_exc()
    
    def _execute_dummy_trade(self, signal_data: dict):
        """Execute a dummy trade based on signal"""
        if not self.dummy_trader:
            return
        
        try:
            direction = 1 if signal_data['direction'] == 'BUY' else -1
            context = self._prepare_rl_context(signal_data)

            self.dummy_trader.execute_trade(
                entry_price=signal_data['entry_price'],
                entry_time=datetime.now(),
                direction=direction,
                strategy=signal_data['strategy'],
                signal_strength=signal_data['signal_strength'],
                stop_loss=signal_data.get('stop_loss'),
                take_profit=signal_data.get('take_profit'),
                symbol=signal_data.get('symbol'),
                profile=signal_data.get('profile'),
                risk_percent=signal_data.get('risk_percent'),
                context=context
            )
        except Exception as e:
            logger.error(f"Error executing dummy trade: {e}")

    def _prepare_rl_context(self, signal_data: dict) -> dict:
        keys_to_capture = {
            'timestamp',
            'profile',
            'symbol',
            'strategy',
            'direction',
            'entry_price',
            'signal_strength',
            'timeframe',
            'stop_loss',
            'take_profit',
            'risk_percent',
            'risk',
            'regime',
            'regime_metrics',
            'bar_timestamp',
            'feature_snapshot',
            'rl_confidence',
            'rl_reason',
            'channels'
        }

        context = {}
        for key in keys_to_capture:
            if key in signal_data:
                context[key] = self._serialize_for_rl(signal_data.get(key))
        return context

    def _extract_feature_snapshot(self, latest_row):
        if latest_row is None:
            return {}
        try:
            data = latest_row.to_dict()
        except AttributeError:
            return {}
        return {str(k): self._serialize_for_rl(v) for k, v in data.items()}

    def _serialize_for_rl(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float, str, bool)):
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        if hasattr(value, 'item'):
            try:
                return value.item()
            except Exception:
                pass
        if isinstance(value, dict):
            return {str(k): self._serialize_for_rl(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._serialize_for_rl(v) for v in value]
        return str(value)
    
    def run_parameter_optimization(self):
        """Run parameter optimization (daily)"""
        logger.info("\n" + "="*70)
        logger.info("🔧 Running Daily Parameter Optimization")
        logger.info("="*70)
        
        try:
            from parameter_optimizer import ParameterOptimizer
            from data_fetch_yfinance import YFinanceDataFetcher
            
            if not self.data_fetcher:
                return
            
            # Optimize each strategy
            for strategy_name, strategy_class in self.strategy_classes.items():
                logger.info(f"\n  Optimizing {strategy_name}...")
                
                try:
                    # Fetch 2 years of daily data for optimization
                    df = self.data_fetcher.fetch_historical_data(
                        'XAUUSD',
                        period='2y',
                        interval='1d'
                    )
                    
                    optimizer = ParameterOptimizer(
                        strategy_class,
                        optimization_metric='win_rate'
                    )
                    
                    results = optimizer.optimize(df, verbose=False)
                    
                    if results:
                        best = results[0]
                        logger.info(f"    ✓ Best params: {best['params']}")
                        logger.info(f"    ✓ Win rate: {best['metrics']['win_rate']:.2f}%")
                        logger.info(f"    ✓ Profit factor: {best['metrics']['profit_factor']:.2f}")
                        
                        # Update strategy with best parameters
                        self.strategy_classes[strategy_name] = lambda **kw: strategy_class(**best['params'])
                    
                except Exception as e:
                    logger.error(f"    ❌ Optimization failed: {e}")
                    
        except Exception as e:
            logger.error(f"Error in parameter optimization: {e}")
    
    def run_rl_training_job(self, strategy_name: str):
        """Daily retraining job per strategy using dummy trade feedback."""
        job_cfg = self.rl_training_jobs.get(strategy_name, {})
        if not job_cfg.get('enabled', True):
            logger.info("RL retraining for %s skipped (disabled)", strategy_name)
            return

        logger.info("\n" + "=" * 70)
        logger.info(f"🤖 Running RL Training Job ({strategy_name})")
        logger.info("=" * 70)

        episodes = job_cfg.get('episodes', 500)
        symbol = job_cfg.get('symbol')
        symbols = job_cfg.get('symbols') or ([] if not symbol else [symbol])
        min_signal = job_cfg.get('min_feedback_signal', 0)

        try:
            from train_rl_agent import run_training

            results = []
            for sym in symbols or [None]:
                if sym:
                    logger.info("   • Training %s on %s", strategy_name, sym)
                else:
                    logger.info("   • Training %s using default symbol", strategy_name)
                result = run_training(
                    strategy_name=strategy_name,
                    symbol=sym,
                    episodes=episodes,
                    verbose=False,
                    log=logger.info,
                    show_tips=False,
                    save_summary=True,
                    min_feedback_signal=min_signal,
                )
                results.append(result)

            if len(results) == 1:
                self.last_rl_training_summary[strategy_name] = results[0]
                result = results[0]
                logger.info("   ✓ RL training job completed for %s (%s)", strategy_name, result.get('symbol'))
                if job_cfg.get('auto_reload', True) and result.get('model_path'):
                    try:
                        self.load_rl_agent(result['model_path'], strategy_name=strategy_name)
                        logger.info(
                            f"   ✓ Reloaded RL agent for {strategy_name} from {result['model_path']}"
                        )
                    except Exception as reload_error:
                        logger.error(
                            f"   ✗ Failed to reload RL agent for {strategy_name}: {reload_error}"
                        )
            else:
                summary_map = {res.get('symbol'): res for res in results}
                self.last_rl_training_summary[strategy_name] = summary_map
                logger.info(
                    "   ✓ RL training job completed for %s across %d symbols",
                    strategy_name,
                    len(results),
                )
                if job_cfg.get('auto_reload', True):
                    logger.info("   ℹ️ Auto-reload skipped for multi-symbol training run")
        except Exception as rl_error:
            logger.error(f"❌ Error during RL training job for {strategy_name}: {rl_error}")

    def generate_performance_report(self):
        """Generate daily performance report"""
        logger.info("\n" + "="*70)
        logger.info("📈 Generating Daily Performance Report")
        logger.info("="*70)
        
        try:
            if self.dummy_trader:
                summary = self.dummy_trader.get_performance_summary()
                logger.info(summary)
                
                # Export performance
                self.dummy_trader.export_trades()
                
        except Exception as e:
            logger.error(f"Error generating report: {e}")
    
    def _save_signal_history(self):
        """Save signal history to file"""
        try:
            Path('data').mkdir(exist_ok=True)
            
            history_file = f"data/signal_history_{datetime.now().strftime('%Y%m%d')}.json"
            
            with open(history_file, 'w') as f:
                json.dump(self.signal_history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving signal history: {e}")
    
    # ------------------------------------------------------------------
    # RL Agent Integration
    # ------------------------------------------------------------------
    
    def load_rl_agent(self, model_path: str = None, strategy_name: str = 'EMA30Strategy', 
                      symbol: str = None, auto_load: bool = True) -> bool:
        """
        Load trained RL brain for live trading decisions.
        Auto-loads from rl_brain directory if available.
        
        Args:
            model_path: Path to saved .pth model file (optional if auto_load=True)
            strategy_name: Strategy identifier this model corresponds to
            symbol: Trading symbol (for brain lookup)
            auto_load: Automatically find and load brain from rl_brain directory
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if not RL_AVAILABLE:
            logger.error("❌ Cannot load RL agent: PyTorch not installed")
            logger.error("   Install with: pip install torch torchvision")
            return False
        
        # Auto-load from brain directory
        if auto_load and model_path is None and symbol:
            slug = strategy_name.lower().replace('strategy', '')
            symbol_safe = symbol.replace('=', '_').replace('.', '_').replace('^', '_').lower()
            
            # Try rl_brain first (intelligent trained models)
            brain_path = Path('models/rl_brain') / f'{slug}_{symbol_safe}.pth'
            if brain_path.exists():
                model_path = str(brain_path)
                logger.info(f"🧠 Auto-loading intelligent brain: {brain_path}")
            else:
                # Fallback to regular rl models
                fallback_path = Path('models/rl') / f'{slug}_{symbol_safe}.pth'
                if fallback_path.exists():
                    model_path = str(fallback_path)
                    logger.info(f"📦 Loading RL model: {fallback_path}")
                else:
                    logger.warning(f"⚠️ No trained brain found for {strategy_name} on {symbol}")
                    return False
        
        if not model_path:
            logger.error("❌ No model path provided and auto-load failed")
            return False
        
        try:
            # Initialize agent with correct dimensions
            agent = PPOAgent(
                state_size=24,  # Matches TradingEnvironment state size
                action_size=4,  # Hold, Buy, Sell, Close
                lr=0.0003,
                gamma=0.99,
                clip_epsilon=0.2
            )
            
            # Load trained model
            agent.load(model_path)
            
            # Store with strategy+symbol key for multi-symbol support
            agent_key = f"{strategy_name}_{symbol}" if symbol else strategy_name
            self.rl_agents[agent_key] = agent
            self.use_rl_decisions = True

            logger.info(f"✅ RL Brain loaded: {agent_key}")
            logger.info(f"   Model: {model_path}")
            logger.info(f"   Confidence threshold: {self.rl_confidence_threshold}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load RL brain: {e}")
            agent_key = f"{strategy_name}_{symbol}" if symbol else strategy_name
            if agent_key in self.rl_agents:
                self.rl_agents.pop(agent_key, None)
            self.use_rl_decisions = bool(self.rl_agents)
            return False
    
    def _build_rl_state(self, signal_data: Dict, df: pd.DataFrame) -> 'np.ndarray':
        """
        Build RL state vector from current market data and signal.
        
        Args:
            signal_data: Current signal information
            df: Historical price dataframe
            
        Returns:
            24-dimensional state vector
        """
        import numpy as np
        
        try:
            latest = df.iloc[-1]
            window = df.tail(50)  # Last 50 bars for indicators
            
            # Calculate features
            features = []
            
            # Price-based features (normalized)
            close_prices = window['Close'].values
            normalized_return = (latest['Close'] - window['Close'].mean()) / (window['Close'].std() + 1e-8)
            features.append(normalized_return)
            
            # Technical indicators
            rsi = self._calculate_rsi(window['Close'], 14)
            features.append(rsi.iloc[-1] / 100 if not rsi.empty else 0.5)  # Normalize RSI to [0,1]
            
            # Volatility
            volatility = window['Close'].pct_change().std()
            features.append(min(volatility * 10, 1.0))  # Cap at 1.0
            
            # Volume ratio
            if 'Volume' in window.columns:
                volume_ratio = latest['Volume'] / (window['Volume'].mean() + 1e-8)
                features.append(min(volume_ratio / 2, 1.0))  # Normalize
            else:
                features.append(0.5)
            
            # Price action
            high_low_ratio = (latest['High'] - latest['Low']) / (latest['Close'] + 1e-8)
            features.append(min(high_low_ratio * 100, 1.0))
            
            close_open_ratio = (latest['Close'] - latest['Open']) / (latest['Open'] + 1e-8)
            features.append(np.tanh(close_open_ratio * 100))  # Normalize with tanh
            
            # Trend indicators (3 features)
            sma_20 = window['Close'].rolling(20).mean().iloc[-1]
            sma_50 = window['Close'].rolling(50).mean().iloc[-1] if len(window) >= 50 else sma_20
            features.append(1.0 if latest['Close'] > sma_20 else 0.0)
            features.append(1.0 if sma_20 > sma_50 else 0.0)
            features.append(1.0 if latest['Close'] > sma_50 else 0.0)
            
            # Current position info (3 features - zeros for now)
            features.append(0.0)  # No position
            features.append(0.0)  # Position size
            features.append(0.0)  # P&L
            
            # Market regime (2 features)
            volatility_percentile = min(volatility * 10, 1.0)
            features.append(volatility_percentile)
            features.append(0.5)  # Volume percentile placeholder
            
            # Recent returns (10 features)
            recent_returns = window['Close'].pct_change().tail(10).fillna(0).values
            features.extend(recent_returns.tolist())
            
            # Ensure exactly 24 features
            state = np.array(features[:24], dtype=np.float32)
            if len(state) < 24:
                state = np.pad(state, (0, 24 - len(state)), constant_values=0)
            
            # Clip extreme values
            state = np.clip(state, -10, 10)
            
            return state
            
        except Exception as e:
            logger.warning(f"Error building RL state: {e}")
            # Return neutral state on error
            import numpy as np
            return np.zeros(24, dtype=np.float32)
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / (loss + 1e-8)
        return 100 - (100 / (1 + rs))
    
    def _should_execute_with_rl(self, signal_data: Dict, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        Use RL agent to decide whether to execute trade.
        
        Args:
            signal_data: Signal information
            df: Historical price dataframe
            
        Returns:
            Tuple of (should_execute, reason, confidence)
        """
        if not self.use_rl_decisions:
            return True, "RL not enabled", 1.0
        strategy_name = signal_data.get('strategy') or 'EMA30Strategy'
        agent = self.rl_agents.get(strategy_name)
        if not agent:
            agent = self.rl_agents.get('EMA30Strategy') or next(iter(self.rl_agents.values()), None)
        if not agent:
            return True, "RL agent missing", 1.0
        
        try:
            # Build state from current market data
            state = self._build_rl_state(signal_data, df)
            
            # Get RL agent's decision (greedy - no exploration)
            action, _ = agent.select_action(state, training=False)
            
            # Get action probabilities for confidence
            import torch
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            with torch.no_grad():
                action_probs, _, _ = agent.policy(state_tensor)
                confidence = action_probs[0][action].item()
            
            # Map actions: 0=Hold, 1=Buy, 2=Sell, 3=Close
            signal_direction = signal_data.get('direction', 'HOLD')
            
            # Check if RL agrees with signal
            if signal_direction == 'BUY' and action == 1:
                if confidence >= self.rl_confidence_threshold:
                    return True, f"RL confirms BUY (confidence: {confidence:.2%})", confidence
                else:
                    return False, f"RL confidence too low: {confidence:.2%} < {self.rl_confidence_threshold:.2%}", confidence
            
            elif signal_direction == 'SELL' and action == 2:
                if confidence >= self.rl_confidence_threshold:
                    return True, f"RL confirms SELL (confidence: {confidence:.2%})", confidence
                else:
                    return False, f"RL confidence too low: {confidence:.2%} < {self.rl_confidence_threshold:.2%}", confidence
            
            elif action == 0:  # RL says Hold
                return False, f"RL recommends HOLD (action confidence: {confidence:.2%})", confidence
            
            else:  # RL disagrees with signal direction
                action_names = ['HOLD', 'BUY', 'SELL', 'CLOSE']
                return False, f"RL disagrees: suggests {action_names[action]} instead of {signal_direction} (confidence: {confidence:.2%})", confidence
        
        except Exception as e:
            logger.warning(f"RL decision error: {e}")
            # On error, fall back to traditional logic
            return True, "RL error, using traditional logic", 1.0
    
    # ------------------------------------------------------------------
    # Configuration Management
    # ------------------------------------------------------------------
    
    def load_config(self):
        """Load scheduler configuration"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.symbols = config.get('symbols', self.symbols)
                    self.check_interval_minutes = config.get('check_interval_minutes', self.check_interval_minutes)
                    profiles = config.get('profiles')
                    if profiles:
                        self.load_profiles(profiles)
                    rl_cfg = config.get('rl_training')
                    if isinstance(rl_cfg, dict):
                        strategies = rl_cfg.get('strategies')
                        if isinstance(strategies, dict):
                            # Merge user config with defaults
                            for name, defaults in self.rl_training_jobs.items():
                                if name in strategies:
                                    merged = defaults.copy()
                                    merged.update(strategies[name] or {})
                                    self.rl_training_jobs[name] = merged
                            for name, custom_cfg in strategies.items():
                                if name not in self.rl_training_jobs:
                                    self.rl_training_jobs[name] = custom_cfg
                        else:
                            # Backward compatibility: single job config
                            merged = self.rl_training_jobs.get('EMA30Strategy', {}).copy()
                            merged.update(rl_cfg)
                            self.rl_training_jobs['EMA30Strategy'] = merged
                    logger.info(f"✓ Loaded scheduler config")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    def save_config(self):
        """Save scheduler configuration"""
        try:
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                'symbols': self.symbols,
                'check_interval_minutes': self.check_interval_minutes,
                'profiles': list(self.strategy_profiles.keys()),
                'last_run': datetime.now().isoformat(),
                'rl_training': {
                    'strategies': self.rl_training_jobs
                }
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get_status(self) -> dict:
        """Get scheduler status"""
        return {
            'is_running': self.is_running,
            'symbols': self.symbols,
            'check_interval_minutes': self.check_interval_minutes,
            'profiles': list(self.strategy_profiles.keys()),
            'profile_state': {
                name: {
                    'current_interval': state.get('current_interval'),
                    'next_run': state.get('next_run').isoformat() if state.get('next_run') else None,
                    'backoff': state.get('backoff')
                }
                for name, state in self.profile_state.items()
            },
            'last_run_time': self.last_run_time,
            'signal_history': self.signal_history,
            'rl_training': {
                'jobs': {
                    name: job.copy() if isinstance(job, dict) else job
                    for name, job in self.rl_training_jobs.items()
                },
                'last_summary': self.last_rl_training_summary.copy() if isinstance(self.last_rl_training_summary, dict) else self.last_rl_training_summary,
            }
        }


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🚀 LIVE TRADING SCHEDULER - STARTING")
    print("=" * 70)
    print()
    
    # Load all gold profiles
    profile_dir = Path('config/strategy_profiles')
    if not profile_dir.exists():
        logger.error(f"Profile directory not found: {profile_dir}")
        exit(1)
    
    # Load all profiles (gold + nifty)
    all_profiles = list(profile_dir.glob('*.json'))
    profile_names = [p.stem for p in all_profiles]
    
    if not profile_names:
        logger.error("No strategy profiles found in config/strategy_profiles/")
        logger.error("Please run the system setup first")
        exit(1)
    
    logger.info(f"Found {len(profile_names)} profiles:")
    for name in profile_names:
        logger.info(f"  • {name}")
    print()
    
    # Initialize webhook config
    from backend.tradingview_webhook import WebhookConfig
    webhook_config = WebhookConfig(config_file='config/webhooks.json')
    
    logger.info("Loading webhook configuration...")
    try:
        webhooks = webhook_config.list_webhooks()
        logger.info(f"✓ Loaded {len(webhooks)} webhook(s):")
        for name, details in webhooks.items():
            status = "✓ enabled" if details.get('enabled') else "✗ disabled"
            logger.info(f"  • {name}: {status}")
    except Exception as e:
        logger.warning(f"Could not load webhooks: {e}")
        logger.warning("Signals will be generated but not sent to Discord")
    print()
    
    # Create scheduler
    scheduler = LiveTradingScheduler(
        strategy_profiles=profile_names,
        check_interval_minutes=1,  # Check every minute for testing
        webhook_config=webhook_config
    )
    
    # Show status
    status = scheduler.get_status()
    logger.info(f"Loaded profiles: {len(status['profiles'])}")
    logger.info(f"Check interval: {status['check_interval_minutes']} minutes")
    print()
    
    # Start scheduler
    logger.info("Starting scheduler loop...")
    logger.info("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    scheduler.start()
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
