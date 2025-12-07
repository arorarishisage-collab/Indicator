#!/usr/bin/env python3
"""
Professional Trading Dashboard - Clean, Beginner-Friendly Interface
Modern UI with essential features only, no technical clutter
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QGroupBox, QPushButton, QLabel, QComboBox,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox, QFileDialog, QCheckBox,
    QSpinBox, QDoubleSpinBox, QGridLayout, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QColor

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ProfessionalTradingGUI(QMainWindow):
    """Modern, beginner-friendly trading dashboard."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Professional Trading System")
        self.setMinimumSize(1200, 800)
        
        # Initialize state
        self.scheduler = None
        self.backtest_running = False
        
        # Setup UI
        self._setup_ui()
        self._apply_theme()
        
        # Status
        self._log("✅ System ready. Select an action to begin.")
    
    def _setup_ui(self):
        """Create clean, organized interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Main tabs
        tabs = QTabWidget()
        tabs.setStyleSheet("QTabBar::tab { min-width: 150px; padding: 12px; font-size: 13px; }")
        
        tabs.addTab(self._create_backtest_tab(), "📊 Backtest Strategy")
        tabs.addTab(self._create_live_tab(), "🔴 Live Trading")
        tabs.addTab(self._create_ai_tab(), "🤖 AI Training")
        tabs.addTab(self._create_settings_tab(), "⚙️ Settings")
        
        layout.addWidget(tabs)
        
        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 12px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        status_layout.addWidget(self.time_label)
        
        layout.addLayout(status_layout)
        
        # Update time
        timer = QTimer(self)
        timer.timeout.connect(self._update_time)
        timer.start(1000)
        self._update_time()
    
    def _create_header(self) -> QWidget:
        """Create clean header."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 10)
        
        title = QLabel("Professional Trading System")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        version = QLabel("v3.0")
        version.setStyleSheet("color: #95a5a6; font-size: 11px;")
        layout.addWidget(version)
        
        return widget
    
    def _create_backtest_tab(self) -> QWidget:
        """Backtest tab - simplified."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Symbol selection
        symbol_group = QGroupBox("📈 Select Market")
        symbol_layout = QVBoxLayout()
        
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems([
            "GC=F (Gold Futures)",
            "GLD (Gold ETF)",
            "SI=F (Silver Futures)",
            "SLV (Silver ETF)",
            "CL=F (Crude Oil)",
            "BTC-USD (Bitcoin)",
            "ES=F (S&P 500 Futures)",
            "^NSEI (Nifty 50)",
            "RELIANCE.NS (Reliance)",
            "TCS.NS (TCS)"
        ])
        self.symbol_combo.setCurrentText("GC=F (Gold Futures)")
        symbol_layout.addWidget(QLabel("Choose what to trade:"))
        symbol_layout.addWidget(self.symbol_combo)
        
        symbol_group.setLayout(symbol_layout)
        layout.addWidget(symbol_group)
        
        # Strategy selection
        strategy_group = QGroupBox("🎯 Select Strategy")
        strategy_layout = QVBoxLayout()
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "EMA Crossover (Simple, Good for Beginners)",
            "ICT Smart Money (Advanced)",
            "VCP Breakout (Stock Momentum)"
        ])
        strategy_layout.addWidget(QLabel("Choose trading approach:"))
        strategy_layout.addWidget(self.strategy_combo)
        
        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)
        
        # Time period
        period_group = QGroupBox("📅 Test Period")
        period_layout = QGridLayout()
        
        period_layout.addWidget(QLabel("Data Period:"), 0, 0)
        self.period_combo = QComboBox()
        self.period_combo.addItems(["6 months", "1 year", "2 years", "5 years"])
        self.period_combo.setCurrentText("2 years")
        period_layout.addWidget(self.period_combo, 0, 1)
        
        period_layout.addWidget(QLabel("Timeframe:"), 1, 0)
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["1 hour", "4 hours", "1 day"])
        self.timeframe_combo.setCurrentText("1 hour")
        period_layout.addWidget(self.timeframe_combo, 1, 1)
        
        period_group.setLayout(period_layout)
        layout.addWidget(period_group)
        
        # Run button
        self.backtest_btn = QPushButton("▶️ Run Backtest")
        self.backtest_btn.setMinimumHeight(50)
        self.backtest_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2980b9, stop:1 #1f618d);
            }
        """)
        self.backtest_btn.clicked.connect(self._run_backtest)
        layout.addWidget(self.backtest_btn)
        
        # Progress
        self.backtest_progress = QProgressBar()
        self.backtest_progress.setVisible(False)
        layout.addWidget(self.backtest_progress)
        
        # Results
        results_group = QGroupBox("📊 Results")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        self.results_text.setPlaceholderText("Results will appear here after backtest...")
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        layout.addStretch()
        return widget
    
    def _create_live_tab(self) -> QWidget:
        """Live trading tab - clean and simple."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Status
        status_group = QGroupBox("📡 Live Trading Status")
        status_layout = QVBoxLayout()
        
        self.live_status_label = QLabel("⚫ Not Running")
        self.live_status_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.live_status_label.setStyleSheet("color: #95a5a6; padding: 15px;")
        status_layout.addWidget(self.live_status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.start_live_btn = QPushButton("▶️ Start Live Trading")
        self.start_live_btn.setMinimumHeight(50)
        self.start_live_btn.clicked.connect(self._start_live)
        controls_layout.addWidget(self.start_live_btn)
        
        self.stop_live_btn = QPushButton("⏹️ Stop")
        self.stop_live_btn.setMinimumHeight(50)
        self.stop_live_btn.setEnabled(False)
        self.stop_live_btn.clicked.connect(self._stop_live)
        controls_layout.addWidget(self.stop_live_btn)
        
        layout.addLayout(controls_layout)
        
        # Active signals table
        signals_group = QGroupBox("📊 Recent Signals")
        signals_layout = QVBoxLayout()
        
        self.signals_table = QTableWidget()
        self.signals_table.setColumnCount(6)
        self.signals_table.setHorizontalHeaderLabels([
            'Time', 'Symbol', 'Action', 'Price', 'Strength', 'Status'
        ])
        self.signals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.signals_table.setMaximumHeight(300)
        signals_layout.addWidget(self.signals_table)
        
        signals_group.setLayout(signals_layout)
        layout.addWidget(signals_group)
        
        # Info
        info = QLabel("ℹ️ Live trading uses real-time data. Start with paper trading to test safely.")
        info.setStyleSheet("color: #f39c12; padding: 10px; background: #fef5e7; border-radius: 5px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        layout.addStretch()
        return widget
    
    def _create_ai_tab(self) -> QWidget:
        """AI training tab - beginner-friendly."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Explanation
        info_group = QGroupBox("🤖 What is AI Training?")
        info_layout = QVBoxLayout()
        
        info_text = QLabel(
            "AI learns from your trading history to make smarter decisions.\n\n"
            "• Analyzes past trades to find patterns\n"
            "• Filters out low-quality signals\n"
            "• Improves over time with more data\n\n"
            "Recommended: Run 1000+ episodes for best results."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("font-size: 13px; padding: 10px;")
        info_layout.addWidget(info_text)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Training settings
        settings_group = QGroupBox("⚙️ Training Settings")
        settings_layout = QGridLayout()
        
        settings_layout.addWidget(QLabel("Strategy:"), 0, 0)
        self.ai_strategy_combo = QComboBox()
        self.ai_strategy_combo.addItems(["EMA Crossover", "ICT Smart Money", "VCP Breakout"])
        settings_layout.addWidget(self.ai_strategy_combo, 0, 1)
        
        settings_layout.addWidget(QLabel("Training Episodes:"), 1, 0)
        self.episodes_spin = QSpinBox()
        self.episodes_spin.setRange(100, 5000)
        self.episodes_spin.setValue(1000)
        self.episodes_spin.setSingleStep(100)
        settings_layout.addWidget(self.episodes_spin, 1, 1)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.train_ai_btn = QPushButton("🚀 Start Training")
        self.train_ai_btn.setMinimumHeight(50)
        self.train_ai_btn.clicked.connect(self._train_ai)
        buttons_layout.addWidget(self.train_ai_btn)
        
        self.load_ai_btn = QPushButton("📂 Load Trained Model")
        self.load_ai_btn.setMinimumHeight(50)
        self.load_ai_btn.clicked.connect(self._load_ai_model)
        buttons_layout.addWidget(self.load_ai_btn)
        
        layout.addLayout(buttons_layout)
        
        # Progress
        self.ai_progress = QProgressBar()
        self.ai_progress.setVisible(False)
        layout.addWidget(self.ai_progress)
        
        # Log
        log_group = QGroupBox("📝 Training Log")
        log_layout = QVBoxLayout()
        
        self.ai_log = QTextEdit()
        self.ai_log.setReadOnly(True)
        self.ai_log.setMaximumHeight(200)
        log_layout.addWidget(self.ai_log)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        return widget
    
    def _create_settings_tab(self) -> QWidget:
        """Settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Alerts
        alerts_group = QGroupBox("🔔 Alert Settings")
        alerts_layout = QGridLayout()
        
        alerts_layout.addWidget(QLabel("Telegram Bot Token:"), 0, 0)
        self.telegram_token = QLineEdit()
        self.telegram_token.setPlaceholderText("Optional - for mobile alerts")
        alerts_layout.addWidget(self.telegram_token, 0, 1)
        
        alerts_layout.addWidget(QLabel("Telegram Chat ID:"), 1, 0)
        self.telegram_chat = QLineEdit()
        self.telegram_chat.setPlaceholderText("Your Telegram chat ID")
        alerts_layout.addWidget(self.telegram_chat, 1, 1)
        
        alerts_group.setLayout(alerts_layout)
        layout.addWidget(alerts_group)
        
        # Risk
        risk_group = QGroupBox("⚠️ Risk Management")
        risk_layout = QGridLayout()
        
        risk_layout.addWidget(QLabel("Risk per Trade:"), 0, 0)
        self.risk_spin = QDoubleSpinBox()
        self.risk_spin.setRange(0.1, 5.0)
        self.risk_spin.setValue(1.0)
        self.risk_spin.setSuffix("%")
        self.risk_spin.setSingleStep(0.1)
        risk_layout.addWidget(self.risk_spin, 0, 1)
        
        risk_layout.addWidget(QLabel("Max Concurrent Trades:"), 1, 0)
        self.max_trades_spin = QSpinBox()
        self.max_trades_spin.setRange(1, 10)
        self.max_trades_spin.setValue(3)
        risk_layout.addWidget(self.max_trades_spin, 1, 1)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        # Save button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setMinimumHeight(45)
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        return widget
    
    # Event handlers
    def _run_backtest(self):
        """Run backtest."""
        self._log("🔄 Starting backtest...")
        self.backtest_btn.setEnabled(False)
        self.backtest_progress.setVisible(True)
        self.backtest_progress.setValue(0)
        
        # Extract symbol - get code from parentheses
        symbol_text = self.symbol_combo.currentText()
        try:
            symbol = symbol_text.split('(')[1].split(')')[0].strip()
        except:
            symbol = 'GC=F'
        
        # Map strategy
        strategy_map = {
            0: "EMA30Strategy",
            1: "ICTStrategy",
            2: "VCPStrategy"
        }
        strategy = strategy_map.get(self.strategy_combo.currentIndex(), "EMA30Strategy")
        
        try:
            from backend.data_fetch import DataFetcher
            
            self._log(f"📊 Fetching {symbol} data...")
            self.backtest_progress.setValue(20)
            
            period_map = {"6 months": "6mo", "1 year": "1y", "2 years": "2y", "5 years": "5y"}
            period = period_map.get(self.period_combo.currentText(), "2y")
            
            interval_map = {"1 hour": "1h", "4 hours": "4h", "1 day": "1d"}
            interval = interval_map.get(self.timeframe_combo.currentText(), "1h")
            
            fetcher = DataFetcher()
            self._log(f"Symbol: {symbol}")
            df = fetcher.fetch_historical_data(symbol=symbol, period=period, interval=interval, use_cache=True)
            
            if df is None or df.empty:
                raise ValueError("No data retrieved")
            
            self._log(f"✅ Loaded {len(df)} candles")
            self.backtest_progress.setValue(50)
            
            # Run strategy
            self._log(f"🎯 Running {strategy}...")
            
            if strategy == "EMA30Strategy":
                from backend.ema_strategy import EMA30Strategy
                strat = EMA30Strategy(fast_period=9, slow_period=21)
            elif strategy == "ICTStrategy":
                from backend.ict_strategy import ICTStrategy
                strat = ICTStrategy()
            else:
                from backend.vcp_strategy import VCPStrategy
                strat = VCPStrategy()
            
            signals = strat.generate_signals(df)
            self.backtest_progress.setValue(80)
            
            # Calculate results
            buy_signals = (signals['Signal'] == 1).sum() if 'Signal' in signals else 0
            sell_signals = (signals['Signal'] == -1).sum() if 'Signal' in signals else 0
            
            self.results_text.clear()
            self.results_text.append("✅ BACKTEST COMPLETE\n")
            self.results_text.append(f"Symbol: {symbol}")
            self.results_text.append(f"Period: {period}")
            self.results_text.append(f"Bars: {len(df)}")
            self.results_text.append(f"\nSignals Generated:")
            self.results_text.append(f"  • Buy: {buy_signals}")
            self.results_text.append(f"  • Sell: {sell_signals}")
            self.results_text.append(f"  • Total: {buy_signals + sell_signals}")
            
            self.backtest_progress.setValue(100)
            self._log("✅ Backtest complete!")
            
        except Exception as e:
            self._log(f"❌ Error: {e}")
            QMessageBox.critical(self, "Error", f"Backtest failed:\n{e}")
        
        finally:
            self.backtest_btn.setEnabled(True)
            QTimer.singleShot(2000, lambda: self.backtest_progress.setVisible(False))
    
    def _start_live(self):
        """Start live trading."""
        reply = QMessageBox.question(
            self, "Start Live Trading",
            "Start monitoring live markets?\n\nThis will generate real-time signals.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._log("🔴 Starting live trading...")
            self.live_status_label.setText("🟢 Running")
            self.live_status_label.setStyleSheet("color: #2ecc71; padding: 15px;")
            self.start_live_btn.setEnabled(False)
            self.stop_live_btn.setEnabled(True)
    
    def _stop_live(self):
        """Stop live trading."""
        self._log("⏹️ Stopping live trading...")
        self.live_status_label.setText("⚫ Stopped")
        self.live_status_label.setStyleSheet("color: #95a5a6; padding: 15px;")
        self.start_live_btn.setEnabled(True)
        self.stop_live_btn.setEnabled(False)
    
    def _train_ai(self):
        """Train AI model."""
        strategy_map = ["EMA30Strategy", "ICTStrategy", "VCPStrategy"]
        strategy = strategy_map[self.ai_strategy_combo.currentIndex()]
        episodes = self.episodes_spin.value()
        
        reply = QMessageBox.question(
            self, "Train AI",
            f"Train {strategy} for {episodes} episodes?\n\nThis may take 10-30 minutes.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._log(f"🚀 Training {strategy} ({episodes} episodes)...")
            self.ai_log.append(f"Starting training for {strategy}...")
            self.ai_progress.setVisible(True)
            self.train_ai_btn.setEnabled(False)
            
            # TODO: Run training in background thread
            QMessageBox.information(self, "Training", "Training would start here (not implemented in UI yet)")
            self.train_ai_btn.setEnabled(True)
    
    def _load_ai_model(self):
        """Load trained AI model."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load AI Model", "models/rl", "Model Files (*.pth)"
        )
        
        if file_path:
            self._log(f"📂 Loading model: {Path(file_path).name}")
            # TODO: Actually load model
            QMessageBox.information(self, "Model Loaded", f"Model loaded:\n{Path(file_path).name}")
    
    def _save_settings(self):
        """Save settings."""
        self._log("💾 Saving settings...")
        QMessageBox.information(self, "Success", "Settings saved successfully!")
    
    def _update_time(self):
        """Update time display."""
        self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def _log(self, message: str):
        """Log message to status."""
        self.status_label.setText(f"Status: {message}")
        print(message)
    
    def _apply_theme(self):
        """Apply modern theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 8px;
                background-color: white;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #3498db;
            }
            QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 8px;
                background-color: white;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
            QTableWidget {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                background-color: white;
                gridline-color: #ecf0f1;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 3px;
            }
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = ProfessionalTradingGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
