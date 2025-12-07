"""
Gold Trading Signal System - Enhanced macOS GUI Application
Features: CSV upload, Live signal dashboard, Multi-pair support
"""

import sys
from pathlib import Path

# Add parent directory to path for backend imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
from typing import Dict, Optional, List
import logging
from datetime import datetime
import pandas as pd

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton, QComboBox,
    QTabWidget, QTextEdit, QMessageBox, QProgressBar, QCheckBox, QGroupBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal, QTimer
from PySide6.QtGui import QFont, QColor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveSignalMonitor(QThread):
    """Background thread to monitor live signals."""
    
    signal_update = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = False
    
    def run(self):
        """Monitor signal history files."""
        self.running = True
        while self.running:
            try:
                # Read today's signal history
                history_file = Path('data') / f"signal_history_{datetime.now().strftime('%Y%m%d')}.json"
                if history_file.exists():
                    with open(history_file, 'r') as f:
                        data = json.load(f)
                        self.signal_update.emit(data)
            except Exception as e:
                logger.error(f"Error reading signals: {e}")
            
            self.msleep(5000)  # Check every 5 seconds
    
    def stop(self):
        """Stop monitoring."""
        self.running = False


class BacktestWorker(QThread):
    """Worker thread for backtest execution with CSV support."""
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    log = pyqtSignal(str)
    
    def __init__(self, config: Dict, filters: Dict, csv_path: Optional[str] = None):
        super().__init__()
        self.config = config
        self.filters = filters
        self.csv_path = csv_path
    
    def run(self):
        """Execute backtest in thread."""
        try:
            from backend.zone_detector import ZoneDetector
            from backend.signal_generator import SignalGenerator
            from backend.backtester import SimpleBacktester
            
            self.progress.emit(10)
            self.log.emit("Starting backtest...")
            
            # Load data (CSV or yfinance)
            if self.csv_path:
                self.log.emit(f"Loading CSV: {Path(self.csv_path).name}")
                df = pd.read_csv(self.csv_path, parse_dates=['Date'] if 'Date' in pd.read_csv(self.csv_path, nrows=1).columns else None)
                # Ensure proper column names
                if 'Date' in df.columns:
                    df.set_index('Date', inplace=True)
                self.log.emit(f"Loaded {len(df)} rows from CSV")
            else:
                self.log.emit("Fetching data from yfinance...")
                try:
                    # Try with yfinance directly first
                    import yfinance as yf
                    symbol = self.config.get('symbol', 'GC=F')
                    
                    # Try multiple symbols as fallbacks
                    symbols_to_try = [symbol]
                    if symbol != 'GC=F':
                        symbols_to_try.append('GC=F')
                    
                    df = pd.DataFrame()
                    for sym in symbols_to_try:
                        try:
                            self.log.emit(f"Downloading {sym} data...")
                            ticker = yf.Ticker(sym)
                            df = ticker.history(period='1y', interval=self.config.get('timeframe', '1h'))
                            
                            if not df.empty:
                                # Flatten column names if MultiIndex
                                if isinstance(df.columns, pd.MultiIndex):
                                    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
                                self.log.emit(f"✓ Fetched {len(df)} candles from {sym}")
                                break
                        except Exception as e:
                            self.log.emit(f"Failed {sym}: {str(e)}")
                            continue
                    
                    if df.empty:
                        raise ValueError(f"No data returned for any symbol: {', '.join(symbols_to_try)}")
                    
                except Exception as yf_error:
                    self.log.emit(f"yfinance error: {yf_error}")
                    self.log.emit("Trying DataManager fallback...")
                    
                    from backend.data_manager import DataManager
                    data_manager = DataManager()
                    data_source = {
                        'type': 'yfinance',
                        'symbol': self.config.get('symbol', 'GC=F'),
                        'interval': self.config.get('timeframe', '1h'),
                        'period': '1y'
                    }
                    df = data_manager.load_source(data_source)
                    
                    if df.empty:
                        raise ValueError("DataManager also returned no data")
                    
                    self.log.emit(f"✓ Fetched {len(df)} candles via DataManager")
            
            if df.empty:
                raise ValueError("No data loaded - please check symbol or upload CSV")
            
            self.progress.emit(25)
            
            # Add indicators if not present
            if 'ATR' not in df.columns:
                self.log.emit("Adding technical indicators...")
                from backend.data_fetch import DataFetcher
                fetcher = DataFetcher()
                df = fetcher.add_technical_indicators(df)
            
            df = df.tail(500)  # Last 500 candles for speed
            
            self.progress.emit(40)
            self.log.emit("Detecting zones and patterns...")
            
            # Detect zones
            detector = ZoneDetector(
                lookback=self.filters.get('swing_lookback', 20),
                atr_multiplier=self.filters.get('atr_multiplier', 1.5)
            )
            
            swing_highs, swing_lows = detector.detect_swings(df)
            zones = detector.detect_supply_demand_zones(df, swing_highs, swing_lows)
            zones = detector.update_zone_mitigation(zones, df)
            
            obs = detector.detect_order_blocks(df)
            fvgs = detector.detect_fair_value_gaps(df)
            srl = detector.detect_support_resistance(df)
            
            self.progress.emit(60)
            strategy_type = self.config.get('strategy_type', 'ict')
            self.log.emit(f"Generating trading signals using {strategy_type.upper()} strategy...")
            
            # Generate signals based on selected strategy
            if strategy_type == 'ema':
                # EMA Strategy: Simpler trend-following
                from backend.ema_strategy import EMA30Strategy
                ema_strat = EMA30Strategy(
                    fast_period=self.filters.get('ema_fast', 9),
                    slow_period=self.filters.get('ema_slow', 30),
                    rsi_threshold=50
                )
                df = ema_strat.generate_signals(df)
            elif strategy_type == 'vcp':
                # VCP Strategy: Minervini's Volatility Contraction Pattern
                from backend.vcp_strategy import VCPStrategy
                vcp_strat = VCPStrategy(
                    lookback_period=60,
                    min_base_length=15,
                    max_base_length=90,
                    grade_a_final_contraction=0.15,
                    grade_b_final_contraction=0.25
                )
                df = vcp_strat.generate_signals(df)
            else:
                # ICT Strategy: Advanced institutional patterns
                generator = SignalGenerator(
                    min_risk_reward=self.filters.get('min_risk_reward', 1.5),
                    ema_fast=self.filters.get('ema_fast', 30),
                    ema_slow=self.filters.get('ema_slow', 200)
                )
                df = generator.generate_signals(df, zones, obs, fvgs, srl, lookback=len(df))
            
            self.progress.emit(75)
            self.log.emit("Running backtest...")
            
            # Normalize column names (EMA30Strategy uses underscores, SignalGenerator doesn't)
            if 'Entry_Price' in df.columns:
                df.rename(columns={
                    'Entry_Price': 'EntryPrice',
                    'Stop_Loss': 'StopLoss',
                    'Take_Profit': 'TakeProfit'
                }, inplace=True)
            
            # Log signal statistics before backtest
            signal_count = (df['Signal'] != 0).sum()
            self.log.emit(f"Found {signal_count} trading signals")
            
            # Run backtest
            backtester = SimpleBacktester(
                initial_capital=float(self.config.get('initial_capital', 10000)),
                slippage_pips=float(self.config.get('slippage_pips', 1.0)),
                spread_pips=float(self.config.get('spread_pips', 0.5))
            )
            
            results = backtester.run_backtest(df)
            
            self.progress.emit(100)
            self.log.emit("✓ Backtest completed!")
            
            self.finished.emit(results)
        
        except Exception as e:
            logger.error(f"Backtest error: {e}", exc_info=True)
            self.error.emit(str(e))


