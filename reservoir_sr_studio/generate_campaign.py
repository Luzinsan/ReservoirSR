#!/usr/bin/env python3
"""Генерация кампании с варьированной проницаемостью по слоям - минимальная версия."""

import logging
import sys
from pathlib import Path

import grpc
import numpy as np

# Импортируем только protobuf напрямую
sys.path.insert(0, str(Path(__file__).parent / "src"))
from reservoir_sr.infrastructure.grpc.generated import simulation_pb2, simulation_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def create_base_config(lr_nx, tu_seconds, epsp):
    """Создаёт базовую конфигурацию симулятора."""
    return dict(
        nb=5, vl=100, lod=0, liz=1, r_skv=0.1,
        ro1_pl=806.0, ro1_deg=870.0, mu1_pl=40.0, mu_deg=26.0, ap1=0.0009, at1=0.00125, c_p_1=1.88,
        ro3_pl=1020.0, mu3_pl=1.6, c_p_3=4.15, ap3=0.0004, at3=0.0008,
        r00=1.12, c_p_2=2.7, ves_g_mol=16.04, ytap2=0.0008, dzt=0.0035, zg=0.941,
        r_c_r=1.0, qunt_cr=140.0, radz0=6.0, sm=0.025, s_t_r=167.5,
        vg0=40.0, ph0=12.0, bt=0.02, bg=0.004, bt_cp=1e-5, bt_tr=1e-5,
        mu_pazp=8.0, x_a=1.0, x_d=0.25, q_zab=50.0, obv_p=180, qq=300, p32=130.0,
        tvk=6, tk_days=1000.3, ltvk=0, ltk=1, dso=30,
        tu_seconds=tu_seconds, n_dr=10, nx=lr_nx, epsp=epsp,
        enb=0.001, evb=0.001, ent=1e-4, evt=0.001,
        tim_0=5000, tim_1=10000, tim_2=10000,
    )


def create_default_layers():
    """5 слоёв с дефолтными значениями."""
    layers = []
    for i in range(5):
        layer = dict(nzm=4, hbm=2, vmb=0.2, vmt=0.04, lwn=1, lwd=0, snt=0.1, snb=0.2, svt=0.9, svb=0.8, akt=0.1, akb=0.01)
        layers.append(layer)
    # Специфичные настройки слоёв 4 и 5
    layers[3]["lwn"] = 0
    layers[3]["akt"] = 0.03
    layers[3]["akb"] = 0.001
    layers[4]["snt"] = 0.0
    layers[4]["svt"] = 1.0
    layers[4]["snb"] = 0.0
    layers[4]["svb"] = 1.0
    layers[4]["lwn"] = 0
    layers[4]["lwd"] = 1
    return layers


def sample_lhs(n_samples, n_dims, seed):
    """Latin Hypercube Sampling."""
    rng = np.random.default_rng(seed)
    u = (np.arange(n_samples, dtype=np.float64) + rng.random(n_samples)) / n_samples
    dims = np.zeros((n_samples, n_dims), dtype=np.float64)
    for idx in range(n_dims):
        perm = rng.permutation(u)
        dims[:, idx] = perm
    return dims


def map_to_range(unit, low, high, scale="linear"):
    """Маппинг из [0,1] в [low, high]."""
    if scale == "log10":
        low, high = np.log10(low), np.log10(high)
        return np.power(10.0, low + (high - low) * unit)
    return low + (high - low) * unit


def apply_layer_akt(layers, layer_idx, value):
    layers[layer_idx]["akt"] = max(1e-8, float(value))
    return layers


def apply_layer_akb(layers, layer_idx, value):
    layers[layer_idx]["akb"] = max(1e-8, float(value))
    return layers


def generate_cases(n_samples, seed, base_config, layers_template):
    """Генерирует кейсы с варьированной проницаемостью по слоям."""
    # 10 параметров: layer_0_akt, layer_0_akb, ..., layer_4_akt, layer_4_akb
    param_names = []
    param_ranges = []
    for i in range(5):
        if i == 3:  # Слой 4 - низкопроницаемый
            param_names.extend([f"layer_{i}_akt", f"layer_{i}_akb"])
            param_ranges.append((0.01, 0.1, "log10"))
            param_ranges.append((0.0005, 0.005, "log10"))
        else:
            param_names.extend([f"layer_{i}_akt", f"layer_{i}_akb"])
            param_ranges.append((0.05, 0.5, "log10"))
            param_ranges.append((0.005, 0.05, "log10"))

    lhs_samples = sample_lhs(n_samples, len(param_names), seed)

    for case_idx in range(n_samples):
        layers = [dict(l) for l in layers_template]  # Копия
        for dim_idx, (name, (low, high, scale)) in enumerate(zip(param_names, param_ranges)):
            layer_idx = int(name.split("_")[1])
            value = map_to_range(lhs_samples[case_idx, dim_idx], low, high, scale)
            if name.endswith("_akt"):
                apply_layer_akt(layers, layer_idx, value)
            else:
                apply_layer_akb(layers, layer_idx, value)

        case_id = f"permeability_campaign_001_case_{case_idx:05d}"
        yield case_id, layers


def to_proto_layers(simulation_pb2, layers):
    return [
        simulation_pb2.LayerConfig(
            nzm=l["nzm"], hbm=l["hbm"], vmb=l["vmb"], vmt=l["vmt"],
            lwn=l["lwn"], lwd=l["lwd"], snt=l["snt"], snb=l["snb"],
            svt=l["svt"], svb=l["svb"], akt=l["akt"], akb=l["akb"]
        ) for l in layers
    ]


def to_proto_config(simulation_pb2, base_cfg, layers):
    cfg = dict(base_cfg)
    cfg["layers"] = to_proto_layers(simulation_pb2, layers)
    return simulation_pb2.SimulationConfig(**cfg)


def main():
    output_dir = Path("/mnt/home/dataset")
    output_dir.mkdir(parents=True, exist_ok=True)

    n_samples = 100
    seed = 42
    steps = 500
    snapshot_stride = 1
    lr_nx = 100
    hr_nx = 400
    tu_seconds = 86.4
    epsp = 1e-6

    logger.info(f"Генерация кампании: {n_samples} симуляций, seed={seed}")
    logger.info(f"Output: {output_dir}")

    base_config = create_base_config(lr_nx, tu_seconds, epsp)
    layers_template = create_default_layers()

    channel = grpc.insecure_channel("localhost:5000")
    stub = simulation_pb2_grpc.SimulationServiceStub(channel)
    logger.info("Подключено к симулятору gRPC (localhost:5000)")

    submitted = 0
    failed = 0

    for case_id, layers in generate_cases(n_samples, seed, base_config, layers_template):
        try:
            proto_cfg = to_proto_config(simulation_pb2, base_config, layers)
            response = stub.RunDatasetJob(
                simulation_pb2.RunDatasetJobRequest(
                    job_id=case_id,
                    output_dir=str(output_dir),
                    steps=steps,
                    config=proto_cfg,
                    snapshot_stride=snapshot_stride,
                    hr_nx=hr_nx,
                )
            )
            if response.ok:
                submitted += 1
                if submitted % 10 == 0 or submitted == n_samples:
                    logger.info(f"Отправлено {submitted}/{n_samples} задач")
            else:
                failed += 1
                logger.warning(f"Кейс {case_id} отклонён: {response.message}")
        except Exception as e:
            failed += 1
            logger.error(f"Ошибка кейса {case_id}: {e}")

    logger.info(f"Всего отправлено: {submitted}, ошибок: {failed}")
    logger.info("Задачи запущены в фоне.")
    channel.close()


if __name__ == "__main__":
    main()
