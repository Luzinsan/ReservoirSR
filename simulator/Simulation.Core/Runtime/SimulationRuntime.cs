using ClassLibrary_FissuredPorousOilReservoir;
using System.Globalization;
using System.Threading;

namespace Simulation.Core.Runtime;

public sealed class SimulationRuntime
{
    private readonly object _gate = new();
    private readonly ReservoirSimulationEngine _engine = new();
    private bool _initialized;

    public void Initialize(SimulationConfig config)
    {
        lock (_gate)
        {
            ThreadCulture();
            _engine.ApplyConfig(config);
            _engine.InitializeRuntimeState();
            _initialized = true;
        }
    }


    public SimulationStepResult Step(int stepCount)
    {
        lock (_gate)
        {
            EnsureInitialized();

            int count = Math.Max(stepCount, 1);
            int stepsPerformed = 0;

            for (int step = 0; step < count; step++)
            {
                _engine.AdvanceSingleStep();
                stepsPerformed += 1;
            }

            return BuildStepResult(stepsPerformed);
        }
    }

    public void GetFieldTo(string fieldName, IList<double> destination)
    {
        lock (_gate)
        {
            EnsureInitialized();
            _engine.ExportFieldTo(fieldName, destination);
        }
    }

    public SimulationRuntimeMetadata GetMetadata()
    {
        lock (_gate)
        {
            EnsureInitialized();
            return new SimulationRuntimeMetadata(
                _engine.NX,
                _engine.NZ,
                _engine.TU,
                _engine.N_Dr,
                _engine.EPSP,
                _engine.TK,
                _engine.Bt_Cp,
                _engine.Bt_Tr,
                _engine.ConfiguredQZab,
                _engine.P32,
                _engine.MU_pazp
            );
        }
    }

    private SimulationStepResult BuildStepResult(int stepsPerformed)
    {
        double qOilBlocks = ConvertRecoveryPercentToVolume(_engine.TB, _engine.VNEB);
        double qOilFractures = ConvertRecoveryPercentToVolume(_engine.TT, _engine.VNET);
        double qOilTotal = ConvertRecoveryPercentToVolume(_engine.TBT, _engine.VNE);

        return new SimulationStepResult(
            stepsPerformed,
            _engine.T,
            _engine.AI,
            _engine.AIT,
            _engine.AIB,
            _engine.P_zab_DC,
            _engine.Q_fld,
            _engine.DISS,
            _engine.DISQ,
            _engine.TBT,
            _engine.TB,
            _engine.TT,
            qOilTotal,
            qOilBlocks,
            qOilFractures
        );
    }

    private static double ConvertRecoveryPercentToVolume(double recoveryPercent, double netVolume)
    {
        return recoveryPercent * netVolume / 100000.0;
    }

    private void EnsureInitialized()
    {
        if (!_initialized)
        {
            throw new InvalidOperationException("Simulation runtime is not initialized.");
        }
    }

    private static void ThreadCulture()
    {
        CultureInfo ci = (CultureInfo)CultureInfo.InvariantCulture.Clone();
        ci.NumberFormat.NumberDecimalSeparator = ".";
        Thread.CurrentThread.CurrentCulture = ci;
        Thread.CurrentThread.CurrentUICulture = ci;
    }
}

public sealed record SimulationStepResult(
    int StepsPerformed,
    double Time,
    double Ai,
    double Ait,
    double Aib,
    double Pzab,
    double QFld,
    double Diss,
    double Disq,
    double Tbt,
    double Tb,
    double Tt,
    double QOilTotal,
    double QOilBlocks,
    double QOilFractures
);

public sealed record SimulationRuntimeMetadata(
    int Nx,
    int Nz,
    double TimeStepDays,
    int DrainageSubsteps,
    double PressureTolerance,
    double TkDays,
    double BtCp,
    double BtTr,
    double ConfiguredQZab,
    double P32,
    double MuPazp
);
