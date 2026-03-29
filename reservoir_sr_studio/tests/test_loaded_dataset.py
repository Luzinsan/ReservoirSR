from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from reservoir_sr.domain.simulation.dataset_models import (
    LoadedDataset,
    normalize_condition_spec,
)
from reservoir_sr.infrastructure.storage.sr_archive_io import load_sr_archive
from reservoir_sr.infrastructure.ml.sr_frame_dataset import SrFrameDataset

ARCHIVE_PATH = Path(__file__).resolve().parents[1] / "dataset" / "campaign_8f2cc29aae_case_00000.npz"


# ------------------------------------------------------------------
# LoadedDataset: field_tensor + condition methods
# ------------------------------------------------------------------


def test_field_tensor_shape_and_dtype() -> None:
    arrays, metadata = load_sr_archive(ARCHIVE_PATH)
    ds = LoadedDataset(arrays, metadata)

    lr = ds.field_tensor(0, "lr")
    hr = ds.field_tensor(0, "hr")

    assert lr.dtype == np.float32
    assert hr.dtype == np.float32
    assert lr.flags["C_CONTIGUOUS"]
    assert hr.flags["C_CONTIGUOUS"]
    assert lr.shape == (3, 50, 100)
    assert hr.shape == (3, 200, 400)


def test_condition_scalars_full() -> None:
    arrays, metadata = load_sr_archive(ARCHIVE_PATH)
    ds = LoadedDataset(arrays, metadata)

    dyn = ds.dynamic_scalars_at(0)
    stat = ds.static_scalars()
    lay = ds.layer_scalars_flat()

    assert dyn.shape == (14,)
    assert stat.shape == (57,)
    assert lay.shape == (60,)


def test_condition_scalars_filtered() -> None:
    arrays, metadata = load_sr_archive(ARCHIVE_PATH)
    ds = LoadedDataset(arrays, metadata)

    dyn = ds.dynamic_scalars_at(0, ["time", "AI"])
    assert dyn.shape == (2,)
    assert float(dyn[0]) == float(ds.dynamic_scalars_at(0)[0])

    stat = ds.static_scalars(["NB", "NX"])
    assert stat.shape == (2,)
    assert float(stat[0]) == 5.0

    lay = ds.layer_scalars_flat(["NZM", "HBM"])
    assert lay.shape == (10,)  # 5 layers * 2 features


def test_normalize_condition_spec() -> None:
    from_tuple = normalize_condition_spec(("dynamic", "layers"))
    assert from_tuple == {"dynamic": None, "layers": None}

    from_dict = normalize_condition_spec({"static": ["NB"]})
    assert from_dict == {"static": ["NB"]}

    from_empty = normalize_condition_spec(())
    assert from_empty == {}


# ------------------------------------------------------------------
# SrFrameDataset
# ------------------------------------------------------------------


def test_sr_frame_dataset_length() -> None:
    ds = SrFrameDataset([ARCHIVE_PATH], cache_size=4)
    assert len(ds) == 100  # 1 archive * 100 steps


def test_sr_frame_dataset_sample_shapes() -> None:
    ds = SrFrameDataset([ARCHIVE_PATH], cache_size=4)
    sample = ds[0]

    assert isinstance(sample["lr"], torch.Tensor)
    assert isinstance(sample["hr"], torch.Tensor)
    assert isinstance(sample["condition"], torch.Tensor)

    assert sample["lr"].shape == (3, 50, 100)
    assert sample["hr"].shape == (3, 200, 400)
    assert sample["condition"].shape == (131,)  # 14 + 57 + 60
    assert sample["lr"].dtype == torch.float32


def test_sr_frame_dataset_no_condition() -> None:
    ds = SrFrameDataset([ARCHIVE_PATH], cache_size=4, condition=())
    sample = ds[0]

    assert "lr" in sample
    assert "hr" in sample
    assert "condition" not in sample


def test_sr_frame_dataset_partial_condition() -> None:
    ds = SrFrameDataset([ARCHIVE_PATH], cache_size=4, condition=("dynamic",))
    sample = ds[0]

    assert sample["condition"].shape == (14,)


def test_sr_frame_dataset_filtered_condition() -> None:
    ds = SrFrameDataset(
        [ARCHIVE_PATH],
        cache_size=4,
        condition={"dynamic": ["time", "AI"], "static": None},
    )
    sample = ds[0]

    assert sample["condition"].shape == (2 + 57,)


def test_sr_frame_dataset_all_steps_accessible() -> None:
    ds = SrFrameDataset([ARCHIVE_PATH], cache_size=4)
    first = ds[0]
    last = ds[99]

    assert not torch.equal(first["lr"], last["lr"])
    assert not torch.equal(first["condition"], last["condition"])
