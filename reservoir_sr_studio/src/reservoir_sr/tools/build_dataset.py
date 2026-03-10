from __future__ import annotations

import argparse
from pathlib import Path

from reservoir_sr.features.simulation.application.dataset_generation_service import (
    DatasetGenerationService,
    build_default_cases,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build raw simulation cases through the gRPC service.")
    parser.add_argument("--endpoint", default="localhost:5000")
    parser.add_argument("--out-dir", default="tmp/sr_dataset_out")
    parser.add_argument("--case-count", type=int, default=8)
    parser.add_argument("--steps", type=int, default=256)
    parser.add_argument("--nx", type=int, default=16)
    parser.add_argument("--nzm", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    args = parser.parse_args()

    service = DatasetGenerationService(endpoint=args.endpoint)
    outputs = service.build_batch(
        cases=build_default_cases(args.case_count, args.nzm),
        base_output_dir=Path(args.out_dir),
        nx=args.nx,
        steps=args.steps,
        workers=args.workers,
        poll_seconds=args.poll_seconds,
    )
    print(f"Generated {len(outputs)} dataset files in {args.out_dir}")


if __name__ == "__main__":
    main()
