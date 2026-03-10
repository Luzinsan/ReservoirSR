using Simulation.Core;
using Simulation.Core.Runtime;
using System.Collections.Concurrent;
namespace Simulation.Server.Services;

public sealed class DatasetJobManager
{
    private const int ScaleFactor = 4;
    private static readonly string[] DatasetFields = ["P", "ST", "SB"];

    private readonly ConcurrentDictionary<string, DatasetJobStatus> _jobs = new(StringComparer.Ordinal);
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
        _logger.LogInformation("Dataset job cancelled {JobId}", jobId);
        return true;
    }

    public bool Remove(string jobId)
    {
        return _jobs.TryRemove(jobId, out _);
    }

    private async Task RunJobAsync(RunDatasetSpec spec)
    {
        string outputPath = Path.Combine(spec.OutputDir, $"{spec.JobId}.npz");
        string tempPath = outputPath + ".tmp";
        try
        {
            Directory.CreateDirectory(spec.OutputDir);

            ValidateDatasetConfig(spec.Config);
            SimulationConfig hrConfig = BuildHrConfig(spec.Config);

            var lrRuntime = new SimulationRuntime();
            var hrRuntime = new SimulationRuntime();
            lrRuntime.Initialize(spec.Config);
            hrRuntime.Initialize(hrConfig);

            SimulationRuntimeMetadata lrMetadata = lrRuntime.GetMetadata();
            SimulationRuntimeMetadata hrMetadata = hrRuntime.GetMetadata();

            int steps = spec.TotalSteps;
            SetStatus(spec.JobId, "running", "Running", 0, steps, outputPath);
            _logger.LogInformation("Dataset job running {JobId} output={OutputPath}", spec.JobId, outputPath);

            using (var writer = new SrSimulationArchiveWriter(tempPath, spec.JobId, steps, spec.Config, hrConfig, lrMetadata, hrMetadata))
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
                        if (IsCancelled(spec.JobId))
                        {
                            return;
                        }

                        SimulationStepResult result = lrRuntime.Step(1);
                        ExportFields(lrRuntime, pressure, saturationFractures, saturationBlocks);
                        writer.WriteLrStep(pressure, saturationFractures, saturationBlocks);
                        writer.WriteDynamicStep(result);
                        int done = Interlocked.Exchange(ref lrDone, step + 1);
                        _ = done;
                        SetStatus(spec.JobId, "running", "Running", Math.Min(lrDone, hrDone), steps, outputPath);
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
                        if (IsCancelled(spec.JobId))
                        {
                            return;
                        }

                        _ = hrRuntime.Step(1);
                        ExportFields(hrRuntime, pressure, saturationFractures, saturationBlocks);
                        writer.WriteHrStep(pressure, saturationFractures, saturationBlocks);
                        int done = Interlocked.Exchange(ref hrDone, step + 1);
                        _ = done;
                        SetStatus(spec.JobId, "running", "Running", Math.Min(lrDone, hrDone), steps, outputPath);
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

    private static SimulationConfig BuildHrConfig(SimulationConfig lrConfig)
    {
        SimulationConfig hrConfig = lrConfig.Clone();
        hrConfig.NX = checked(lrConfig.NX * ScaleFactor);
        hrConfig.Layers = hrConfig.Layers
            .Select(layer =>
            {
                LayerConfig scaled = layer.Clone();
                scaled.NZM = checked(layer.NZM * ScaleFactor);
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
}

public sealed record RunDatasetSpec(
    string JobId,
    string OutputDir,
    Simulation.Core.SimulationConfig Config,
    int TotalSteps
);

public sealed record DatasetJobStatus(
    string JobId,
    string State,
    string Message,
    int StepsDone,
    int StepsTotal,
    string OutputPath
);
