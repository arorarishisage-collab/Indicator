"""
Forward Tester / Paper Trading Module
Simulates live trading for validation on recent data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ForwardTester:
    """Simulates forward/paper trading on recent data."""
    
    def __init__(self, log_dir: str = './logs'):
        """
        Initialize forward tester.
        
        Args:
            log_dir: Directory to store trading logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.trades_log = self.log_dir / f"forward_trades_{datetime.now().strftime('%Y%m%d')}.csv"
        self.signals_log = self.log_dir / f"signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    def log_signal(self, signal: dict) -> None:
        """
        Log a trading signal.
        
        Args:
            signal: Dictionary with signal details
        """
        log_msg = f"""
╔════════════════════════════════════════════════════════════╗
║ NEW TRADING SIGNAL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
╠════════════════════════════════════════════════════════════╣
║ Direction:        {signal.get('direction', 'N/A')}
║ Entry Price:      {signal.get('entry_price', 'N/A')}
║ Stop Loss:        {signal.get('stop_loss', 'N/A')}
║ Take Profit:      {signal.get('take_profit', 'N/A')}
║ Risk/Reward:      {signal.get('risk_reward', 'N/A')}
║ Timeframe:        {signal.get('timeframe', 'N/A')}
║ Reasons:          {signal.get('reason', 'N/A')}
╚════════════════════════════════════════════════════════════╝
"""
        print(log_msg)
        
        with open(self.signals_log, 'a') as f:
            f.write(log_msg + '\n')
        
        logger.info(f"Signal logged: {signal.get('direction')} @ {signal.get('entry_price')}")
    
    def log_trade_result(self, trade: dict) -> None:
        """
        Log completed trade result.
        
        Args:
            trade: Dictionary with trade details
        """
        # Append to CSV
        df = pd.DataFrame([trade])
        
        if self.trades_log.exists():
            existing = pd.read_csv(self.trades_log)
            df = pd.concat([existing, df], ignore_index=True)
        
        df.to_csv(self.trades_log, index=False)
        logger.info(f"Trade result logged: {trade.get('direction')} P&L ${trade.get('pnl', 0):.2f}")
    
    def generate_daily_report(self, trades: list) -> str:
        """
        Generate daily summary report.
        
        Args:
            trades: List of trade dictionaries
        
        Returns:
            Formatted report string
        """
        if not trades:
            return "No trades for today."
        
        trades_df = pd.DataFrame(trades)
        
        total_trades = len(trades_df)
        winning = len(trades_df[trades_df['pnl'] > 0])
        losing = len(trades_df[trades_df['pnl'] < 0])
        total_pnl = trades_df['pnl'].sum()
        
        report = f"""
╔════════════════════════════════════════════════════════════╗
║ DAILY TRADING REPORT - {datetime.now().strftime('%Y-%m-%d')}
╠════════════════════════════════════════════════════════════╣
║ Total Trades:          {total_trades}
║ Winning Trades:        {winning} ({winning/total_trades*100:.1f}%)
║ Losing Trades:         {losing}
║ Total P&L:             ${total_pnl:,.2f}
║ Avg Win:               ${trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning > 0 else 0:,.2f}
║ Avg Loss:              ${trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing > 0 else 0:,.2f}
╚════════════════════════════════════════════════════════════╝
"""
        return report
    
    def validate_signal_quality(self, signal: dict, min_rr: float = 1.5) -> bool:
        """
        Validate signal quality before execution.
        
        Args:
            signal: Signal dictionary
            min_rr: Minimum acceptable risk/reward ratio
        
        Returns:
            True if signal passes validation
        """
        checks = []
        
        # Check required fields
        required = ['entry_price', 'stop_loss', 'take_profit', 'direction']
        for field in required:
            if field not in signal or signal[field] is None:
                logger.warning(f"Missing required field: {field}")
                checks.append(False)
            else:
                checks.append(True)
        
        if not all(checks):
            return False
        
        # Check risk/reward
        rr = signal.get('risk_reward', 0)
        if rr < min_rr:
            logger.warning(f"Risk/Reward {rr:.2f} below minimum {min_rr}")
            return False
        
        # Check direction
        if signal['direction'] not in ['BUY', 'SELL']:
            logger.warning(f"Invalid direction: {signal['direction']}")
            return False
        
        logger.info(f"✓ Signal validation passed: {signal['direction']} RR={rr:.2f}")
        return True


