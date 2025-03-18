import backtrader as bt
from telegram_bot import send_message  # Функция для отправки сообщений
import time

class EMAStochMACDRSI(bt.Strategy):
    """Стратегия на основе EMA, MACD, RSI и Стохастика"""

    params = (
        ('fast_ema_period', 12),
        ('slow_ema_period', 26),
        ('stoch_period', 14),
        ('rsi_period', 14),
        ('stoch_overbought', 80),
        ('stoch_oversold', 20),
        ('rsi_overbought', 70),
        ('rsi_oversold', 30),
        ('max_positions', 10),
        ('pivot_period', 14),
        ('risk_reward_ratio', 2.0)
    )

    def __init__(self, is_final_run=False):
        
        self.capital = self.broker.getvalue() #Сумма при вызове
        self.close = self.datas[0].close
        self.order = None
        self.trades = []  # Список для хранения сделок
        self.log_file = open('trades.txt', 'w')
        self.is_final_run = is_final_run
        self.total_trades = 0 # общее колличество сделок
        self.profitable_trades = 0 # колличество прибыльных сделок

        # Исторические данные для расчета Pivot Points
        self.high_buffer = []
        self.low_buffer = []
        self.close_buffer = []

        # Индикаторы стратегии
        self.fast_ema = bt.indicators.ExponentialMovingAverage(self.datas[0], period=self.p.fast_ema_period)
        self.slow_ema = bt.indicators.ExponentialMovingAverage(self.datas[0], period=self.p.slow_ema_period)
        self.stochastic = bt.indicators.Stochastic(self.datas[0], period=self.p.stoch_period)
        self.macd = bt.indicators.MACD(self.datas[0]) 
        self.rsi = bt.indicators.RelativeStrengthIndex(self.datas[0], period=self.p.rsi_period)

        # Для хранения уровней стопов и тейков
        self.current_pp = 0
        self.current_r1 = 0
        self.current_s1 = 0

    def log(self, txt, dt=None, log = False):
        dt = bt.num2date(self.datas[0].datetime[0]) if dt is None else dt
        message = f'{dt.strftime("%d.%m.%Y %H:%M")}, {txt}'
        print(message)
        if self.is_final_run and log:
            self.log_file.write(message + "\n")
            send_message(message)
            time.sleep(0.012)


    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                message = f'Bought @{order.executed.price:.2f}, Cost={order.executed.value:.2f}, Comm={order.executed.comm:.2f}, Size={(self.getposition(self.datas[0])).size}'
                if self.is_final_run:
                    self.log(message, log = True)
                else:
                    self.log(message)

            elif order.issell():
                message = f'Sold @{order.executed.price:.2f}, Cost={order.executed.value:.2f}, Comm={order.executed.comm:.2f}, Size={(self.getposition(self.datas[0])).size}'
                if self.is_final_run:
                    self.log(message, log = True)
                else:
                    self.log(message)

            # Сохраняется информация о сделке
            self.trades.append(order)  # Добавляется заказ в список сделок

        # elif order.status in [order.Canceled, order.Margin, order.Rejected]:
        #     self.log('Canceled/Margin/Rejected')
        
        elif order.status == order.Canceled:
            self.log('Order Canceled: недостаточно средств или изменение цены или отмена стопа/тейка при срабатывании связанного с ним тейка/стопа')
        elif order.status == order.Margin:
            self.log('Margin: недостаточно маржи')
        elif order.status == order.Rejected:
            self.log('Rejected: ордер отклонен биржей')
        
        self.order = None


    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        message = f'Trade Profit, Gross={trade.pnl:.2f}, NET={trade.pnlcomm:.2f}'
        if self.is_final_run:
            self.log(message, log = True)
        else:
            self.log(message)

        if trade.isclosed:
            self.total_trades += 1
            if trade.pnlcomm > 0:
                self.profitable_trades += 1

    def count_open_long_positions(self):
        """Подсчет открытых длинных позиций"""
        position = self.getposition(self.datas[0])
        return position.size if position.size > 0 else 0

    def count_open_short_positions(self):
        """Подсчет открытых коротких позиций"""
        position = self.getposition(self.datas[0])
        return abs(position.size) if position.size < 0 else 0


    def calculate_pivot_points(self):
            """Метод расчета Pivot Points"""
            if len(self.high_buffer) < self.p.pivot_period:
                return 0, 0, 0
            
            high = max(self.high_buffer)
            low = min(self.low_buffer)
            close = self.close_buffer[-1]
            
            pp = (high + low + close) / 3
            r1 = 2 * pp - low
            s1 = 2 * pp - high
            r2 = pp + (high - low)
            s2 = pp - (high - low)
            r3 = pp + 2 * (high - low)
            s3 = pp - 2 * (high - low)
            
            return pp, r1, s1, r2, s2, r3, s3


    def next(self):
        # Обновляем буферы данных
        self.high_buffer.append(self.data.high[0])
        self.low_buffer.append(self.data.low[0])
        self.close_buffer.append(self.data.close[0])
        
        # Поддерживаем размер буфера равным pivot_period
        if len(self.high_buffer) > self.p.pivot_period:
            self.high_buffer.pop(0)
            self.low_buffer.pop(0)
            self.close_buffer.pop(0)
        
        # Рассчитываем Pivot Points
        pp_levels = self.calculate_pivot_points()
        if pp_levels[0] != 0:
            (self.current_pp, self.current_r1, self.current_s1, 
             _, _, _, _) = pp_levels

        self.log(f'Close={self.close[0]:.2f}')
        if self.order:
            return

        buy_signals, sell_signals = 0, 0
        
        # Условия для покупки
        if self.close[0] > self.fast_ema[0] and self.fast_ema[0] > self.slow_ema[0]:  
            buy_signals += 1
        if self.stochastic.percK[0] < self.p.stoch_oversold:  
            buy_signals += 1
        if self.macd.macd[0] > self.macd.signal[0]:  
            buy_signals += 1
        if self.rsi[0] < self.p.rsi_oversold:  
            buy_signals += 1

        # Условия для продажи
        if self.close[0] < self.fast_ema[0] and self.fast_ema[0] < self.slow_ema[0]:  
            sell_signals += 1
        if self.stochastic.percK[0] > self.p.stoch_overbought:  
            sell_signals += 1
        if self.macd.macd[0] < self.macd.signal[0]:  
            sell_signals += 1
        if self.rsi[0] > self.p.rsi_overbought:  
            sell_signals += 1

        if buy_signals >= 2 and self.count_open_long_positions() < self.params.max_positions and self.count_open_short_positions() == 0:
            self.log('Buy Market')
            self.execute_long()
            return

        if sell_signals >= 2 and self.count_open_short_positions() < self.params.max_positions and self.count_open_long_positions() == 0:
            self.log('Sell Market')
            self.execute_short()
            return

    
    def execute_long(self):
        price = self.close[0]
        stop_loss = self.current_s1 if self.current_s1 != 0 else price*0.95
        take_profit = price + self.p.risk_reward_ratio * (price - stop_loss)
        
        # Проверка корректности уровней
        if stop_loss >= price or take_profit <= price:
            self.log('Invalid levels for Short and Take positions, so they will be set by default')
            stop_loss = price*0.95
            take_profit = price*1.1

        # Получаем размер сделки через сисайзер
        size = self.getsizing(data=self.data, isbuy=True)
        if size <= 0:  # Если размер сделки недопустим, выходим
            self.log('Invalid trade size: size <= 0')
            return
            
        self.log(f'LONG Entry: {price:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}', log =True)
        self.order = self.buy_bracket(
            price=price,
            stopprice=stop_loss,
            limitprice=take_profit,
            exectype=bt.Order.Market,
            stopexec=bt.Order.Stop,
            limitexec=bt.Order.Limit,
            size=size  # Передаем размер сделки
        )

    def execute_short(self):
        price = self.close[0]
        stop_loss = self.current_r1 if self.current_r1 != 0 else price*1.05
        take_profit = price - self.p.risk_reward_ratio * (stop_loss - price)
        
        # Проверка корректности уровней
        if stop_loss <= price or take_profit >= price:
            self.log('Invalid levels for Short and Take positions, so they will be set by default')
            stop_loss = price*1.05
            take_profit = price*0.9

        # Получаем размер сделки через сисайзер
        size = self.getsizing(data=self.data, isbuy=False)
        if size <= 0:  # Если размер сделки недопустим, выходим
            self.log('Invalid trade size: size <= 0')
            return
            
        self.log(f'SHORT Entry: {price:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}', log = True)
        self.order = self.sell_bracket(
            price=price,
            stopprice=stop_loss,
            limitprice=take_profit,
            exectype=bt.Order.Market,
            stopexec=bt.Order.Stop,
            limitexec=bt.Order.Limit,
            size=size
        )

    def stop(self):
        """Закрытие лог файла при завершении стратегии"""
        self.log_file.close()
        print(self.capital)