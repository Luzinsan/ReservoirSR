namespace ClassLibrary_FissuredPorousOilReservoir;

public partial class ReservoirSimulationEngine
{
    public void SKFB(double S1, double S2, double X, double AMUF, ref double BKF, ref double FK, ref double Psik)
    {
        double SK1, SK2;
        if (X <= S1) SK1 = 0.0;
        else SK1 = Math.Pow((X - S1) / S2, 3.13) / MixtureProperties.WaterProperties.Mu3_PL;
        if (X >= S2) SK2 = 0.0;
        else SK2 = Math.Pow((S2 - X) / (S2 - S1), 2.73) / AMUF;
        BKF = SK1 + SK2;
        FK = SK1 / BKF;
        Psik = FK * SK2;
    }

    public void SKFT(double S1, double S2, double X, double AMUF, ref double BKF, ref double FK, ref double Psik)
    {
        double SK1, SK2;
        if (X <= S1) SK1 = 0.0;
        else SK1 = (X - S1) / MixtureProperties.WaterProperties.Mu3_PL;
        if (X >= S2) SK2 = 0.0;
        else SK2 = (S2 - X) / AMUF;
        BKF = SK1 + SK2;
        FK = SK1 / BKF;
        Psik = FK * SK2;
    }

    public void WKF(double ModV, ref double Vis)
    {
        if (ModV < X_A)
            Vis = 1.0 / (1.0 / MixtureProperties.OilProperties.Mu1_PL + a_ * Math.Pow(ModV, b_) * Math.Exp(-c_ * ModV));
        else
            Vis = MU_pazp;
    }
}
