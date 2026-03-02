using System.Text.Json;

namespace Simulation.Core;

public class SimulationConfig
{
    public int NB { get; set; } = 5;
    public double VL { get; set; } = 100;
    public int LOD { get; set; } = 0;
    public int LIZ { get; set; } = 1;
    public double R_Skv { get; set; } = 0.1;

    public double Ro1_PL { get; set; } = 806.0;
    public double Ro1_deg { get; set; } = 870.0;
    public double Mu1_PL { get; set; } = 40.0;
    public double Mu_Deg { get; set; } = 26.0;
    public double AP1 { get; set; } = 0.0009;
    public double AT1 { get; set; } = 0.00125;
    public double C_P_1 { get; set; } = 1.88;

    public double Ro3_PL { get; set; } = 1020.0;
    public double Mu3_PL { get; set; } = 1.6;
    public double C_P_3 { get; set; } = 4.15;
    public double AP3 { get; set; } = 0.0004;
    public double AT3 { get; set; } = 0.0008;

    public double R00 { get; set; } = 1.12;
    public double C_P_2 { get; set; } = 2.7;
    public double VesGMol { get; set; } = 16.04;
    public double YTAP2 { get; set; } = 0.0008;
    public double DZT { get; set; } = 0.0035;
    public double ZG { get; set; } = 0.941;
    public double R_C_R { get; set; } = 1.0;
    public double QUNT_CR { get; set; } = 140.0;
    public double RADZ0 { get; set; } = 6.0;
    public double SM { get; set; } = 0.025;
    public double S_T_R { get; set; } = 167.5;

    public double VG0 { get; set; } = 40.0;
    public double PH0 { get; set; } = 12.0;
    public double BT { get; set; } = 0.02;
    public double BG { get; set; } = 0.004;

    public double Bt_Cp { get; set; } = 1e-5;
    public double Bt_Tr { get; set; } = 1e-5;

    public double MU_pazp { get; set; } = 8.0;
    public double X_A { get; set; } = 1.0;
    public double X_D { get; set; } = 0.25;

    public double Q_zab { get; set; } = 50.0;
    public double OBV_P { get; set; } = 180;
    public double QQ { get; set; } = 300;
    public double P32 { get; set; } = 130.0;

    public double TVK { get; set; } = 6;
    public double TK { get; set; } = 1000.3;
    public int LTVK { get; set; } = 0;
    public int LTK { get; set; } = 1;
    public double DSO { get; set; } = 30;
    
    // TU in days. 86.4 seconds = 0.001 days.
    public double TU { get; set; } = 86.4 / 86400.0; 
    public int N_Dr { get; set; } = 10;
    public int NX { get; set; } = 100;

    public double EPSP { get; set; } = 1e-6;
    public double ENB { get; set; } = 0.001;
    public double EVB { get; set; } = 0.001;
    public double ENT { get; set; } = 1e-4;
    public double EVT { get; set; } = 0.001;

    public double Tim_0 { get; set; } = 5000;
    public double Tim_1 { get; set; } = 10000;
    public double Tim_2 { get; set; } = 10000;

    public LayerConfig[] Layers { get; set; }

    public SimulationConfig()
    {
        Layers = new LayerConfig[NB];
        for (int i = 0; i < NB; i++)
        {
            Layers[i] = new LayerConfig
            {
                NZM = 4,
                HBM = 2,
                VMB = 0.2,
                VMT = 0.04,
                LWN = 1,
                LWD = 0,
                SNT = 0.1,
                SNB = 0.2,
                SVT = 0.9,
                SVB = 0.8,
                AKT = 0.1,
                AKB = 0.01
            };
        }

        // Layer 4 (index 3) overrides? No, indices in C# code were 1-based.
        // i=1..NB.
        // SNT[5] = 0.0, SVT[5] = 1.0, SNB[5] = 0.0, SVB[5] = 1.0
        // LWN[4]=0, LWN[5]=0, LWD[5]=1
        // AKT[4]=0.03, AKB[4]=0.001

        // Adjust for 0-based index
        if (NB >= 5)
        {
            // Layer 5 (index 4)
            Layers[4].SNT = 0.0;
            Layers[4].SVT = 1.0;
            Layers[4].SNB = 0.0;
            Layers[4].SVB = 1.0;
            Layers[4].LWN = 0;
            Layers[4].LWD = 1;
        }

        if (NB >= 4)
        {
            // Layer 4 (index 3)
            Layers[3].LWN = 0;
            Layers[3].AKT = 0.03;
            Layers[3].AKB = 0.001;
        }
    }

    public static SimulationConfig LoadFromJson(string path)
    {
        if (!File.Exists(path))
        {
            throw new FileNotFoundException($"Config file not found: {path}");
        }
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<SimulationConfig>(json) ?? new SimulationConfig();
    }
}

public class LayerConfig
{
    public int NZM { get; set; }
    public double HBM { get; set; }
    public double VMB { get; set; }
    public double VMT { get; set; }
    public int LWN { get; set; }
    public int LWD { get; set; }
    public double SNT { get; set; }
    public double SNB { get; set; }
    public double SVT { get; set; }
    public double SVB { get; set; }
    public double AKT { get; set; }
    public double AKB { get; set; }
}
