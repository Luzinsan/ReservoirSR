using Simulation.Core;
using Simulation.Core.Runtime;
using System.IO.Compression;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

namespace Simulation.Server.Services;

internal sealed class SrSimulationArchiveWriter : IDisposable
{
    private static readonly string[] Channels = ["P", "ST", "SB"];
    private static readonly string[] DynamicScalarNames =
    [
        "time",
        "AI",
        "AIT",
        "AIB",
        "P_zab",
        "Q_fld",
        "DISS",
        "DISQ",
        "TBT",
        "TB",
        "TT",
        "Q_oil_total",
        "Q_oil_blocks",
        "Q_oil_fractures"
    ];

    private static readonly string[] StaticScalarNames =
    [
        "NB", "VL", "LOD", "LIZ", "R_Skv",
        "Ro1_PL", "Ro1_deg", "Mu1_PL", "Mu_Deg", "AP1", "AT1", "C_P_1",
        "Ro3_PL", "Mu3_PL", "C_P_3", "AP3", "AT3",
        "R00", "C_P_2", "VesGMol", "YTAP2", "DZT", "ZG", "R_C_R", "QUNT_CR", "RADZ0", "SM", "S_T_R",
        "VG0", "PH0", "BT", "BG",
        "Bt_Cp", "Bt_Tr",
        "MU_pazp", "X_A", "X_D",
        "Q_zab", "OBV_P", "QQ", "P32",
        "TVK", "TK", "LTVK", "LTK", "DSO",
        "TU", "N_Dr", "NX",
        "EPSP", "ENB", "EVB", "ENT", "EVT",
        "Tim_0", "Tim_1", "Tim_2"
    ];

    private static readonly string[] LayerScalarNames =
    [
        "NZM",
        "HBM",
        "VMB",
        "VMT",
        "LWN",
        "LWD",
        "SNT",
        "SNB",
        "SVT",
        "SVB",
        "AKT",
        "AKB"
    ];

    private readonly string _archivePath;
    private readonly string _workDir;
    private readonly NpyFloat32Writer _lrFieldsWriter;
    private readonly NpyFloat32Writer _hrFieldsWriter;
    private readonly NpyFloat32Writer _dynamicScalarsWriter;
    private readonly float[] _lrScratch;
    private readonly float[] _hrScratch;
    private readonly string _jobId;
    private readonly int _steps;
    private readonly SimulationRuntimeMetadata _lrMetadata;
    private readonly SimulationRuntimeMetadata _hrMetadata;
    private bool _disposed;

    public SrSimulationArchiveWriter(
        string archivePath,
        string jobId,
        int steps,
        SimulationConfig lrConfig,
        SimulationConfig hrConfig,
        SimulationRuntimeMetadata lrMetadata,
        SimulationRuntimeMetadata hrMetadata)
    {
        _jobId = jobId;
        _steps = steps;
        _lrMetadata = lrMetadata;
        _hrMetadata = hrMetadata;
        _archivePath = archivePath;
        _workDir = archivePath + ".work";
        if (Directory.Exists(_workDir))
        {
            Directory.Delete(_workDir, recursive: true);
        }
        Directory.CreateDirectory(_workDir);

        _lrFieldsWriter = CreateWriter("lr_fields.npy", steps, Channels.Length, lrMetadata.Nz, lrMetadata.Nx);
        _hrFieldsWriter = CreateWriter("hr_fields.npy", steps, Channels.Length, hrMetadata.Nz, hrMetadata.Nx);
        _dynamicScalarsWriter = CreateWriter("dynamic_scalars.npy", steps, DynamicScalarNames.Length);

        _lrScratch = new float[lrMetadata.Nx * lrMetadata.Nz];
        _hrScratch = new float[hrMetadata.Nx * hrMetadata.Nz];

        WriteStaticArray("static_scalars.npy", BuildStaticScalars(lrConfig), StaticScalarNames.Length);
        WriteStaticArray("layer_scalars.npy", BuildLayerScalars(lrConfig), 5, LayerScalarNames.Length);
        WriteMeta(lrConfig, hrConfig);
    }

