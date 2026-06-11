# Reservoir SR

Платформа супер-разрешения трещиновато-пористых нефтяных коллекторов на базе .NET-симулятора и PyTorch-моделей.

## Содержание

- [Требования](#требования)
- [Структура](#структура)
- [Установка](#установка)
- [Запуск](#запуск)
- [Конфигурация](#конфигурация)
- [Типовые сценарии](#типовые-сценарии)

## Требования

- **.NET SDK 8.0**
- **Python 3.10+**
- **CUDA 12.1** (опционально, для обучения на GPU)
- Linux x64

## Структура

| Каталог | Назначение |
|---|---|
| `simulator/` | .NET-симулятор фильтрации (gRPC-сервер) |
| `reservoir_sr_studio/` | Python-приложение: GUI, обучение, инференс |
| `artifacts/` | Чекпоинты, статистика, экспортированные ONNX |

## Установка

### Симулятор

```bash
dotnet build simulator/Simulation.Server/Simulation.Server.csproj -c Release
```

### Python-окружение

```bash
# базовая установка (UI + gRPC-клиент)
pip install -e reservoir_sr_studio

# с ML-зависимостями (torch, lightning, hydra, mlflow, torchmetrics, onnx*)
pip install -e "reservoir_sr_studio[ml]"

# с dev-инструментами (pytest, ruff, grpcio-tools)
pip install -e "reservoir_sr_studio[dev]"
```

### Генерация gRPC-стабов

После установки в editable-режиме доступна консольная команда:

```bash
reservoir-sr-generate-proto
```

Она генерирует `simulation_pb2.py` и `simulation_pb2_grpc.py` в `reservoir_sr_studio/src/reservoir_sr/infrastructure/grpc/generated/` из `simulator/Simulation.Contracts/Protos/simulation.proto`. Требуется группа `[dev]` (`grpcio-tools`).

## Запуск

Все компоненты запускаются независимо. Минимальный сценарий — только GUI; симулятор нужен для генерации данных и runtime-режима.

### 1. gRPC-сервер симулятора

Слушает порт `5000` (HTTP/2).

```bash
dotnet run --project simulator/Simulation.Server -c Release
```

В фоне:

```bash
nohup dotnet run -c Release > server.log 2>&1 &
```

### 2. Доступные консольные команды

После `pip install -e .`:

- `reservoir-sr-studio` — десктоп-приложение (PySide6)
- `reservoir-sr-build-dataset` — сборка датасета
- `reservoir-sr-generate-proto` — генерация gRPC-стабов
- `reservoir-sr-train` — обучение SR/GAN-моделей через Hydra

По умолчанию клиент ходит на gRPC-сервер по адресу `localhost:5000`; изменить можно в настройках UI (Settings → General → gRPC endpoint) либо флагом `--endpoint` в `generate_campaign.py`.


### 3. MLflow UI

```bash
mlflow ui --host 127.0.0.1 --port 5001
```

Tracking URI берётся из `conf/globals/default.yaml` (по умолчанию `http://127.0.0.1:5001`).



### 4. Обучение модели (CLI)

```bash
cd reservoir_sr_studio
python -m reservoir_sr.tools.train +experiment=srresnet_baseline
```

Доступные эксперименты: `srresnet_baseline`, `mdsr_baseline`, `mdsr_conditioned`, `rfdn`, `gan_srresnet`, `gan_rfdn`, `gan_mdsr`.

### 5. Экспорт чекпоинтов в ONNX

```bash
cd reservoir_sr_studio
python -m reservoir_sr.tools.export
```

Параметры берутся из `conf/export.yaml`. Возможны два режима:

- **Пакетный** — `source_dir` + `destination_dir`: все `.ckpt` из папки экспортируются в `destination_dir/<basename(source_dir)>/`.
- **Одиночный** — `source_checkpoint` + `output_path`.

Переопределение из CLI:

```bash
python -m reservoir_sr.tools.export \
  source_dir=/path/to/checkpoints \
  destination_dir=/path/to/onnx
```

## GUI

Вкладки:

- **Data** — runtime-симуляция, генерация датасета, просмотр архивов
- **Evaluation** — сравнение SR-модели с эталоном HR на готовых архивах

Перед использованием Evaluation и SR-overlay укажите в **Settings → Inference**:

- **Default model dir** — папка с экспортированными `.onnx`
- **Stats file (JSON)** — путь к `stats.json` (по нему была обучена модель)

## Типовые сценарии

### Сгенерировать датасет

1. Запустить gRPC-сервер.
2. Открыть GUI → **Data** → **Simulation generation**.
3. Указать `Output dir`, `Steps`, `LR NX`, `HR NX`.
4. Выбрать режим (`Single` / `Campaign`) и нажать **Start**.

Архивы сохраняются как `<job_id>.npz` в указанной папке.

### Обучить модель

```bash
python -m reservoir_sr.tools.train +experiment=srresnet_baseline
```

Чекпоинты: `artifacts/checkpoints/<experiment>/`.
Метрики: MLflow UI.

### Экспортировать обученную модель

```bash
python -m reservoir_sr.tools.export \
  source_dir=artifacts/checkpoints/srresnet_baseline \
  destination_dir=artifacts/checkpoints/export
```

### Оценить модель в GUI

1. Settings → Inference → указать `Default model dir` и `Stats file`.
2. GUI → вкладка **Evaluation** → выбрать модель, сплит, архив.

### Просмотр SR-апскейла во время runtime-симуляции

1. GUI → **Data** → **Runtime** → запустить симуляцию.
2. В правой панели **Maps** выбрать `Режим карты: SR (нейросеть)` и указать модель в combo `SR-модель`.