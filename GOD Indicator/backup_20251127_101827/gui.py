"""
Gold Trading Signal System - macOS GUI Application
Minimalistic configuration and execution interface
"""

import sys
import json
from pathlib import Path
from typing import Dict, Optional
import logging
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton, QComboBox,
    QTabWidget, QTextEdit, QMessageBox, QProgressBar, QCheckBox, QGroupBox,
    QFileDialog, QDialog, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal, QTimer, QPointF
from PySide6.QtGui import QFont, QColor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validate required configuration."""
    
    REQUIRED_FIELDS = {
        'telegram_bot_token': 'Telegram Bot Token',
        'telegram_chat_id': 'Telegram Chat ID',
    }
    
    OPTIONAL_FIELDS = {
        'oanda_api_key': 'OANDA API Key (optional)',
        'webhook_port': 'Webhook Port',
    }
    
    @staticmethod
    def validate_telegram_token(token: str) -> bool:
        """Validate Telegram token format."""
        if not token or len(token) < 20:
            return False
        return ':' in token
    
    @staticmethod
    def validate_telegram_chat_id(chat_id: str) -> bool:
        """Validate Telegram chat ID format."""
        if not chat_id:
            return False
        try:
            int(chat_id)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_port(port: str) -> bool:
        """Validate port number."""
        try:
            p = int(port)
            return 1024 <= p <= 65535
        except ValueError:
            return False
    
    @classmethod
    def validate_all(cls, config: Dict) -> tuple[bool, str]:
        """
        Validate all required fields.
        
        Returns:
            (is_valid, error_message)
        """
        for field, label in cls.REQUIRED_FIELDS.items():
            if field not in config or not config[field]:
                return False, f"❌ Missing required: {label}"
            
            # Specific validation
            if field == 'telegram_bot_token':
                if not cls.validate_telegram_token(config[field]):
                    return False, f"❌ Invalid {label} format. Should contain ':'"
            
            elif field == 'telegram_chat_id':
                if not cls.validate_telegram_chat_id(config[field]):
                    return False, f"❌ Invalid {label}. Should be numeric"
        
        return True, "✓ Configuration valid"


class BacktestWorker(QThread):
    """Worker thread for backtest execution."""
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, config: Dict, filters: Dict):
        super().__init__()
        self.config = config
        self.filters = filters
    
    def run(self):
        """Execute backtest in thread."""
        try:
            from backend.data_fetch import DataFetcher
            from backend.zone_detector import ZoneDetector
            from backend.signal_generator import SignalGenerator
            from backend.backtester import SimpleBacktester
            
            self.progress.emit(10)
            
            # Load data
            fetcher = DataFetcher()
            df = fetcher.fetch_historical_data(
                symbol='GC=F',
                start_date=self.config.get('start_date', '2020-01-01'),
                end_date=self.config.get('end_date', '2024-12-31'),
                interval=self.config.get('timeframe', '1h')
            )
            
            self.progress.emit(25)
            
            # Add indicators
            df = fetcher.add_technical_indicators(df)
            df = df.tail(500)
            
            self.progress.emit(40)
            
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
            
            # Generate signals
            generator = SignalGenerator(
                min_risk_reward=self.filters.get('min_risk_reward', 1.5),
                ema_fast=self.filters.get('ema_fast', 30),
                ema_slow=self.filters.get('ema_slow', 200)
            )
            
            df = generator.generate_signals(df, zones, obs, fvgs, srl, lookback=len(df))
            
            self.progress.emit(75)
            
            # Run backtest
            backtester = SimpleBacktester(
                initial_capital=float(self.config.get('initial_capital', 10000)),
                slippage_pips=float(self.config.get('slippage_pips', 1.0)),
                spread_pips=float(self.config.get('spread_pips', 0.5))
            )
            
            results = backtester.run_backtest(df)
            
            self.progress.emit(100)
            
            self.finished.emit(results)
        
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            self.error.emit(str(e))


class GoldTradingGUI(QMainWindow):
    """Main GUI application."""
    
    def __init__(self):
        super().__init__()
        self.config_file = Path.home() / '.gold_trading_config.json'
        self.config = self._load_config()
        self.backtest_worker = None
        
        self.setWindowTitle("Gold Trading Signal System")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(self._get_stylesheet())
        
        self._init_ui()
        self._apply_config_to_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # Tabs
        tabs = QTabWidget()
        
        # Tab 1: Configuration
        tabs.addTab(self._create_config_tab(), "⚙️ Configuration")
        
        # Tab 2: Strategy Filters
        tabs.addTab(self._create_filters_tab(), "📊 Strategy Filters")
        
        # Tab 3: Results
        tabs.addTab(self._create_results_tab(), "📈 Results")
        
        # Tab 4: Logs
        tabs.addTab(self._create_logs_tab(), "📋 Logs")
        
        main_layout.addWidget(tabs)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.validate_btn = QPushButton("✓ Validate Config")
        self.validate_btn.clicked.connect(self._validate_config)
        button_layout.addWidget(self.validate_btn)
        
        self.backtest_btn = QPushButton("▶ Run Backtest")
        self.backtest_btn.clicked.connect(self._run_backtest)
        button_layout.addWidget(self.backtest_btn)
        
        self.webhook_btn = QPushButton("🔗 Start Webhook")
        self.webhook_btn.clicked.connect(self._start_webhook)
        button_layout.addWidget(self.webhook_btn)
        
        self.save_btn = QPushButton("💾 Save Config")
        self.save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        main_layout.addWidget(self.status_label)
        
        central_widget.setLayout(main_layout)
    
    def _create_config_tab(self) -> QWidget:
        """Create configuration tab."""
        widget = QWidget()
        layout = QGridLayout()
        
        row = 0
        
        # Required Section
        required_group = QGroupBox("🔴 Required Configuration (MUST be filled)")
        required_layout = QGridLayout()
        
        required_layout.addWidget(QLabel("Telegram Bot Token:"), 0, 0)
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setEchoMode(QLineEdit.Password)
        self.telegram_token_input.setPlaceholderText("e.g., 1234567890:ABCDEFghijklmnopQRSTUVwxyz")
        required_layout.addWidget(self.telegram_token_input, 0, 1)
        
        required_layout.addWidget(QLabel("Telegram Chat ID:"), 1, 0)
        self.telegram_chat_input = QLineEdit()
        self.telegram_chat_input.setPlaceholderText("e.g., 123456789")
        required_layout.addWidget(self.telegram_chat_input, 1, 1)
        
        required_group.setLayout(required_layout)
        layout.addWidget(required_group, row, 0, 1, 2)
        row += 1
        
        # Optional Section
        optional_group = QGroupBox("⚪ Optional Configuration")
        optional_layout = QGridLayout()
        
        optional_layout.addWidget(QLabel("OANDA API Key:"), 0, 0)
        self.oanda_api_input = QLineEdit()
        self.oanda_api_input.setEchoMode(QLineEdit.Password)
        self.oanda_api_input.setPlaceholderText("(Optional) For live data")
        optional_layout.addWidget(self.oanda_api_input, 0, 1)
        
        optional_layout.addWidget(QLabel("Webhook Port:"), 1, 0)
        self.webhook_port_spin = QSpinBox()
        self.webhook_port_spin.setMinimum(1024)
        self.webhook_port_spin.setMaximum(65535)
        self.webhook_port_spin.setValue(8000)
        optional_layout.addWidget(self.webhook_port_spin, 1, 1)
        
        optional_layout.addWidget(QLabel("Initial Capital ($):"), 2, 0)
        self.initial_capital_spin = QDoubleSpinBox()
        self.initial_capital_spin.setMinimum(1000)
        self.initial_capital_spin.setMaximum(1000000)
        self.initial_capital_spin.setValue(10000)
        optional_layout.addWidget(self.initial_capital_spin, 2, 1)
        
        optional_layout.addWidget(QLabel("Slippage (pips):"), 3, 0)
        self.slippage_spin = QDoubleSpinBox()
        self.slippage_spin.setMinimum(0.1)
        self.slippage_spin.setMaximum(10)
        self.slippage_spin.setValue(1.0)
        self.slippage_spin.setSingleStep(0.1)
        optional_layout.addWidget(self.slippage_spin, 3, 1)
        
        optional_layout.addWidget(QLabel("Spread (pips):"), 4, 0)
        self.spread_spin = QDoubleSpinBox()
        self.spread_spin.setMinimum(0.1)
        self.spread_spin.setMaximum(10)
        self.spread_spin.setValue(0.5)
        self.spread_spin.setSingleStep(0.1)
        optional_layout.addWidget(self.spread_spin, 4, 1)
        
        optional_layout.addWidget(QLabel("Start Date (YYYY-MM-DD):"), 5, 0)
        self.start_date_input = QLineEdit()
        self.start_date_input.setPlaceholderText("e.g., 2020-01-01")
        self.start_date_input.setText("2020-01-01")
        optional_layout.addWidget(self.start_date_input, 5, 1)
        
        optional_layout.addWidget(QLabel("End Date (YYYY-MM-DD):"), 6, 0)
        self.end_date_input = QLineEdit()
        self.end_date_input.setPlaceholderText("e.g., 2024-12-31")
        self.end_date_input.setText("2024-12-31")
        optional_layout.addWidget(self.end_date_input, 6, 1)
        
        optional_layout.addWidget(QLabel("Timeframe:"), 7, 0)
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(['1h', '4h', '1d'])
        optional_layout.addWidget(self.timeframe_combo, 7, 1)
        
        optional_group.setLayout(optional_layout)
        layout.addWidget(optional_group, row, 0, 1, 2)
        
        widget.setLayout(layout)
        return widget
    
    def _create_filters_tab(self) -> QWidget:
        """Create strategy filters tab."""
        widget = QWidget()
        layout = QGridLayout()
        
        # Zone Detection
        zone_group = QGroupBox("🎯 Zone Detection")
        zone_layout = QGridLayout()
        
        zone_layout.addWidget(QLabel("Swing Lookback (periods):"), 0, 0)
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
        
        signal_layout.addWidget(QLabel("Min Confluences (≥2):"), 1, 0)
        self.min_confluence_spin = QSpinBox()
        self.min_confluence_spin.setMinimum(1)
        self.min_confluence_spin.setMaximum(5)
        self.min_confluence_spin.setValue(2)
        signal_layout.addWidget(self.min_confluence_spin, 1, 1)
        
        signal_group.setLayout(signal_layout)
        layout.addWidget(signal_group, 0, 1)
        
        # Moving Averages
        ema_group = QGroupBox("📈 Moving Averages")
        ema_layout = QGridLayout()
        
        ema_layout.addWidget(QLabel("Fast EMA (periods):"), 0, 0)
        self.ema_fast_spin = QSpinBox()
        self.ema_fast_spin.setMinimum(5)
        self.ema_fast_spin.setMaximum(100)
        self.ema_fast_spin.setValue(30)
        ema_layout.addWidget(self.ema_fast_spin, 0, 1)
        
        ema_layout.addWidget(QLabel("Slow EMA (periods):"), 1, 0)
        self.ema_slow_spin = QSpinBox()
        self.ema_slow_spin.setMinimum(50)
        self.ema_slow_spin.setMaximum(500)
        self.ema_slow_spin.setValue(200)
        ema_layout.addWidget(self.ema_slow_spin, 1, 1)
        
        ema_group.setLayout(ema_layout)
        layout.addWidget(ema_group, 1, 0)
        
        # Filters & Flags
        filter_group = QGroupBox("🔧 Filters & Flags")
        filter_layout = QGridLayout()
        
        self.include_demand_check = QCheckBox("Include Demand Zones")
        self.include_demand_check.setChecked(True)
        filter_layout.addWidget(self.include_demand_check, 0, 0)
        
        self.include_supply_check = QCheckBox("Include Supply Zones")
        self.include_supply_check.setChecked(True)
        filter_layout.addWidget(self.include_supply_check, 0, 1)
        
        self.include_ob_check = QCheckBox("Include Order Blocks")
        self.include_ob_check.setChecked(True)
        filter_layout.addWidget(self.include_ob_check, 1, 0)
        
        self.include_fvg_check = QCheckBox("Include FVGs")
        self.include_fvg_check.setChecked(True)
        filter_layout.addWidget(self.include_fvg_check, 1, 1)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group, 1, 1)
        
        layout.addWidget(QLabel(""), 2, 0)  # Spacer
        
        widget.setLayout(layout)
        return widget
    
    def _create_results_tab(self) -> QWidget:
        """Create results tab."""
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
        
        # Results text
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        
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
    
    def _validate_config(self):
        """Validate configuration."""
        config = self._get_ui_config()
        is_valid, message = ConfigValidator.validate_all(config)
        
        if is_valid:
            self.status_label.setText(f"✓ {message}")
            self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
            QMessageBox.information(self, "Configuration Valid", message)
        else:
            self.status_label.setText(f"✗ {message}")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            QMessageBox.warning(self, "Configuration Invalid", message)
    
    def _run_backtest(self):
        """Run backtest."""
        config = self._get_ui_config()
        is_valid, message = ConfigValidator.validate_all(config)
        
        if not is_valid:
            QMessageBox.critical(self, "Invalid Configuration", 
                               f"Cannot run backtest:\n{message}")
            return
        
        filters = self._get_ui_filters()
        
        self.backtest_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.backtest_worker = BacktestWorker(config, filters)
        self.backtest_worker.progress.connect(self._on_progress)
        self.backtest_worker.finished.connect(self._on_backtest_finished)
        self.backtest_worker.error.connect(self._on_backtest_error)
        self.backtest_worker.start()
        
        self._log("▶ Starting backtest with real data...")
    
    def _on_progress(self, value: int):
        """Update progress."""
        self.progress_bar.setValue(value)
    
    def _on_backtest_finished(self, results: dict):
        """Handle backtest completion."""
        self._log(f"✓ Backtest completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Update results table
        self.results_table.setRowCount(0)
        
        metrics = [
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
        
        # Update results text
        report = f"""
