from __future__ import annotations

import numpy as np

from reservoir_sr.infrastructure.storage.sr_archive_io import load_sr_archive, write_sr_archive


def test_sr_archive_round_trip(tmp_path) -> None:
    archive_path = tmp_path / "sample.sr"
    arrays = {
        "lr_fields": np.arange(24, dtype=np.float32).reshape(2, 3, 2, 2),
        "dynamic_scalars": np.arange(10, dtype=np.float32).reshape(2, 5),
    }
    metadata = {"channels": ["P", "ST", "SB"], "steps": 2}

    write_sr_archive(archive_path, arrays, metadata)
    loaded_arrays, loaded_metadata = load_sr_archive(archive_path)

    assert loaded_metadata == metadata
    assert set(loaded_arrays) == set(arrays)
    for name, values in arrays.items():
        assert np.array_equal(loaded_arrays[name], values)
