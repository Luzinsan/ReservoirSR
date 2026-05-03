using ClassLibrary_Global;

namespace ClassLibrary_FissuredPorousOilReservoir;

public partial class ReservoirSimulationEngine
{
    public void AdvanceSingleStep()
    {
        int kOut = 1;
        Calc_Filt_Process_Pressure(false, ref kOut);
        if (kOut == -2)
        {
            throw new InvalidOperationException(
                $"Pressure solver did not converge after {LS} iterations at t={T:F6}."
            );
        }

        if (kOut == -1)
        {
            throw new InvalidOperationException(
                $"Calc_Filt_Process_Pressure failed at t={T:F6}, NX={NX}, NZ={NZ}."
            );
        }

        Saturation_and_Main_Characts(false, ref kOut);
        if (kOut == -1)
        {
            throw new InvalidOperationException(
                $"Saturation_and_Main_Characts failed at t={T:F6}, NX={NX}, NZ={NZ}."
            );
        }

        T_Tek += TU;
        T += TU;
        for (int k = 1; k <= N1; k++)
        {
            P_0[k] = P[k];
        }
    }

    public void Prepear_To_Go_New_Time_Sublayer(ref int Cod_Out)
    {
        LST = LST + 1;
        Cod_Out = 1;
        T_Tek = T_Tek + TU;
        T = T + TU;
        if (T_Tek + TU / 4 > DSO)
        {
            T_Tek = 0;
        }

        while (Cod_Out > 0)
        {
            switch (Cod_Out)
            {
                case 1: if (LTVK == 0) Cod_Out = 3; else Cod_Out = 2; break;
                case 2: if (AI >= TVK) Cod_Out = 7; else Cod_Out = 3; break;
                case 3: if (LTK == 0) Cod_Out = 5; else Cod_Out = 4; break;
                case 4: if (T + TU / 4 >= TK) Cod_Out = 7; else Cod_Out = 5; break;
                case 5: if (LTB == 1) Cod_Out = -1; else Cod_Out = 6; break;
                case 6:
                    if (AI > 1)
                    {
                        LTB = 1;
                    }
                    Cod_Out = -1;
                    break;
                case 7:
                    Cod_Out = 0;
                    break;
            }
        }
    }

    public void Clc_Of_Qz_At_Pz_Fix(bool DoExternalInterations, double P_Zb_Fix, ref int K_Out)
    {
        int PrA, PrB, N_itr_Pz, N_itr = 0;
        double Qzab_A = 0.0, Qzab_B = 0.0, Ra, Rb;
        double Pz_A, Pz_B;

        const double Eps = 1e-3;
        try
        {
            Pz_A = 0.0; Pz_B = 0.0;
            PrA = 0; PrB = 0; N_itr_Pz = 0;

            while (PrA + PrB != 2)
            {
                Calc_Filt_Process_Pressure(DoExternalInterations, ref K_Out);

                if (Maths.Abs(P_zab_DC - P_Zb_Fix) <= Eps)
                {
                    break;
                }

                if (P_zab_DC > P_Zb_Fix)
                {
                    Qzab_A = Q_zab;
                    if (PrB == 0.0)
                        Qzab_B = Q_zab + 0.1;
                    Pz_A = P_zab_DC;
                    PrA = 1;
                }
                else
                {
                    Qzab_B = Q_zab;
                    if (PrA == 0.0)
                        Qzab_A = Q_zab - 0.1;
                    Pz_B = P_zab_DC;
                    PrB = 1;
                }

                Q_zab = (Qzab_A + Qzab_B) / 2;
                N_itr_Pz = N_itr_Pz + 1;
                N_itr = N_itr_Pz;

                if (N_itr > 30)
                {
                    K_Out = -2;
                    return;
                }
            }

            while (Maths.Abs(P_zab_DC - P_Zb_Fix) > Eps)
            {
                Ra = Maths.Abs((Pz_A - P_Zb_Fix) / (Pz_A - Pz_B));
                Rb = Maths.Abs((Pz_B - P_Zb_Fix) / (Pz_A - Pz_B));
                if (N_itr_Pz - N_itr > 50)
                {
                    if (Ra < Rb)
                    {
                        P_zab_DC = Pz_B;
                    }
                    if (Ra >= Rb)
                    {
                        P_zab_DC = Pz_A;
                    }
                    break;
                }

                Q_zab = Qzab_B * (1 - Rb) + Qzab_A * (1 - Ra);
                Calc_Filt_Process_Pressure(DoExternalInterations, ref K_Out);

                if (P_zab_DC > P_Zb_Fix)
                {
                    Pz_B = P_zab_DC; Qzab_B = Q_zab;
                }
                else
                {
                    Pz_A = P_zab_DC; Qzab_A = Q_zab;
                }
                N_itr_Pz = N_itr_Pz + 1;
            }

            N_itr_Out = N_itr_Pz;
            Q_Dob = Q_zab * 2.0 * Math.PI;
        }
        catch
        {
            K_Out = -1;
        }
    }

    public void Saturation_and_Main_Characts(bool DoExternalInterations, ref int K_Out)
    {
        K_Out = 1;
        try
        {
            if (DoExternalInterations)
            {
                if (NB1 < NB)
                    for (int i = NM[NB1] + 1; i <= NM[NB]; i++)
                        P[i] = P[i + NZ];
                Saturations();
                Main_Characts();
            }
            else
            {
                if (NB1 < NB)
                    for (int i = NM[NB1] + 1; i <= NM[NB]; i++)
                        P[i] = P[i + NZ];
                Calculation_Of_Total_Flows();
                Saturations();
                Main_Characts();
                VISCOSITIES();
            }
        }
        catch
        {
            K_Out = -1;
        }
    }
}
