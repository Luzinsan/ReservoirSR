using Simulation.Core.Runtime;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace Simulation.Server.Services;

internal sealed class SimulationReportWriter : IDisposable
{
    private readonly FileStream _stream;
    private readonly Utf8JsonWriter _writer;
    private bool _stepsArrayOpen;
    private bool _disposed;

    public SimulationReportWriter(string reportPath, RunDatasetSpec spec, SimulationRuntime runtime)
    {
        SimulationRuntimeMetadata metadata = runtime.GetMetadata();
        _stream = File.Open(reportPath, FileMode.Create, FileAccess.Write, FileShare.None);
        _writer = new Utf8JsonWriter(_stream, new JsonWriterOptions
        {
            Indented = true,
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
        });

        _writer.WriteStartObject();
        _writer.WriteString("job_id", spec.JobId);
        _writer.WriteString("output_dir", spec.OutputDir);
        _writer.WriteNumber("steps_total", spec.TotalSteps);
        _writer.WriteBoolean("capture_every_step", spec.CaptureEveryStep);
        _writer.WriteNumber("nx", metadata.Nx);
        _writer.WriteNumber("nz", metadata.Nz);
        _writer.WriteNumber("tu", metadata.TimeStepDays);

        _writer.WriteStartObject("static_params");
        _writer.WriteNumber("N_Dr", metadata.DrainageSubsteps);
        _writer.WriteNumber("EPSP", metadata.PressureTolerance);
        _writer.WriteNumber("TK", metadata.TkDays);
        _writer.WriteNumber("Bt_Cp", metadata.BtCp);
        _writer.WriteNumber("Bt_Tr", metadata.BtTr);
        _writer.WriteNumber("Q_zab", metadata.ConfiguredQZab);
        _writer.WriteNumber("P32", metadata.P32);
        _writer.WriteNumber("MU_pazp", metadata.MuPazp);
        _writer.WriteEndObject();

        _writer.WriteStartArray("steps");
        _stepsArrayOpen = true;
    }

    public void WriteStep(int stepIndex, SimulationStepResult result, IReadOnlyDictionary<string, double[]> fields)
    {
        _writer.WriteStartObject();
        _writer.WriteNumber("step", stepIndex);
        _writer.WriteNumber("time", result.Time);
        _writer.WriteNumber("ai", result.Ai);
        _writer.WriteNumber("ait", result.Ait);
        _writer.WriteNumber("aib", result.Aib);
        _writer.WriteNumber("p_zab", result.Pzab);
        _writer.WriteNumber("q_fld", result.QFld);
        _writer.WriteNumber("diss", result.Diss);
        _writer.WriteNumber("disq", result.Disq);
        _writer.WriteNumber("tbt", result.Tbt);
        _writer.WriteNumber("tb", result.Tb);
        _writer.WriteNumber("tt", result.Tt);
        _writer.WriteNumber("q_oil_total", result.QOilTotal);
        _writer.WriteNumber("q_oil_blocks", result.QOilBlocks);
        _writer.WriteNumber("q_oil_fractures", result.QOilFractures);

        _writer.WriteStartObject("fields");
        foreach ((string fieldName, double[] values) in fields)
        {
            _writer.WriteStartArray(fieldName);
            foreach (double value in values)
            {
                _writer.WriteNumberValue(value);
            }
            _writer.WriteEndArray();
        }
        _writer.WriteEndObject();
        _writer.WriteEndObject();
        _writer.Flush();
    }

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        if (_stepsArrayOpen)
        {
            _writer.WriteEndArray();
            _writer.WriteEndObject();
            _stepsArrayOpen = false;
        }

        _writer.Dispose();
        _stream.Dispose();
        _disposed = true;
    }
}
