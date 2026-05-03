from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[5]
    proto = root / "simulator" / "Simulation.Contracts" / "Protos" / "simulation.proto"
    out_dir = Path(__file__).resolve().parent / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{proto.parent}",
        f"--python_out={out_dir}",
        f"--grpc_python_out={out_dir}",
        str(proto),
    ]
    subprocess.run(cmd, check=True)
    print(f"Generated Python gRPC stubs into: {out_dir}")


if __name__ == "__main__":
    main()
