using ClassLibrary_Global;

namespace ClassLibrary_FissuredPorousOilReservoir;

public partial class ReservoirSimulationEngine
{
    private void Array_Of_Coefficients_On_SubPoints(ref int K_Out)
    {
        try
        {
            K_Out = 1;

            for (int I = 1; I <= NX + 1; I++)
                for (int K = 1; K <= NB; K++)
                    for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
                    {
                        int M1 = M + (I - 1) * NZ;
                        int M2 = M1 + NZ;
                        double AMUF = 0.5 * (WT[M1] + WT[M2]);
                        double R = 0.5 * (ST[M2] + ST[M1]);
                        double R1 = 0.0;
                        double R2 = 0.0;
                        double R3 = 0.0;
                        SKFT(SNT[K], SVT[K], R, AMUF, ref R1, ref R2, ref R3);
                        AT[M1] = R1 * APT[M1];
                        AMUF = 0.5 * (WB[M2] + WB[M1]);
                        R = 0.5 * (SB[M2] + SB[M1]);
                        SKFB(SNB[K], SVB[K], R, AMUF, ref R1, ref R2, ref R3);
                        AB[M1] = R1 * APB[M1];
                        A[M1] = AB[M1] + AT[M1];
                    }

            double RR1 = 0.0;
            double RRR1 = 0.0;
            double RR3 = 0.0;
            double RRR3 = 0.0;

            for (int I = 1; I <= NX; I++)
                for (int K = 1; K <= NB; K++)
                    for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
                    {
                        int M1 = M + (I - 1) * NZ;
                        int M2 = M1 + NZ;
                        double AMUF = WT[M2];
                        double R = ST[M2];
                        double R1 = 0.0;
                        double R2 = 0.0;
                        double R3 = 0.0;
                        SKFT(SNT[K], SVT[K], R, AMUF, ref R1, ref R2, ref R3);
                        double RR2 = R1 * BPT[M1];
                        R = 2 * RR1 * RR2 / (RR1 + RR2);
                        BT[M1] = R;
                        double RR4 = ROWO * R2 * HM[K];
                        BVT[M1] = 0.5 * R * (RR3 + RR4);

                        AMUF = WB[M2];
                        R = SB[M2];
                        SKFB(SNB[K], SVB[K], R, AMUF, ref R1, ref R2, ref R3);
                        double RRR2 = R1 * BPB[M1];
                        R = 2.0 * RRR1 * RRR2 / (RRR1 + RRR2);
                        BB[M1] = R;
                        double RRR4 = ROWO * R2 * HM[K];
                        BVB[M1] = 0.5 * R * (RRR3 + RRR4);

                        RR1 = RR2;
                        RRR1 = RRR2;
                        RR3 = RR4;
                        RRR3 = RRR4;
                        B[M1] = BB[M1] + BT[M1];
                    }

            for (int I = 1; I <= NX + 1; I++)
            {
                int M1 = 1 + (I - 1) * NZ;
                B[M1] = 0.0;
                BT[M1] = 0.0;
                BVT[M1] = 0.0;
                BB[M1] = 0.0;
                BVB[M1] = 0.0;
            }

            for (int K = 1; K <= N; K++)
                FG[K] = BVB[K + 1] + BVT[K + 1] - BVB[K] - BVT[K];

            for (int I = 1; I <= NX; I++)
                for (int k = 1; k <= NB; k++)
                    for (int M = 1 + NM[k - 1]; M <= NM[k]; M++)
                    {
                        int M1 = M + (I - 1) * NZ;
                        int M2 = M1 + NZ;
                        CBet[M1] = HM[k] * HX * HX * (I - 0.5) / TU *
                            (Bet_oB[k] + SB[M2] * (Bet_wB[k] - Bet_oB[k]) +
                             Bet_oT[k] + ST[M2] * (Bet_wT[k] - Bet_oT[k]));
                        FG[M1] = FG[M1] - CBet[M1] * P_0[M2];
                    }
        }
        catch
        {
            K_Out = -1;
        }
    }

