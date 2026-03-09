using Simulation.Core.Runtime;
using System.Collections.Concurrent;
using System.Globalization;
using System.Text.Json;

namespace Simulation.Server.Services;

public sealed class DatasetJobManager
{
    private static readonly string[] ScalarSeriesNames =
    [
        "times", "AI", "AIT", "AIB", "P_zab", "Q_fld", "DISS", "DISQ", "TBT", "TB", "TT", "Q_oil_total", "Q_oil_blocks", "Q_oil_fractures"
    ];

    private static readonly string[] SpatialFieldNames =
    [
        "P", "P0", "ST", "SB", "WT", "WB", "AVST", "AVSB", "AT", "AB", "BT", "BB", "BVT", "BVB", "CBET"
    ];

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
        try
        {
            Directory.CreateDirectory(spec.OutputDir);
            string caseDir = Path.Combine(spec.OutputDir, spec.JobId);
            Directory.CreateDirectory(caseDir);

            var runtime = new SimulationRuntime();
            runtime.Initialize(spec.Config);
            var metadata = runtime.GetMetadata();
            string reportPath = Path.Combine(caseDir, "report.json");
            using var reportWriter = new SimulationReportWriter(reportPath, spec, runtime);

            int steps = spec.TotalSteps;
            SetStatus(spec.JobId, "running", "Running", 0, steps, caseDir);
            _logger.LogInformation("Dataset job running {JobId} caseDir={CaseDir}", spec.JobId, caseDir);

            // Preallocate arrays for fields
            var fieldData = new Dictionary<string, double[]>(StringComparer.OrdinalIgnoreCase);
            int n = metadata.Nx * metadata.Nz;
            foreach (string field in SpatialFieldNames)
            {
                fieldData[field] = new double[n];
            }

            var disposables = new List<IDisposable>();
            try
            {
                var fieldWriters = new Dictionary<string, BinaryWriter>(StringComparer.OrdinalIgnoreCase);
                foreach (string field in SpatialFieldNames)
                {
                    var bw = new BinaryWriter(File.Open(Path.Combine(caseDir, $"{field}.bin"), FileMode.Create, FileAccess.Write, FileShare.None));
                    disposables.Add(bw);
                    fieldWriters[field] = bw;
                }

                BinaryWriter CreateBw(string name)
                {
                    var bw = new BinaryWriter(File.Open(Path.Combine(caseDir, $"{name}.bin"), FileMode.Create, FileAccess.Write, FileShare.None));
                    disposables.Add(bw);
                    return bw;
                }

                var bwTime = CreateBw("times");
                var bwAI = CreateBw("AI");
                var bwAIT = CreateBw("AIT");
                var bwAIB = CreateBw("AIB");
                var bwPz = CreateBw("P_zab");
                var bwQFld = CreateBw("Q_fld");
                var bwDiss = CreateBw("DISS");
                var bwDisq = CreateBw("DISQ");
                var bwTbt = CreateBw("TBT");
                var bwTb = CreateBw("TB");
                var bwTt = CreateBw("TT");
                var bwQOilTotal = CreateBw("Q_oil_total");
                var bwQOilBlocks = CreateBw("Q_oil_blocks");
                var bwQOilFractures = CreateBw("Q_oil_fractures");

                int? observedNz = null;

                for (int step = 0; step < steps; step++)
                {
                    if (IsCancelled(spec.JobId))
                    {
                        _logger.LogInformation("Dataset job observed cancellation {JobId} at step {Step}", spec.JobId, step);
                        return;
                    }

                    var result = runtime.Step(1);
                    bwTime.Write(result.Time);
                    bwAI.Write(result.Ai);
                    bwAIT.Write(result.Ait);
                    bwAIB.Write(result.Aib);
                    bwPz.Write(result.Pzab);
                    bwQFld.Write(result.QFld);
                    bwDiss.Write(result.Diss);
                    bwDisq.Write(result.Disq);
                    bwTbt.Write(result.Tbt);
                    bwTb.Write(result.Tb);
                    bwTt.Write(result.Tt);
                    bwQOilTotal.Write(result.QOilTotal);
                    bwQOilBlocks.Write(result.QOilBlocks);
                    bwQOilFractures.Write(result.QOilFractures);

                    foreach (string field in SpatialFieldNames)
                    {
                        double[] values = fieldData[field];
                        runtime.GetFieldTo(field, values);
                        foreach (double value in values)
                        {
                            fieldWriters[field].Write(value);
                        }
                    }

                    reportWriter.WriteStep(step + 1, result, fieldData);

                    if (observedNz is null)
                    {
                        int nx = metadata.Nx;
                        int pCount = fieldData["P"].Length;
                        if (nx <= 0 || pCount % nx != 0)
                        {
                            throw new InvalidOperationException($"Cannot infer NZ from P field length={pCount} and NX={nx}.");
                        }

                        observedNz = pCount / nx;
                        WriteMeta(caseDir, metadata, steps, observedNz.Value);
                    }

                    if (spec.CaptureEveryStep)
                    {
                        foreach ((string field, double[] values) in fieldData)
                        {
                            SaveFieldCsv(Path.Combine(caseDir, $"{field}_{step}.csv"), values, metadata.Nx, observedNz ?? metadata.Nz);
                        }
                    }

                    SetStatus(spec.JobId, "running", "Running", step + 1, steps, caseDir);
                    await Task.Yield();
                }

                if (observedNz is null)
                {
                    WriteMeta(caseDir, metadata, steps, metadata.Nz);
                }
                SetStatus(spec.JobId, "completed", "Completed", steps, steps, caseDir);
                _logger.LogInformation("Dataset job completed {JobId}. report={ReportPath}", spec.JobId, reportPath);
            }
            finally
            {
                foreach (var d in Enumerable.Reverse(disposables))
                {
                    d.Dispose();
                }
            }
        }
        catch (Exception ex)
        {
            SetStatus(spec.JobId, "failed", ex.Message, 0, spec.TotalSteps, spec.OutputDir);
            _logger.LogError(ex, "Dataset job failed {JobId}", spec.JobId);
        }
    }

    private static void SaveFieldCsv(string path, double[] arr, int nx, int nz)
    {
        using var w = new StreamWriter(path, false, System.Text.Encoding.UTF8);
        int idx = 0;
        for (int kz = 0; kz < nz; kz++)
        {
            for (int ix = 0; ix < nx; ix++)
            {
                if (ix > 0) w.Write(',');
                w.Write(arr[idx++].ToString("R", CultureInfo.InvariantCulture));
            }
            w.WriteLine();
        }
    }

    private static void WriteMeta(string caseDir, SimulationRuntimeMetadata metadata, int steps, int nz)
    {
        var obj = new
        {
            steps,
            nx = metadata.Nx,
            nz,
            tu = metadata.TimeStepDays,
            spatial_fields = SpatialFieldNames,
            scalar_series = ScalarSeriesNames,
            static_params = new
            {
                N_Dr = metadata.DrainageSubsteps,
                EPSP = metadata.PressureTolerance,
                TK = metadata.TkDays,
                Bt_Cp = metadata.BtCp,
                Bt_Tr = metadata.BtTr,
                Q_zab = metadata.ConfiguredQZab,
                metadata.P32,
                MU_pazp = metadata.MuPazp
            }
        };
        File.WriteAllText(Path.Combine(caseDir, "meta.json"), JsonSerializer.Serialize(obj));
    }

    private bool IsCancelled(string jobId)
    {
        return _jobs.TryGetValue(jobId, out var status) && status.State == "cancelled";
    }

    private void SetStatus(string jobId, string state, string message, int done, int total, string outputDir)
    {
        _jobs[jobId] = new DatasetJobStatus(jobId, state, message, done, total, outputDir);
    }
}

public sealed record RunDatasetSpec(
    string JobId,
    string OutputDir,
    Simulation.Core.SimulationConfig Config,
    int TotalSteps,
    bool CaptureEveryStep
);

public sealed record DatasetJobStatus(
    string JobId,
    string State,
    string Message,
    int StepsDone,
    int StepsTotal,
    string OutputDir
);
