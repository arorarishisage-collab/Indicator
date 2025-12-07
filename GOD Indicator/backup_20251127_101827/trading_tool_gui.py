"""
Advanced PyQt6 GUI for multi-strategy backtesting.
Supports individual and combined strategy testing with visualization.
"""

import sys
import json
import traceback
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
        QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QTextEdit,
        QProgressBar, QScrollArea, QMessageBox, QFileDialog, QFrame
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtGui import QColor, QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.data_fetch import DataFetcher
from backend.strategies import StrategyFactory
from backend.enhanced_backtester import EnhancedBacktester
from backend.chart_generator import ChartGenerator


class BacktestWorker(QThread):
    """Worker thread for running backtests without blocking GUI"""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, df, strategies, backtest_config):
        super().__init__()
        self.df = df
        self.strategies = strategies
        self.backtest_config = backtest_config
        self.results = {}
    
    def run(self):
        try:
            self.progress.emit("🔄 Starting backtest...")
            
            bt = EnhancedBacktester(
                initial_capital=self.backtest_config['initial_capital'],
                risk_per_trade=self.backtest_config['risk_per_trade'],
                slippage=self.backtest_config['slippage'],
                commission=self.backtest_config['commission']
            )
            
            for i, strategy in enumerate(self.strategies):
                self.progress.emit(f"📊 Testing strategy {i+1}/{len(self.strategies)}: {strategy.name}")
                
                # Generate signals
                df_with_signals = strategy.generate_signals(self.df.copy())
                
                # Run backtest
                results = bt.run_backtest(df_with_signals, strategy.name)
                self.results[strategy.name] = results
                
                self.progress.emit(f"✅ Strategy {i+1}/{len(self.strategies)} complete")
            
            self.progress.emit("🎉 Backtest completed!")
            self.finished.emit(self.results)
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)


