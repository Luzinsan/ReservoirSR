using ContractsConfig = Simulation.Contracts.SimulationConfig;
using ContractsLayerConfig = Simulation.Contracts.LayerConfig;
using CoreConfig = Simulation.Core.SimulationConfig;
using CoreLayerConfig = Simulation.Core.LayerConfig;

namespace Simulation.Server.Services;

internal static class SimulationConfigMapper
{
    public static CoreConfig ToCoreConfig(ContractsConfig? source)
    {
        if (source is null || source.CalculateSize() == 0)
        {
            return new CoreConfig();
        }

        var config = new CoreConfig
        {
            NB = source.Nb,
            VL = source.Vl,
            LOD = source.Lod,
            LIZ = source.Liz,
            R_Skv = source.RSkv,

            Ro1_PL = source.Ro1Pl,
            Ro1_deg = source.Ro1Deg,
            Mu1_PL = source.Mu1Pl,
            Mu_Deg = source.MuDeg,
            AP1 = source.Ap1,
            AT1 = source.At1,
            C_P_1 = source.CP1,

            Ro3_PL = source.Ro3Pl,
            Mu3_PL = source.Mu3Pl,
            C_P_3 = source.CP3,
            AP3 = source.Ap3,
            AT3 = source.At3,

            R00 = source.R00,
            C_P_2 = source.CP2,
            VesGMol = source.VesGMol,
            YTAP2 = source.Ytap2,
            DZT = source.Dzt,
            ZG = source.Zg,
            R_C_R = source.RCR,
            QUNT_CR = source.QuntCr,
            RADZ0 = source.Radz0,
            SM = source.Sm,
            S_T_R = source.STR,

            VG0 = source.Vg0,
            PH0 = source.Ph0,
            BT = source.Bt,
            BG = source.Bg,

            Bt_Cp = source.BtCp,
            Bt_Tr = source.BtTr,

            MU_pazp = source.MuPazp,
            X_A = source.XA,
            X_D = source.XD,

            Q_zab = source.QZab,
            OBV_P = source.ObvP,
            QQ = source.Qq,
            P32 = source.P32,

            TVK = source.Tvk,
            TK = source.TkDays,
            LTVK = source.Ltvk,
            LTK = source.Ltk,
            DSO = source.Dso,

            TU = source.TuSeconds / 86400.0,
            N_Dr = source.NDr,
            NX = source.Nx,

            EPSP = source.Epsp,
            ENB = source.Enb,
            EVB = source.Evb,
            ENT = source.Ent,
            EVT = source.Evt,

            Tim_0 = source.Tim0,
            Tim_1 = source.Tim1,
            Tim_2 = source.Tim2
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
        return new CoreLayerConfig
        {
            NZM = layer.Nzm,
            HBM = layer.Hbm,
            VMB = layer.Vmb,
            VMT = layer.Vmt,
            LWN = layer.Lwn,
            LWD = layer.Lwd,
            SNT = layer.Snt,
            SNB = layer.Snb,
            SVT = layer.Svt,
            SVB = layer.Svb,
            AKT = layer.Akt,
            AKB = layer.Akb
        };
    }
}
