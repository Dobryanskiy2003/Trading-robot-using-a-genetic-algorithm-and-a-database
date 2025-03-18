import threading
from ga_optimization import run_ga_optimization
from backtest import run_backtest
from telegram_bot import main as start_bot
from database import load_data_to_db

def main():
    # Загрузка данных в базу данных из текстового файла
    load_data_to_db('data_output.txt')

    # Telegram-бот в отдельном потоке
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.start()

    best_ind = run_ga_optimization()
    run_backtest(*best_ind, plot=True)

if __name__ == '__main__':
    main()
