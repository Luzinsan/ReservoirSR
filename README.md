# Reservoir SR Studio

Desktop-приложение для **Super-Resolution** карт давления и насыщенности в задачах моделирования нефтяных пластов. Включает runtime-симулятор, инструменты генерации датасетов, обучение нейросетей (вынесено в отдельный CLI) и валидацию обученных моделей.

## Демонстрация

### Runtime-симуляция с восстановлением через SR-модели
Карты низкого разрешения, генерируемые симулятором в реальном времени, апскейлятся обученной нейросетью на лету.

<video src="demo/runtime_simulator_demo.mp4" controls width="100%"></video>

### Валидация модели на тестовом архиве
Покадровое сравнение `LR / SR / HR / |HR-SR|` по трём каналам (`P`, `ST`, `SB`).

<video src="demo/models_validation_demo.mp4" controls width="100%"></video>

---

## Возможности

- **Data tab** — запуск симуляции пласта, просмотр карт и метрик, генерация датасетов в формате `.npz`.
- **Evaluation tab** — сравнение SR-моделей (ONNX) на архивах по всем timestep'ам.
- **CLI** — обучение и экспорт моделей в ONNX через Hydra-конфиги.

## Установка

```bash
git clone <repo-url>
cd reservoir_sr_studio
uv sync           # или: poetry install
```

Требования: **Python 3.10.12**, PySide6, PyTorch ≥ 2.11, ONNX Runtime.

## Запуск GUI

```bash
uv run reservoir-sr-studio
```

При первом запуске откройте `Settings` и укажите пути:
- **Data** — путь к JSON-конфигу симуляции
- **Inference** — папка с ONNX-моделями, файл статистики, входная папка с архивами

## Обучение моделей (CLI)

Конфигурация через Hydra (см. `src/reservoir_sr/conf/`):

```bash
# mdsr архитектура
python -m reservoir_sr.tools.train +experiment=mdsr_baseline


# GAN-вариант
python -m reservoir_sr.tools.train +experiment=gan_srresnet
```

Доступные эксперименты: `mdsr_baseline`, `mdsr_conditioned`, `rfdn`, `srresnet_baseline`, `gan_mdsr`, `gan_rfdn`, `gan_srresnet`.

Все логи и чекпойнты — в `${artifacts_dir}` (по умолчанию `/mnt/home/ReservoirSR/artifacts`), метрики — в MLflow (`http://127.0.0.1:5001`).

## Экспорт в ONNX

```bash
python -m reservoir_sr.tools.export
```

Параметры (входной чекпойнт, выходной путь, EMA-веса) — в `conf/export.yaml`.

## Структура конфигов

```
src/reservoir_sr/conf/
├── train.yaml              # корневой конфиг обучения
├── export.yaml             # экспорт в ONNX
├── data/                   # источник данных, condition, нормализация
├── model/                  # mdsr, rfdn, srresnet + optimizer/scheduler/loss
├── gan/                    # GAN-конфиги (generator + discriminator)
├── experiment/             # готовые сценарии запуска
├── trainer/                # параметры Lightning Trainer
└── gui/                    # настройки GUI (general, data, inference)
```

## Архитектура моделей

- **MDSR** — multi-scale residual SR с опциональным FiLM-кондиционированием на 131-мерном векторе физических параметров (динамика + статика + слои пласта).
- **RFDN** — лёгкая residual feature distillation network.
- **MSRResNet** — компактный SRResNet-генератор для GAN-режима.
- **GAN-варианты** — те же генераторы + Residual PatchGAN дискриминатор + физический perceptual loss (Sobel + spectral L1).

Все модели работают со scale=4 и тремя каналами (`P`, `ST`, `SB`).

## Лицензия

Внутренний проект.