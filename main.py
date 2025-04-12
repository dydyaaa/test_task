import re
import argparse
import multiprocessing as mp
from queue import Empty
from abc import ABC, abstractmethod

class Report(ABC):
    """Абстрактный базовый класс для отчетов."""
    def __init__(self, log_files):
        self.log_files = log_files  # Список путей к лог-файлам
    
    @abstractmethod
    def generate(self):
        """Абстрактный метод для генерации отчета."""
        pass
    
class DefaultReport(Report):
    """Заглушка для неподдерживаемых типов отчетов."""
    def generate(self):
        print('Указан неверный тип отчета!')

class HandlersReport(Report):
    def process_log_file(self, log_file_path, output_queue):
        """
        Обрабатывает один лог-файл и отправляет результаты в очередь.
        
        Args:
            log_file_path (str): Путь к лог-файлу.
            output_queue (mp.Queue): Очередь для передачи результатов.
        """
        stats = {}  # Статистика: {маршрут: {уровень: количество}}
        total_requests = 0  # Общее число обработанных запросов

        # Регулярные выражения для поиска нужных данных
        django_pattern = re.compile(r'django\.request')
        level_pattern = re.compile(r'\s+(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+')
        route_pattern = re.compile(r'(/[\w/]+/?)')

        try:
            with open(log_file_path, 'r') as file:
                for line in file:
                    if not django_pattern.search(line):
                        continue

                    # Извлекаем уровень логирования
                    level_match = level_pattern.search(line)
                    if not level_match:
                        continue
                    level = level_match.group(1)

                    # Извлекаем маршрут
                    route_match = route_pattern.search(line)
                    if route_match:
                        route = route_match.group(1)
                        if route not in stats:
                            stats[route] = {}
                        stats[route][level] = stats[route].get(level, 0) + 1
                        total_requests += 1

        except FileNotFoundError:
            print(f"Ошибка: Файл {log_file_path} не найден.")
        except Exception as e:
            print(f"Ошибка при обработке файла {log_file_path}: {e}")

        # Отправляем результаты в очередь
        output_queue.put((stats, total_requests))

    def aggregate_stats(self, results):
        """
        Агрегирует статистику из всех процессов.
        
        Args:
            results (list): Список кортежей [(stats, total_requests), ...].
        
        Returns:
            tuple: Агрегированная статистика и общее число запросов.
        """
        aggregated_stats = {}
        total_requests = 0

        for stats, count in results:
            total_requests += count
            for route, levels in stats.items():
                if route not in aggregated_stats:
                    aggregated_stats[route] = {}
                for level, value in levels.items():
                    aggregated_stats[route][level] = aggregated_stats[route].get(level, 0) + value

        return aggregated_stats, total_requests

    def print_table(self, stats, total_requests):
        """
        Выводит таблицу с результатами анализа.
        
        Args:
            stats (dict): Агрегированная статистика.
            total_requests (int): Общее число запросов.
        """
        print(f"\nTotal requests: {total_requests}\n")
        
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        # Заголовок таблицы
        print(f"{'HANDLER':<30} {'DEBUG':>8} {'INFO':>8} {'WARNING':>8} {'ERROR':>8} {'CRITICAL':>8}")
        
        totals = {}  # Суммы по уровням логирования
        for route in sorted(stats.keys()):
            row = f"{route:<30}"
            for level in levels:
                count = stats[route].get(level, 0)
                totals[level] = totals.get(level, 0) + count
                row += f"{count:>8}"
            print(row)
        
        # Итоговая строка
        total_row = f"{'':<30}"
        for level in levels:
            total_row += f"{totals.get(level, 0):>8}"
        print(total_row)

    def generate(self):
        """Генерирует отчет, используя многопроцессную обработку."""
        if not self.log_files:
            print("Нет файлов для обработки.")
            return

        output_queue = mp.Queue()  # Очередь для результатов
        processes = []

        # Запускаем процесс для каждого лог-файла
        for log_file in self.log_files:
            process = mp.Process(
                target=self.process_log_file,
                args=(log_file, output_queue)
            )
            processes.append(process)
            process.start()

        # Дожидаемся завершения всех процессов
        for process in processes:
            process.join()

        results = []
        # Извлекаем результаты из очереди
        for _ in range(len(self.log_files)):
            try:
                result = output_queue.get(timeout=5)
                results.append(result)
            except Empty:
                break

        if not results:
            return

        # Агрегируем и выводим результаты
        aggregated_stats, total_requests = self.aggregate_stats(results)
        self.print_table(aggregated_stats, total_requests)

if __name__ == "__main__":
    # Сопоставление типов отчетов с классами
    parametr_to_class = {
        "handlers": HandlersReport
    }
    
    # Настройка парсера аргументов
    parser = argparse.ArgumentParser(description="Анализатор журнала логов")
    parser.add_argument("logs", nargs="+", help="Список лог-файлов")
    parser.add_argument("--report", help="Тип отчета")
    args = parser.parse_args()
    
    log_files = args.logs
    
    # Создаем экземпляр отчета (по умолчанию DefaultReport)
    report = parametr_to_class.get(args.report, DefaultReport)(log_files)
    report.generate()