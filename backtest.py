# backtest.py
from datetime import datetime
import backtrader as bt
from strategy import EMAStochMACDRSI
import telegram_bot as td
import math
import pandas as pd
from database import fetch_data_from_db


class PositionAwareSizer(bt.Sizer):
    params = (
        ('percent', 25), 
        ('max_positions', None),
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        # Получаем позицию через брокера, а не через стратегию
        position = self.broker.getposition(data)
        current_size = position.size if position else 0
        
        # Рассчитываем желаемый размер
        price = data.close[0]
        if price == 0:
            return 0
        desired_size = (cash * self.p.percent / 100) / price
        
        # Корректируем размер с учетом лимита
        available_size = self.p.max_positions - current_size if isbuy else self.p.max_positions + current_size
        size = min(desired_size, available_size)
        
        return math.floor(size) if math.floor(size) > 0 else 1 if available_size > 0 else 0

# Колличество денег для совершения сделок
cash = 150000


def run_backtest(fast_ema_period, slow_ema_period, stoch_period, rsi_period, stoch_overbought, stoch_oversold, rsi_overbought, rsi_oversold, plot=False):
    cerebro = bt.Cerebro()
    if plot:
        cerebro.addstrategy(EMAStochMACDRSI,
                        fast_ema_period=fast_ema_period,
                        slow_ema_period=slow_ema_period,
                        stoch_period=stoch_period,
                        rsi_period=rsi_period,
                        stoch_overbought=stoch_overbought,
                        stoch_oversold=stoch_oversold,
                        rsi_overbought=rsi_overbought,
                        rsi_oversold=rsi_oversold, is_final_run=True)
    else:
        cerebro.addstrategy(EMAStochMACDRSI,
                        fast_ema_period=fast_ema_period,
                        slow_ema_period=slow_ema_period,
                        stoch_period=stoch_period,
                        rsi_period=rsi_period,
                        stoch_overbought=stoch_overbought,
                        stoch_oversold=stoch_oversold,
                        rsi_overbought=rsi_overbought,
                        rsi_oversold=rsi_oversold)

     # Загрузка данных из базы данных
    data = fetch_data_from_db()
    
    # Преобразуем данные в формат, понятный Backtrader
    data_feed = bt.feeds.PandasData(
        dataname=pd.DataFrame(data, columns=['DateTime', '<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>', '<VOL>']),
        datetime='DateTime',
        open='<OPEN>',
        high='<HIGH>',
        low='<LOW>',
        close='<CLOSE>',
        volume='<VOL>',
    )
    
    cerebro.adddata(data_feed)
    cerebro.broker.setcash(cash)
    cerebro.addsizer(
        PositionAwareSizer, 
        percent=25, 
        max_positions=10  # Берём значение из стратегии
    )
    cerebro.broker.setcommission(commission=0.0005)

    try:
        results = cerebro.run()
        strat = results[0]
    except ZeroDivisionError:
        print("Ошибка: Деление на ноль в индикаторе.")
        return 0, 0

    broker_final_value = cerebro.broker.getvalue()
    td.update_balance(broker_final_value)
    total_profit = broker_final_value - cash

    trades_count = strat.total_trades
    profitable_trades = strat.profitable_trades

    profitable_trades_percentage = (profitable_trades / trades_count) * 100 if trades_count > 0 else 0

    if plot:
        print("Лучшие параметры:", (fast_ema_period, slow_ema_period, stoch_period, rsi_period, stoch_overbought, stoch_oversold, rsi_overbought, rsi_oversold))
        print("Максимальная доходность:", total_profit)
        print("Количество прибыльных сделок в %:", profitable_trades_percentage)
        print(f'Общее количество сделок: {trades_count}')
        td.get_balance()
        cerebro.plot(style='candle', 
                barup='green', 
                bardown='red',
                volume=False,  # Отключаем объемы для чистоты графика
                locnum=True)  
        cerebro.plot(style='line')
        
    return total_profit, profitable_trades_percentage