class TradingToolGUI(QMainWindow):
    """Main GUI application for multi-strategy backtesting"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gold Trading Signal System - Multi-Strategy Backtester")
        self.setGeometry(100, 100, 1400, 900)
        
        self.df = None
        self.backtest_results = {}
        self.worker = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components"""
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Controls
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Right panel - Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_strategies_tab(), "📊 Strategies")
        self.tabs.addTab(self.create_backtest_tab(), "⚙️ Backtest")
        self.tabs.addTab(self.create_results_tab(), "📈 Results")
        self.tabs.addTab(self.create_charts_tab(), "📉 Charts")
        self.tabs.addTab(self.create_analysis_tab(), "📋 Analysis")
        
        main_layout.addWidget(self.tabs, 3)
        
        central_widget.setLayout(main_layout)
    
    def create_left_panel(self) -> QFrame:
        """Create left control panel"""
        frame = QFrame()
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("⚡ Trading System")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Data loading
        layout.addWidget(QLabel("📥 Load Data"))
        load_btn = QPushButton("Load Historical Data")
        load_btn.clicked.connect(self.load_data)
        layout.addWidget(load_btn)
        
        self.data_status = QLabel("Status: No data loaded")
        self.data_status.setStyleSheet("color: orange;")
        layout.addWidget(self.data_status)
        
        # Strategy selection
        layout.addSpacing(20)
        layout.addWidget(QLabel("🎯 Select Strategies"))
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(StrategyFactory.list_strategies())
        layout.addWidget(self.strategy_combo)
        
        # Add strategy button
        self.add_strategy_btn = QPushButton("➕ Add Strategy")
        self.add_strategy_btn.clicked.connect(self.add_strategy)
        layout.addWidget(self.add_strategy_btn)
        
        # Selected strategies list
        self.selected_strategies = QTextEdit()
        self.selected_strategies.setReadOnly(True)
        self.selected_strategies.setMaximumHeight(150)
        layout.addWidget(QLabel("Selected:"))
        layout.addWidget(self.selected_strategies)
        
        # Clear strategies
        clear_btn = QPushButton("🔄 Clear All")
        clear_btn.clicked.connect(self.clear_strategies)
        layout.addWidget(clear_btn)
        
        # Backtest config
        layout.addSpacing(20)
        layout.addWidget(QLabel("⚙️ Backtest Config"))
        
        layout.addWidget(QLabel("Initial Capital ($):"))
        self.capital_spin = QSpinBox()
        self.capital_spin.setValue(10000)
        self.capital_spin.setMaximum(1000000)
        layout.addWidget(self.capital_spin)
        
        layout.addWidget(QLabel("Risk per Trade (%):"))
        self.risk_spin = QDoubleSpinBox()
        self.risk_spin.setValue(2.0)
        self.risk_spin.setMaximum(10.0)
        layout.addWidget(self.risk_spin)
        
        layout.addWidget(QLabel("Slippage (%):"))
        self.slippage_spin = QDoubleSpinBox()
        self.slippage_spin.setValue(0.1)
        layout.addWidget(self.slippage_spin)
        
        layout.addWidget(QLabel("Commission (%):"))
        self.commission_spin = QDoubleSpinBox()
        self.commission_spin.setValue(0.1)
        layout.addWidget(self.commission_spin)
        
        # Run backtest
        layout.addSpacing(20)
        self.run_btn = QPushButton("▶️ RUN BACKTEST")
        self.run_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.run_btn.clicked.connect(self.run_backtest)
        layout.addWidget(self.run_btn)
        
        # Progress
        self.progress_label = QLabel("Ready")
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        
        frame.setLayout(layout)
        return frame
    
    def create_strategies_tab(self) -> QWidget:
        """Create strategies information tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.strategies_info = QTextEdit()
        self.strategies_info.setReadOnly(True)
        self.update_strategies_info()
        
        layout.addWidget(self.strategies_info)
        widget.setLayout(layout)
        return widget
    
    def create_backtest_tab(self) -> QWidget:
        """Create backtest configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        info = QTextEdit()
        info.setReadOnly(True)
        info.setText("""
📊 BACKTEST CONFIGURATION GUIDE

1. Select Strategies: Choose one or more strategies from the left panel
2. Configure Parameters: Set initial capital, risk, slippage, commission
3. Load Data: Load historical gold price data
4. Run Backtest: Click the RUN BACKTEST button

RESULTS INCLUDE:
• Total trades and win rate
• Profit factor and return metrics
• Drawdown analysis (max, duration)
• Sharpe ratio and other risk metrics
• Trade-by-trade analysis
• Equity curve visualization

TIPS:
• Test individual strategies first
• Use low risk settings for initial testing
• Check equity curve for drawdown patterns
• Analyze consecutive wins/losses
• Compare strategies using Sharpe ratio
        """)
        
        layout.addWidget(info)
        widget.setLayout(layout)
        return widget
    
    def create_results_tab(self) -> QWidget:
        """Create results display tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(10)
        self.results_table.setHorizontalHeaderLabels([
            "Strategy", "Trades", "Win Rate", "P&L", "Return %",
            "Sharpe", "Max DD %", "Profit Factor", "Avg Win", "Avg Loss"
        ])
        self.results_table.setRowCount(0)
        
        layout.addWidget(QLabel("📈 Backtest Results Summary"))
        layout.addWidget(self.results_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_charts_tab(self) -> QWidget:
        """Create charts visualization tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Chart selector
        chart_layout = QHBoxLayout()
        chart_layout.addWidget(QLabel("Chart Type:"))
        
        self.chart_combo = QComboBox()
        self.chart_combo.addItems(["Equity Curve", "Price Chart", "Trade Chart", "Drawdown"])
        chart_layout.addWidget(self.chart_combo)
        
        self.chart_combo.currentTextChanged.connect(self.update_chart)
        layout.addLayout(chart_layout)
        
        # Chart display
        self.chart_view = QWebEngineView()
        layout.addWidget(self.chart_view)
        
        widget.setLayout(layout)
        return widget
    
    def create_analysis_tab(self) -> QWidget:
        """Create detailed analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        
        layout.addWidget(QLabel("📋 Detailed Trade Analysis"))
        layout.addWidget(self.analysis_text)
        
        widget.setLayout(layout)
        return widget
    
    def load_data(self):
        """Load historical data"""
        try:
            self.progress_label.setText("📥 Loading data...")
            
            fetcher = DataFetcher()
            self.df = fetcher.fetch_historical_data('XAUUSD')
            
            if self.df is None or self.df.empty:
                raise ValueError("Failed to load data")
            
            self.data_status.setText(f"✅ Loaded: {len(self.df)} bars")
            self.data_status.setStyleSheet("color: green;")
            self.progress_label.setText("Ready")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")
            self.progress_label.setText("Ready")
    
    def add_strategy(self):
        """Add selected strategy to backtest list"""
        strategy_name = self.strategy_combo.currentText()
        
        if not hasattr(self, '_selected_strategies'):
            self._selected_strategies = []
        
        self._selected_strategies.append(strategy_name)
        
        text = "\n".join([f"✓ {s}" for s in self._selected_strategies])
        self.selected_strategies.setText(text)
    
    def clear_strategies(self):
        """Clear selected strategies"""
        self._selected_strategies = []
        self.selected_strategies.clear()
    
    def run_backtest(self):
        """Run backtest on selected strategies"""
        
        if self.df is None or self.df.empty:
            QMessageBox.warning(self, "Warning", "Please load data first")
            return
        
        if not hasattr(self, '_selected_strategies') or not self._selected_strategies:
            QMessageBox.warning(self, "Warning", "Please select strategies first")
            return
        
        # Create strategy instances
        strategies = []
        for strategy_name in self._selected_strategies:
            strategies.append(StrategyFactory.create(strategy_name))
        
        # Backtest config
        config = {
            'initial_capital': float(self.capital_spin.value()),
            'risk_per_trade': self.risk_spin.value() / 100,
            'slippage': self.slippage_spin.value() / 100,
            'commission': self.commission_spin.value() / 100
        }
        
        # Run in worker thread
        self.worker = BacktestWorker(self.df, strategies, config)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_backtest_finished)
        self.worker.error.connect(self.on_backtest_error)
        self.worker.start()
        
        self.run_btn.setEnabled(False)
    
    def on_progress(self, message: str):
        """Handle progress updates"""
        self.progress_label.setText(message)
    
    def on_backtest_finished(self, results: dict):
        """Handle backtest completion"""
        self.backtest_results = results
        self.display_results(results)
        self.run_btn.setEnabled(True)
        self.progress_label.setText("✅ Backtest completed!")
    
    def on_backtest_error(self, error_msg: str):
        """Handle backtest errors"""
        QMessageBox.critical(self, "Backtest Error", error_msg)
        self.run_btn.setEnabled(True)
        self.progress_label.setText("❌ Backtest failed")
    
    def display_results(self, results: dict):
        """Display backtest results"""
        self.results_table.setRowCount(len(results))
        
        for row, (strategy_name, result) in enumerate(results.items()):
            metrics = result['metrics']
            
            self.results_table.setItem(row, 0, QTableWidgetItem(strategy_name))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(metrics['total_trades'])))
            self.results_table.setItem(row, 2, QTableWidgetItem(f"{metrics['win_rate']:.1f}%"))
            self.results_table.setItem(row, 3, QTableWidgetItem(f"${metrics['total_pnl']:.2f}"))
            self.results_table.setItem(row, 4, QTableWidgetItem(f"{metrics['total_return']:.2f}%"))
            self.results_table.setItem(row, 5, QTableWidgetItem(f"{metrics['sharpe_ratio']:.2f}"))
            self.results_table.setItem(row, 6, QTableWidgetItem(f"{metrics['max_drawdown']:.2f}%"))
            self.results_table.setItem(row, 7, QTableWidgetItem(f"{metrics['profit_factor']:.2f}"))
            self.results_table.setItem(row, 8, QTableWidgetItem(f"${metrics['average_win']:.2f}"))
            self.results_table.setItem(row, 9, QTableWidgetItem(f"${metrics['average_loss']:.2f}"))
        
        # Display detailed analysis
        self.display_analysis(results)
    
    def display_analysis(self, results: dict):
        """Display detailed trade analysis"""
        analysis_text = ""
        
        for strategy_name, result in results.items():
            analysis_text += f"\n{'='*60}\n"
            analysis_text += f"Strategy: {strategy_name}\n"
            analysis_text += f"{'='*60}\n\n"
            
            metrics = result['metrics']
            
            analysis_text += f"Performance Metrics:\n"
            analysis_text += f"  Total Return:        {metrics['total_return']:>10.2f}%\n"
            analysis_text += f"  Annualized Return:   {metrics['annualized_return']:>10.2f}%\n"
            analysis_text += f"  Sharpe Ratio:        {metrics['sharpe_ratio']:>10.2f}\n"
            analysis_text += f"  Sortino Ratio:       {metrics['sortino_ratio']:>10.2f}\n"
            analysis_text += f"  Calmar Ratio:        {metrics['calmar_ratio']:>10.2f}\n\n"
            
            analysis_text += f"Trade Statistics:\n"
            analysis_text += f"  Total Trades:        {metrics['total_trades']:>10d}\n"
            analysis_text += f"  Winning Trades:      {metrics['winning_trades']:>10d}\n"
            analysis_text += f"  Losing Trades:       {metrics['losing_trades']:>10d}\n"
            analysis_text += f"  Win Rate:            {metrics['win_rate']:>10.1f}%\n"
            analysis_text += f"  Profit Factor:       {metrics['profit_factor']:>10.2f}\n"
            analysis_text += f"  Avg Win:             ${metrics['average_win']:>9.2f}\n"
            analysis_text += f"  Avg Loss:            ${metrics['average_loss']:>9.2f}\n"
            analysis_text += f"  Risk/Reward Ratio:   {metrics['risk_reward_ratio']:>10.2f}\n\n"
            
            analysis_text += f"Risk Metrics:\n"
            analysis_text += f"  Max Drawdown:        {metrics['max_drawdown']:>10.2f}%\n"
            analysis_text += f"  Drawdown Duration:   {metrics['max_drawdown_duration']:>10d} bars\n"
            analysis_text += f"  Recovery Factor:     {metrics['recovery_factor']:>10.2f}\n"
            analysis_text += f"  Ulcer Index:         {metrics['ulcer_index']:>10.2f}\n\n"
            
            analysis_text += f"Profitability:\n"
            analysis_text += f"  Total P&L:           ${metrics['total_pnl']:>9.2f}\n"
            analysis_text += f"  Gross Profit:        ${metrics['gross_profit']:>9.2f}\n"
            analysis_text += f"  Gross Loss:          ${metrics['gross_loss']:>9.2f}\n"
            analysis_text += f"  Expectancy:          ${metrics['expectancy']:>9.2f}\n"
        
        self.analysis_text.setText(analysis_text)
    
    def update_chart(self, chart_type: str):
        """Update chart display"""
        if not self.backtest_results:
            return
        
        try:
            # Get first strategy results
            first_strategy = list(self.backtest_results.keys())[0]
            result = self.backtest_results[first_strategy]
            
            if chart_type == "Equity Curve":
                html = ChartGenerator.create_equity_curve(
                    result['equity_curve'],
                    result['drawdown_curve']
                )
            elif chart_type == "Trade Chart":
                html = ChartGenerator.create_trade_chart(
                    self.df,
                    result['trades']
                )
            elif chart_type == "Price Chart":
                html = ChartGenerator.create_candlestick_chart(self.df)
            else:  # Drawdown
                html = ChartGenerator.create_equity_curve(
                    result['equity_curve'],
                    result['drawdown_curve']
                )
            
            self.chart_view.setHtml(html)
            
        except Exception as e:
            self.chart_view.setHtml(f"<p>Error: {str(e)}</p>")
    
    def update_strategies_info(self):
        """Update strategies information display"""
        info_text = "Registered Strategies:\n\n"
        
        for strategy_name in StrategyFactory.list_strategies():
            try:
                strategy = StrategyFactory.create(strategy_name)
                info = strategy.get_info()
                
                info_text += f"📌 {strategy_name}\n"
                info_text += f"   {info['description']}\n"
                info_text += f"   Parameters: {info['parameters']}\n\n"
            except:
                pass
        
        self.strategies_info.setText(info_text)


def main():
    """Main entry point"""
    if not PYQT6_AVAILABLE:
        print("❌ PyQt6 not installed")
        print("Install with: pip install PyQt6")
        print("\nUsing headless mode instead...")
        return
    
    app = QApplication(sys.argv)
    gui = TradingToolGUI()
    gui.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
