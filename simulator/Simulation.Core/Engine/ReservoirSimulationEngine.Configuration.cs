using Simulation.Core;

namespace ClassLibrary_FissuredPorousOilReservoir;

public partial class ReservoirSimulationEngine
{
    public void ApplyConfig(SimulationConfig config)
    {
        SimulationConfig normalizedConfig = NormalizeAndValidateConfig(config);
        ApplyConfigCore(normalizedConfig);
    }

    private static SimulationConfig NormalizeAndValidateConfig(SimulationConfig config)
    {
        if (config is null)
        {
            throw new ArgumentNullException(nameof(config));
        }

        SimulationConfig normalized = config.Clone();

        if (normalized.NX % 2 != 0)
        {
            normalized.NX += 1;
        }

        if (normalized.NB <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(config.NB), "Количество слоев должно быть положительным.");
        }

        if (normalized.NX <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(config.NX), "Количество радиальных блоков должно быть положительным.");
        }

        if (normalized.N_Dr <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(config.N_Dr), "Количество дренажных подшагов должно быть положительным.");
        }

        if (normalized.TU <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(config.TU), "Шаг по времени должен быть положительным.");
        }

        if (Math.Abs(normalized.X_A - normalized.X_D) < 1e-12)
        {
            throw new ArgumentException("Параметры X_A и X_D не должны совпадать.", nameof(config));
        }

        if (normalized.Layers is null)
        {
            throw new InvalidOperationException("Конфигурация не содержит описание слоев.");
        }

        if (normalized.Layers.Length < normalized.NB)
        {
            throw new InvalidOperationException(
                $"Количество описаний слоев ({normalized.Layers.Length}) меньше NB ({normalized.NB})."
            );
        }

        for (int i = 0; i < normalized.NB; i++)
        {
            LayerConfig layer = normalized.Layers[i];
            if (layer.NZM <= 0)
            {
                throw new ArgumentOutOfRangeException(nameof(config.Layers), $"Слой {i + 1}: NZM должен быть положительным.");
            }

            if (layer.HBM <= 0)
            {
                throw new ArgumentOutOfRangeException(nameof(config.Layers), $"Слой {i + 1}: HBM должен быть положительным.");
            }

            if (layer.SNT > layer.SVT)
            {
                throw new ArgumentException($"Слой {i + 1}: SNT не может быть больше SVT.", nameof(config));
            }

            if (layer.SNB > layer.SVB)
            {
                throw new ArgumentException($"Слой {i + 1}: SNB не может быть больше SVB.", nameof(config));
            }
        }

        return normalized;
    }

    private void ApplyConfigCore(SimulationConfig config)
    {
        ApplyCoreSettings(config);
        ApplyMixtureProperties(config);

        ROW = MixtureProperties.WaterProperties.Ro3_PL / 1000.0;
        ROO = MixtureProperties.OilProperties.Ro1_PL / 1000.0;

        c_ = X_A / Math.Pow(X_A - X_D, 2.0);
        b_ = c_ * X_A;
        a_ =
            (1.0 / MU_pazp - 1.0 / MixtureProperties.OilProperties.Mu1_PL)
            * Math.Pow(X_A, -b_)
            * Math.Exp(c_ * X_A);

        MixtureProperties.Set_PpL_Tpl(P32 / 10.0, 40.0);

        ApplyGridAndSolverSettings(config);

        Free_Ini_Arrayes_Razm_NB();
        Create_Ini_Arrayes_Razm_NB();
        ApplyLayerSettings(config);

        Calc_NZ_My_And_HL_My(NB, HBM, NZM);
        Pr_Count = 1;
        S_min = 0;
        S_max = 1;
    }

    private void ApplyCoreSettings(SimulationConfig config)
    {
        NB = config.NB;
        VL = config.VL;
        LOD = config.LOD;
        LIZ = config.LIZ;
        R_Skv = config.R_Skv;

        Bt_Cp = config.Bt_Cp;
        Bt_Tr = config.Bt_Tr;

        MU_pazp = config.MU_pazp;
        X_A = config.X_A;
        X_D = config.X_D;

        ConfiguredQZab = config.Q_zab;
        Q_zab = ConfiguredQZab;
        OBV_P = config.OBV_P;
        QQ = config.QQ;
        P32 = config.P32;

        TVK = config.TVK;
        TK = config.TK;
        LTVK = config.LTVK;
        LTK = config.LTK;
        DSO = config.DSO;
    }

    private void ApplyMixtureProperties(SimulationConfig config)
    {
        MixtureProperties.OilProperties.Ro1_PL = config.Ro1_PL;
        MixtureProperties.OilProperties.Ro1_deg = config.Ro1_deg;
        MixtureProperties.OilProperties.Mu1_PL = config.Mu1_PL;
        MixtureProperties.OilProperties.Mu_Deg = config.Mu_Deg;
        MixtureProperties.OilProperties.AP1 = config.AP1;
        MixtureProperties.OilProperties.AT1 = config.AT1;
        MixtureProperties.OilProperties.C_P_1 = config.C_P_1;

        MixtureProperties.WaterProperties.Ro3_PL = config.Ro3_PL;
        MixtureProperties.WaterProperties.Mu3_PL = config.Mu3_PL;
        MixtureProperties.WaterProperties.C_P_3 = config.C_P_3;
        MixtureProperties.WaterProperties.AP3 = config.AP3;
        MixtureProperties.WaterProperties.AT3 = config.AT3;

        MixtureProperties.OilProperties.GasProperties.R00 = config.R00;
        MixtureProperties.OilProperties.GasProperties.C_P_2 = config.C_P_2;
        MixtureProperties.OilProperties.GasProperties.VesGMol = config.VesGMol;
        MixtureProperties.OilProperties.GasProperties.YTAP2 = config.YTAP2;
        MixtureProperties.OilProperties.GasProperties.DZT = config.DZT;
        MixtureProperties.OilProperties.GasProperties.ZG = config.ZG;
        MixtureProperties.OilProperties.GasProperties.R_C_R = config.R_C_R;
        MixtureProperties.OilProperties.GasProperties.QUNT_CR = config.QUNT_CR;
        MixtureProperties.OilProperties.GasProperties.RADZ0 = config.RADZ0;
        MixtureProperties.OilProperties.GasProperties.SM = config.SM;
        MixtureProperties.OilProperties.GasProperties.S_T_R = config.S_T_R;

        MixtureProperties.OilProperties.VG0 = config.VG0;
        MixtureProperties.OilProperties.PH0 = config.PH0;
        MixtureProperties.OilProperties.BT = config.BT;
        MixtureProperties.OilProperties.BG = config.BG;
    }

    private void ApplyGridAndSolverSettings(SimulationConfig config)
    {
        TU = config.TU;
        Tu_icx = config.TU;
        N_Dr = config.N_Dr;
        NX = config.NX;

        EPSP = config.EPSP;
        ENB = config.ENB;
        EVB = config.EVB;
        ENT = config.ENT;
        EVT = config.EVT;

        Tim_0 = config.Tim_0;
        Tim_1 = config.Tim_1;
        Tim_2 = config.Tim_2;
    }

    private void ApplyLayerSettings(SimulationConfig config)
    {
        for (int i = 0; i < NB; i++)
        {
            LayerConfig layer = config.Layers[i];
            int idx = i + 1;
            NZM[idx] = layer.NZM;
            HBM[idx] = layer.HBM;
            VMB[idx] = layer.VMB;
            VMT[idx] = layer.VMT;
            LWN[idx] = layer.LWN;
            LWD[idx] = layer.LWD;
            SNT[idx] = layer.SNT;
            SNB[idx] = layer.SNB;
            SVT[idx] = layer.SVT;
            SVB[idx] = layer.SVB;
            AKT[idx] = layer.AKT;
            AKB[idx] = layer.AKB;
        }
    }
}
