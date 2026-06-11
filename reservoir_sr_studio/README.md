## Reservoir SR Studio

`reservoir_sr_studio` is the new Python package for simulation runtime, dataset generation, dataset packing, dataset validation, and desktop UI wiring.

## Training quick start

Install ML dependencies first:

```bash
pip install -e .[ml]
```

Training logs are written to **MLflow** (TensorBoard is not used).

- Start MLFlow Server:
`mlflow server     --host 127.0.0.1     --port 5001     --backend-store-uri sqlite:////mnt/home/ReservoirSR/artifacts/mlflow/backend/mlflow.db     --default-artifact-root /mnt/home/ReservoirSR/artifacts/mlflow/artifacts`
- Default tracking URI: `http://127.0.0.1:5001`
- If needed, you can still override it from CLI:
  - `reservoir-sr-train +experiment=mdsr_baseline globals.mlflow.tracking_uri=file:./mlruns`

To open local MLflow UI:

```bash
mlflow ui --host 127.0.0.1 --port 5001
```

All commands below are run from `reservoir_sr_studio`:

```bash
reservoir-sr-train +experiment=<experiment_name>
```

By default, trainer config is set for **1x H100** (`gpu`, `devices=1`, `bf16-mixed`).

### SR baselines (generator-only)

- MDSR baseline:
  - `reservoir-sr-train +experiment=mdsr_baseline`
- MDSR conditioned (FiLM):
  - `reservoir-sr-train +experiment=mdsr_conditioned`
- RRDB baseline:
  - `reservoir-sr-train +experiment=rrdb_baseline`
- Lightweight SRResNet/MSRResNet baseline:
  - `reservoir-sr-train +experiment=srresnet_baseline`

### GAN training

- SRGAN-like setup:
  - Generator: `MSRResNet`
  - Discriminator: `SRResNetDiscriminator`
  - Command: `reservoir-sr-train +experiment=gan_srresnet`
- ESRGAN-like setup:
  - Generator: `RRDBNet`
  - Discriminator: `ESRGANDiscriminator`
  - Command: `reservoir-sr-train +experiment=gan_esrgan`

### Useful overrides

- Reduce epochs for smoke run:
  - `reservoir-sr-train +experiment=gan_srresnet trainer.max_epochs=5`
- Switch dataset normalization:
  - `reservoir-sr-train +experiment=mdsr_baseline data/norm=log_pressure`
- Resume from checkpoint:
  - `reservoir-sr-train +experiment=gan_esrgan globals.resume_from=/path/to/ckpt.ckpt`