    public void WriteLrStep(
        double[] pressure,
        double[] saturationFractures,
        double[] saturationBlocks)
    {
        WriteFieldTriplet(_lrFieldsWriter, _lrScratch, pressure, saturationFractures, saturationBlocks);
    }

    public void WriteHrStep(
        double[] pressure,
        double[] saturationFractures,
        double[] saturationBlocks)
    {
        WriteFieldTriplet(_hrFieldsWriter, _hrScratch, pressure, saturationFractures, saturationBlocks);
    }

    public void WriteDynamicStep(SimulationStepResult lrResult)
    {
        Span<float> dynamic = stackalloc float[14]
        {
            (float)lrResult.Time,
            (float)lrResult.Ai,
            (float)lrResult.Ait,
            (float)lrResult.Aib,
            (float)lrResult.Pzab,
            (float)lrResult.QFld,
            (float)lrResult.Diss,
            (float)lrResult.Disq,
            (float)lrResult.Tbt,
            (float)lrResult.Tb,
            (float)lrResult.Tt,
            (float)lrResult.QOilTotal,
            (float)lrResult.QOilBlocks,
            (float)lrResult.QOilFractures
        };
        _dynamicScalarsWriter.Write(dynamic);
    }

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _lrFieldsWriter.Dispose();
        _hrFieldsWriter.Dispose();
        _dynamicScalarsWriter.Dispose();
        CreateArchive();
        Directory.Delete(_workDir, recursive: true);
        _disposed = true;
    }

    private NpyFloat32Writer CreateWriter(string entryName, params int[] shape)
    {
        string path = Path.Combine(_workDir, entryName);
        return new NpyFloat32Writer(File.Open(path, FileMode.Create, FileAccess.Write, FileShare.None), shape);
    }

    private static void WriteFieldTriplet(
        NpyFloat32Writer writer,
        float[] scratch,
        double[] pressure,
        double[] saturationFractures,
        double[] saturationBlocks)
    {
        WriteDoubles(writer, scratch, pressure);
        WriteDoubles(writer, scratch, saturationFractures);
        WriteDoubles(writer, scratch, saturationBlocks);
    }

    private static void WriteDoubles(NpyFloat32Writer writer, float[] scratch, double[] values)
    {
        for (int i = 0; i < values.Length; i++)
        {
            scratch[i] = (float)values[i];
        }
        writer.Write(scratch.AsSpan(0, values.Length));
    }

    private void WriteStaticArray(string entryName, float[] values, params int[] shape)
    {
        using NpyFloat32Writer writer = CreateWriter(entryName, shape);
        writer.Write(values);
    }

    private void WriteMeta(SimulationConfig lrConfig, SimulationConfig hrConfig)
    {
        var meta = new
        {
            format_version = 1,
            task = "conditional_super_resolution",
            scale_factor = 4,
            steps = _steps,
            dtype = "float32",
            axes = "T,C,Z,X",
            channels = Channels,
            dynamic_scalar_names = DynamicScalarNames,
            static_scalar_names = StaticScalarNames,
            layer_scalar_names = LayerScalarNames,
            static_scalars_source = "lr_config",
            layer_scalars_source = "lr_config",
            lr_grid = new { nx = _lrMetadata.Nx, nz = _lrMetadata.Nz },
            hr_grid = new { nx = _hrMetadata.Nx, nz = _hrMetadata.Nz },
            lr_simulation_id = $"{_jobId}_lr",
            hr_simulation_id = $"{_jobId}_hr",
            lr_config = new { nb = lrConfig.NB, nx = lrConfig.NX, tu = lrConfig.TU },
            hr_config = new { nb = hrConfig.NB, nx = hrConfig.NX, tu = hrConfig.TU }
        };

        File.WriteAllText(Path.Combine(_workDir, "meta.json"), JsonSerializer.Serialize(meta), Encoding.UTF8);
    }

    private void CreateArchive()
    {
        using ZipArchive archive = ZipFile.Open(_archivePath, ZipArchiveMode.Create);
        foreach (string path in Directory.GetFiles(_workDir))
        {
            archive.CreateEntryFromFile(path, Path.GetFileName(path), CompressionLevel.Fastest);
        }
    }

    private static float[] BuildStaticScalars(SimulationConfig config)
    {
        return
        [
            config.NB, (float)config.VL, config.LOD, config.LIZ, (float)config.R_Skv,
            (float)config.Ro1_PL, (float)config.Ro1_deg, (float)config.Mu1_PL, (float)config.Mu_Deg, (float)config.AP1, (float)config.AT1, (float)config.C_P_1,
            (float)config.Ro3_PL, (float)config.Mu3_PL, (float)config.C_P_3, (float)config.AP3, (float)config.AT3,
            (float)config.R00, (float)config.C_P_2, (float)config.VesGMol, (float)config.YTAP2, (float)config.DZT, (float)config.ZG, (float)config.R_C_R, (float)config.QUNT_CR, (float)config.RADZ0, (float)config.SM, (float)config.S_T_R,
            (float)config.VG0, (float)config.PH0, (float)config.BT, (float)config.BG,
            (float)config.Bt_Cp, (float)config.Bt_Tr,
            (float)config.MU_pazp, (float)config.X_A, (float)config.X_D,
            (float)config.Q_zab, (float)config.OBV_P, (float)config.QQ, (float)config.P32,
            (float)config.TVK, (float)config.TK, config.LTVK, config.LTK, (float)config.DSO,
            (float)config.TU, config.N_Dr, config.NX,
            (float)config.EPSP, (float)config.ENB, (float)config.EVB, (float)config.ENT, (float)config.EVT,
            (float)config.Tim_0, (float)config.Tim_1, (float)config.Tim_2
        ];
    }

    private static float[] BuildLayerScalars(SimulationConfig config)
    {
        float[] values = new float[5 * LayerScalarNames.Length];
        for (int i = 0; i < 5; i++)
        {
            LayerConfig layer = config.Layers[i];
            int offset = i * LayerScalarNames.Length;
            values[offset + 0] = layer.NZM;
            values[offset + 1] = (float)layer.HBM;
            values[offset + 2] = (float)layer.VMB;
            values[offset + 3] = (float)layer.VMT;
            values[offset + 4] = layer.LWN;
            values[offset + 5] = layer.LWD;
            values[offset + 6] = (float)layer.SNT;
            values[offset + 7] = (float)layer.SNB;
            values[offset + 8] = (float)layer.SVT;
            values[offset + 9] = (float)layer.SVB;
            values[offset + 10] = (float)layer.AKT;
            values[offset + 11] = (float)layer.AKB;
        }
        return values;
    }
}