class PaperTradingEngine:
    """Simulates live paper trading with real-time signal processing."""
    
    def __init__(self, initial_balance: float = 10000):
        """
        Initialize paper trading engine.
        
        Args:
            initial_balance: Starting balance in USD
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.open_positions = []
        self.closed_trades = []
    
    def process_signal(self, signal: dict) -> dict:
        """
        Process incoming signal for paper trading.
        
        Args:
            signal: Signal dictionary with entry, SL, TP
        
        Returns:
            Trade execution result
        """
        entry = signal['entry_price']
        sl = signal['stop_loss']
        tp = signal['take_profit']
        direction = signal['direction']
        
        # Calculate position size (2% risk per trade)
        risk = abs(entry - sl)
        risk_amount = self.current_balance * 0.02
        contracts = risk_amount / risk if risk > 0 else 0
        
        position = {
            'id': len(self.closed_trades) + len(self.open_positions) + 1,
            'timestamp': datetime.now(),
            'direction': direction,
            'entry': entry,
            'stop_loss': sl,
            'take_profit': tp,
            'contracts': contracts,
            'status': 'OPEN'
        }
        
        self.open_positions.append(position)
        
        result = {
            'position_id': position['id'],
            'status': 'OPENED',
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'size': contracts,
            'timestamp': position['timestamp']
        }
        
        logger.info(f"Position opened: {direction} {contracts:.2f} contracts @ {entry}")
        return result
    
    def process_candle(self, candle: dict) -> list:
        """
        Process new candle to check for exits.
        
        Args:
            candle: Dictionary with High, Low, Close
        
        Returns:
            List of closed positions
        """
        closed = []
        high = candle['High']
        low = candle['Low']
        
        for position in self.open_positions[:]:
            exit_price = None
            exit_type = None
            
            if position['direction'] == 'BUY':
                if low <= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_type = 'SL'
                elif high >= position['take_profit']:
                    exit_price = position['take_profit']
                    exit_type = 'TP'
            
            else:  # SELL
                if high >= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_type = 'SL'
                elif low <= position['take_profit']:
                    exit_price = position['take_profit']
                    exit_type = 'TP'
            
            if exit_price:
                # Calculate P&L
                if position['direction'] == 'BUY':
                    pnl = (exit_price - position['entry']) * position['contracts']
                else:
                    pnl = (position['entry'] - exit_price) * position['contracts']
                
                self.current_balance += pnl
                
                trade = {
                    'id': position['id'],
                    'direction': position['direction'],
                    'entry': position['entry'],
                    'exit': exit_price,
                    'exit_type': exit_type,
                    'contracts': position['contracts'],
                    'pnl': pnl,
                    'balance': self.current_balance,
                    'duration': datetime.now() - position['timestamp']
                }
                
                self.closed_trades.append(trade)
                self.open_positions.remove(position)
                closed.append(trade)
                
                logger.info(f"Position closed {exit_type}: P&L ${pnl:,.2f}")
        
        return closed


def run_paper_trading_simulation(df: pd.DataFrame, signals_df: pd.DataFrame) -> dict:
    """
    Simulate paper trading on DataFrame with signals.
    
    Args:
        df: OHLCV DataFrame
        signals_df: DataFrame with signals
    
    Returns:
        Trading results
    """
    engine = PaperTradingEngine(initial_balance=10000)
    forward_tester = ForwardTester()
    
    all_closed = []
    
    for idx, row in df.iterrows():
        # Check for new signals
        if row['Signal'] != 0:
            signal = {
                'entry_price': row['EntryPrice'],
                'stop_loss': row['StopLoss'],
                'take_profit': row['TakeProfit'],
                'direction': 'BUY' if row['Signal'] == 1 else 'SELL',
                'risk_reward': row['RiskReward']
            }
            
            if forward_tester.validate_signal_quality(signal):
                forward_tester.log_signal({**signal, 'timeframe': '1H', 'reason': row['Reason']})
                engine.process_signal(signal)
        
        # Check for exits
        candle = {'High': row['High'], 'Low': row['Low'], 'Close': row['Close']}
        closed = engine.process_candle(candle)
        all_closed.extend(closed)
    
    # Generate report
    report = forward_tester.generate_daily_report(all_closed)
    print(report)
    
    return {
        'engine': engine,
        'closed_trades': all_closed,
        'open_positions': engine.open_positions,
        'final_balance': engine.current_balance
    }


if __name__ == "__main__":
    # Example usage
    from data_fetch import load_demo_data
    from zone_detector import ZoneDetector
    from signal_generator import SignalGenerator
    
    df = load_demo_data()
    df = df.tail(200)
    
    detector = ZoneDetector()
    swing_highs, swing_lows = detector.detect_swings(df)
    zones = detector.detect_supply_demand_zones(df, swing_highs, swing_lows)
    zones = detector.update_zone_mitigation(zones, df)
    
    obs = detector.detect_order_blocks(df)
    fvgs = detector.detect_fair_value_gaps(df)
    srl = detector.detect_support_resistance(df)
    
    generator = SignalGenerator()
    df = generator.generate_signals(df, zones, obs, fvgs, srl, lookback=len(df))
    
    # Run paper trading
    results = run_paper_trading_simulation(df, df[df['Signal'] != 0])
    
    print(f"\nFinal Balance: ${results['final_balance']:.2f}")
    print(f"Open Positions: {len(results['open_positions'])}")
