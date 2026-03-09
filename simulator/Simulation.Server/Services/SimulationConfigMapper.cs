using ContractsConfig = Simulation.Contracts.SimulationConfig;
using ContractsLayerConfig = Simulation.Contracts.LayerConfig;
using CoreConfig = Simulation.Core.SimulationConfig;
using CoreLayerConfig = Simulation.Core.LayerConfig;

namespace Simulation.Server.Services;

internal static class SimulationConfigMapper
{
    private static int Map(int val, int def) => val > 0 ? val : def;
    private static double Map(double val, double def) => val > 0 ? val : def;

    public static CoreConfig ToCoreConfig(ContractsConfig? source)
    {
        var def = new CoreConfig();
        if (source is null)
        {
            return def;
        }

        var config = new CoreConfig
        {
            NB = Map(source.Nb, def.NB),
            VL = Map(source.Vl, def.VL),
            LOD = source.Lod,
            LIZ = Map(source.Liz, def.LIZ),
            R_Skv = Map(source.RSkv, def.R_Skv),

            Ro1_PL = Map(source.Ro1Pl, def.Ro1_PL),
            Ro1_deg = Map(source.Ro1Deg, def.Ro1_deg),
            Mu1_PL = Map(source.Mu1Pl, def.Mu1_PL),
            Mu_Deg = Map(source.MuDeg, def.Mu_Deg),
            AP1 = Map(source.Ap1, def.AP1),
            AT1 = Map(source.At1, def.AT1),
            C_P_1 = Map(source.CP1, def.C_P_1),

            Ro3_PL = Map(source.Ro3Pl, def.Ro3_PL),
            Mu3_PL = Map(source.Mu3Pl, def.Mu3_PL),
            C_P_3 = Map(source.CP3, def.C_P_3),
            AP3 = Map(source.Ap3, def.AP3),
            AT3 = Map(source.At3, def.AT3),

            R00 = Map(source.R00, def.R00),
            C_P_2 = Map(source.CP2, def.C_P_2),
            VesGMol = Map(source.VesGMol, def.VesGMol),
            YTAP2 = Map(source.Ytap2, def.YTAP2),
            DZT = Map(source.Dzt, def.DZT),
            ZG = Map(source.Zg, def.ZG),
            R_C_R = Map(source.RCR, def.R_C_R),
            QUNT_CR = Map(source.QuntCr, def.QUNT_CR),
            RADZ0 = Map(source.Radz0, def.RADZ0),
            SM = Map(source.Sm, def.SM),
            S_T_R = Map(source.STR, def.S_T_R),

            VG0 = Map(source.Vg0, def.VG0),
            PH0 = Map(source.Ph0, def.PH0),
            BT = Map(source.Bt, def.BT),
            BG = Map(source.Bg, def.BG),

            Bt_Cp = Map(source.BtCp, def.Bt_Cp),
            Bt_Tr = Map(source.BtTr, def.Bt_Tr),

            MU_pazp = Map(source.MuPazp, def.MU_pazp),
            X_A = Map(source.XA, def.X_A),
            X_D = Map(source.XD, def.X_D),

            Q_zab = Map(source.QZab, def.Q_zab),
            OBV_P = Map(source.ObvP, def.OBV_P),
            QQ = Map(source.Qq, def.QQ),
            P32 = Map(source.P32, def.P32),

            TVK = Map(source.Tvk, def.TVK),
            TK = Map(source.TkDays, def.TK),
            LTVK = source.Ltvk,
            LTK = Map(source.Ltk, def.LTK),
            DSO = Map(source.Dso, def.DSO),

            TU = source.TuSeconds > 0 ? source.TuSeconds / 86400.0 : def.TU,
            N_Dr = Map(source.NDr, def.N_Dr),
            NX = Map(source.Nx, def.NX),

            EPSP = Map(source.Epsp, def.EPSP),
            ENB = Map(source.Enb, def.ENB),
            EVB = Map(source.Evb, def.EVB),
            ENT = Map(source.Ent, def.ENT),
            EVT = Map(source.Evt, def.EVT),

            Tim_0 = Map(source.Tim0, def.Tim_0),
            Tim_1 = Map(source.Tim1, def.Tim_1),
            Tim_2 = Map(source.Tim2, def.Tim_2)
        };

        if (source.Layers.Count > 0)
        {
            config.NB = source.Layers.Count;
            config.Layers = source.Layers.Select(ToCoreLayer).ToArray();
        }

        return config;
    }

    private static CoreLayerConfig ToCoreLayer(ContractsLayerConfig layer)
    {
        var def = new CoreLayerConfig();
        return new CoreLayerConfig
        {
            NZM = Map(layer.Nzm, def.NZM),
            HBM = Map(layer.Hbm, def.HBM),
            VMB = Map(layer.Vmb, def.VMB),
            VMT = Map(layer.Vmt, def.VMT),
            LWN = layer.Lwn,
            LWD = layer.Lwd,
            SNT = Map(layer.Snt, def.SNT),
            SNB = Map(layer.Snb, def.SNB),
            SVT = Map(layer.Svt, def.SVT),
            SVB = Map(layer.Svb, def.SVB),
            AKT = Map(layer.Akt, def.AKT),
            AKB = Map(layer.Akb, def.AKB)
        };
    }
}
