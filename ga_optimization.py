# Этот код реализует генетический алгоритм для оптимизации параметров торговой стратегии.
# Нормализация значений доходности и процента прибыльных сделок выполняется для приведения их к диапазону [0, 1],
# что позволяет сравнивать и комбинировать метрики в оценке индивидов в популяции,
# предотвращая доминирование одной метрики над другой и обеспечивая справедливую и стабильную оценку.
import random
from deap import base, creator, tools, algorithms
from backtest import run_backtest

# Задаем веса для каждой из целевых функций
w1 = 0.7  # Важность доходности
w2 = 0.3  # Важность процента прибыльных сделок

# Сохраняем минимальные и максимальные значения для нормализации
min_return = None
max_return = None
min_profit_percentage = None
max_profit_percentage = None

def normalize(value, min_value, max_value):
    """Нормализация показателя по шкале [0, 1] на основе минимума и максимума."""
    if max_value > min_value:
        return (value - min_value) / (max_value - min_value)
    return 0  # Возврат 0, если нет диапазона

def run_ga_optimization():
    """Используется генетический алгоритм для мультиобъектной оптимизации параметров торговой стратегии."""
    
    global min_return, max_return, min_profit_percentage, max_profit_percentage

    # Создается многоцелевую фитнес-функцию
    creator.create("FitnessMulti", base.Fitness, weights=(1.0, 1.0))  # Максимизация
    creator.create("Individual", list, fitness=creator.FitnessMulti)

    toolbox = base.Toolbox()

    toolbox.register("fast_ema_period", random.randint, 5, 30)
    toolbox.register("slow_ema_period", random.randint, 13, 60)
    toolbox.register("stoch_period", random.randint, 5, 20)
    toolbox.register("rsi_period", random.randint, 5, 20)
    toolbox.register("stoch_overbought", random.randint, 70, 100)
    toolbox.register("stoch_oversold", random.randint, 0, 30)
    toolbox.register("rsi_overbought", random.randint, 50, 100)
    toolbox.register("rsi_oversold", random.randint, 0, 50)

    # Определяется индивидуум
    toolbox.register("individual", tools.initCycle, creator.Individual,
                     (toolbox.fast_ema_period, toolbox.slow_ema_period, toolbox.stoch_period,
                      toolbox.rsi_period, toolbox.stoch_overbought, toolbox.stoch_oversold,
                      toolbox.rsi_overbought, toolbox.rsi_oversold),
                     n=1)

    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    def evaluate(individual):
        # Применяется ограничения для параметров индивидуума.
        for idx, value in enumerate(individual):
            if idx < 4:
                individual[idx] = max(int(value), 1)
            else:
                individual[idx] = max(int(value), 0)
        # Приводятся параметры к целым числам
        individual = list(map(int, individual))

        # Получаем результат backtest: доходность и процент прибыльных сделок
        total_return, profitable_trades_percentage = run_backtest(*individual)

        # Обновлются минимальные и максимальные значения для нормализации
        global min_return, max_return, min_profit_percentage, max_profit_percentage
        if total_return is not None:
            if min_return is None or total_return < min_return:
                min_return = total_return
            if max_return is None or total_return > max_return:
                max_return = total_return
        if profitable_trades_percentage is not None:
            if min_profit_percentage is None or profitable_trades_percentage < min_profit_percentage:
                min_profit_percentage = profitable_trades_percentage
            if max_profit_percentage is None or profitable_trades_percentage > max_profit_percentage:
                max_profit_percentage = profitable_trades_percentage

        # Нормализируются значение доходности и процента прибыльных сделок
        normalized_return = normalize(total_return, min_return, max_return) if min_return is not None and max_return is not None else 0
        normalized_profit_percentage = normalize(profitable_trades_percentage, 
                                                min_profit_percentage, max_profit_percentage) if min_profit_percentage is not None and max_profit_percentage is not None else 0

        return (normalized_return * w1, normalized_profit_percentage * w2)

    # Регистрация функций в toolbox
    toolbox.register("evaluate", evaluate)
    toolbox.register("mate", tools.cxBlend, alpha=0.5)
    toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=1, indpb=0.2)
    toolbox.register("select", tools.selNSGA2)  # Используем NSGA-II для многокритериальной селекции.

    pop = toolbox.population(n=10)  
    hall_of_fame = tools.HallOfFame(1)

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", lambda values: (sum(v[0] for v in values) / len(values),
                                           sum(v[1] for v in values) / len(values)))
    stats.register("min", min)
    stats.register("max", max)

    # Запуск алгоритма
    algorithms.eaSimple(pop, toolbox, cxpb=0.8, mutpb=0.2, ngen=10,
                          stats=stats, halloffame=hall_of_fame, verbose=True)

    best_ind = hall_of_fame[0]
    return best_ind