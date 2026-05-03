using Simulation.Core;
using Simulation.Core.Runtime;
using System.Collections.Concurrent;
namespace Simulation.Server.Services;

public sealed class DatasetJobManager
{
    private static readonly string[] DatasetFields = ["P", "ST", "SB"];

    private readonly ConcurrentDictionary<string, DatasetJobStatus> _jobs = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<string, SemaphoreSlim> _pauseGates = new(StringComparer.Ordinal);
    private readonly ILogger<DatasetJobManager> _logger;

    public DatasetJobManager(ILogger<DatasetJobManager> logger)
    {
        _logger = logger;
    }

    public DatasetJobStatus Start(RunDatasetSpec spec)
    {
        string jobId = string.IsNullOrWhiteSpace(spec.JobId) ? Guid.NewGuid().ToString("N") : spec.JobId;
        var status = new DatasetJobStatus(jobId, "queued", "Job queued", 0, spec.TotalSteps, spec.OutputDir);
        if (!_jobs.TryAdd(jobId, status))
        {
            throw new InvalidOperationException($"Job '{jobId}' already exists.");
        }

        _pauseGates[jobId] = new SemaphoreSlim(1, 1);

        _logger.LogInformation("Queue dataset job {JobId} output={OutputDir} steps={TotalSteps}", jobId, spec.OutputDir, spec.TotalSteps);
        _ = Task.Run(() => RunJobAsync(spec with { JobId = jobId }));
        return status;
    }

    public bool TryGet(string jobId, out DatasetJobStatus status)
    {
        return _jobs.TryGetValue(jobId, out status!);
    }

    public bool Cancel(string jobId)
    {
        if (!_jobs.TryGetValue(jobId, out var status))
        {
            return false;
        }

        _jobs[jobId] = status with { State = "cancelled", Message = "Cancelled by user." };
        ReleaseGate(jobId);
        _logger.LogInformation("Dataset job cancelled {JobId}", jobId);
        return true;
    }

    public bool Pause(string jobId)
    {
        if (!_jobs.TryGetValue(jobId, out var status))
        {
            return false;
        }

        if (status.State != "running")
        {
            return false;
        }

        if (!_pauseGates.TryGetValue(jobId, out var gate))
        {
            return false;
        }

        gate.Wait();
        _jobs[jobId] = status with { State = "paused", Message = "Paused by user." };
        _logger.LogInformation("Dataset job paused {JobId}", jobId);
        return true;
    }

    public bool Resume(string jobId)
    {
        if (!_jobs.TryGetValue(jobId, out var status))
        {
            return false;
        }

        if (status.State != "paused")
        {
            return false;
        }

        _jobs[jobId] = status with { State = "running", Message = "Resumed." };

        if (_pauseGates.TryGetValue(jobId, out var gate))
        {
            gate.Release();
        }

        _logger.LogInformation("Dataset job resumed {JobId}", jobId);
        return true;
    }

    public bool Remove(string jobId)
    {
        bool removed = _jobs.TryRemove(jobId, out _);
        if (_pauseGates.TryRemove(jobId, out var gate))
        {
            gate.Dispose();
        }
        return removed;
    }

