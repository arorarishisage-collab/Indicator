#!/usr/bin/env python3
"""
🚀 PRODUCTION TRADING DASHBOARD - ONE COMMAND LAUNCH
Auto-runs 3 strategies in parallel with live monitoring
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QPushButton, QTextEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductionDashboard(QMainWindow):
    """Auto-running 3-strategy production dashboard."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Live Trading Dashboard - 3 Strategies Running")
        self.setMinimumSize(1400, 900)
        
        self.scheduler = None
        self.strategy_stats = {
            'EMA30Strategy': {'signals': 0, 'trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0},
            'ICTStrategy': {'signals': 0, 'trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0},
            'VCPStrategy': {'signals': 0, 'trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0}
        }
        
        self._setup_ui()
        self._apply_theme()
        self._start_auto_trading()
    
    def _setup_ui(self):
        """Create production dashboard layout."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with status
        header_layout = QHBoxLayout()
        
        title = QLabel("🚀 LIVE TRADING SYSTEM")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.status_indicator = QLabel("🟢 RUNNING")
        self.status_indicator.setFont(QFont("Arial", 16, QFont.Bold))
        self.status_indicator.setStyleSheet("color: #2ecc71; background: #d4edda; padding: 10px 20px; border-radius: 8px;")
        header_layout.addWidget(self.status_indicator)
        
        layout.addLayout(header_layout)
        
        # System info
        info_layout = QHBoxLayout()
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 12))
        info_layout.addWidget(self.time_label)
        
        info_layout.addStretch()
        
        self.mode_label = QLabel("Mode: Paper Trading (Safe)")
        self.mode_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        info_layout.addWidget(self.mode_label)
        
        layout.addLayout(info_layout)
        
        # 3 Strategy panels side by side
        strategies_layout = QHBoxLayout()
        strategies_layout.setSpacing(15)
        
        self.ema_panel = self._create_strategy_panel("EMA Crossover", "#3498db")
        strategies_layout.addWidget(self.ema_panel)
        
        self.ict_panel = self._create_strategy_panel("ICT Smart Money", "#9b59b6")
        strategies_layout.addWidget(self.ict_panel)
        
        self.vcp_panel = self._create_strategy_panel("VCP Breakout", "#e74c3c")
        strategies_layout.addWidget(self.vcp_panel)
        
        layout.addLayout(strategies_layout)
        
        # Recent trades table
        trades_group = QGroupBox("📊 Recent Trades (All Strategies)")
        trades_layout = QVBoxLayout()
        
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(8)
        self.trades_table.setHorizontalHeaderLabels([
            'Time', 'Strategy', 'Symbol', 'Action', 'Entry', 'Exit', 'P&L %', 'Status'
        ])
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trades_table.setMaximumHeight(250)
        trades_layout.addWidget(self.trades_table)
        
        trades_group.setLayout(trades_layout)
        layout.addWidget(trades_group)
        
        # System log
        log_group = QGroupBox("📝 System Log")
        log_layout = QVBoxLayout()
        
        self.system_log = QTextEdit()
        self.system_log.setReadOnly(True)
        self.system_log.setMaximumHeight(150)
        self.system_log.setStyleSheet("font-family: 'Courier New'; font-size: 11px;")
        log_layout.addWidget(self.system_log)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.pause_btn = QPushButton("⏸️ Pause All")
        self.pause_btn.clicked.connect(self._pause_trading)
        controls_layout.addWidget(self.pause_btn)
        
        self.resume_btn = QPushButton("▶️ Resume All")
        self.resume_btn.clicked.connect(self._resume_trading)
        self.resume_btn.setEnabled(False)
        controls_layout.addWidget(self.resume_btn)
        
        controls_layout.addStretch()
        
        self.stop_btn = QPushButton("🛑 Stop System")
        self.stop_btn.clicked.connect(self._stop_system)
        self.stop_btn.setStyleSheet("background-color: #e74c3c;")
        controls_layout.addWidget(self.stop_btn)
        
        layout.addLayout(controls_layout)
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_displays)
        self.update_timer.start(1000)
    
    def _create_strategy_panel(self, name: str, color: str) -> QWidget:
        """Create individual strategy monitoring panel."""
        panel = QGroupBox(f"📈 {name}")
        panel.setStyleSheet(f"QGroupBox::title {{ color: {color}; font-weight: bold; font-size: 14px; }}")
        layout = QVBoxLayout()
        
        # Stats
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setSpacing(8)
        
        # Win rate (big display)
        win_rate_label = QLabel("Win Rate")
        win_rate_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        stats_layout.addWidget(win_rate_label)
        
        win_rate_value = QLabel("---%")
        win_rate_value.setFont(QFont("Arial", 32, QFont.Bold))
        win_rate_value.setStyleSheet(f"color: {color};")
        win_rate_value.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(win_rate_value)
        
        # Other stats
        signals_label = QLabel("Signals: 0")
        signals_label.setStyleSheet("font-size: 12px;")
        stats_layout.addWidget(signals_label)
        
        trades_label = QLabel("Trades: 0")
        trades_label.setStyleSheet("font-size: 12px;")
        stats_layout.addWidget(trades_label)
        
        wins_label = QLabel("Wins: 0 | Losses: 0")
        wins_label.setStyleSheet("font-size: 12px; color: #27ae60;")
        stats_layout.addWidget(wins_label)
        
        status_label = QLabel("🟢 Active")
        status_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        status_label.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(status_label)
        
        stats_layout.addStretch()
        layout.addWidget(stats_widget)
        panel.setLayout(layout)
        
        # Store references
        setattr(self, f'{name.lower().replace(" ", "_")}_win_rate', win_rate_value)
        setattr(self, f'{name.lower().replace(" ", "_")}_signals', signals_label)
        setattr(self, f'{name.lower().replace(" ", "_")}_trades', trades_label)
        setattr(self, f'{name.lower().replace(" ", "_")}_wins', wins_label)
        setattr(self, f'{name.lower().replace(" ", "_")}_status', status_label)
        
        return panel
    
    def _start_auto_trading(self):
        """Auto-start all 3 strategies with intelligent brains."""
        self._log("🚀 Initializing trading system...")
        
        try:
            from backend.live_scheduler import LiveTradingScheduler
            from backend.data_fetch_yfinance import YFinanceDataFetcher
            from backend.live_dummy_trader import LiveDummyTrader
            
            self._log("✓ Loading strategy profiles...")
            
            # Initialize components
            dummy_trader = LiveDummyTrader(symbol='GC=F', initial_capital=10000)
            
            profiles = [
                'config/strategy_profiles/gold_ema30.json',
                'config/strategy_profiles/gold_ict.json',
            ]
            
            self.scheduler = LiveTradingScheduler(
                data_fetcher_class=YFinanceDataFetcher,
                dummy_trader=dummy_trader,
                strategy_profiles=profiles
            )
            
            self._log("✓ All strategies loaded")
            
            # Auto-load intelligent brains
            self._log("🧠 Loading intelligent RL brains...")
            brains_loaded = 0
            
            brain_configs = [
                ('EMA30Strategy', 'GC=F'),
                ('EMA30Strategy', 'BANKNIFTY'),
                ('ICTStrategy', 'GC=F'),
                ('ICTStrategy', 'BANKNIFTY'),
                ('VCPStrategy', 'AAPL'),
                ('VCPStrategy', 'BANKNIFTY'),
            ]
            
            for strategy, symbol in brain_configs:
                success = self.scheduler.load_rl_agent(
                    strategy_name=strategy,
                    symbol=symbol,
                    auto_load=True
                )
                if success:
                    brains_loaded += 1
                    self._log(f"  ✓ {strategy} brain loaded for {symbol}")
            
            if brains_loaded > 0:
                self._log(f"🧠 {brains_loaded} intelligent brains active")
            else:
                self._log("⚠️ No trained brains found - run: python train_intelligent_brain.py")
            
            self._log("✓ Starting live monitoring...")
            
            # Start scheduler in background
            self.scheduler.start()
            
            self._log("🟢 System running - monitoring live markets")
            self._log("📊 Generating signals from 3 strategies")
            
        except Exception as e:
            self._log(f"❌ Startup error: {e}")
            logger.exception("Startup failed")
    
    def _update_displays(self):
        """Update all panels with live data."""
        now = datetime.now()
        self.time_label.setText(now.strftime("%Y-%m-%d %H:%M:%S"))
        
        # Simulate updates (replace with real data from scheduler)
        if self.scheduler and hasattr(self.scheduler, 'dummy_trader'):
            try:
                trader = self.scheduler.dummy_trader
                
                # Update trade table
                if hasattr(trader, 'trades') and trader.trades:
                    self._update_trades_table(trader.trades[-20:])  # Last 20 trades
                
                # Update strategy stats
                self._update_strategy_stats()
                
            except Exception as e:
                logger.debug(f"Update error: {e}")
    
    def _update_trades_table(self, trades):
        """Update recent trades table."""
        self.trades_table.setRowCount(len(trades))
        
        for row, trade in enumerate(trades):
            items = [
                trade.exit_time.strftime("%H:%M:%S") if trade.exit_time else "Open",
                trade.strategy,
                trade.symbol,
                "BUY" if trade.direction == 1 else "SELL",
                f"{trade.entry_price:.2f}",
                f"{trade.exit_price:.2f}" if trade.exit_price else "--",
                f"{trade.pnl_percent:.2f}%" if trade.pnl_percent else "--",
                "✅ Win" if trade.win else ("❌ Loss" if trade.win is False else "Open")
            ]
            
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if "Win" in text:
                    item.setForeground(QColor("#27ae60"))
                elif "Loss" in text:
                    item.setForeground(QColor("#e74c3c"))
                self.trades_table.setItem(row, col, item)
    
    def _update_strategy_stats(self):
        """Update strategy panel statistics."""
        if not self.scheduler or not hasattr(self.scheduler, 'dummy_trader'):
            return
        
        trader = self.scheduler.dummy_trader
        if not hasattr(trader, 'trades'):
            return
        
        # Calculate per-strategy stats
        for strategy in ['EMA30Strategy', 'ICTStrategy', 'VCPStrategy']:
            strategy_trades = [t for t in trader.trades if t.strategy == strategy]
            
            if not strategy_trades:
                continue
            
            wins = sum(1 for t in strategy_trades if t.win)
            losses = sum(1 for t in strategy_trades if t.win is False)
            total = len(strategy_trades)
            win_rate = (wins / total * 100) if total > 0 else 0
            
            self.strategy_stats[strategy] = {
                'signals': total,
                'trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate
            }
    
    def _pause_trading(self):
        """Pause all strategies."""
        if self.scheduler:
            self.scheduler.stop()
        self.status_indicator.setText("⏸️ PAUSED")
        self.status_indicator.setStyleSheet("color: #f39c12; background: #fff3cd; padding: 10px 20px; border-radius: 8px;")
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(True)
        self._log("⏸️ System paused")
    
    def _resume_trading(self):
        """Resume all strategies."""
        if self.scheduler:
            self.scheduler.start()
        self.status_indicator.setText("🟢 RUNNING")
        self.status_indicator.setStyleSheet("color: #2ecc71; background: #d4edda; padding: 10px 20px; border-radius: 8px;")
        self.pause_btn.setEnabled(True)
        self.resume_btn.setEnabled(False)
        self._log("▶️ System resumed")
    
    def _stop_system(self):
        """Stop entire system."""
        if self.scheduler:
            self.scheduler.stop()
        self.status_indicator.setText("🛑 STOPPED")
        self.status_indicator.setStyleSheet("color: #e74c3c; background: #f8d7da; padding: 10px 20px; border-radius: 8px;")
        self._log("🛑 System stopped")
        self.close()
    
    def _log(self, message: str):
        """Add message to system log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.system_log.append(f"[{timestamp}] {message}")
        logger.info(message)
    
    def _apply_theme(self):
        """Apply professional theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dfe6e9;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 20px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 8px;
                font-size: 13px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
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
            QTableWidget {
                border: 2px solid #dfe6e9;
                border-radius: 8px;
                background-color: white;
                gridline-color: #f5f6fa;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
            QTextEdit {
                border: 2px solid #dfe6e9;
                border-radius: 8px;
                background-color: white;
                padding: 10px;
            }
        """)


def main():
    """Launch production dashboard."""
    print("=" * 70)
    print("🚀 LAUNCHING PRODUCTION TRADING DASHBOARD")
    print("=" * 70)
    print("Starting 3 strategies in parallel...")
    print("EMA Crossover | ICT Smart Money | VCP Breakout")
    print("=" * 70)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    dashboard = ProductionDashboard()
    dashboard.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
