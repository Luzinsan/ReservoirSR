using ClassLibrary_FissuredPorousOilReservoir;
using System.Globalization;
using System.Threading;

namespace Simulation.Core.Runtime;

public sealed class SimulationRuntime
{
    public Class_FPOR Engine { get; } = new();

    public void Initialize(SimulationConfig config)
    {
        ThreadCulture();

        if (config.NX % 2 != 0)
        {
            config.NX += 1;
        }

        Engine.ApplyConfig(config);

        Engine.Create_Work_Dyn_Arrayes();

        Engine.T = 0.0;
        Engine.Q_zab = Engine.Q_zab / (2.0 * Math.PI);
        Engine.QQ_ICX = Engine.Q_zab;

        Engine.Prepaire_Of_Constants();
        for (int k = 1; k <= Engine.NB; k++)
        {
            for (int i = 1 + Engine.NM[k - 1]; i <= Engine.NM[k]; i++)
            {
                Engine.HZM[i] = Engine.HM[k];
                Engine.VPIT[i] = Engine.VMT[k] * Engine.HM[k] * Engine.HX * Engine.HX;
                Engine.VPIB[i] = Engine.VMB[k] * Engine.HM[k] * Engine.HX * Engine.HX;
            }
        }

        Engine.VPIT[0] = Engine.VPIT[1];
        Engine.VPIB[0] = Engine.VPIB[1];
        Engine.HZM[Engine.NZ + 1] = 0.0;

        Engine.Evaluate_Of_Parameters();
        Engine.Boundary_Conditions_And_Initial_Appr();
        Engine.Initialization_Of_S0(false);
        Engine.Prepeare_Of_Array_Abs_Permeability();
        Engine.Cod_Exit = 15;
    }


    public SimulationStepResult Step(int stepCount)
    {
        int count = Math.Max(stepCount, 1);
        int stepsPerformed = 0;

        for (int step = 0; step < count; step++)
        {
            int kOut = 1;
            Engine.Calc_Filt_Process_Pressure(false, ref kOut);
            if (kOut == -1)
            {
                throw new InvalidOperationException("Calc_Filt_Process_Pressure failed.");
            }

            Engine.Saturation_and_Main_Characts(false, ref kOut);
            if (kOut == -1)
            {
                throw new InvalidOperationException("Saturation_and_Main_Characts failed.");
            }

            Engine.T_Tek += Engine.TU;
            Engine.T += Engine.TU;
            for (int k = 1; k <= Engine.N1; k++)
            {
                Engine.P_0[k] = Engine.P[k];
            }

            stepsPerformed += 1;
        }

        return BuildStepResult(stepsPerformed);
    }

    public double[] GetField(string fieldName)
    {
        string key = fieldName.Trim().ToUpperInvariant();
        return key switch
        {
            "P" => CopyField(Engine.P),
            "P0" => CopyField(Engine.P_0),
            "ST" => CopyField(Engine.ST),
            "SB" => CopyField(Engine.SB),
            "WT" => CopyField(Engine.WT),
            "WB" => CopyField(Engine.WB),
            "AX" => CopyField(Engine.AX),
            "AV" => CopyField(Engine.AV),
            "KABX" => CopyField(Engine.Kabx),
            "KABZ" => CopyField(Engine.Kabz),
            "AVST" => CopyField(Engine.AVST),
            "AVSB" => CopyField(Engine.AVSB),
            "AT" => CopyField(Engine.AT),
            "AB" => CopyField(Engine.AB),
            "BT" => CopyField(Engine.BT),
            "BB" => CopyField(Engine.BB),
            "BVT" => CopyField(Engine.BVT),
            "BVB" => CopyField(Engine.BVB),
            "CBET" => CopyField(Engine.CBet),
            _ => throw new ArgumentOutOfRangeException(nameof(fieldName), $"Unknown field: {fieldName}")
        };
    }

    private SimulationStepResult BuildStepResult(int stepsPerformed)
    {
        return new SimulationStepResult(
            stepsPerformed,
            Engine.T,
            Engine.AI,
            Engine.AIT,
            Engine.AIB,
            Engine.P_zab_DC,
            Engine.Q_fld,
            Engine.DISS,
            Engine.DISQ
        );
    }

    private double[] CopyField(double[] source)
    {
        int n = Engine.NX * Engine.NZ;
        var result = new double[n];
        int idx = 0;
        for (int kz = 1; kz <= Engine.NZ; kz++)
        {
            for (int ix = 1; ix <= Engine.NX; ix++)
            {
                int m = kz + ix * Engine.NZ;
                result[idx++] = source[m];
            }
        }

        return result;
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
    double Disq
);
