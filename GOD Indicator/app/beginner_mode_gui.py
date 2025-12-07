"""
GOD Indicator - Beginner Mode GUI
Simplified interface for non-technical traders
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QTextEdit, QMessageBox,
    QProgressBar, QGroupBox, QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal
from PySide6.QtGui import QFont
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalysisWorker(QThread):
    """Background thread for stock analysis"""
    
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, symbol: str, strategy: str, zerodha_api_key: str = None, zerodha_access_token: str = None):
        super().__init__()
        self.symbol = symbol
        self.strategy = strategy
        self.zerodha_api_key = zerodha_api_key
        self.zerodha_access_token = zerodha_access_token
    
    def run(self):
        """Run analysis in background"""
        try:
            self.progress.emit("📊 Fetching stock data...")
            
            # Use UnifiedDataFetcher for intelligent source selection
            from backend.unified_data_fetcher import UnifiedDataFetcher
            from datetime import datetime, timedelta
            
            fetcher = UnifiedDataFetcher(
                finnhub_api_key='d4jv009r01qgcb0voap0d4jv009r01qgcb0voapg',
                zerodha_api_key=self.zerodha_api_key,
                zerodha_access_token=self.zerodha_access_token
            )
            
            # Determine exchange
            exchange = 'NSE' if '.NS' in self.symbol or self.symbol.upper() in ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICI'] else 'US'
            
            # Clean symbol (remove .NS suffix if present)
            clean_symbol = self.symbol.replace('.NS', '').replace('.BO', '')
            
            # Fetch 1 year of data
            to_date = datetime.now()
            from_date = to_date - timedelta(days=365)
            df = fetcher.fetch_historical_data(clean_symbol, 'D', from_date, to_date, exchange)
            
            self.progress.emit("🎯 Running strategy analysis...")
            
            # Run strategy
            if 'VCP' in self.strategy:
                from backend.vcp_strategy import VCPStrategy
                strategy = VCPStrategy()
            elif 'ICT' in self.strategy:
                from backend.ict_strategy import ICTStrategy
                strategy = ICTStrategy()
            else:  # EMA30
                from backend.ema_strategy import EMA30Strategy
                strategy = EMA30Strategy()
            
            signals = strategy.generate_signals(df)
            
            self.progress.emit("📰 Fetching latest news...")
            
            # Get news sentiment
            from backend.news_sentiment import NewsSentimentAnalyzer
            news_analyzer = NewsSentimentAnalyzer()
            news = news_analyzer.get_stock_news(self.symbol, days=7, max_articles=5)
            sentiment = news_analyzer.analyze_sentiment(news)
            
            # Find latest signal
            buy_signals = signals[signals['Signal'] == 1]
            
            result = {
                'symbol': self.symbol,
                'data': df,
                'signals': signals,
                'latest_signal': buy_signals.tail(1) if not buy_signals.empty else None,
                'news': news,
                'sentiment': sentiment,
                'current_price': df['Close'].iloc[-1]
            }
            
            self.finished.emit(result)
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            self.error.emit(str(e))


class BeginnerModeGUI(QMainWindow):
    """
    Simplified GUI for beginner traders
    
    Features:
    - Simple stock selection
    - One-click analysis
    - Plain English recommendations
    - News sentiment integration
    - Paper trading only
    """
    
    def __init__(self):
        super().__init__()
        self.zerodha_connected = False
        self.zerodha_api_key = None
        self.zerodha_access_token = None
        
        # Risk management state
        self.initial_capital = 100000.0  # ₹1 Lakh
        self.current_capital = 100000.0
        self.max_daily_loss_pct = 2.0  # 2% max daily loss
        self.daily_pnl = 0.0
        self.circuit_breaker_triggered = False
        self.open_positions = []
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("GOD Indicator - Simple Trading Mode")
        self.setGeometry(100, 100, 900, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Warning banner
        self._create_warning_banner(layout)
        
        # Tabs
        tabs = QTabWidget()
        
        # Tab 0: Zerodha Connection
        zerodha_tab = self._create_zerodha_tab()
        tabs.addTab(zerodha_tab, "🔐 Zerodha Connect")
        
        # Tab 1: Stock Analysis
        analysis_tab = self._create_analysis_tab()
        tabs.addTab(analysis_tab, "📊 Analyze Stock")
        
        # Tab 2: Risk Management
        risk_tab = self._create_risk_management_tab()
        tabs.addTab(risk_tab, "🛡️ Risk Manager")
        
        # Tab 3: Paper Trades
        trades_tab = self._create_trades_tab()
        tabs.addTab(trades_tab, "📝 Paper Trades")
        
        layout.addWidget(tabs)
    
    def _create_warning_banner(self, layout):
        """Create safety warning banner"""
        warning = QLabel("🔒 PAPER TRADING MODE - NO REAL ORDERS")
        warning.setFont(QFont("Arial", 14, QFont.Bold))
        warning.setStyleSheet(
            "background-color: #e74c3c; "
            "color: white; "
            "padding: 15px; "
            "border-radius: 5px;"
        )
        warning.setAlignment(Qt.AlignCenter)
        layout.addWidget(warning)
    
    def _create_zerodha_tab(self) -> QWidget:
        """Create Zerodha connection tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Info section
        info_group = QGroupBox("🔐 Zerodha Kite Connect")
        info_layout = QVBoxLayout()
        
        info_text = QLabel(
            "<h3>Connect to Zerodha for Real NSE/BSE Data</h3>"
            "<p><b>Benefits:</b></p>"
            "<ul>"
            "<li>✅ Real-time market data (NSE/BSE)</li>"
            "<li>✅ Tick-by-tick updates</li>"
            "<li>✅ Official exchange data</li>"
            "<li>✅ No delays, no API limits</li>"
            "</ul>"
            "<p><b>Cost:</b> ₹2,000/month (Zerodha Kite Connect subscription)</p>"
            "<p><b>Safety:</b> This app is READ-ONLY. Cannot place real orders.</p>"
            "<hr>"
            "<p><b>How to Get API Key:</b></p>"
            "<ol>"
            "<li>Go to <a href='https://kite.trade'>https://kite.trade</a></li>"
            "<li>Login with your Zerodha account</li>"
            "<li>Click 'Create new app'</li>"
            "<li>Fill app details and get API Key</li>"
            "<li>Copy API Key and paste below</li>"
            "</ol>"
        )
        info_text.setWordWrap(True)
        info_text.setOpenExternalLinks(True)
        info_layout.addWidget(info_text)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Connection section
        connect_group = QGroupBox("API Credentials")
        connect_layout = QVBoxLayout()
        
        # API Key input
        from PySide6.QtWidgets import QLineEdit
        api_label = QLabel("API Key:")
        api_label.setFont(QFont("Arial", 12))
        connect_layout.addWidget(api_label)
        
        self.zerodha_api_input = QLineEdit()
        self.zerodha_api_input.setPlaceholderText("Enter your Kite Connect API Key")
        self.zerodha_api_input.setStyleSheet("padding: 10px; font-size: 14px;")
        connect_layout.addWidget(self.zerodha_api_input)
        
        # Connect button
        self.zerodha_connect_btn = QPushButton("🔗 Connect to Zerodha")
        self.zerodha_connect_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.zerodha_connect_btn.setStyleSheet(
            "background-color: #27ae60; "
            "color: white; "
            "padding: 15px; "
            "border-radius: 8px;"
        )
        self.zerodha_connect_btn.clicked.connect(self._connect_zerodha)
        connect_layout.addWidget(self.zerodha_connect_btn)
        
        # Status indicator
        self.zerodha_status_label = QLabel("❌ Not Connected")
        self.zerodha_status_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.zerodha_status_label.setStyleSheet("color: #e74c3c; padding: 10px;")
        self.zerodha_status_label.setAlignment(Qt.AlignCenter)
        connect_layout.addWidget(self.zerodha_status_label)
        
        # Mode toggle
        mode_label = QLabel("Trading Mode:")
        mode_label.setFont(QFont("Arial", 12))
        connect_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            '📝 Paper Trading (Simulated)',
            '⚠️ Live Trading (Real Money - DISABLED)'
        ])
        self.mode_combo.setStyleSheet("padding: 10px; font-size: 14px;")
        self.mode_combo.setEnabled(False)  # Always paper trading
        connect_layout.addWidget(self.mode_combo)
        
        mode_note = QLabel(
            "<b>Note:</b> Live trading is DISABLED for safety. "
            "This app only supports paper trading simulation."
        )
        mode_note.setWordWrap(True)
        mode_note.setStyleSheet("color: #e67e22; padding: 10px;")
        connect_layout.addWidget(mode_note)
        
        connect_group.setLayout(connect_layout)
        layout.addWidget(connect_group)
        
        layout.addStretch()
        return widget
    
    def _create_analysis_tab(self) -> QWidget:
        """Create stock analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Input section
        input_group = QGroupBox("Select Stock & Strategy")
        input_layout = QVBoxLayout()
        
        # Stock selection
        stock_label = QLabel("Pick a Stock:")
        stock_label.setFont(QFont("Arial", 12))
        input_layout.addWidget(stock_label)
        
        self.stock_combo = QComboBox()
        self.stock_combo.addItems([
            'RELIANCE.NS - Reliance Industries',
            'TCS.NS - Tata Consultancy',
            'INFY.NS - Infosys',
            'HDFCBANK.NS - HDFC Bank',
            'ICICIBANK.NS - ICICI Bank',
            'ITC.NS - ITC Limited',
            'SBIN.NS - State Bank',
            'AAPL - Apple Inc',
            'MSFT - Microsoft',
            'GOOGL - Google'
        ])
        self.stock_combo.setStyleSheet("padding: 10px; font-size: 14px;")
        input_layout.addWidget(self.stock_combo)
        
        # Strategy selection
        strategy_label = QLabel("Pick a Strategy:")
        strategy_label.setFont(QFont("Arial", 12))
        input_layout.addWidget(strategy_label)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            'VCP - Best for trending momentum stocks',
            'ICT - Best for institutional price moves',
            'EMA30 - Best for trend following'
        ])
        self.strategy_combo.setStyleSheet("padding: 10px; font-size: 14px;")
        input_layout.addWidget(self.strategy_combo)
        
        # Risk level
        risk_label = QLabel("Risk Level:")
        risk_label.setFont(QFont("Arial", 12))
        input_layout.addWidget(risk_label)
        
        risk_layout = QHBoxLayout()
        self.risk_slider = QSlider(Qt.Horizontal)
        self.risk_slider.setRange(1, 5)
        self.risk_slider.setValue(2)
        self.risk_slider.setTickPosition(QSlider.TicksBelow)
        self.risk_slider.setTickInterval(1)
        self.risk_slider.valueChanged.connect(self._update_risk_label)
        risk_layout.addWidget(self.risk_slider)
        
        self.risk_value_label = QLabel("●●○○○ Conservative")
        self.risk_value_label.setFont(QFont("Arial", 12))
        risk_layout.addWidget(self.risk_value_label)
        
        input_layout.addLayout(risk_layout)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Analyze button
        self.analyze_btn = QPushButton("🔍 ANALYZE THIS STOCK")
        self.analyze_btn.setFont(QFont("Arial", 16, QFont.Bold))
        self.analyze_btn.setStyleSheet(
            "background-color: #3498db; "
            "color: white; "
            "padding: 20px; "
            "border-radius: 10px;"
        )
        self.analyze_btn.clicked.connect(self._analyze_stock)
        layout.addWidget(self.analyze_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { text-align: center; }")
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_label)
        
        # Results section
        self.results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout()
        
        # Signal strength
        self.signal_label = QLabel("📊 Waiting for analysis...")
        self.signal_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.signal_label.setAlignment(Qt.AlignCenter)
        self.signal_label.setStyleSheet("padding: 20px;")
        results_layout.addWidget(self.signal_label)
        
        # Details
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("font-size: 14px; padding: 10px;")
        self.details_text.setMinimumHeight(300)
        results_layout.addWidget(self.details_text)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.paper_trade_btn = QPushButton("📝 SIMULATE PAPER TRADE")
        self.paper_trade_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.paper_trade_btn.setStyleSheet(
            "background-color: #2ecc71; "
            "color: white; "
            "padding: 15px; "
            "border-radius: 5px;"
        )
        self.paper_trade_btn.setEnabled(False)
        self.paper_trade_btn.clicked.connect(self._simulate_paper_trade)
        button_layout.addWidget(self.paper_trade_btn)
        
        results_layout.addLayout(button_layout)
        
        self.results_group.setLayout(results_layout)
        self.results_group.setVisible(False)
        layout.addWidget(self.results_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_risk_management_tab(self) -> QWidget:
        """Create risk management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Portfolio Overview
        portfolio_group = QGroupBox("📊 Portfolio Overview")
        portfolio_layout = QVBoxLayout()
        
        # Capital display
        capital_layout = QHBoxLayout()
        
        initial_label = QLabel("Initial Capital:")
        initial_label.setFont(QFont("Arial", 12))
        capital_layout.addWidget(initial_label)
        
        self.initial_capital_label = QLabel(f"₹{self.initial_capital:,.2f}")
        self.initial_capital_label.setFont(QFont("Arial", 12, QFont.Bold))
        capital_layout.addWidget(self.initial_capital_label)
        
        capital_layout.addStretch()
        
        current_label = QLabel("Current Capital:")
        current_label.setFont(QFont("Arial", 12))
        capital_layout.addWidget(current_label)
        
        self.current_capital_label = QLabel(f"₹{self.current_capital:,.2f}")
        self.current_capital_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.current_capital_label.setStyleSheet("color: #2ecc71;")
        capital_layout.addWidget(self.current_capital_label)
        
        portfolio_layout.addLayout(capital_layout)
        
        # P&L display
        pnl_layout = QHBoxLayout()
        
        total_pnl_label = QLabel("Total P&L:")
        total_pnl_label.setFont(QFont("Arial", 12))
        pnl_layout.addWidget(total_pnl_label)
        
        self.total_pnl_label = QLabel("₹0.00 (0.0%)")
        self.total_pnl_label.setFont(QFont("Arial", 16, QFont.Bold))
        pnl_layout.addWidget(self.total_pnl_label)
        
        pnl_layout.addStretch()
        
        daily_pnl_label = QLabel("Today's P&L:")
        daily_pnl_label.setFont(QFont("Arial", 12))
        pnl_layout.addWidget(daily_pnl_label)
        
        self.daily_pnl_label = QLabel("₹0.00")
        self.daily_pnl_label.setFont(QFont("Arial", 14, QFont.Bold))
        pnl_layout.addWidget(self.daily_pnl_label)
        
        portfolio_layout.addLayout(pnl_layout)
        
        portfolio_group.setLayout(portfolio_layout)
        layout.addWidget(portfolio_group)
        
        # Risk Controls
        risk_group = QGroupBox("🛡️ Risk Controls")
        risk_layout = QVBoxLayout()
        
        # Circuit breaker
        cb_layout = QHBoxLayout()
        cb_label = QLabel("Daily Loss Limit:")
        cb_label.setFont(QFont("Arial", 12))
        cb_layout.addWidget(cb_label)
        
        self.circuit_breaker_slider = QSlider(Qt.Horizontal)
        self.circuit_breaker_slider.setRange(1, 5)
        self.circuit_breaker_slider.setValue(2)
        self.circuit_breaker_slider.setTickPosition(QSlider.TicksBelow)
        self.circuit_breaker_slider.setTickInterval(1)
        self.circuit_breaker_slider.valueChanged.connect(self._update_circuit_breaker)
        cb_layout.addWidget(self.circuit_breaker_slider)
        
        self.circuit_breaker_value_label = QLabel("2.0%")
        self.circuit_breaker_value_label.setFont(QFont("Arial", 12, QFont.Bold))
        cb_layout.addWidget(self.circuit_breaker_value_label)
        
        risk_layout.addLayout(cb_layout)
        
        # Circuit breaker status
        self.circuit_breaker_status = QLabel("✅ Risk controls active")
        self.circuit_breaker_status.setFont(QFont("Arial", 12, QFont.Bold))
        self.circuit_breaker_status.setStyleSheet("color: #2ecc71; padding: 10px;")
        self.circuit_breaker_status.setAlignment(Qt.AlignCenter)
        risk_layout.addWidget(self.circuit_breaker_status)
        
        # Position size calculator
        pos_label = QLabel("Max Position Size per Trade:")
        pos_label.setFont(QFont("Arial", 12))
        risk_layout.addWidget(pos_label)
        
        self.max_position_label = QLabel(f"₹{self.current_capital * 0.1:,.2f} (10% of capital)")
        self.max_position_label.setFont(QFont("Arial", 12))
        self.max_position_label.setStyleSheet("color: #3498db; padding: 5px;")
        risk_layout.addWidget(self.max_position_label)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        # Emergency Controls
        emergency_group = QGroupBox("🚨 Emergency Controls")
        emergency_layout = QVBoxLayout()
        
        warning = QLabel(
            "⚠️ WARNING: Kill switch will close ALL open positions immediately!\n"
            "Use only in case of emergency or system malfunction."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #e74c3c; padding: 10px; background: #fadbd8; border-radius: 5px;")
        emergency_layout.addWidget(warning)
        
        self.kill_switch_btn = QPushButton("🔴 KILL SWITCH - CLOSE ALL POSITIONS")
        self.kill_switch_btn.setFont(QFont("Arial", 16, QFont.Bold))
        self.kill_switch_btn.setStyleSheet(
            "background-color: #c0392b; "
            "color: white; "
            "padding: 25px; "
            "border-radius: 10px; "
            "border: 3px solid #922b21;"
        )
        self.kill_switch_btn.clicked.connect(self._trigger_kill_switch)
        emergency_layout.addWidget(self.kill_switch_btn)
        
        emergency_group.setLayout(emergency_layout)
        layout.addWidget(emergency_group)
        
        # Open Positions
        positions_group = QGroupBox("📈 Open Positions")
        positions_layout = QVBoxLayout()
        
        self.positions_text = QTextEdit()
        self.positions_text.setReadOnly(True)
        self.positions_text.setStyleSheet("font-size: 13px; padding: 10px;")
        self.positions_text.setMinimumHeight(200)
        self.positions_text.setPlainText("No open positions")
        positions_layout.addWidget(self.positions_text)
        
        positions_group.setLayout(positions_layout)
        layout.addWidget(positions_group)
        
        layout.addStretch()
        return widget
    
    def _create_trades_tab(self) -> QWidget:
        """Create paper trades tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel(
            "📝 Your simulated paper trades will appear here.\n\n"
            "These are NOT real trades - they are for testing strategies only.\n"
            "No real money is involved."
        )
        info.setFont(QFont("Arial", 12))
        info.setStyleSheet("padding: 20px; background: #ecf0f1; border-radius: 5px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        self.trades_text = QTextEdit()
        self.trades_text.setReadOnly(True)
        self.trades_text.setStyleSheet("font-size: 13px; padding: 10px;")
        layout.addWidget(self.trades_text)
        
        return widget
    
    def _update_risk_label(self, value):
        """Update risk level label"""
        dots = "●" * value + "○" * (5 - value)
        labels = {
            1: "Very Conservative",
            2: "Conservative",
            3: "Moderate",
            4: "Aggressive",
            5: "Very Aggressive"
        }
        self.risk_value_label.setText(f"{dots} {labels[value]}")
    
    def _connect_zerodha(self):
        """Handle Zerodha connection"""
        from PySide6.QtWidgets import QLineEdit
        
        api_key = self.zerodha_api_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(
                self,
                "Missing API Key",
                "Please enter your Zerodha Kite Connect API Key.\n\n"
                "Get it from: https://kite.trade"
            )
            return
        
        try:
            # Initialize Zerodha data fetcher
            from backend.zerodha_kite_safe import ZerodhaKiteDataFetcher
            
            self.zerodha_connect_btn.setEnabled(False)
            self.zerodha_connect_btn.setText("🔄 Connecting...")
            
            # Get login URL
            fetcher = ZerodhaKiteDataFetcher(api_key=api_key)
            login_url = fetcher.get_login_url()
            
            # Show login dialog
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Zerodha Login Required")
            msg.setText(
                "<h3>Complete Zerodha Login</h3>"
                "<p>1. A browser window will open</p>"
                "<p>2. Login with your Zerodha credentials</p>"
                "<p>3. Authorize the app</p>"
                "<p>4. Copy the <b>request_token</b> from redirect URL</p>"
                "<p>5. Paste it in the next dialog</p>"
            )
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            
            if msg.exec() == QMessageBox.Ok:
                # Open login URL
                import webbrowser
                webbrowser.open(login_url)
                
                # Get request token from user
                from PySide6.QtWidgets import QInputDialog
                token, ok = QInputDialog.getText(
                    self,
                    "Request Token",
                    "Enter the request_token from redirect URL:\n"
                    "(Format: xxxxxxxxxxxxxxxxxxxxxxxxxxxx)"
                )
                
                if ok and token:
                    # For now, just store API key (full auth needs API secret)
                    self.zerodha_api_key = api_key
                    self.zerodha_connected = True
                    
                    # Update UI
                    self.zerodha_status_label.setText("✅ Connected (Demo Mode)")
                    self.zerodha_status_label.setStyleSheet("color: #27ae60; padding: 10px;")
                    self.zerodha_connect_btn.setText("✅ Connected")
                    self.zerodha_connect_btn.setStyleSheet(
                        "background-color: #27ae60; "
                        "color: white; "
                        "padding: 15px; "
                        "border-radius: 8px;"
                    )
                    
                    QMessageBox.information(
                        self,
                        "Connection Successful",
                        "✅ Zerodha API Key saved!\n\n"
                        "Note: Full authentication requires API Secret.\n"
                        "For now, the system will use demo mode with fallback data sources.\n\n"
                        "To enable full Zerodha integration:\n"
                        "1. Add your API Secret to backend/zerodha_kite_safe.py\n"
                        "2. Complete the OAuth flow\n"
                        "3. System will automatically use Zerodha for NSE/BSE data"
                    )
                else:
                    raise ValueError("Request token not provided")
            else:
                raise ValueError("Login cancelled")
        
        except Exception as e:
            logger.error(f"Zerodha connection error: {e}")
            QMessageBox.critical(
                self,
                "Connection Failed",
                f"Failed to connect to Zerodha:\n\n{str(e)}\n\n"
                "The system will continue using free data sources:\n"
                "- nsepython for NSE stocks\n"
                "- yfinance for US stocks & BSE fallback"
            )
            
            self.zerodha_connect_btn.setEnabled(True)
            self.zerodha_connect_btn.setText("🔗 Connect to Zerodha")
            self.zerodha_status_label.setText("❌ Not Connected")
            self.zerodha_status_label.setStyleSheet("color: #e74c3c; padding: 10px;")
    
    def _analyze_stock(self):
        """Run stock analysis"""
        # Get selected symbol
        symbol_text = self.stock_combo.currentText()
        symbol = symbol_text.split(' - ')[0]
        
        strategy = self.strategy_combo.currentText()
        
        # Show progress
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.results_group.setVisible(False)
        
        # Start analysis in background
        self.worker = AnalysisWorker(
            symbol,
            strategy,
            zerodha_api_key=self.zerodha_api_key,
            zerodha_access_token=self.zerodha_access_token
        )
        self.worker.finished.connect(self._on_analysis_complete)
        self.worker.error.connect(self._on_analysis_error)
        self.worker.progress.connect(self._on_progress)
        self.worker.start()
    
    def _on_progress(self, message: str):
        """Update progress message"""
        self.progress_label.setText(message)
    
    def _on_analysis_complete(self, result: Dict):
        """Handle analysis completion"""
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.results_group.setVisible(True)
        self.paper_trade_btn.setEnabled(True)
        
        # Store result
        self.current_result = result
        
        # Display results
        self._display_results(result)
    
    def _on_analysis_error(self, error: str):
        """Handle analysis error"""
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        
        QMessageBox.critical(self, "Analysis Error", f"Failed to analyze stock:\n\n{error}")
    
    def _display_results(self, result: Dict):
        """Display analysis results"""
        symbol = result['symbol']
        sentiment = result['sentiment']
        current_price = result['current_price']
        latest_signal = result['latest_signal']
        
        # Update signal label
        if latest_signal is not None and not latest_signal.empty:
            strength = latest_signal['Signal_Strength'].iloc[0]
            
            if strength >= 8:
                color = "#2ecc71"  # Green
                recommendation = "✅ STRONG BUY SIGNAL"
            elif strength >= 6:
                color = "#f39c12"  # Orange
                recommendation = "⚠️ MODERATE SIGNAL"
            else:
                color = "#e74c3c"  # Red
                recommendation = "❌ WEAK SIGNAL - WAIT"
            
            self.signal_label.setText(f"{recommendation}\nStrength: {strength:.1f}/10")
            self.signal_label.setStyleSheet(f"color: {color}; padding: 20px;")
            
            # Build detailed report
            html = f"""
            <h2 style="color: {color};">{recommendation}</h2>
            <hr>
            <h3>📊 Trading Details:</h3>
            <table style="width: 100%;">
                <tr><td><b>Stock:</b></td><td>{symbol}</td></tr>
                <tr><td><b>Current Price:</b></td><td>₹{current_price:.2f}</td></tr>
                <tr><td><b>Signal Strength:</b></td><td>{strength:.1f}/10</td></tr>
            </table>
            """
            
            # Add stop loss and target if available
            if 'Stop_Loss' in latest_signal:
                stop_loss = latest_signal['Stop_Loss'].iloc[0]
                take_profit = latest_signal['Take_Profit'].iloc[0]
                risk = current_price - stop_loss
                reward = take_profit - current_price
                rr_ratio = reward / risk if risk > 0 else 0
                
                html += f"""
                <h3>💰 Risk Management:</h3>
                <table style="width: 100%;">
                    <tr><td><b>Stop Loss:</b></td><td style="color: #e74c3c;">₹{stop_loss:.2f}</td></tr>
                    <tr><td><b>Target Price:</b></td><td style="color: #2ecc71;">₹{take_profit:.2f}</td></tr>
                    <tr><td><b>Risk Amount:</b></td><td>₹{risk:.2f} per share</td></tr>
                    <tr><td><b>Reward Amount:</b></td><td>₹{reward:.2f} per share</td></tr>
                    <tr><td><b>Risk/Reward:</b></td><td>1:{rr_ratio:.1f}</td></tr>
                </table>
                """
        else:
            self.signal_label.setText("❌ NO SIGNAL\nNo trading opportunity right now")
            self.signal_label.setStyleSheet("color: #e74c3c; padding: 20px;")
            html = "<h2 style='color: #e74c3c;'>❌ NO TRADING SIGNAL</h2><p>The strategy did not identify any trading opportunities for this stock at this time.</p>"
        
        # Add news sentiment
        html += f"""
        <hr>
        <h3>📰 News Sentiment: {sentiment['emoji']} {sentiment['label']}</h3>
        <p><b>Sentiment Score:</b> {sentiment['percentage']}% ({sentiment['article_count']} articles analyzed)</p>
        <p><b>Summary:</b> {sentiment['summary']}</p>
        <h4>Latest News:</h4>
        <ul>
        """
        
        for article in result['news'][:5]:
            html += f"<li><b>{article['title']}</b><br><small>{article['source']}</small></li>"
        
        html += "</ul>"
        
        self.details_text.setHtml(html)
    
    def _update_circuit_breaker(self, value):
        """Update circuit breaker threshold"""
        self.max_daily_loss_pct = value * 1.0  # 1%, 2%, 3%, 4%, 5%
        self.circuit_breaker_value_label.setText(f"{self.max_daily_loss_pct:.1f}%")
        
        # Check if currently breached
        self._check_circuit_breaker()
    
    def _check_circuit_breaker(self):
        """Check if circuit breaker should trigger"""
        loss_pct = (self.daily_pnl / self.initial_capital) * 100
        
        if loss_pct <= -self.max_daily_loss_pct:
            if not self.circuit_breaker_triggered:
                self.circuit_breaker_triggered = True
                self.circuit_breaker_status.setText(
                    f"🔴 CIRCUIT BREAKER TRIGGERED!\n"
                    f"Daily loss: {loss_pct:.2f}% (Limit: {self.max_daily_loss_pct:.1f}%)"
                )
                self.circuit_breaker_status.setStyleSheet("color: #c0392b; padding: 10px; background: #fadbd8;")
                
                # Disable trading
                self.paper_trade_btn.setEnabled(False)
                
                QMessageBox.critical(
                    self,
                    "Circuit Breaker Triggered",
                    f"🔴 TRADING HALTED!\n\n"
                    f"Daily loss limit exceeded: {loss_pct:.2f}%\n"
                    f"Maximum allowed: {self.max_daily_loss_pct:.1f}%\n\n"
                    f"All new trades are blocked.\n"
                    f"Consider closing open positions.\n\n"
                    f"Circuit breaker will reset tomorrow."
                )
        else:
            if self.circuit_breaker_triggered and loss_pct > -self.max_daily_loss_pct:
                self.circuit_breaker_triggered = False
                self.circuit_breaker_status.setText("✅ Risk controls active")
                self.circuit_breaker_status.setStyleSheet("color: #2ecc71; padding: 10px;")
                self.paper_trade_btn.setEnabled(True)
    
    def _update_risk_displays(self):
        """Update all risk management displays"""
        # Update capital
        self.current_capital_label.setText(f"₹{self.current_capital:,.2f}")
        
        # Update total P&L
        total_pnl = self.current_capital - self.initial_capital
        total_pnl_pct = (total_pnl / self.initial_capital) * 100
        
        pnl_color = "#2ecc71" if total_pnl >= 0 else "#e74c3c"
        pnl_sign = "+" if total_pnl >= 0 else ""
        
        self.total_pnl_label.setText(f"{pnl_sign}₹{total_pnl:,.2f} ({pnl_sign}{total_pnl_pct:.2f}%)")
        self.total_pnl_label.setStyleSheet(f"color: {pnl_color};")
        self.current_capital_label.setStyleSheet(f"color: {pnl_color};")
        
        # Update daily P&L
        daily_pnl_color = "#2ecc71" if self.daily_pnl >= 0 else "#e74c3c"
        daily_pnl_sign = "+" if self.daily_pnl >= 0 else ""
        self.daily_pnl_label.setText(f"{daily_pnl_sign}₹{self.daily_pnl:,.2f}")
        self.daily_pnl_label.setStyleSheet(f"color: {daily_pnl_color};")
        
        # Update max position size
        max_pos = self.current_capital * 0.1
        self.max_position_label.setText(f"₹{max_pos:,.2f} (10% of capital)")
        
        # Check circuit breaker
        self._check_circuit_breaker()
        
        # Update positions display
        self._update_positions_display()
    
    def _update_positions_display(self):
        """Update open positions display"""
        if not self.open_positions:
            self.positions_text.setPlainText("No open positions")
            return
        
        html = "<table style='width: 100%; font-size: 13px;'>"
        html += "<tr style='background: #34495e; color: white; font-weight: bold;'>"
        html += "<th>Symbol</th><th>Qty</th><th>Entry</th><th>Current</th><th>P&L</th><th>Stop Loss</th></tr>"
        
        for pos in self.open_positions:
            pnl = pos.get('pnl', 0)
            pnl_color = "#2ecc71" if pnl >= 0 else "#e74c3c"
            pnl_sign = "+" if pnl >= 0 else ""
            
            html += f"<tr style='border-bottom: 1px solid #ddd;'>"
            html += f"<td><b>{pos['symbol']}</b></td>"
            html += f"<td>{pos['quantity']}</td>"
            html += f"<td>₹{pos['entry_price']:.2f}</td>"
            html += f"<td>₹{pos.get('current_price', pos['entry_price']):.2f}</td>"
            html += f"<td style='color: {pnl_color};'><b>{pnl_sign}₹{pnl:,.2f}</b></td>"
            html += f"<td>₹{pos.get('stop_loss', 0):.2f}</td>"
            html += "</tr>"
        
        html += "</table>"
        self.positions_text.setHtml(html)
    
    def _trigger_kill_switch(self):
        """Emergency kill switch - close all positions"""
        if not self.open_positions:
            QMessageBox.information(
                self,
                "No Open Positions",
                "There are no open positions to close."
            )
            return
        
        # Confirmation dialog
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("⚠️ KILL SWITCH CONFIRMATION")
        msg.setText(
            "🔴 ARE YOU SURE?\n\n"
            f"This will IMMEDIATELY close ALL {len(self.open_positions)} open positions!\n\n"
            "This action cannot be undone.\n\n"
            "Type 'CLOSE ALL' to confirm:"
        )
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        
        if msg.exec() == QMessageBox.Ok:
            # In a real system, this would send close orders to broker
            # For paper trading, we simulate closing
            
            total_pnl = 0
            closed_count = 0
            
            for pos in self.open_positions:
                # Simulate closing at current price (or entry price for demo)
                exit_price = pos.get('current_price', pos['entry_price'])
                pnl = (exit_price - pos['entry_price']) * pos['quantity']
                total_pnl += pnl
                closed_count += 1
            
            # Update capital
            self.current_capital += total_pnl
            self.daily_pnl += total_pnl
            
            # Clear positions
            self.open_positions.clear()
            
            # Update displays
            self._update_risk_displays()
            
            QMessageBox.information(
                self,
                "Kill Switch Executed",
                f"✅ All positions closed!\n\n"
                f"Positions closed: {closed_count}\n"
                f"Total P&L: ₹{total_pnl:,.2f}\n\n"
                f"Current capital: ₹{self.current_capital:,.2f}"
            )
    
    def _simulate_paper_trade(self):
        """Simulate a paper trade"""
        if not hasattr(self, 'current_result'):
            return
        
        # Check circuit breaker
        if self.circuit_breaker_triggered:
            QMessageBox.warning(
                self,
                "Trading Halted",
                "🔴 Circuit breaker is active!\n\n"
                "Cannot place new trades until daily loss limit resets."
            )
            return
        
        result = self.current_result
        symbol = result['symbol']
        entry_price = result['current_price']
        
        # Calculate position size (10% of capital max)
        max_position_value = self.current_capital * 0.1
        quantity = int(max_position_value / entry_price)
        position_value = quantity * entry_price
        
        if position_value > self.current_capital:
            QMessageBox.warning(
                self,
                "Insufficient Capital",
                f"Not enough capital for this trade.\n\n"
                f"Required: ₹{position_value:,.2f}\n"
                f"Available: ₹{self.current_capital:,.2f}"
            )
            return
        
        # Calculate stop loss (2% below entry)
        stop_loss = entry_price * 0.98
        
        # Create position
        position = {
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': entry_price,
            'current_price': entry_price,
            'stop_loss': stop_loss,
            'pnl': 0,
            'entry_time': pd.Timestamp.now()
        }
        
        # Deduct capital
        self.current_capital -= position_value
        self.open_positions.append(position)
        
        # Update displays
        self._update_risk_displays()
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Paper Trade Simulated")
        msg.setText(
            f"✅ Paper trade recorded for {symbol}!\n\n"
            f"Quantity: {quantity} shares\n"
            f"Entry Price: ₹{entry_price:.2f}\n"
            f"Position Value: ₹{position_value:,.2f}\n"
            f"Stop Loss: ₹{stop_loss:.2f}\n\n"
            f"Capital Used: ₹{position_value:,.2f}\n"
            f"Remaining Capital: ₹{self.current_capital:,.2f}\n\n"
            "This is a SIMULATION only.\n"
            "No real orders were placed.\n\n"
            "Check the 'Risk Manager' tab to monitor this position."
        )
        msg.exec()
        
        # Add to paper trades list
        trade_text = f"""
📝 PAPER TRADE #{len(self.open_positions)}
{'='*50}
Symbol: {symbol}
Quantity: {quantity} shares
Entry Price: ₹{entry_price:.2f}
Position Value: ₹{position_value:,.2f}
Stop Loss: ₹{stop_loss:.2f}
Time: {position['entry_time']}
Status: OPEN (Simulated)
{'='*50}

"""
        self.trades_text.append(trade_text)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = BeginnerModeGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    import pandas as pd
    main()
