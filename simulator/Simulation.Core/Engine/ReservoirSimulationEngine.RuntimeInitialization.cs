namespace ClassLibrary_FissuredPorousOilReservoir;

public partial class ReservoirSimulationEngine
{
    public void InitializeRuntimeState()
    {
        Create_Work_Dyn_Arrayes();

        T = 0.0;
        Q_zab = ConfiguredQZab / (2.0 * Math.PI);
        QQ_ICX = Q_zab;

        Prepaire_Of_Constants();
        for (int k = 1; k <= NB; k++)
        {
            for (int i = 1 + NM[k - 1]; i <= NM[k]; i++)
            {
                HZM[i] = HM[k];
                VPIT[i] = VMT[k] * HM[k] * HX * HX;
                VPIB[i] = VMB[k] * HM[k] * HX * HX;
            }
        }

        VPIT[0] = VPIT[1];
        VPIB[0] = VPIB[1];
        HZM[NZ + 1] = 0.0;

        Evaluate_Of_Parameters();
        Boundary_Conditions_And_Initial_Appr();
        Initialization_Of_S0(false);
        Prepeare_Of_Array_Abs_Permeability();
        Cod_Exit = 15;
    }
}