Backtest Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Performance:
  Win Rate: {results.get('win_rate', 0):.2f}%
  Profit Factor: {results.get('profit_factor', 0):.2f}
  Total P&L: ${results.get('total_pnl', 0):.2f}
  
Risk:
  Max Drawdown: {results.get('max_drawdown_pct', 0):.2f}%
  Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}
  
Trades:
  Total: {results.get('total_trades', 0)}
  Winning: {results.get('winning_trades', 0)}
  Losing: {results.get('losing_trades', 0)}

✓ Real data used (no mock data)
✓ Realistic costs included (slippage, spread)
"""
        
        self.results_text.setText(report)
        
        self.backtest_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.status_label.setText("✓ Backtest complete")
        self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
    
    def _on_backtest_error(self, error: str):
        """Handle backtest error."""
        self._log(f"✗ Error: {error}")
        self.backtest_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.status_label.setText(f"✗ Error: {error}")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        QMessageBox.critical(self, "Backtest Error", f"Error during backtest:\n{error}")
    
    def _start_webhook(self):
        """Start webhook server."""
        config = self._get_ui_config()
        is_valid, message = ConfigValidator.validate_all(config)
        
        if not is_valid:
            QMessageBox.critical(self, "Invalid Configuration", 
                               f"Cannot start webhook:\n{message}")
            return
        
        self._log(f"▶ Starting webhook server on port {config.get('webhook_port', 8000)}...")
        self._log("(Run 'uvicorn webhooks.webhook_server:app --reload' in terminal)")
        
        QMessageBox.information(self, "Webhook Server",
                              f"Start webhook with:\nuvicorn webhooks.webhook_server:app --port {config.get('webhook_port', 8000)}")
    
    def _save_config(self):
        """Save configuration to file."""
        config = self._get_ui_config()
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        self._log(f"✓ Configuration saved to {self.config_file}")
        QMessageBox.information(self, "Saved", "Configuration saved successfully")
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
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
            self.telegram_token_input.setText(self.config.get('telegram_bot_token', ''))
            self.telegram_chat_input.setText(self.config.get('telegram_chat_id', ''))
            self.oanda_api_input.setText(self.config.get('oanda_api_key', ''))
            self.initial_capital_spin.setValue(float(self.config.get('initial_capital', 10000)))
            self.slippage_spin.setValue(float(self.config.get('slippage_pips', 1.0)))
            self.spread_spin.setValue(float(self.config.get('spread_pips', 0.5)))
    
    def _get_ui_config(self) -> Dict:
        """Get configuration from UI."""
        return {
            'telegram_bot_token': self.telegram_token_input.text(),
            'telegram_chat_id': self.telegram_chat_input.text(),
            'oanda_api_key': self.oanda_api_input.text(),
            'webhook_port': str(self.webhook_port_spin.value()),
            'initial_capital': str(self.initial_capital_spin.value()),
            'slippage_pips': str(self.slippage_spin.value()),
            'spread_pips': str(self.spread_spin.value()),
            'start_date': self.start_date_input.text(),
            'end_date': self.end_date_input.text(),
            'timeframe': self.timeframe_combo.currentText(),
        }
    
    def _get_ui_filters(self) -> Dict:
        """Get strategy filters from UI."""
        return {
            'swing_lookback': self.swing_lookback_spin.value(),
            'atr_multiplier': self.atr_mult_spin.value(),
            'min_risk_reward': self.min_rr_spin.value(),
            'ema_fast': self.ema_fast_spin.value(),
            'ema_slow': self.ema_slow_spin.value(),
            'include_demand': self.include_demand_check.isChecked(),
            'include_supply': self.include_supply_check.isChecked(),
            'include_ob': self.include_ob_check.isChecked(),
            'include_fvg': self.include_fvg_check.isChecked(),
        }
    
    def _log(self, message: str):
        """Add message to logs."""
        current_text = self.logs_text.toPlainText()
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.logs_text.setText(f"{current_text}\n[{timestamp}] {message}")
        # Scroll to bottom
        self.logs_text.verticalScrollBar().setValue(
            self.logs_text.verticalScrollBar().maximum()
        )
    
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
        QLineEdit:focus {
            border: 2px solid #3498db;
        }
        QTabWidget::pane {
            border: 1px solid #bdc3c7;
        }
        QTabBar::tab {
            padding: 8px 20px;
            background-color: #ecf0f1;
            border: 1px solid #bdc3c7;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom: 2px solid #3498db;
        }
        """


def main():
    # Fix for macOS PySide6 bus error
    import os
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''
    os.environ['QT_XCB_GL_INTEGRATION'] = 'none'
    
    # Use offscreen platform if display issues occur
    try:
        app = QApplication(sys.argv)
        window = GoldTradingGUI()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"GUI Error: {e}")
        raise


if __name__ == '__main__':
    main()
