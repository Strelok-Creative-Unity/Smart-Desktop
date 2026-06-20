# Тесты памяти Smart Desktop

> **Примечание:** этот набор тестов был написан нейросетью (AI) в рамках диагностики потребления RAM в KDE HTML Wallpaper (QtWebEngine). Код не проходил ручной ревью «с нуля» — при использовании в CI или продакшене имеет смысл проверить результаты самостоятельно.

## Зачем

Имитация условий KDE HTML Wallpaper:

- Chromium / QtWebEngine, протокол `file://`
- viewport 1920×1080
- ускоренная смена всех кадров обоев (day + night)
- сбор RSS процессов, in-page логов и CDP-дампа памяти

## Установка

```bash
pip install -r test/requirements.txt
```

## Запуск

```bash
# Быстрый прогон
python3 test/run-memory-test.py --cycles 6 --interval 400 --transition 100

# Полная диагностика (95 кадров, MEMLOG на каждый кадр, heap snapshots)
./test/run-full-diagnostic.sh

# Сравнение fixed (текущий код) vs legacy (старое поведение без очистки img)
./test/compare-modes.sh 95 500 150
```

### Основные параметры `run-memory-test.py`

| Флаг | Описание |
|------|----------|
| `--mode fixed\|legacy` | fixed — с фиксом памяти; legacy — для сравнения |
| `--cycles N` | число переключений кадров |
| `--interval MS` | пауза между переключениями |
| `--transition MS` | длительность кроссфейда |
| `--log-every N` | частота MEMLOG (1 = каждый кадр) |
| `--snapshots none\|end\|all` | heap snapshots (по умолчанию `none`) |
| `--port N` | порт CDP (Remote Debugging) |

## Структура

```
test/
├── memory-test.html      # точка входа теста
├── bootstrap.js          # загрузка скриптов, параметры из URL
├── harness.js            # ускоренный цикл по всем кадрам
├── legacy-image.js       # старая логика img (режим legacy)
├── run-memory-test.py    # раннер: Chromium + CDP + RSS
├── run-full-diagnostic.sh
├── compare-modes.sh
├── requirements.txt
└── output/               # артефакты прогонов (в .gitignore)
```

## Артефакты (`test/output/<timestamp>-<mode>/`)

| Файл | Содержимое |
|------|------------|
| `summary.json` | конфиг и итоговые метрики |
| `memory-rss.csv` | RSS по секундам |
| `memlogs.json` | состояние img/JS heap на каждом тике |
| `memory-dump.json` | CDP: DOM counters, Performance metrics |
| `heap-snapshots/*.heapsnapshot` | дампы для Chrome DevTools → Memory |
| `REPORT.md` | человекочитаемый отчёт (если создан) |

## Ограничения

- Это не unit-тесты, а **интеграционный стенд** с реальным Chromium и тяжёлыми PNG.
- Heap snapshots на больших обоях могут занимать минуты или падать по таймауту — для повседневной проверки достаточно `memory-rss.csv` и `memory-dump.json`.
- Точное поведение QtWebEngine в Plasma может незначительно отличаться от standalone Chromium.
