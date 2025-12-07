"""
Professional Stock Screener GUI
Strategy-first approach: Find stocks that match YOUR criteria
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QTabWidget, QHeaderView, QMessageBox,
    QSpinBox, QDoubleSpinBox, QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal
from PySide6.QtGui import QFont, QColor
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScreenerWorker(QThread):
    """Background thread for stock screening"""
    
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)
    
    def __init__(self, market: str, strategy_name: str, min_strength: float, max_results: int):
        super().__init__()
        self.market = market
        self.strategy_name = strategy_name
        self.min_strength = min_strength
        self.max_results = max_results
    
    def run(self):
        """Run screening in background"""
        try:
            from backend.unified_data_fetcher import UnifiedDataFetcher
            from backend.stock_screener import StockScreener
            from backend.tradingview_webhook import WebhookConfig
            
            self.progress.emit(f"🔍 Initializing screener...", 10)
            
            # Initialize
            fetcher = UnifiedDataFetcher(finnhub_api_key='d4jv009r01qgcb0voap0d4jv009r01qgcb0voapg')
            webhook_config = WebhookConfig('config/webhooks.json')
            screener = StockScreener(
                fetcher,
                webhook_config=webhook_config,
                webhook_channels=['main']
            )
            
            self.progress.emit(f"📊 Loading {self.strategy_name} strategy...", 20)
            
            # Load strategy - USE SIMPLE EMA FOR RELIABILITY
            if 'VCP' in self.strategy_name:
                try:
                    from backend.vcp_strategy import VCPStrategy
                    strategy = VCPStrategy()
                except:
                    # Fallback to simple EMA
                    from backend.simple_ema_strategy import SimpleEMAStrategy
                    strategy = SimpleEMAStrategy()
            elif 'ICT' in self.strategy_name:
                try:
                    from backend.ict_strategy import ICTStrategy
                    strategy = ICTStrategy()
                except:
                    # Fallback to simple EMA
                    from backend.simple_ema_strategy import SimpleEMAStrategy
                    strategy = SimpleEMAStrategy()
            else:  # EMA30
                # Use new reliable simple EMA
                from backend.simple_ema_strategy import SimpleEMAStrategy
                strategy = SimpleEMAStrategy(fast_period=9, slow_period=30)
            
            self.progress.emit(f"🔎 Scanning {self.market} market...", 40)
            
            # Run screen
            results = screener.screen_by_strategy(
                strategy=strategy,
                market=self.market,
                min_signal_strength=self.min_strength,
                max_stocks=self.max_results,
                days=180
            )
            
            self.progress.emit(f"✅ Found {len(results)} opportunities!", 100)
            self.finished.emit(results)
            
        except Exception as e:
            logger.error(f"Screening error: {e}")
            self.error.emit(str(e))


class ProfessionalScreenerGUI(QMainWindow):
    """
    Professional Stock Screener
    Find stocks that match your strategy criteria automatically
    """
    
    def __init__(self):
        super().__init__()
        self.screen_results = []
        self.init_ui()
    
    def init_ui(self):
        """Initialize professional UI"""
        self.setWindowTitle("GOD Indicator - Professional Stock Screener")
        self.setGeometry(50, 50, 1400, 900)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Header
        self._create_header(layout)
        
        # Main content
        tabs = QTabWidget()
        
        # Tab 1: Stock Screener
        screener_tab = self._create_screener_tab()
        tabs.addTab(screener_tab, "🔍 Stock Screener")
        
        # Tab 2: Top Movers
        movers_tab = self._create_movers_tab()
        tabs.addTab(movers_tab, "🚀 Top Movers")
        
        # Tab 3: Watchlist
        watchlist_tab = self._create_watchlist_tab()
        tabs.addTab(watchlist_tab, "⭐ Watchlist")
        
        layout.addWidget(tabs)
    
    def _create_header(self, layout):
        """Create professional header"""
        header = QLabel("🎯 PROFESSIONAL STOCK SCREENER")
        header.setFont(QFont("Arial", 24, QFont.Bold))
        header.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #667eea, stop:1 #764ba2); "
            "color: white; "
            "padding: 20px; "
            "border-radius: 10px;"
        )
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        subtitle = QLabel("Find stocks that match YOUR strategy criteria - automatically")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setStyleSheet("color: #666; padding: 10px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
    
    def _create_screener_tab(self) -> QWidget:
        """Create stock screener tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Screening criteria
        criteria_group = QGroupBox("🎯 Screening Criteria")
        criteria_layout = QVBoxLayout()
        
        # Market selection
        market_layout = QHBoxLayout()
        market_label = QLabel("Market:")
        market_label.setFont(QFont("Arial", 12, QFont.Bold))
        market_layout.addWidget(market_label)
        
        self.market_combo = QComboBox()
        self.market_combo.addItems([
            '🇮🇳 NSE - National Stock Exchange (200+ stocks)',
            '🇺🇸 US - NASDAQ + NYSE (100+ stocks)',
            '💰 FOREX & COMMODITIES - Gold, Silver, Oil, etc.',
            '🌍 ALL MARKETS - Complete scan'
        ])
        self.market_combo.setStyleSheet("padding: 10px; font-size: 14px;")
        market_layout.addWidget(self.market_combo, 1)
        criteria_layout.addLayout(market_layout)
        
        # Strategy selection
        strategy_layout = QHBoxLayout()
        strategy_label = QLabel("Strategy:")
        strategy_label.setFont(QFont("Arial", 12, QFont.Bold))
        strategy_layout.addWidget(strategy_label)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            '📈 VCP - Volatility Contraction Pattern (Momentum)',
            '🏛️ ICT - Inner Circle Trader (Institutional)',
            '📊 EMA30 - Exponential Moving Average (Trend Following)'
        ])
        self.strategy_combo.setStyleSheet("padding: 10px; font-size: 14px;")
        strategy_layout.addWidget(self.strategy_combo, 1)
        criteria_layout.addLayout(strategy_layout)
        
        # Advanced filters
        filters_layout = QHBoxLayout()
        
        # Min signal strength
        strength_label = QLabel("Min Signal Strength:")
        strength_label.setFont(QFont("Arial", 11))
        filters_layout.addWidget(strength_label)
        
        self.min_strength_spin = QDoubleSpinBox()
        self.min_strength_spin.setRange(0.0, 10.0)
        self.min_strength_spin.setValue(6.0)
        self.min_strength_spin.setSingleStep(0.5)
        self.min_strength_spin.setSuffix(" /10")
        self.min_strength_spin.setStyleSheet("padding: 8px; font-size: 13px;")
        filters_layout.addWidget(self.min_strength_spin)
        
        filters_layout.addStretch()
        
        # Max results
        results_label = QLabel("Max Results:")
        results_label.setFont(QFont("Arial", 11))
        filters_layout.addWidget(results_label)
        
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(10, 100)
        self.max_results_spin.setValue(50)
        self.max_results_spin.setSingleStep(10)
        self.max_results_spin.setSuffix(" stocks")
        self.max_results_spin.setStyleSheet("padding: 8px; font-size: 13px;")
        filters_layout.addWidget(self.max_results_spin)
        
        criteria_layout.addLayout(filters_layout)
        
        criteria_group.setLayout(criteria_layout)
        layout.addWidget(criteria_group)
        
        # Scan button
        self.scan_btn = QPushButton("🔍 START SCANNING")
        self.scan_btn.setFont(QFont("Arial", 16, QFont.Bold))
        self.scan_btn.setStyleSheet(
            "background-color: #667eea; "
            "color: white; "
            "padding: 20px; "
            "border-radius: 10px; "
            "border: none;"
        )
        self.scan_btn.clicked.connect(self._start_scan)
        layout.addWidget(self.scan_btn)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 2px solid #667eea; border-radius: 5px; text-align: center; }"
            "QProgressBar::chunk { background-color: #667eea; }"
        )
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.progress_label)
        
        # Add log viewer for debugging
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet("font-family: monospace; font-size: 11px; background: #f9f9f9;")
        self.log_text.setVisible(False)  # Hidden by default
        layout.addWidget(self.log_text)
        
        # Toggle logs button
        self.toggle_logs_btn = QPushButton("📋 Show Logs")
        self.toggle_logs_btn.setStyleSheet("padding: 5px; font-size: 11px;")
        self.toggle_logs_btn.clicked.connect(self._toggle_logs)
        layout.addWidget(self.toggle_logs_btn)
        
        # Results table
        results_group = QGroupBox("📊 Scan Results - Stocks Matching Your Criteria")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            '⭐', 'Symbol', 'Name', 'Price', 'Signal Strength', 'Signal Date', 'Volume', 'Action'
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setStyleSheet(
            "QTableWidget { font-size: 13px; }"
            "QHeaderView::section { background-color: #667eea; color: white; font-weight: bold; padding: 10px; }"
        )
        self.results_table.setAlternatingRowColors(True)
        results_layout.addWidget(self.results_table)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        return widget
    
    def _create_movers_tab(self) -> QWidget:
        """Create top movers tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel(
            "🚀 Top Movers: Stocks with highest price movement + volume\n"
            "Perfect for day trading and momentum strategies"
        )
        info.setFont(QFont("Arial", 12))
        info.setStyleSheet("padding: 15px; background: #f0f0f0; border-radius: 5px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        # Coming soon
        placeholder = QLabel("⏳ Feature coming in next update...")
        placeholder.setFont(QFont("Arial", 14))
        placeholder.setStyleSheet("color: #999; padding: 50px;")
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)
        
        return widget
    
    def _create_watchlist_tab(self) -> QWidget:
        """Create watchlist tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel(
            "⭐ Watchlist: Save your favorite stocks and track them\n"
            "Get alerts when signals match your criteria"
        )
        info.setFont(QFont("Arial", 12))
        info.setStyleSheet("padding: 15px; background: #f0f0f0; border-radius: 5px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        # Coming soon
        placeholder = QLabel("⏳ Feature coming in next update...")
        placeholder.setFont(QFont("Arial", 14))
        placeholder.setStyleSheet("color: #999; padding: 50px;")
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)
        
        return widget
    
    def _start_scan(self):
        """Start stock screening"""
        # Get parameters
        market_text = self.market_combo.currentText()
        if 'NSE' in market_text:
            market = 'NSE'
        elif 'US' in market_text:
            market = 'US'
        elif 'FOREX' in market_text:
            market = 'FOREX'
        else:
            market = 'ALL'
        
        strategy = self.strategy_combo.currentText()
        min_strength = self.min_strength_spin.value()
        max_results = self.max_results_spin.value()
        
        # UI state
        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.results_table.setRowCount(0)
        
        # Start worker
        self.worker = ScreenerWorker(market, strategy, min_strength, max_results)
        self.worker.finished.connect(self._on_scan_complete)
        self.worker.error.connect(self._on_scan_error)
        self.worker.progress.connect(self._on_progress)
        self.worker.start()
    
    def _on_progress(self, message: str, progress: int):
        """Update progress"""
        self.progress_label.setText(message)
        self.progress_bar.setValue(progress)
        
        # Also log it
        self.log_text.append(f"[{progress}%] {message}")
    
    def _toggle_logs(self):
        """Toggle log viewer visibility"""
        if self.log_text.isVisible():
            self.log_text.setVisible(False)
            self.toggle_logs_btn.setText("📋 Show Logs")
        else:
            self.log_text.setVisible(True)
            self.toggle_logs_btn.setText("📋 Hide Logs")
    
    def _on_scan_complete(self, results: List[Dict]):
        """Handle scan completion"""
        self.scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        
        self.screen_results = results
        self._display_results(results)
    
    def _on_scan_error(self, error: str):
        """Handle scan error"""
        self.scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        
        QMessageBox.critical(self, "Scan Error", f"Failed to scan stocks:\n\n{error}")
    
    def _display_results(self, results: List[Dict]):
        """Display scan results in table"""
        self.results_table.setRowCount(len(results))
        
        for i, result in enumerate(results):
            # Star button
            star_btn = QPushButton("⭐")
            star_btn.setStyleSheet("border: none; font-size: 18px;")
            self.results_table.setCellWidget(i, 0, star_btn)
            
            # Symbol
            symbol_item = QTableWidgetItem(result['symbol'])
            symbol_item.setFont(QFont("Arial", 12, QFont.Bold))
            self.results_table.setItem(i, 1, symbol_item)
            
            # Name
            name_item = QTableWidgetItem(result.get('name', result['symbol']))
            self.results_table.setItem(i, 2, name_item)
            
            # Price
            currency = "₹" if result['exchange'] == 'NSE' else "$"
            price_item = QTableWidgetItem(f"{currency}{result['current_price']:.2f}")
            price_item.setFont(QFont("Arial", 11, QFont.Bold))
            self.results_table.setItem(i, 3, price_item)
            
            # Signal strength
            strength = result['signal_strength']
            strength_item = QTableWidgetItem(f"{strength:.1f}/10")
            strength_item.setFont(QFont("Arial", 11, QFont.Bold))
            
            # Color code by strength
            if strength >= 8:
                strength_item.setForeground(QColor("#2ecc71"))
            elif strength >= 6:
                strength_item.setForeground(QColor("#f39c12"))
            else:
                strength_item.setForeground(QColor("#e74c3c"))
            
            self.results_table.setItem(i, 4, strength_item)
            
            # Signal date
            date_item = QTableWidgetItem(str(result['signal_date'].date()) if hasattr(result['signal_date'], 'date') else str(result['signal_date']))
            self.results_table.setItem(i, 5, date_item)
            
            # Volume
            volume_item = QTableWidgetItem(f"{result['volume']:,.0f}")
            self.results_table.setItem(i, 6, volume_item)
            
            # Action button
            action_btn = QPushButton("📊 Analyze")
            action_btn.setStyleSheet(
                "background-color: #3498db; "
                "color: white; "
                "padding: 8px; "
                "border-radius: 5px; "
                "font-weight: bold;"
            )
            action_btn.clicked.connect(lambda checked, r=result: self._analyze_stock(r))
            self.results_table.setCellWidget(i, 7, action_btn)
        
        # Show summary
        if results:
            QMessageBox.information(
                self,
                "Scan Complete",
                f"✅ Found {len(results)} stocks matching your criteria!\n\n"
                f"Top stock: {results[0]['symbol']} "
                f"(Strength: {results[0]['signal_strength']:.1f}/10)"
            )
    
    def _analyze_stock(self, result: Dict):
        """Analyze selected stock in detail"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(f"Analysis: {result['symbol']}")
        msg.setText(
            f"<h2>{result['symbol']} - {result.get('name', '')}</h2>"
            f"<p><b>Exchange:</b> {result['exchange']}</p>"
            f"<p><b>Current Price:</b> {'₹' if result['exchange'] == 'NSE' else '$'}{result['current_price']:.2f}</p>"
            f"<p><b>Signal Strength:</b> {result['signal_strength']:.1f}/10</p>"
            f"<p><b>Signal Date:</b> {result['signal_date']}</p>"
            f"<p><b>Volume:</b> {result['volume']:,.0f}</p>"
            f"<hr>"
            f"<p>🎯 This stock matches your strategy criteria!</p>"
            f"<p>Consider adding to watchlist for further analysis.</p>"
        )
        msg.exec()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = ProfessionalScreenerGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
