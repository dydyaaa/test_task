import pytest
import tempfile
import os
from main import HandlersReport

LOG_SAMPLE = """
2025-04-12 10:12:45,123 django.request INFO /home/ Обработка запроса
2025-04-12 10:12:46,456 django.request ERROR /home/ Ошибка при обработке
2025-04-12 10:12:47,789 django.request WARNING /about/ Предупреждение
2025-04-12 10:12:48,000 django.request INFO /about/ Всё нормально
2025-04-12 10:12:49,000 some.other.module DEBUG /other/ Не тот модуль
"""

@pytest.fixture
def temp_log_file():
    """Создаёт временный лог-файл с данными."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        f.write(LOG_SAMPLE)
        temp_name = f.name
    yield temp_name
    os.remove(temp_name)

def test_process_log_file(temp_log_file):
    """Проверяет, что process_log_file правильно парсит лог."""
    import multiprocessing as mp
    queue = mp.Queue()
    report = HandlersReport([temp_log_file])
    
    report.process_log_file(temp_log_file, queue)
    stats, total = queue.get()

    assert total == 4  # Только строки с django.request
    assert stats['/home/']['INFO'] == 1
    assert stats['/home/']['ERROR'] == 1
    assert stats['/about/']['WARNING'] == 1
    assert stats['/about/']['INFO'] == 1
    assert '/other/' not in stats

def test_aggregate_stats():
    """Проверяет, что aggregate_stats правильно суммирует статистику."""
    report = HandlersReport([])
    input_data = [
        ({'/home/': {'INFO': 2}, '/about/': {'ERROR': 1}}, 3),
        ({'/home/': {'ERROR': 1}}, 1),
    ]
    agg_stats, total = report.aggregate_stats(input_data)

    assert total == 4
    assert agg_stats['/home/']['INFO'] == 2
    assert agg_stats['/home/']['ERROR'] == 1
    assert agg_stats['/about/']['ERROR'] == 1

def test_print_table(capsys):
    """Проверяет, что print_table выводит корректную таблицу."""
    report = HandlersReport([])
    stats = {
        '/home/': {'INFO': 2, 'ERROR': 1},
        '/about/': {'WARNING': 1}
    }
    total_requests = 4

    report.print_table(stats, total_requests)
    captured = capsys.readouterr()
    assert "Total requests: 4" in captured.out
    assert "/home/" in captured.out
    assert "/about/" in captured.out
    assert "INFO" in captured.out
    assert "ERROR" in captured.out
    assert "WARNING" in captured.out
