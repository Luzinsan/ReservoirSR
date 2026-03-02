using Simulation.Core.Runtime;
using System.Collections.Concurrent;
using System.Globalization;
using System.Text.Json;

namespace Simulation.Server.Services;

public sealed class DatasetJobManager
{
    private static readonly string[] SpatialFieldNames =
    [
        "P", "P0", "ST", "SB", "WT", "WB", "AVST", "AVSB", "AT", "AB", "BT", "BB", "BVT", "BVB", "CBET"
    ];

    private readonly ConcurrentDictionary<string, DatasetJobStatus> _jobs = new(StringComparer.Ordinal);

    public DatasetJobStatus Start(RunDatasetSpec spec)
    {
        string jobId = string.IsNullOrWhiteSpace(spec.JobId) ? Guid.NewGuid().ToString("N") : spec.JobId;
        var status = new DatasetJobStatus(jobId, "queued", "Job queued", 0, spec.TotalSteps, spec.OutputDir);
        if (!_jobs.TryAdd(jobId, status))
        {
            throw new InvalidOperationException($"Job '{jobId}' already exists.");
        }

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
        return true;
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

            int steps = spec.TotalSteps;
            SetStatus(spec.JobId, "running", "Running", 0, steps, caseDir);

            var fieldWriters = new Dictionary<string, BinaryWriter>(StringComparer.OrdinalIgnoreCase);
            foreach (string field in SpatialFieldNames)
            {
                fieldWriters[field] = new BinaryWriter(File.Open(Path.Combine(caseDir, $"{field}.bin"), FileMode.Create, FileAccess.Write, FileShare.None));
            }
            using var bwTime = new BinaryWriter(File.Open(Path.Combine(caseDir, "times.bin"), FileMode.Create, FileAccess.Write, FileShare.None));
            using var bwAI = new BinaryWriter(File.Open(Path.Combine(caseDir, "AI.bin"), FileMode.Create, FileAccess.Write, FileShare.None));
            using var bwAIT = new BinaryWriter(File.Open(Path.Combine(caseDir, "AIT.bin"), FileMode.Create, FileAccess.Write, FileShare.None));
            using var bwAIB = new BinaryWriter(File.Open(Path.Combine(caseDir, "AIB.bin"), FileMode.Create, FileAccess.Write, FileShare.None));
            using var bwPz = new BinaryWriter(File.Open(Path.Combine(caseDir, "P_zab.bin"), FileMode.Create, FileAccess.Write, FileShare.None));
            using var bwQFld = new BinaryWriter(File.Open(Path.Combine(caseDir, "Q_fld.bin"), FileMode.Create, FileAccess.Write, FileShare.None));
            using var bwDiss = new BinaryWriter(File.Open(Path.Combine(caseDir, "DISS.bin"), FileMode.Create, FileAccess.Write, FileShare.None));
            using var bwDisq = new BinaryWriter(File.Open(Path.Combine(caseDir, "DISQ.bin"), FileMode.Create, FileAccess.Write, FileShare.None));
            int? observedNz = null;

            try
            {
                for (int step = 0; step < steps; step++)
                {
                    if (IsCancelled(spec.JobId))
                    {
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

                    var fieldData = new Dictionary<string, double[]>(StringComparer.OrdinalIgnoreCase);
                    foreach (string field in SpatialFieldNames)
                    {
                        double[] values = runtime.GetField(field);
                        fieldData[field] = values;
                        foreach (double value in values)
                        {
                            fieldWriters[field].Write(value);
                        }
                    }

                    if (observedNz is null)
                    {
                        int nx = runtime.Engine.NX;
                        int pCount = fieldData["P"].Length;
                        if (nx <= 0 || pCount % nx != 0)
                        {
                            throw new InvalidOperationException($"Cannot infer NZ from P field length={pCount} and NX={nx}.");
                        }

                        observedNz = pCount / nx;
                        WriteMeta(caseDir, runtime, steps, observedNz.Value);
                    }

                    if (spec.CaptureEveryStep)
                    {
                        foreach ((string field, double[] values) in fieldData)
                        {
                            SaveFieldCsv(Path.Combine(caseDir, $"{field}_{step}.csv"), values, runtime.Engine.NX, observedNz ?? runtime.Engine.NZ);
                        }
                    }

                    SetStatus(spec.JobId, "running", "Running", step + 1, steps, caseDir);
                    await Task.Yield();
                }
            }
            finally
            {
                foreach (BinaryWriter writer in fieldWriters.Values)
                {
                    writer.Dispose();
                }
            }

            if (observedNz is null)
            {
                WriteMeta(caseDir, runtime, steps, runtime.Engine.NZ);
            }
            SetStatus(spec.JobId, "completed", "Completed", steps, steps, caseDir);
        }
        catch (Exception ex)
        {
            SetStatus(spec.JobId, "failed", ex.Message, 0, spec.TotalSteps, spec.OutputDir);
        }
    }

    private static void SaveFieldCsv(string path, double[] arr, int nx, int nz)
    {
        using var w = new StreamWriter(path, false, System.Text.Encoding.UTF8);
        int idx = 0;
        for (int kz = 0; kz < nz; kz++)
        {
            var row = new string[nx];
            for (int ix = 0; ix < nx; ix++)
            {
                row[ix] = arr[idx++].ToString("R", CultureInfo.InvariantCulture);
            }

            w.WriteLine(string.Join(",", row));
        }
    }

    private static void WriteMeta(string caseDir, SimulationRuntime runtime, int steps, int nz)
    {
        var obj = new
        {
            steps,
            nx = runtime.Engine.NX,
            nz,
            tu = runtime.Engine.TU,
            spatial_fields = SpatialFieldNames,
            scalar_series = new[] { "times", "AI", "AIT", "AIB", "P_zab", "Q_fld", "DISS", "DISQ" },
            static_params = new
            {
                runtime.Engine.N_Dr,
                runtime.Engine.EPSP,
                runtime.Engine.TK,
                runtime.Engine.Bt_Cp,
                runtime.Engine.Bt_Tr,
                runtime.Engine.Q_zab,
                runtime.Engine.P32,
                runtime.Engine.MU_pazp
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
