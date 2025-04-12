import pytest
import os
import tempfile
import multiprocessing as mp
from main import HandlersReport, DefaultReport

@pytest.fixture
def temp_log_file():
    """Создает временный лог-файл с тестовыми данными."""
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
        f.write("2023-10-10 12:00:00 django.request INFO /api/users/ ...\n")
        f.write("2023-10-10 12:01:00 django.request ERROR /api/users/ ...\n")
        f.write("2023-10-10 12:02:00 django.request DEBUG /api/posts/ ...\n")
        f.write("2023-10-10 12:03:00 other.line WARNING /api/users/ ...\n")  # Не django.request
    yield f.name
    os.unlink(f.name)

@pytest.fixture
def empty_log_file():
    """Создает пустой временный лог-файл."""
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
        pass
    yield f.name
    os.unlink(f.name)

def test_handlers_report_empty_file(empty_log_file, capsys):
    """Проверяет обработку пустого файла."""
    report = HandlersReport([empty_log_file])
    report.generate()
    captured = capsys.readouterr()
    assert "Файл" in captured.out
    assert "пуст" in captured.out

def test_handlers_report_valid_file(temp_log_file):
    """Проверяет обработку файла с корректными данными."""
    report = HandlersReport([temp_log_file])
    output_queue = mp.Queue()
    report.process_log_file(temp_log_file, output_queue)
    stats, total_requests = output_queue.get(timeout=5)
    
    assert total_requests == 3
    assert stats == {
        '/api/users/': {'INFO': 1, 'ERROR': 1},
        '/api/posts/': {'DEBUG': 1}
    }

def test_handlers_report_nonexistent_file(capsys):
    """Проверяет обработку несуществующего файла."""
    report = HandlersReport(["nonexistent.log"])
    report.generate()
    captured = capsys.readouterr()
    assert "Файл nonexistent.log не найден" in captured.out

def test_aggregate_stats():
    """Проверяет агрегацию статистики."""
    report = HandlersReport([])
    results = [
        ({'/api/users/': {'INFO': 1, 'ERROR': 1}, '/api/posts/': {'DEBUG': 1}}, 3),
        ({'/api/users/': {'INFO': 2}, '/api/comments/': {'WARNING': 1}}, 3)
    ]
    aggregated_stats, total_requests = report.aggregate_stats(results)
    
    assert total_requests == 6
    assert aggregated_stats == {
        '/api/users/': {'INFO': 3, 'ERROR': 1},
        '/api/posts/': {'DEBUG': 1},
        '/api/comments/': {'WARNING': 1}
    }

def test_default_report(capsys):
    """Проверяет поведение DefaultReport."""
    report = DefaultReport([])
    report.generate()
    captured = capsys.readouterr()
    assert "Указан неверный тип отчета!" in captured.out