    private async Task RunJobAsync(RunDatasetSpec spec)
    {
        string outputPath = Path.Combine(spec.OutputDir, $"{spec.JobId}.npz");
        string tempPath = outputPath + ".tmp";
        try
        {
            Directory.CreateDirectory(spec.OutputDir);

            ValidateDatasetConfig(spec.Config);
            SimulationConfig hrConfig = BuildHrConfig(spec.Config, spec.HrNx);
            int snapshotStride = Math.Max(spec.SnapshotStride, 1);
            int recordedSteps = (spec.TotalSteps + snapshotStride - 1) / snapshotStride;

            var lrRuntime = new SimulationRuntime();
            var hrRuntime = new SimulationRuntime();
            lrRuntime.Initialize(spec.Config);
            hrRuntime.Initialize(hrConfig);

            SimulationRuntimeMetadata lrMetadata = lrRuntime.GetMetadata();
            SimulationRuntimeMetadata hrMetadata = hrRuntime.GetMetadata();

            int steps = spec.TotalSteps;
            SetStatus(spec.JobId, "running", "Running", 0, steps, outputPath);
            _logger.LogInformation("Dataset job running {JobId} output={OutputPath}", spec.JobId, outputPath);

            using (
                var writer = new SrSimulationArchiveWriter(
                    tempPath,
                    spec.JobId,
                    recordedSteps,
                    spec.Config,
                    hrConfig,
                    lrMetadata,
                    hrMetadata
                )
            )
            {
                int lrDone = 0;
                int hrDone = 0;

                Task lrTask = Task.Run(async () =>
                {
                    double[] pressure = new double[lrMetadata.Nx * lrMetadata.Nz];
                    double[] saturationFractures = new double[lrMetadata.Nx * lrMetadata.Nz];
                    double[] saturationBlocks = new double[lrMetadata.Nx * lrMetadata.Nz];

                    for (int step = 0; step < steps; step++)
                    {
                        await WaitIfPausedAsync(spec.JobId);
                        if (IsCancelled(spec.JobId))
                        {
                            return;
                        }

                        SimulationStepResult result = lrRuntime.Step(1);
                        if (step % snapshotStride == 0)
                        {
                            ExportFields(lrRuntime, pressure, saturationFractures, saturationBlocks);
                            writer.WriteLrStep(pressure, saturationFractures, saturationBlocks);
                            writer.WriteDynamicStep(result);
                        }
                        int done = Interlocked.Exchange(ref lrDone, step + 1);
                        _ = done;
                        UpdateProgress(spec.JobId, Math.Min(lrDone, hrDone), steps, outputPath);
                        await Task.Yield();
                    }
                });

                Task hrTask = Task.Run(async () =>
                {
                    double[] pressure = new double[hrMetadata.Nx * hrMetadata.Nz];
                    double[] saturationFractures = new double[hrMetadata.Nx * hrMetadata.Nz];
                    double[] saturationBlocks = new double[hrMetadata.Nx * hrMetadata.Nz];

                    for (int step = 0; step < steps; step++)
                    {
                        await WaitIfPausedAsync(spec.JobId);
                        if (IsCancelled(spec.JobId))
                        {
                            return;
                        }

                        _ = hrRuntime.Step(1);
                        if (step % snapshotStride == 0)
                        {
                            ExportFields(hrRuntime, pressure, saturationFractures, saturationBlocks);
                            writer.WriteHrStep(pressure, saturationFractures, saturationBlocks);
                        }
                        int done = Interlocked.Exchange(ref hrDone, step + 1);
                        _ = done;
                        UpdateProgress(spec.JobId, Math.Min(lrDone, hrDone), steps, outputPath);
                        await Task.Yield();
                    }
                });

                await Task.WhenAll(lrTask, hrTask);

                if (IsCancelled(spec.JobId))
                {
                    _logger.LogInformation("Dataset job observed cancellation {JobId}", spec.JobId);
                    return;
                }
            }

            if (File.Exists(outputPath))
            {
                File.Delete(outputPath);
            }
            File.Move(tempPath, outputPath);

            SetStatus(spec.JobId, "completed", "Completed", steps, steps, outputPath);
            _logger.LogInformation("Dataset job completed {JobId}. file={OutputPath}", spec.JobId, outputPath);
        }
        catch (Exception ex)
        {
            if (File.Exists(tempPath))
            {
                File.Delete(tempPath);
            }

            SetStatus(spec.JobId, "failed", ex.Message, 0, spec.TotalSteps, outputPath);
            _logger.LogError(ex, "Dataset job failed {JobId}", spec.JobId);
        }
        finally
        {
            if (_pauseGates.TryRemove(spec.JobId, out var gate))
            {
                gate.Dispose();
            }
        }
    }

    private async Task WaitIfPausedAsync(string jobId)
    {
        if (!_pauseGates.TryGetValue(jobId, out var gate))
        {
            return;
        }

        await gate.WaitAsync();
        gate.Release();
    }

    private static void ExportFields(SimulationRuntime runtime, double[] pressure, double[] saturationFractures, double[] saturationBlocks)
    {
        runtime.GetFieldTo(DatasetFields[0], pressure);
        runtime.GetFieldTo(DatasetFields[1], saturationFractures);
        runtime.GetFieldTo(DatasetFields[2], saturationBlocks);
    }

    private static void ValidateDatasetConfig(SimulationConfig config)
    {
        if (config.NB != 5 || config.Layers.Length != 5)
        {
            throw new InvalidOperationException("SR-датасет поддерживает только конфигурации с ровно 5 слоями.");
        }
    }

    private static SimulationConfig BuildHrConfig(SimulationConfig lrConfig, int hrNx)
    {
        int scaleFactor = hrNx / Math.Max(lrConfig.NX, 1);
        SimulationConfig hrConfig = lrConfig.Clone();
        hrConfig.NX = hrNx;
        hrConfig.Layers = hrConfig.Layers
            .Select(layer =>
            {
                LayerConfig scaled = layer.Clone();
                scaled.NZM = checked(layer.NZM * scaleFactor);
                return scaled;
            })
            .ToArray();
        return hrConfig;
    }

    private bool IsCancelled(string jobId)
    {
        return _jobs.TryGetValue(jobId, out var status) && status.State == "cancelled";
    }

    private void SetStatus(string jobId, string state, string message, int done, int total, string outputPath)
    {
        _jobs[jobId] = new DatasetJobStatus(jobId, state, message, done, total, outputPath);
    }

    private void UpdateProgress(string jobId, int done, int total, string outputPath)
    {
        _jobs.AddOrUpdate(jobId,
            _ => new DatasetJobStatus(jobId, "running", "Running", done, total, outputPath),
            (_, existing) => existing.State is "paused" or "cancelled"
                ? existing with { StepsDone = done, StepsTotal = total }
                : existing with { State = "running", Message = "Running", StepsDone = done, StepsTotal = total, OutputPath = outputPath });
    }

    private void ReleaseGate(string jobId)
    {
        if (_pauseGates.TryGetValue(jobId, out var gate) && gate.CurrentCount == 0)
        {
            gate.Release();
        }
    }
}

public sealed record RunDatasetSpec(
    string JobId,
    string OutputDir,
    Simulation.Core.SimulationConfig Config,
    int TotalSteps,
    int SnapshotStride,
    int HrNx
);

public sealed record DatasetJobStatus(
    string JobId,
    string State,
    string Message,
    int StepsDone,
    int StepsTotal,
    string OutputPath
);