class EnhancedGoldTradingGUI(QMainWindow):
    """Enhanced GUI with CSV upload and live monitoring."""
    
    def __init__(self):
        super().__init__()
        self.config_file = Path.home() / '.gold_trading_config.json'
        self.config = self._load_config()
        self.backtest_worker = None
        self.signal_monitor = None
        self.uploaded_csv_path = None
        
        self.setWindowTitle("Gold Trading System - Multi-Pair & CSV Support")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet(self._get_stylesheet())
        
        self._init_ui()
        self._apply_config_to_ui()
        self._start_signal_monitoring()
    
    def _init_ui(self):
        """Initialize UI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # Tabs
        tabs = QTabWidget()
        
        tabs.addTab(self._create_config_tab(), "⚙️ Configuration")
        tabs.addTab(self._create_filters_tab(), "📊 Strategy Filters")
        tabs.addTab(self._create_regime_tab(), "🎨 Market Regime")
        tabs.addTab(self._create_correlation_tab(), "🔗 Correlation Matrix")
        tabs.addTab(self._create_mtf_tab(), "⏰ Multi-Timeframe")
        tabs.addTab(self._create_rl_tab(), "🤖 RL Controls")
        tabs.addTab(self._create_live_dashboard_tab(), "📡 Live Signals")
        tabs.addTab(self._create_results_tab(), "📈 Backtest Results")
        tabs.addTab(self._create_logs_tab(), "📋 Logs")
        
        main_layout.addWidget(tabs)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.validate_btn = QPushButton("✓ Validate Config")
        self.validate_btn.clicked.connect(self._validate_config)
        button_layout.addWidget(self.validate_btn)
        
        self.csv_btn = QPushButton("📂 Upload CSV")
        self.csv_btn.clicked.connect(self._upload_csv)
        button_layout.addWidget(self.csv_btn)
        
        self.backtest_btn = QPushButton("▶ Run Backtest")
        self.backtest_btn.clicked.connect(self._run_backtest)
        button_layout.addWidget(self.backtest_btn)
        
        self.apply_live_btn = QPushButton("🔄 Apply to Live")
        self.apply_live_btn.clicked.connect(self._apply_filters_to_live)
        button_layout.addWidget(self.apply_live_btn)
        
        self.save_btn = QPushButton("💾 Save Config")
        self.save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
        
        # Status bar
        self.status_label = QLabel("Ready | Multi-Pair Support: XAUUSD, XAUEUR, XAUGBP | Discord Alerts Supported")
        self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        main_layout.addWidget(self.status_label)
        
        central_widget.setLayout(main_layout)
    
    def _create_config_tab(self) -> QWidget:
        """Create configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Data Source Selection
        source_group = QGroupBox("📊 Data Source")
        source_layout = QVBoxLayout()
        
        # Symbol/Pair Selection
        pair_layout = QHBoxLayout()
        pair_layout.addWidget(QLabel("Gold Pair:"))
        self.pair_combo = QComboBox()
        self.pair_combo.addItems([
            'XAUUSD (Gold/US Dollar)',
            'XAUEUR (Gold/Euro)',
            'XAUGBP (Gold/British Pound)',
            'GC=F (Gold Futures)'
        ])
        pair_layout.addWidget(self.pair_combo)
        source_layout.addLayout(pair_layout)
        
        # CSV Upload Section
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(QLabel("CSV File:"))
        self.csv_path_label = QLabel("None selected")
        self.csv_path_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        csv_layout.addWidget(self.csv_path_label)
        csv_layout.addStretch()
        source_layout.addLayout(csv_layout)
        
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # Alert Configuration (Discord is primary)
        alert_group = QGroupBox("🔔 Alert Configuration (Optional)")
        alert_layout = QGridLayout()
        
        alert_layout.addWidget(QLabel("Discord Webhook URL:"), 0, 0)
        self.discord_webhook_input = QLineEdit()
        self.discord_webhook_input.setPlaceholderText("https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN")
        alert_layout.addWidget(self.discord_webhook_input, 0, 1)
        
        alert_layout.addWidget(QLabel("Telegram Bot Token (Optional):"), 1, 0)
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setEchoMode(QLineEdit.Password)
        self.telegram_token_input.setPlaceholderText("Optional - 1234567890:ABCDEFghijklmnopQRSTUVwxyz")
        alert_layout.addWidget(self.telegram_token_input, 1, 1)
        
        alert_layout.addWidget(QLabel("Telegram Chat ID (Optional):"), 2, 0)
        self.telegram_chat_input = QLineEdit()
        self.telegram_chat_input.setPlaceholderText("Optional - 123456789")
        alert_layout.addWidget(self.telegram_chat_input, 2, 1)
        
        alert_group.setLayout(alert_layout)
        layout.addWidget(alert_group)
        
        # Backtest Config
        backtest_group = QGroupBox("⚙️ Backtest Configuration")
        backtest_layout = QGridLayout()
        
        backtest_layout.addWidget(QLabel("Initial Capital ($):"), 0, 0)
        self.initial_capital_spin = QDoubleSpinBox()
        self.initial_capital_spin.setMinimum(1000)
        self.initial_capital_spin.setMaximum(1000000)
        self.initial_capital_spin.setValue(10000)
        backtest_layout.addWidget(self.initial_capital_spin, 0, 1)
        
        backtest_layout.addWidget(QLabel("Slippage (pips):"), 1, 0)
        self.slippage_spin = QDoubleSpinBox()
        self.slippage_spin.setMinimum(0.1)
        self.slippage_spin.setMaximum(10)
        self.slippage_spin.setValue(1.0)
        self.slippage_spin.setSingleStep(0.1)
        backtest_layout.addWidget(self.slippage_spin, 1, 1)
        
        backtest_layout.addWidget(QLabel("Spread (pips):"), 2, 0)
        self.spread_spin = QDoubleSpinBox()
        self.spread_spin.setMinimum(0.1)
        self.spread_spin.setMaximum(10)
        self.spread_spin.setValue(0.5)
        self.spread_spin.setSingleStep(0.1)
        backtest_layout.addWidget(self.spread_spin, 2, 1)
        
        backtest_layout.addWidget(QLabel("Timeframe:"), 3, 0)
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(['1h', '4h', '1d'])
        backtest_layout.addWidget(self.timeframe_combo, 3, 1)
        
        backtest_layout.addWidget(QLabel("Strategy:"), 4, 0)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            'ICT Strategy (Order Blocks, FVG, Liquidity)', 
            'EMA Strategy (Trend Following)',
            'VCP Strategy (Minervini Volatility Contraction)'
        ])
        self.strategy_combo.setToolTip("ICT: Advanced institutional concepts\nEMA: Simple trend-based entries\nVCP: Minervini's momentum breakout patterns")
        backtest_layout.addWidget(self.strategy_combo, 4, 1)
        
        backtest_group.setLayout(backtest_layout)
        layout.addWidget(backtest_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_filters_tab(self) -> QWidget:
        """Create strategy filters tab."""
        widget = QWidget()
        layout = QGridLayout()
        
        # Zone Detection
        zone_group = QGroupBox("🎯 Zone Detection")
        zone_layout = QGridLayout()
        
        zone_layout.addWidget(QLabel("Swing Lookback:"), 0, 0)
        self.swing_lookback_spin = QSpinBox()
        self.swing_lookback_spin.setMinimum(5)
        self.swing_lookback_spin.setMaximum(100)
        self.swing_lookback_spin.setValue(20)
        zone_layout.addWidget(self.swing_lookback_spin, 0, 1)
        
        zone_layout.addWidget(QLabel("ATR Multiplier:"), 1, 0)
        self.atr_mult_spin = QDoubleSpinBox()
        self.atr_mult_spin.setMinimum(0.5)
        self.atr_mult_spin.setMaximum(5.0)
        self.atr_mult_spin.setValue(1.5)
        self.atr_mult_spin.setSingleStep(0.1)
        zone_layout.addWidget(self.atr_mult_spin, 1, 1)
        
        zone_group.setLayout(zone_layout)
        layout.addWidget(zone_group, 0, 0)
        
        # Signal Generation
        signal_group = QGroupBox("📡 Signal Generation")
        signal_layout = QGridLayout()
        
        signal_layout.addWidget(QLabel("Min Risk/Reward:"), 0, 0)
        self.min_rr_spin = QDoubleSpinBox()
        self.min_rr_spin.setMinimum(1.0)
        self.min_rr_spin.setMaximum(5.0)
        self.min_rr_spin.setValue(1.5)
        self.min_rr_spin.setSingleStep(0.1)
        signal_layout.addWidget(self.min_rr_spin, 0, 1)
        
        signal_layout.addWidget(QLabel("Confidence Threshold:"), 1, 0)
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setMinimum(0)
        self.confidence_spin.setMaximum(10)
        self.confidence_spin.setValue(5.0)
        self.confidence_spin.setSingleStep(0.5)
        signal_layout.addWidget(self.confidence_spin, 1, 1)
        
        signal_group.setLayout(signal_layout)
        layout.addWidget(signal_group, 0, 1)
        
        # Moving Averages
        ema_group = QGroupBox("📈 Moving Averages")
        ema_layout = QGridLayout()
        
        ema_layout.addWidget(QLabel("Fast EMA:"), 0, 0)
        self.ema_fast_spin = QSpinBox()
        self.ema_fast_spin.setMinimum(5)
        self.ema_fast_spin.setMaximum(100)
        self.ema_fast_spin.setValue(30)
        ema_layout.addWidget(self.ema_fast_spin, 0, 1)
        
        ema_layout.addWidget(QLabel("Slow EMA:"), 1, 0)
        self.ema_slow_spin = QSpinBox()
        self.ema_slow_spin.setMinimum(50)
        self.ema_slow_spin.setMaximum(500)
        self.ema_slow_spin.setValue(200)
        ema_layout.addWidget(self.ema_slow_spin, 1, 1)
        
        ema_group.setLayout(ema_layout)
        layout.addWidget(ema_group, 1, 0)
        
        # Risk Management
        risk_group = QGroupBox("⚠️ Risk Management (Live)")
        risk_layout = QGridLayout()
        
        risk_layout.addWidget(QLabel("Risk per Trade (%):"), 0, 0)
        self.risk_per_trade_spin = QDoubleSpinBox()
        self.risk_per_trade_spin.setMinimum(0.1)
        self.risk_per_trade_spin.setMaximum(10)
        self.risk_per_trade_spin.setValue(1.5)
        self.risk_per_trade_spin.setSingleStep(0.1)
        risk_layout.addWidget(self.risk_per_trade_spin, 0, 1)
        
        risk_layout.addWidget(QLabel("Max Exposure (%):"), 1, 0)
        self.max_exposure_spin = QDoubleSpinBox()
        self.max_exposure_spin.setMinimum(1)
        self.max_exposure_spin.setMaximum(50)
        self.max_exposure_spin.setValue(5.0)
        self.max_exposure_spin.setSingleStep(1.0)
        risk_layout.addWidget(self.max_exposure_spin, 1, 1)
        
        risk_layout.addWidget(QLabel("Max Concurrent Trades:"), 2, 0)
        self.max_trades_spin = QSpinBox()
        self.max_trades_spin.setMinimum(1)
        self.max_trades_spin.setMaximum(10)
        self.max_trades_spin.setValue(2)
        risk_layout.addWidget(self.max_trades_spin, 2, 1)
        
        risk_layout.addWidget(QLabel("Cooldown (minutes):"), 3, 0)
        self.cooldown_spin = QSpinBox()
        self.cooldown_spin.setMinimum(0)
        self.cooldown_spin.setMaximum(240)
        self.cooldown_spin.setValue(30)
        risk_layout.addWidget(self.cooldown_spin, 3, 1)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group, 1, 1)
        
        widget.setLayout(layout)
        return widget
    
    def _create_regime_tab(self) -> QWidget:
        """Create market regime detection tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Regime Status Display
        status_group = QGroupBox("🎨 Current Market Regime")
        status_layout = QVBoxLayout()
        
        self.regime_label = QLabel("Regime: Loading...")
        self.regime_label.setFont(QFont('Arial', 16, QFont.Bold))
        self.regime_label.setStyleSheet("color: #3498db; padding: 10px;")
        status_layout.addWidget(self.regime_label)
        
        self.regime_metrics_label = QLabel("Metrics: N/A")
        self.regime_metrics_label.setStyleSheet("color: #7f8c8d; padding: 5px;")
        status_layout.addWidget(self.regime_metrics_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Regime Settings
        settings_group = QGroupBox("⚙️ Regime Detection Settings")
        settings_layout = QGridLayout()
        
        settings_layout.addWidget(QLabel("ADX Threshold:"), 0, 0)
        self.adx_threshold_spin = QSpinBox()
        self.adx_threshold_spin.setMinimum(10)
        self.adx_threshold_spin.setMaximum(50)
        self.adx_threshold_spin.setValue(25)
        self.adx_threshold_spin.setToolTip("ADX above this = trending market")
        settings_layout.addWidget(self.adx_threshold_spin, 0, 1)
        
        settings_layout.addWidget(QLabel("Efficiency Ratio Threshold:"), 1, 0)
        self.efficiency_threshold_spin = QDoubleSpinBox()
        self.efficiency_threshold_spin.setMinimum(0.1)
        self.efficiency_threshold_spin.setMaximum(1.0)
        self.efficiency_threshold_spin.setValue(0.3)
        self.efficiency_threshold_spin.setSingleStep(0.05)
        self.efficiency_threshold_spin.setToolTip("Below this = choppy market")
        settings_layout.addWidget(self.efficiency_threshold_spin, 1, 1)
        
        settings_layout.addWidget(QLabel("Volatility Percentile:"), 2, 0)
        self.volatility_percentile_spin = QSpinBox()
        self.volatility_percentile_spin.setMinimum(50)
        self.volatility_percentile_spin.setMaximum(90)
        self.volatility_percentile_spin.setValue(70)
        self.volatility_percentile_spin.setToolTip("Above this = high volatility")
        settings_layout.addWidget(self.volatility_percentile_spin, 2, 1)
        
        self.enable_regime_filter_cb = QCheckBox("Enable Regime-Based Signal Filtering")
        self.enable_regime_filter_cb.setChecked(True)
        self.enable_regime_filter_cb.setToolTip("Block signals in unfavorable regimes (CHOPPY, VOLATILE)")
        settings_layout.addWidget(self.enable_regime_filter_cb, 3, 0, 1, 2)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Regime History Table
        history_group = QGroupBox("📊 Regime History")
        history_layout = QVBoxLayout()
        
        self.regime_history_table = QTableWidget()
        self.regime_history_table.setColumnCount(5)
        self.regime_history_table.setHorizontalHeaderLabels(['Time', 'Regime', 'ADX', 'Efficiency', 'Signal Action'])
        self.regime_history_table.horizontalHeader().setStretchLastSection(True)
        history_layout.addWidget(self.regime_history_table)
        
        refresh_btn = QPushButton("🔄 Refresh Regime Data")
        refresh_btn.clicked.connect(self._refresh_regime_data)
        history_layout.addWidget(refresh_btn)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_correlation_tab(self) -> QWidget:
        """Create correlation matrix tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Correlation Settings
        settings_group = QGroupBox("⚙️ Correlation Settings")
        settings_layout = QGridLayout()
        
        settings_layout.addWidget(QLabel("High Correlation Threshold:"), 0, 0)
        self.corr_threshold_spin = QDoubleSpinBox()
        self.corr_threshold_spin.setMinimum(0.5)
        self.corr_threshold_spin.setMaximum(1.0)
        self.corr_threshold_spin.setValue(0.7)
        self.corr_threshold_spin.setSingleStep(0.05)
        self.corr_threshold_spin.setToolTip("Correlation above this = highly correlated")
        settings_layout.addWidget(self.corr_threshold_spin, 0, 1)
        
        settings_layout.addWidget(QLabel("Max Correlated Positions:"), 1, 0)
        self.max_corr_positions_spin = QSpinBox()
        self.max_corr_positions_spin.setMinimum(1)
        self.max_corr_positions_spin.setMaximum(10)
        self.max_corr_positions_spin.setValue(2)
        self.max_corr_positions_spin.setToolTip("Maximum number of correlated positions allowed")
        settings_layout.addWidget(self.max_corr_positions_spin, 1, 1)
        
        settings_layout.addWidget(QLabel("Max Correlated Risk (%):"), 2, 0)
        self.max_corr_risk_spin = QDoubleSpinBox()
        self.max_corr_risk_spin.setMinimum(1.0)
        self.max_corr_risk_spin.setMaximum(20.0)
        self.max_corr_risk_spin.setValue(5.0)
        self.max_corr_risk_spin.setSingleStep(0.5)
        self.max_corr_risk_spin.setToolTip("Maximum total risk % for correlated positions")
        settings_layout.addWidget(self.max_corr_risk_spin, 2, 1)
        
        self.enable_corr_filter_cb = QCheckBox("Enable Correlation-Based Position Limiting")
        self.enable_corr_filter_cb.setChecked(True)
        self.enable_corr_filter_cb.setToolTip("Prevent over-exposure to correlated assets")
        settings_layout.addWidget(self.enable_corr_filter_cb, 3, 0, 1, 2)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Correlation Matrix Display
        matrix_group = QGroupBox("🔗 Correlation Matrix (Last 90 Days)")
        matrix_layout = QVBoxLayout()
        
        self.correlation_table = QTableWidget()
        self.correlation_table.setToolTip("Pearson correlation on daily returns")
        matrix_layout.addWidget(self.correlation_table)
        
        update_btn = QPushButton("🔄 Update Correlation Matrix")
        update_btn.clicked.connect(self._update_correlation_matrix)
        matrix_layout.addWidget(update_btn)
        
        matrix_group.setLayout(matrix_layout)
        layout.addWidget(matrix_group)
        
        # Predefined Groups Display
        groups_group = QGroupBox("📦 Predefined Correlation Groups")
        groups_layout = QVBoxLayout()
        
        groups_text = QTextEdit()
        groups_text.setReadOnly(True)
        groups_text.setMaximumHeight(150)
        groups_text.setPlainText(
            "Gold Group: GC=F, GLD, XAUUSD, XAUEUR, XAUGBP\n"
            "Indian Indices: ^NSEI, ^NSEBANK\n"
            "US Indices: ^GSPC, ^DJI, ^IXIC\n"
            "Oil: CL=F, BZ=F\n"
            "Crypto: BTC-USD, ETH-USD\n\n"
            "Note: System prevents over-concentration in correlated groups"
        )
        groups_layout.addWidget(groups_text)
        
        groups_group.setLayout(groups_layout)
        layout.addWidget(groups_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_mtf_tab(self) -> QWidget:
        """Create multi-timeframe analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # MTF Settings
        settings_group = QGroupBox("⚙️ Multi-Timeframe Settings")
        settings_layout = QGridLayout()
        
        settings_layout.addWidget(QLabel("Daily Timeframe:"), 0, 0)
        self.mtf_daily_combo = QComboBox()
        self.mtf_daily_combo.addItems(['1d', '1w'])
        self.mtf_daily_combo.setToolTip("Higher timeframe for trend context")
        settings_layout.addWidget(self.mtf_daily_combo, 0, 1)
        
        settings_layout.addWidget(QLabel("Confirmation Timeframe:"), 1, 0)
        self.mtf_confirm_combo = QComboBox()
        self.mtf_confirm_combo.addItems(['4h', '1d'])
        self.mtf_confirm_combo.setCurrentText('4h')
        self.mtf_confirm_combo.setToolTip("Medium timeframe for signal confirmation")
        settings_layout.addWidget(self.mtf_confirm_combo, 1, 1)
        
        settings_layout.addWidget(QLabel("Entry Timeframe:"), 2, 0)
        self.mtf_entry_combo = QComboBox()
        self.mtf_entry_combo.addItems(['1h', '15m', '5m'])
        self.mtf_entry_combo.setCurrentText('1h')
        self.mtf_entry_combo.setToolTip("Lower timeframe for precise entries")
        settings_layout.addWidget(self.mtf_entry_combo, 2, 1)
        
        settings_layout.addWidget(QLabel("Min Signal Strength:"), 3, 0)
        self.mtf_min_strength_spin = QDoubleSpinBox()
        self.mtf_min_strength_spin.setMinimum(0.0)
        self.mtf_min_strength_spin.setMaximum(10.0)
        self.mtf_min_strength_spin.setValue(5.0)
        self.mtf_min_strength_spin.setSingleStep(0.5)
        self.mtf_min_strength_spin.setToolTip("Minimum combined signal strength for entry")
        settings_layout.addWidget(self.mtf_min_strength_spin, 3, 1)
        
        self.enable_mtf_cb = QCheckBox("Enable Multi-Timeframe Confirmation")
        self.enable_mtf_cb.setChecked(True)
        self.enable_mtf_cb.setToolTip("Require all timeframes to align before trading")
        settings_layout.addWidget(self.enable_mtf_cb, 4, 0, 1, 2)
        
        self.strict_alignment_cb = QCheckBox("Strict Alignment Mode")
        self.strict_alignment_cb.setChecked(False)
        self.strict_alignment_cb.setToolTip("All timeframes must show same signal direction")
        settings_layout.addWidget(self.strict_alignment_cb, 5, 0, 1, 2)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Current MTF Analysis Display
        analysis_group = QGroupBox("📊 Current Multi-Timeframe Analysis")
        analysis_layout = QVBoxLayout()
        
        self.mtf_analysis_table = QTableWidget()
        self.mtf_analysis_table.setColumnCount(5)
        self.mtf_analysis_table.setHorizontalHeaderLabels(['Timeframe', 'Trend', 'Signal', 'Strength', 'Status'])
        self.mtf_analysis_table.horizontalHeader().setStretchLastSection(True)
        self.mtf_analysis_table.setRowCount(3)  # Daily, 4H, 1H
        analysis_layout.addWidget(self.mtf_analysis_table)
        
        refresh_mtf_btn = QPushButton("🔄 Refresh MTF Analysis")
        refresh_mtf_btn.clicked.connect(self._refresh_mtf_analysis)
        analysis_layout.addWidget(refresh_mtf_btn)
        
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)
        
        # Trading Recommendation
        rec_group = QGroupBox("✅ Trading Recommendation")
        rec_layout = QVBoxLayout()
        
        self.mtf_recommendation_label = QLabel("Recommendation: Run analysis to get recommendation")
        self.mtf_recommendation_label.setFont(QFont('Arial', 12, QFont.Bold))
        self.mtf_recommendation_label.setStyleSheet("padding: 10px; color: #3498db;")
        rec_layout.addWidget(self.mtf_recommendation_label)
        
        rec_group.setLayout(rec_layout)
        layout.addWidget(rec_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_rl_tab(self) -> QWidget:
        """Create reinforcement learning controls tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # RL Status
        status_group = QGroupBox("🤖 RL Agent Status")
        status_layout = QVBoxLayout()
        
        self.rl_status_label = QLabel("Status: Not Initialized")
        self.rl_status_label.setFont(QFont('Arial', 14, QFont.Bold))
        self.rl_status_label.setStyleSheet("color: #e74c3c; padding: 10px;")
        status_layout.addWidget(self.rl_status_label)
        
        self.rl_metrics_label = QLabel("Training Episodes: 0 | Best Reward: N/A | Win Rate: N/A")
        self.rl_metrics_label.setStyleSheet("color: #7f8c8d; padding: 5px;")
        status_layout.addWidget(self.rl_metrics_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # RL Training Settings
        training_group = QGroupBox("⚙️ Training Settings")
        training_layout = QGridLayout()
        
        training_layout.addWidget(QLabel("Learning Rate:"), 0, 0)
        self.rl_lr_spin = QDoubleSpinBox()
        self.rl_lr_spin.setDecimals(5)
        self.rl_lr_spin.setMinimum(0.00001)
        self.rl_lr_spin.setMaximum(0.01)
        self.rl_lr_spin.setValue(0.0003)
        self.rl_lr_spin.setSingleStep(0.00001)
        training_layout.addWidget(self.rl_lr_spin, 0, 1)
        
        training_layout.addWidget(QLabel("Gamma (Discount Factor):"), 1, 0)
        self.rl_gamma_spin = QDoubleSpinBox()
        self.rl_gamma_spin.setMinimum(0.90)
        self.rl_gamma_spin.setMaximum(0.999)
        self.rl_gamma_spin.setValue(0.99)
        self.rl_gamma_spin.setSingleStep(0.01)
        training_layout.addWidget(self.rl_gamma_spin, 1, 1)
        
        training_layout.addWidget(QLabel("PPO Clip Epsilon:"), 2, 0)
        self.rl_clip_spin = QDoubleSpinBox()
        self.rl_clip_spin.setMinimum(0.1)
        self.rl_clip_spin.setMaximum(0.5)
        self.rl_clip_spin.setValue(0.2)
        self.rl_clip_spin.setSingleStep(0.05)
        training_layout.addWidget(self.rl_clip_spin, 2, 1)
        
        training_layout.addWidget(QLabel("Training Episodes:"), 3, 0)
        self.rl_episodes_spin = QSpinBox()
        self.rl_episodes_spin.setMinimum(10)
        self.rl_episodes_spin.setMaximum(10000)
        self.rl_episodes_spin.setValue(200)
        self.rl_episodes_spin.setSingleStep(50)
        training_layout.addWidget(self.rl_episodes_spin, 3, 1)
        
        training_group.setLayout(training_layout)
        layout.addWidget(training_group)
        
        # RL Control Buttons
        controls_layout = QHBoxLayout()
        
        self.rl_train_btn = QPushButton("▶ Start Training")
        self.rl_train_btn.clicked.connect(self._start_rl_training)
        controls_layout.addWidget(self.rl_train_btn)
        
        self.rl_stop_btn = QPushButton("⏹ Stop Training")
        self.rl_stop_btn.setEnabled(False)
        self.rl_stop_btn.clicked.connect(self._stop_rl_training)
        controls_layout.addWidget(self.rl_stop_btn)
        
        self.rl_load_btn = QPushButton("📂 Load Model")
        self.rl_load_btn.clicked.connect(self._load_rl_model)
        controls_layout.addWidget(self.rl_load_btn)
        
        self.rl_save_btn = QPushButton("💾 Save Model")
        self.rl_save_btn.clicked.connect(self._save_rl_model)
        controls_layout.addWidget(self.rl_save_btn)
        
        layout.addLayout(controls_layout)
        
        # Training Progress
        progress_group = QGroupBox("📈 Training Progress")
        progress_layout = QVBoxLayout()
        
        self.rl_progress_bar = QProgressBar()
        self.rl_progress_bar.setValue(0)
        progress_layout.addWidget(self.rl_progress_bar)
        
        self.rl_training_log = QTextEdit()
        self.rl_training_log.setReadOnly(True)
        self.rl_training_log.setMaximumHeight(200)
        progress_layout.addWidget(self.rl_training_log)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Deployment Settings
        deploy_group = QGroupBox("🚀 Deployment Settings")
        deploy_layout = QVBoxLayout()
        
        self.enable_rl_trading_cb = QCheckBox("Enable RL-Based Trading (EXPERIMENTAL)")
        self.enable_rl_trading_cb.setChecked(False)
        self.enable_rl_trading_cb.setToolTip("Use RL agent for live trading decisions")
        deploy_layout.addWidget(self.enable_rl_trading_cb)
        
        note_label = QLabel("⚠️ Note: RL trading is experimental. Test thoroughly with paper trading first!")
        note_label.setStyleSheet("color: #e67e22; font-style: italic;")
        deploy_layout.addWidget(note_label)
        
        deploy_group.setLayout(deploy_layout)
        layout.addWidget(deploy_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_live_dashboard_tab(self) -> QWidget:
        """Create live signal monitoring dashboard."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Status header
        status_layout = QHBoxLayout()
        self.live_status_label = QLabel("🟢 Live Monitoring Active")
        self.live_status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2ecc71;")
        status_layout.addWidget(self.live_status_label)
        status_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self._refresh_live_signals)
        status_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(status_layout)
        
        # Active Pairs
        pairs_label = QLabel("Active Pairs: XAUUSD, XAUEUR, XAUGBP")
        pairs_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(pairs_label)
        
        # Info about scheduler
        info_label = QLabel("ℹ️ Live signals require scheduler to be running. Start: python backend/live_scheduler.py")
        info_label.setStyleSheet("color: #f39c12; font-style: italic; padding: 5px; background: #2c3e50; border-radius: 3px;")
        layout.addWidget(info_label)
        
        # Live Market Data Display
        market_group = QGroupBox("📈 Live Market Data")
        market_layout = QVBoxLayout()
        
        # Gold prices
        gold_layout = QHBoxLayout()
        
        self.gcf_label = QLabel("GC=F (Futures): --")
        self.gcf_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #34495e; border-radius: 5px;")
        gold_layout.addWidget(self.gcf_label)
        
        self.gld_label = QLabel("GLD (Spot ETF): --")
        self.gld_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #34495e; border-radius: 5px;")
        gold_layout.addWidget(self.gld_label)
        
        self.spot_calc_label = QLabel("Spot (calc): --")
        self.spot_calc_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #34495e; border-radius: 5px;")
        gold_layout.addWidget(self.spot_calc_label)
        
        market_layout.addLayout(gold_layout)
        
        # Indian indices
        india_layout = QHBoxLayout()
        
        self.nifty_label = QLabel("NIFTY 50: --")
        self.nifty_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #34495e; border-radius: 5px;")
        india_layout.addWidget(self.nifty_label)
        
        self.banknifty_label = QLabel("BANK NIFTY: --")
        self.banknifty_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #34495e; border-radius: 5px;")
        india_layout.addWidget(self.banknifty_label)
        
        market_layout.addLayout(india_layout)
        
        self.last_update_label = QLabel("Last update: Never")
        self.last_update_label.setStyleSheet("font-size: 11px; color: #7f8c8d; padding: 10px;")
        market_layout.addWidget(self.last_update_label)
        
        market_group.setLayout(market_layout)
        layout.addWidget(market_group)
        
        # Recent Signals Table
        signals_group = QGroupBox("📊 Recent Signals (Last 24h)")
        signals_layout = QVBoxLayout()
        
        self.signals_table = QTableWidget()
        self.signals_table.setColumnCount(8)
        self.signals_table.setHorizontalHeaderLabels([
            'Time', 'Profile', 'Symbol', 'Direction', 'Price', 'Confidence', 'Status', 'Risk'
        ])
        self.signals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        signals_layout.addWidget(self.signals_table)
        
        signals_group.setLayout(signals_layout)
        layout.addWidget(signals_group)
        
        # Exposure Metrics
        metrics_layout = QHBoxLayout()
        
        self.open_trades_label = QLabel("Open Trades: 0")
        self.open_trades_label.setStyleSheet("font-size: 13px; padding: 10px;")
        metrics_layout.addWidget(self.open_trades_label)
        
        self.exposure_label = QLabel("Total Exposure: 0.0%")
        self.exposure_label.setStyleSheet("font-size: 13px; padding: 10px;")
        metrics_layout.addWidget(self.exposure_label)
        
        self.last_signal_label = QLabel("Last Signal: None")
        self.last_signal_label.setStyleSheet("font-size: 13px; padding: 10px;")
        metrics_layout.addWidget(self.last_signal_label)
        
        layout.addLayout(metrics_layout)
        
        widget.setLayout(layout)
        return widget
    
    def _create_results_tab(self) -> QWidget:
        """Create backtest results tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(['Metric', 'Value'])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.results_table)
        
        widget.setLayout(layout)
        return widget
    
    def _create_logs_tab(self) -> QWidget:
        """Create logs tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Menlo", 10))
        layout.addWidget(self.logs_text)
        
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self.logs_text.clear)
        layout.addWidget(clear_btn)
        
        widget.setLayout(layout)
        return widget
    
    def _upload_csv(self):
        """Handle CSV file upload."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            str(Path.home()),
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                # Validate CSV
                df = pd.read_csv(file_path, nrows=5)
                required_cols = ['Open', 'High', 'Low', 'Close']
                missing = [col for col in required_cols if col not in df.columns]
                
                if missing:
                    QMessageBox.warning(
                        self,
                        "Invalid CSV",
                        f"CSV missing required columns: {', '.join(missing)}\n\n"
                        f"Required: Open, High, Low, Close, Volume (optional)"
                    )
                    return
                
                self.uploaded_csv_path = file_path
                self.csv_path_label.setText(f"✓ {Path(file_path).name}")
                self.csv_path_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
                self._log(f"✓ CSV uploaded: {Path(file_path).name}")
                
                QMessageBox.information(
                    self,
                    "CSV Loaded",
                    f"Successfully loaded: {Path(file_path).name}\n\n"
                    f"Rows: {len(pd.read_csv(file_path))}\n"
                    f"Columns: {', '.join(df.columns)}"
                )
            
            except Exception as e:
                QMessageBox.critical(self, "CSV Error", f"Failed to load CSV:\n{e}")
                self._log(f"✗ CSV load error: {e}")
    
    def _validate_config(self):
        """Validate configuration."""
        config = self._get_ui_config()
        
        # Check if any alert method is configured
        has_discord = config.get('discord_webhook_url') and 'discord.com/api/webhooks' in config['discord_webhook_url']
        has_telegram = config.get('telegram_bot_token') and config.get('telegram_chat_id')
        
        if not has_discord and not has_telegram:
            msg = "⚠️ No alert method configured\n\n" \
                  "For live trading, configure at least one:\n" \
                  "• Discord Webhook URL (recommended)\n" \
                  "• Telegram Bot Token + Chat ID\n\n" \
                  "✓ Backtesting is still available without alerts"
            self.status_label.setText("⚠️ No alerts configured")
            self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
            QMessageBox.warning(self, "Alert Configuration", msg)
            return
        
        # Validate Discord if provided
        if config.get('discord_webhook_url'):
            if 'discord.com/api/webhooks' not in config['discord_webhook_url']:
                self.status_label.setText("✗ Invalid Discord Webhook URL")
                self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                QMessageBox.warning(self, "Invalid Discord URL", 
                                  "Discord webhook URL should start with:\nhttps://discord.com/api/webhooks/")
                return
        
        # Validate Telegram if provided
        if config.get('telegram_bot_token') or config.get('telegram_chat_id'):
            if config.get('telegram_bot_token') and ':' not in config['telegram_bot_token']:
                self.status_label.setText("✗ Invalid Telegram Token format")
                self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                QMessageBox.warning(self, "Invalid Token", "Telegram token should contain ':'")
                return
        
        # Success message
        alert_methods = []
        if has_discord:
            alert_methods.append("Discord")
        if has_telegram:
            alert_methods.append("Telegram")
        
        msg = f"✓ Configuration valid!\n\nAlert methods: {', '.join(alert_methods)}"
        self.status_label.setText(f"✓ Ready - Alerts: {', '.join(alert_methods)}")
        self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        QMessageBox.information(self, "Valid Configuration", msg)
    
    def _run_backtest(self):
        """Run backtest with CSV or yfinance data."""
        config = self._get_ui_config()
        filters = self._get_ui_filters()
        
        if self.uploaded_csv_path:
            self._log(f"Starting backtest with CSV: {Path(self.uploaded_csv_path).name}")
        else:
            # GC=F (Gold Futures) is most reliable on yfinance
            symbol_map = {
                'XAUUSD (Gold/US Dollar)': 'GC=F',  # Gold futures (most reliable)
                'XAUEUR (Gold/Euro)': 'GC=F',
                'XAUGBP (Gold/British Pound)': 'GC=F',
                'GC=F (Gold Futures)': 'GC=F'
            }
            config['symbol'] = symbol_map.get(self.pair_combo.currentText(), 'GC=F')
            pair_name = self.pair_combo.currentText().split(' ')[0]
            self._log(f"Starting backtest with {config['symbol']} ({pair_name})")
        
        self.backtest_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.backtest_worker = BacktestWorker(config, filters, self.uploaded_csv_path)
        self.backtest_worker.progress.connect(self._on_progress)
        self.backtest_worker.finished.connect(self._on_backtest_finished)
        self.backtest_worker.error.connect(self._on_backtest_error)
        self.backtest_worker.log.connect(self._log)
        self.backtest_worker.start()
    
    def _apply_filters_to_live(self):
        """Apply current filter settings to live trading profiles."""
        try:
            filters = self._get_ui_filters()
            profiles_dir = Path('config/strategy_profiles')
            
            updated = []
            for profile_file in profiles_dir.glob('gold_*.json'):
                with open(profile_file, 'r') as f:
                    profile = json.load(f)
                
                # Update live settings
                if 'live' not in profile:
                    profile['live'] = {}
                
                profile['live']['confidence_threshold'] = filters['confidence_threshold']
                profile['live']['risk_per_trade_percent'] = filters['risk_per_trade']
                profile['live']['max_exposure_percent'] = filters['max_exposure']
                profile['live']['max_concurrent_trades'] = filters['max_concurrent_trades']
                profile['live']['cooldown_minutes'] = filters['cooldown_minutes']
                
                # Update strategy params
                if 'EMA' in profile['strategy']['class']:
                    profile['strategy']['params']['fast_period'] = filters['ema_fast']
                    profile['strategy']['params']['slow_period'] = filters['ema_slow']
                
                with open(profile_file, 'w') as f:
                    json.dump(profile, f, indent=2)
                
                updated.append(profile_file.stem)
            
            self._log(f"✓ Updated {len(updated)} profiles: {', '.join(updated)}")
            QMessageBox.information(
                self,
                "Profiles Updated",
                f"✓ Applied filters to {len(updated)} strategy profiles\n\n"
                f"Profiles: {', '.join(updated)}\n\n"
                f"Restart live scheduler to apply changes."
            )
        
        except Exception as e:
            self._log(f"✗ Error updating profiles: {e}")
            QMessageBox.critical(self, "Update Error", f"Failed to update profiles:\n{e}")
    
    def _start_signal_monitoring(self):
        """Start background signal monitoring."""
        self.signal_monitor = LiveSignalMonitor()
        self.signal_monitor.signal_update.connect(self._update_live_signals)
        self.signal_monitor.start()
    
    def _update_live_signals(self, data: dict):
        """Update live signals table and market data."""
        try:
            # Fetch real-time prices
            import yfinance as yf
            
            try:
                # Gold futures
                gcf = yf.Ticker('GC=F').history(period='1d', interval='1h')
                if not gcf.empty:
                    gcf_price = gcf.iloc[-1]['Close']
                    self.gcf_label.setText(f"GC=F (Futures): ${gcf_price:.2f}")
                    self.gcf_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #f39c12; color: white; border-radius: 5px;")
                
                # Gold spot ETF
                gld = yf.Ticker('GLD').history(period='1d', interval='1h')
                if not gld.empty:
                    gld_price = gld.iloc[-1]['Close']
                    spot_price = gld_price * 10  # GLD is 1/10 oz
                    self.gld_label.setText(f"GLD (Spot ETF): ${gld_price:.2f}")
                    self.gld_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #f39c12; color: white; border-radius: 5px;")
                    self.spot_calc_label.setText(f"Spot (calc): ${spot_price:.2f}/oz")
                    self.spot_calc_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #27ae60; color: white; border-radius: 5px;")
                
                # Nifty 50
                nifty = yf.Ticker('^NSEI').history(period='1d', interval='5m')
                if not nifty.empty:
                    nifty_price = nifty.iloc[-1]['Close']
                    self.nifty_label.setText(f"NIFTY 50: ₹{nifty_price:.2f}")
                    self.nifty_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #3498db; color: white; border-radius: 5px;")
                
                # Bank Nifty
                banknifty = yf.Ticker('^NSEBANK').history(period='1d', interval='5m')
                if not banknifty.empty:
                    banknifty_price = banknifty.iloc[-1]['Close']
                    self.banknifty_label.setText(f"BANK NIFTY: ₹{banknifty_price:.2f}")
                    self.banknifty_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #3498db; color: white; border-radius: 5px;")
                
            except Exception as e:
                logger.error(f"Error fetching live prices: {e}")
            
            self.last_update_label.setText(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
            
            self.signals_table.setRowCount(0)
            
            all_signals = []
            for profile_name, profile_data in data.items():
                for signal in profile_data.get('signals', []):
                    signal['profile'] = profile_name
                    all_signals.append(signal)
            
            # Sort by timestamp (most recent first)
            all_signals.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Display last 20 signals
            for signal in all_signals[:20]:
                row = self.signals_table.rowCount()
                self.signals_table.insertRow(row)
                
                timestamp = signal.get('timestamp', '')[:19]  # Remove milliseconds
                self.signals_table.setItem(row, 0, QTableWidgetItem(timestamp))
                self.signals_table.setItem(row, 1, QTableWidgetItem(signal.get('profile', 'N/A')))
                self.signals_table.setItem(row, 2, QTableWidgetItem(signal.get('symbol', 'N/A')))
                self.signals_table.setItem(row, 3, QTableWidgetItem(signal.get('direction', 'N/A')))
                self.signals_table.setItem(row, 4, QTableWidgetItem(f"{signal.get('entry_price', 0):.2f}"))
                self.signals_table.setItem(row, 5, QTableWidgetItem(f"{signal.get('signal_strength', 0):.1f}/10"))
                self.signals_table.setItem(row, 6, QTableWidgetItem(signal.get('status', 'unknown')))
                self.signals_table.setItem(row, 7, QTableWidgetItem(f"{signal.get('risk_percent', 0):.1f}%"))
            
            # Update metrics
            open_count = sum(1 for s in all_signals if s.get('status') == 'executed')
            self.open_trades_label.setText(f"Open Trades: {open_count}")
            
            if all_signals:
                last = all_signals[0]
                self.last_signal_label.setText(
                    f"Last Signal: {last.get('direction')} {last.get('symbol')} @ {last.get('entry_price', 0):.2f}"
                )
        
        except Exception as e:
            logger.error(f"Error updating signals: {e}")
    
    def _refresh_live_signals(self):
        """Manually refresh live signals."""
        self._log("Refreshing live signals...")
        history_file = Path('data') / f"signal_history_{datetime.now().strftime('%Y%m%d')}.json"
        if history_file.exists():
            with open(history_file, 'r') as f:
                data = json.load(f)
                self._update_live_signals(data)
        else:
            self._log("No signal history found for today")
    
    def _on_progress(self, value: int):
        """Update progress bar."""
        self.progress_bar.setValue(value)
    
    def _on_backtest_finished(self, results: dict):
        """Handle backtest completion."""
        self._log(f"✓ Backtest completed at {datetime.now().strftime('%H:%M:%S')}")
        
        # Update results table
        self.results_table.setRowCount(0)
        
        metrics = [
            ('Data Source', 'CSV' if self.uploaded_csv_path else 'yfinance'),
            ('Total Trades', results.get('total_trades', 0)),
            ('Win Rate (%)', f"{results.get('win_rate', 0):.2f}"),
            ('Profit Factor', f"{results.get('profit_factor', 0):.2f}"),
            ('Total P&L ($)', f"{results.get('total_pnl', 0):.2f}"),
            ('Gross Profit ($)', f"{results.get('gross_profit', 0):.2f}"),
            ('Gross Loss ($)', f"{results.get('gross_loss', 0):.2f}"),
            ('Max Drawdown (%)', f"{results.get('max_drawdown_pct', 0):.2f}"),
            ('Sharpe Ratio', f"{results.get('sharpe_ratio', 0):.2f}"),
            ('Sortino Ratio', f"{results.get('sortino_ratio', 0):.2f}"),
        ]
        
        for row, (metric, value) in enumerate(metrics):
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(metric))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(value)))
        
        self.backtest_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("✓ Backtest complete")
    
    def _on_backtest_error(self, error: str):
        """Handle backtest error."""
        self._log(f"✗ Error: {error}")
        self.backtest_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"✗ Error: {error}")
        QMessageBox.critical(self, "Backtest Error", f"Error:\n{error}")
    
    def _save_config(self):
        """Save configuration."""
        config = self._get_ui_config()
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Also save Discord webhook to webhook config if provided
        discord_url = config.get('discord_webhook_url', '').strip()
        if discord_url and 'discord.com/api/webhooks' in discord_url:
            try:
                from backend.tradingview_webhook import WebhookConfig
                webhook_config = WebhookConfig()
                webhook_config.add_webhook(
                    name='main',
                    url=discord_url,
                    enabled=True
                )
                self._log("✓ Discord webhook saved to config/webhooks.json")
            except Exception as e:
                self._log(f"⚠️ Could not save Discord webhook: {e}")
        
        self._log(f"✓ Configuration saved")
        QMessageBox.information(self, "Saved", "Configuration saved successfully")
    
    def _load_config(self) -> Dict:
        """Load configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _apply_config_to_ui(self):
        """Apply loaded config to UI."""
        if self.config:
            self.discord_webhook_input.setText(self.config.get('discord_webhook_url', ''))
            self.telegram_token_input.setText(self.config.get('telegram_bot_token', ''))
            self.telegram_chat_input.setText(self.config.get('telegram_chat_id', ''))
            self.initial_capital_spin.setValue(float(self.config.get('initial_capital', 10000)))
            self.slippage_spin.setValue(float(self.config.get('slippage_pips', 1.0)))
            self.spread_spin.setValue(float(self.config.get('spread_pips', 0.5)))
    
    def _get_ui_config(self) -> Dict:
        """Get configuration from UI."""
        strategy_text = self.strategy_combo.currentText()
        if 'EMA' in strategy_text:
            strategy_type = 'ema'
        elif 'VCP' in strategy_text:
            strategy_type = 'vcp'
        else:
            strategy_type = 'ict'
        
        return {
            'discord_webhook_url': self.discord_webhook_input.text().strip(),
            'telegram_bot_token': self.telegram_token_input.text().strip(),
            'telegram_chat_id': self.telegram_chat_input.text().strip(),
            'initial_capital': str(self.initial_capital_spin.value()),
            'slippage_pips': str(self.slippage_spin.value()),
            'spread_pips': str(self.spread_spin.value()),
            'timeframe': self.timeframe_combo.currentText(),
            'strategy_type': strategy_type,
        }
    
    def _get_ui_filters(self) -> Dict:
        """Get strategy filters from UI."""
        return {
            'swing_lookback': self.swing_lookback_spin.value(),
            'atr_multiplier': self.atr_mult_spin.value(),
            'min_risk_reward': self.min_rr_spin.value(),
            'confidence_threshold': self.confidence_spin.value(),
            'ema_fast': self.ema_fast_spin.value(),
            'ema_slow': self.ema_slow_spin.value(),
            'risk_per_trade': self.risk_per_trade_spin.value(),
            'max_exposure': self.max_exposure_spin.value(),
            'max_concurrent_trades': self.max_trades_spin.value(),
            'cooldown_minutes': self.cooldown_spin.value(),
        }
    
    def _log(self, message: str):
        """Add message to logs."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.logs_text.append(f"[{timestamp}] {message}")
    
    def _refresh_regime_data(self):
        """Refresh market regime detection data."""
        try:
            from backend.market_regime_detector import MarketRegimeDetector
            from backend.data_fetch_yfinance import YFinanceDataFetcher
            
            self._log("Fetching regime data...")
            
            # Ensure data directory exists
            Path('data').mkdir(exist_ok=True)
            
            fetcher = YFinanceDataFetcher()
            symbol = self.pair_combo.currentText().split('(')[1].split(')')[0]
            df = fetcher.fetch_historical_data(symbol, period='3mo', interval='1d')
            
            detector = MarketRegimeDetector(adx_threshold=self.adx_threshold_spin.value())
            regime, metrics = detector.detect_regime(df, verbose=True)
            
            # Update status
            self.regime_label.setText(f"Regime: {regime.value}")
            regime_colors = {'TRENDING_UP': '#2ecc71', 'TRENDING_DOWN': '#e74c3c', 
                           'RANGING': '#f39c12', 'VOLATILE': '#e67e22', 'CHOPPY': '#95a5a6'}
            self.regime_label.setStyleSheet(f"color: {regime_colors.get(regime.value, '#3498db')}; padding: 10px;")
            
            # Update metrics
            self.regime_metrics_label.setText(f"ADX: {metrics.get('adx', 0):.2f} | Efficiency: {metrics.get('efficiency_ratio', 0):.3f}")
            self._log(f"✓ Regime: {regime.value}")
            
        except Exception as e:
            self._log(f"✗ Regime error: {e}")
    
    def _update_correlation_matrix(self):
        """Update correlation matrix."""
        try:
            from backend.correlation_manager import CorrelationManager
            from backend.data_fetch_yfinance import YFinanceDataFetcher
            
            self._log("Calculating correlations...")
            symbols = ['GC=F', 'GLD', '^NSEI', '^NSEBANK']
            fetcher = YFinanceDataFetcher()
            manager = CorrelationManager(data_fetcher=fetcher, high_correlation_threshold=self.corr_threshold_spin.value())
            matrix = manager.build_correlation_matrix(symbols)
            
            # Update table
            self.correlation_table.setRowCount(len(symbols))
            self.correlation_table.setColumnCount(len(symbols))
            self.correlation_table.setHorizontalHeaderLabels(symbols)
            self.correlation_table.setVerticalHeaderLabels(symbols)
            
            for i, sym1 in enumerate(symbols):
                for j, sym2 in enumerate(symbols):
                    corr_value = matrix.loc[sym1, sym2]
                    item = QTableWidgetItem(f"{corr_value:.2f}")
                    if corr_value > 0.7:
                        item.setBackground(QColor('#e74c3c'))
                        item.setForeground(QColor('white'))
                    self.correlation_table.setItem(i, j, item)
            
            self._log(f"✓ Correlation matrix updated")
        except Exception as e:
            self._log(f"✗ Correlation error: {e}")
    
    def _refresh_mtf_analysis(self):
        """Refresh multi-timeframe analysis."""
        try:
            from backend.multi_timeframe_analyzer import MultiTimeframeAnalyzer
            from backend.data_fetch_yfinance import YFinanceDataFetcher
            from backend.ict_strategy import ICTStrategy
            
            self._log("Running MTF analysis...")
            fetcher = YFinanceDataFetcher()
            symbol = self.pair_combo.currentText().split('(')[1].split(')')[0]
            
            analyzer = MultiTimeframeAnalyzer(data_fetcher=fetcher, strategy_class=ICTStrategy)
            mtf_signal = analyzer.analyze_multi_timeframe(symbol, verbose=False)
            
            # Update recommendation
            should_trade, reason = analyzer.get_trading_recommendation(mtf_signal)
            if should_trade:
                self.mtf_recommendation_label.setText(f"✅ TRADE: {mtf_signal.direction} | Strength: {mtf_signal.strength:.1f}")
                self.mtf_recommendation_label.setStyleSheet("padding: 10px; color: #2ecc71;")
            else:
                self.mtf_recommendation_label.setText(f"❌ NO TRADE: {reason}")
                self.mtf_recommendation_label.setStyleSheet("padding: 10px; color: #e74c3c;")
            
            self._log(f"✓ MTF: Direction={mtf_signal.direction}")
        except Exception as e:
            self._log(f"✗ MTF error: {e}")
    
    def _start_rl_training(self):
        """Start RL training."""
        try:
            self._log("Starting RL training...")
            self.rl_train_btn.setEnabled(False)
            self.rl_status_label.setText("Status: Training...")
            self.rl_status_label.setStyleSheet("color: #f39c12; padding: 10px;")
            
            # Ensure data directory exists
            Path('data').mkdir(exist_ok=True)
            Path('models').mkdir(exist_ok=True)
            
            from backend.advanced_rl_trading_system import TradingEnvironment, PPOAgent
            from backend.data_fetch_yfinance import YFinanceDataFetcher
            
            fetcher = YFinanceDataFetcher()
            symbol = self.pair_combo.currentText().split('(')[1].split(')')[0]
            df = fetcher.fetch_historical_data(symbol, period='2y', interval='1d')
            self.rl_training_log.append(f"Training data: {len(df)} days")
            
            env = TradingEnvironment(df, initial_balance=10000)
            agent = PPOAgent(state_size=env._get_state_size(), action_size=env.get_action_space_size())
            
            self.rl_training_log.append("Training 50 episodes (demo)...")
            for ep in range(50):
                self.rl_progress_bar.setValue(int((ep+1)/50*100))
                state = env.reset()
                done = False
                while not done:
                    action, _ = agent.select_action(state, training=True)
                    state, _, done, info = env.step(action)
                if (ep+1) % 10 == 0:
                    self.rl_training_log.append(f"Episode {ep+1}: Balance=${info['balance']:.2f}")
                QApplication.processEvents()
            
            agent.save('models/ppo_trading_agent.pth')
            self.rl_status_label.setText("Status: Training Complete")
            self.rl_status_label.setStyleSheet("color: #2ecc71; padding: 10px;")
            self._log("✓ RL training complete")
        except Exception as e:
            self._log(f"✗ RL training error: {e}")
        finally:
            self.rl_train_btn.setEnabled(True)
    
    def _stop_rl_training(self):
        """Stop RL training."""
        self._log("Stopping RL training...")
        self.rl_train_btn.setEnabled(True)
    
    def _load_rl_model(self):
        """Load RL model into scheduler."""
        try:
            from PySide6.QtWidgets import QInputDialog
            
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Load RL Model", "models/rl", "PyTorch Models (*.pth)"
            )
            if not file_path:
                return
            
            # Strategy selection dialog
            strategies = ["EMA30Strategy", "ICTStrategy", "VCPStrategy"]
            strategy, ok = QInputDialog.getItem(
                self, "Select Strategy", 
                "Choose the strategy this model was trained for:",
                strategies, 0, False
            )
            if not ok:
                return
            
            self._log(f"Loading RL model for {strategy}: {Path(file_path).name}")
            
            # Load into scheduler if available
            if hasattr(self, 'scheduler') and self.scheduler:
                success = self.scheduler.load_rl_agent(file_path, strategy_name=strategy)
                if success:
                    self.rl_status_label.setText(
                        f"✅ {strategy}: {Path(file_path).name}"
                    )
                    self.rl_status_label.setStyleSheet("color: #2ecc71; padding: 10px;")
                    self._log(f"✓ RL agent loaded and active for {strategy}")
                    self._log(f"✓ Confidence threshold: {self.scheduler.rl_confidence_threshold:.0%}")
                    
                    # Update enable checkbox
                    if hasattr(self, 'enable_rl_trading_cb'):
                        self.enable_rl_trading_cb.setChecked(True)
                else:
                    self.rl_status_label.setText("❌ Load Failed")
                    self.rl_status_label.setStyleSheet("color: #e74c3c; padding: 10px;")
                    self._log(f"✗ Failed to load RL agent")
            else:
                # Scheduler not initialized - just validate model file
                try:
                    from backend.advanced_rl_trading_system import PPOAgent, TORCH_AVAILABLE
                    if not TORCH_AVAILABLE:
                        raise ImportError("PyTorch not available")
                    
                    # Test load
                    agent = PPOAgent(state_size=24, action_size=4)
                    agent.load(file_path)
                    
                    self.rl_status_label.setText(
                        f"✅ {strategy}: {Path(file_path).name} (scheduler offline)"
                    )
                    self.rl_status_label.setStyleSheet("color: #f39c12; padding: 10px;")
                    self._log(f"✓ Model validated (will load when scheduler starts)")
                except Exception as load_err:
                    self.rl_status_label.setText("❌ Invalid Model")
                    self.rl_status_label.setStyleSheet("color: #e74c3c; padding: 10px;")
                    self._log(f"✗ Model validation failed: {load_err}")
                    
        except Exception as e:
            self._log(f"✗ Model load error: {e}")
            self.rl_status_label.setText("❌ Load Error")
            self.rl_status_label.setStyleSheet("color: #e74c3c; padding: 10px;")
    
    def _save_rl_model(self):
        """Save RL model."""
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save RL Model", "models/ppo_trading_agent.pth", "PyTorch Models (*.pth)")
            if file_path:
                self._log(f"Saved RL model: {Path(file_path).name}")
        except Exception as e:
            self._log(f"✗ Model save error: {e}")
    
    def closeEvent(self, event):
        """Clean up on close."""
        if self.signal_monitor:
            self.signal_monitor.stop()
            self.signal_monitor.wait()
        event.accept()
    
    @staticmethod
    def _get_stylesheet() -> str:
        """Get application stylesheet."""
        return """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QGroupBox {
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
        }
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 8px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:pressed {
            background-color: #1f618d;
        }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            padding: 5px;
            background-color: white;
        }
        QTableWidget {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            background-color: white;
        }
        """


def main():
    app = QApplication(sys.argv)
    window = EnhancedGoldTradingGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