    private void Coefficients_For_Evaluate_Pressure(ref int K_Out)
    {
        try
        {
            K_Out = 1;

            for (int I = 1; I <= NX + 1; I++)
            {
                SIG_P[I] = 0.0;
                for (int k = 1; k <= NZ; k++)
                {
                    int M = k + (I - 1) * NZ;
                    SIG_P[I] = SIG_P[I] + A[M];
                }
            }

            for (int I = 2; I <= NX + 1; I++)
            {
                CS[I] = 0;
                for (int k = 1; k <= NZ; k++)
                {
                    int M = k + (I - 2) * NZ;
                    CS[I] = CS[I] + CBet[M];
                }
            }

            CS[1] = 1.0 / SIG_P[1];
            CS[2] = 1.0 / (SIG_P[2] + CS[2] + LPQ1 * SIG_P[1]);
            for (int I = 2; I <= NX; I++)
            {
                int I1 = I + 1;
                CS[I1] = 1.0 / (SIG_P[I1] + CS[I1] + (1 - SIG_P[I] * CS[I]) * SIG_P[I]);
            }
            for (int I = 1; I <= N; I++)
                C[I] = A[I] + A[I + NZ] + B[I] + B[I + 1] + CBet[I];

            AX[1 + N] = 0.0;
            int K = 1;

            do
            {
                int I1 = 0;
                int I2 = 0;
                int I3 = 0;

                for (int I = 1; I <= NZ; I++)
                {
                    int IK = I + K - 1;
                    I1 = IK + I;
                    I2 = I1 - 1;
                    I3 = IK + NZ;
                    AX[I2] = B[IK]; AX[I1] = B[I3];
                    AY[I2] = 0.0; AY[I1] = A[I3];
                    ZM[2 * I - 1] = C[IK]; ZM[2 * I] = C[I3];
                }
                int K1 = K + 1;
                int K2 = K1 + 1;
                C[K] = 1.0 / ZM[1];
                GM[K] = AY[K1] * C[K];
                BM[K] = AX[K2] * C[K];
                C[K1] = 1.0 / (ZM[2] - AY[K1] * GM[K]);
                GM[K1] = AY[K1] * BM[K] * C[K1];
                BM[K1] = AX[K1 + 2] * C[K1];

                for (int I = K2; I <= I2; I++)
                {
                    I1 = I - 1;
                    int I0 = I - 2;
                    int M = 3 + I - K2;
                    C[I] = 1.0 / (ZM[M] - AX[I] * (BM[I0] + GM[I1] * GM[I0]) - AY[I] * GM[I1]);
                    GM[I] = (AY[I + 1] + AY[I] * BM[I1] + AX[I] * BM[I1] * GM[I0]) * C[I];
                    BM[I] = AX[I + 2] * C[I];
                }
                C[I3] = 1.0 / (ZM[NZ2] - AX[I3] * (BM[I1] + GM[I2] * GM[I1]) - AY[I3] * GM[I2]);
                K = K + NZ2;
            }
            while (K != NKON + NZ2);

        }
        catch
        {
            K_Out = -1;
        }
    }

    private void Circular_Pass(ref int K_Out)
    {
        try
        {
            K_Out = 1;
            DL = 0.0;
            int K = 1;
            do
            {
                int K1 = K - 1;
                int K1N = K1 + NZ2;
                int K1NZ = K1N + NZ;
                for (int I = 1; I <= NZ; I++)
                {
                    int M1 = K1 + I;
                    int M2 = M1 + NZ2;
                    ZM[I + I - 1] = A[M1] * P[M1] - FG[M1];
                    ZM[I + I] = A[M2] * P[M2 + NZ] - FG[M2 - NZ];
                }
                int K2 = K + 1;
                ZM[1] = ZM[1] * C[K];
                ZM[2] = (AY[K2] * ZM[1] + ZM[2]) * C[K2];
                for (int I = 3; I <= NZ2; I++)
                {
                    int M = K1 + I;
                    ZM[I] = (ZM[I - 1] * (AY[M] + AX[M] * GM[M - 2]) + ZM[I - 2] * AX[M] + ZM[I]) * C[M];
                }
                double R1 = ZM[NZ2];
                if (DL < Maths.Abs(R1 - P[K1NZ])) DL = Maths.Abs(R1 - P[K1NZ]);
                P[K1NZ] = R1;
                double R2 = ZM[NZ2 - 1] + GM[K1N - 1] * R1;
                if (DL < Maths.Abs(R2 - P[K1N])) DL = Maths.Abs(R2 - P[K1N]);
                P[K1N] = R2;
                for (int I = NZ - 1; I >= 1; I--)
                {
                    int I2 = I + I;
                    int M = K1 + I2;
                    int M1 = K1N + I;
                    R1 = ZM[I2] + GM[M] * R2 + BM[M] * R1;
                    if (DL < Maths.Abs(R1 - P[M1])) DL = Maths.Abs(R1 - P[M1]);
                    P[M1] = R1;
                    M = M - 1;
                    M1 = M1 - NZ;
                    R2 = ZM[I2 - 1] + GM[M] * R1 + BM[M] * R2;
                    if (DL < Maths.Abs(R2 - P[M1])) DL = Maths.Abs(R2 - P[M1]);
                    P[M1] = R2;
                }
                K = K + NZ2;
            }
            while (K != NKON + NZ2);

        }
        catch
        {
            K_Out = -1;
        }
    }

