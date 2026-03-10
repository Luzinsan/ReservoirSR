from __future__ import annotations

import numpy as np

from reservoir_sr.features.simulation.application.dataset_view_service import DatasetViewService
from reservoir_sr.infrastructure.storage.sr_archive_io import write_sr_archive


def test_dataset_view_service_loads_archive_and_extracts_frame(tmp_path) -> None:
    archive_path = tmp_path / "sample.sr"
    arrays = {
        "lr_fields": np.arange(24, dtype=np.float32).reshape(2, 3, 2, 2),
        "hr_fields": np.arange(48, dtype=np.float32).reshape(2, 3, 2, 4),
    }
    metadata = {"channels": ["P", "ST", "SB"], "steps": 2, "description": "sample"}
    write_sr_archive(archive_path, arrays, metadata)

    service = DatasetViewService()
    archive = service.load_archive(archive_path)
    frame = service.frame(archive, "hr_fields", step_index=1, channel_index=2)
    description = service.describe(archive)

    assert archive.metadata["description"] == "sample"
    assert np.array_equal(frame.values, arrays["hr_fields"][1, 2])
    assert description["arrays"]["lr_fields"] == (2, 3, 2, 2)
