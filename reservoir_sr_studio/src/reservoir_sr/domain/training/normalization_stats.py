from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class FeatureStats:
    """Statistics for a single feature. """

    min: float
    max: float
    mean: float
    std: float
    log_min: float | None = None
    log_max: float | None = None
    log_mean: float | None = None
    log_std: float | None = None


@dataclass
class NormalizationStats:
    """Per-parameter normalization statistics for the full SR pipeline.

    LR and HR fields have separate stats so that inference can normalise
    the LR input and denormalise the SR output independently.
    """

    lr_fields: dict[str, FeatureStats]
    hr_fields: dict[str, FeatureStats]
    dynamic: dict[str, FeatureStats]
    static: dict[str, FeatureStats]
    layers: dict[str, FeatureStats]

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        def _ser(group: dict[str, FeatureStats]) -> dict:
            return {name: asdict(fs) for name, fs in group.items()}

        payload = {
            "lr_fields": _ser(self.lr_fields),
            "hr_fields": _ser(self.hr_fields),
            "dynamic": _ser(self.dynamic),
            "static": _ser(self.static),
            "layers": _ser(self.layers),
        }
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8",
        )

    @classmethod
    def from_json(cls, path: Path) -> NormalizationStats:
        raw = json.loads(path.read_text(encoding="utf-8"))

        def _deser(group: dict) -> dict[str, FeatureStats]:
            return {name: FeatureStats(**vals) for name, vals in group.items()}

        return cls(
            lr_fields=_deser(raw["lr_fields"]),
            hr_fields=_deser(raw["hr_fields"]),
            dynamic=_deser(raw["dynamic"]),
            static=_deser(raw["static"]),
            layers=_deser(raw["layers"]),
        )