internal sealed class NpyFloat32Writer : IDisposable
{
    private readonly Stream _stream;
    private bool _disposed;

    public NpyFloat32Writer(Stream stream, params int[] shape)
    {
        _stream = stream;
        WriteHeader(shape);
    }

    public void Write(ReadOnlySpan<float> values)
    {
        _stream.Write(MemoryMarshal.AsBytes(values));
    }

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _stream.Dispose();
        _disposed = true;
    }

    private void WriteHeader(int[] shape)
    {
        string shapeText = shape.Length == 1
            ? $"({shape[0]},)"
            : $"({string.Join(", ", shape)})";
        string dict = $"{{'descr': '<f4', 'fortran_order': False, 'shape': {shapeText}, }}";
        int headerPrefixLength = 10;
        int padding = 16 - ((headerPrefixLength + dict.Length + 1) % 16);
        if (padding == 16)
        {
            padding = 0;
        }

        string header = dict + new string(' ', padding) + '\n';
        byte[] headerBytes = Encoding.ASCII.GetBytes(header);
        Span<byte> prefix = stackalloc byte[10];
        prefix[0] = 0x93;
        prefix[1] = (byte)'N';
        prefix[2] = (byte)'U';
        prefix[3] = (byte)'M';
        prefix[4] = (byte)'P';
        prefix[5] = (byte)'Y';
        prefix[6] = 1;
        prefix[7] = 0;
        prefix[8] = (byte)(headerBytes.Length & 0xFF);
        prefix[9] = (byte)((headerBytes.Length >> 8) & 0xFF);
        _stream.Write(prefix);
        _stream.Write(headerBytes);
    }
}