    private void Do_Iteration(ref int K_Out)
    {
        try
        {
            K_Out = 1;

            DL1 = 0.0;
            for (int K = 1; K <= NX + 1; K++)
            {
                FI[K] = 0.0;
                for (int I = 1 + (K - 1) * NZ; I <= K * NZ; I++)
                    FI[K] = FI[K] + A[I] * (P[I + NZ] - P[I]);
            }

            for (int K = NX; K >= 1; K--)
            {
                int K1 = K + 1;
                FI[K1] = FI[K1] - FI[K];
            }

            for (int I = 1; I <= NX; I++)
            {
                double RR = 0.0;
                for (int K = 1; K <= NB; K++)
                    for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
                    {
                        int M1 = M + (I - 1) * NZ;
                        int M2 = M1 + NZ;
                        RR = RR + FG[M1] + CBet[M1] * P[M2];
                    }
                FI[I + 1] = FI[I + 1] - RR;
            }

            FI[1] = LPQ * (FI[1] - Q_zab) * CS[1];
            for (int K = 2; K <= NX + 1; K++)
                FI[K] = (FI[K] + FI[K - 1] * SIG_P[K - 1]) * CS[K];
            for (int K = NX; K >= 2; K--)
            {
                FI[K] = SIG_P[K] * CS[K] * FI[K + 1] + FI[K];
                if (DL1 < Maths.Abs(FI[K])) DL1 = Maths.Abs(FI[K]);
            }

            FI[1] = LPQ * FI[2] + FI[1];
            if (DL1 < Maths.Abs(FI[1])) DL1 = Maths.Abs(FI[1]);
            LS = LS + 1;
            for (int K = 1; K <= NX + 1; K++)
                for (int I = 1; I <= NZ; I++)
                {
                    int M = I + (K - 1) * NZ;
                    P[M] = P[M] + FI[K];
                }
        }
        catch
        {
            K_Out = -1;
        }
    }

    internal void Calc_Filt_Process_Pressure(bool DoExternalInterations, ref int K_Out)
    {
        try
        {
            K_Out = 1;
            Array_Of_Coefficients_On_SubPoints(ref K_Out);
            if (K_Out == -1) return;
            Coefficients_For_Evaluate_Pressure(ref K_Out);
            if (K_Out == -1) return;
            LS = 0;
            do
            {
                if (DoExternalInterations)
                {
                    Array_Of_Coefficients_On_SubPoints(ref K_Out);
                    if (K_Out == -1) return;
                    Coefficients_For_Evaluate_Pressure(ref K_Out);
                    if (K_Out == -1) return;
                    Circular_Pass(ref K_Out);
                    if (K_Out == -1) return;
                    Do_Iteration(ref K_Out);
                    if (K_Out == -1) return;
                    if (NB1 < NB)
                        for (int i = NM[NB1] + 1; i <= NM[NB]; i++)
                            P[i] = P[i + NZ];
                    Calculation_Of_Total_Flows();
                    VISCOSITIES();
                }
                else
                {
                    Circular_Pass(ref K_Out);
                    if (K_Out == -1) return;
                    Do_Iteration(ref K_Out);
                    if (K_Out == -1) return;
                }

                if (LS >= LKM_Max)
                {
                    K_Out = -2;
                    return;
                }
            }
            while (!(DL + DL1 <= EPSP));

            P_zab_DC = P[1];
        }
        catch
        {
            K_Out = -1;
        }
    }
}
