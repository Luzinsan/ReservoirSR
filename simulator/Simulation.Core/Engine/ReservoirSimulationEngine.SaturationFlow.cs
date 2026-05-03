using ClassLibrary_Global;

namespace ClassLibrary_FissuredPorousOilReservoir;

public partial class ReservoirSimulationEngine
{
    public void Calculation_Of_Total_Flows()
    {
        // 7.ВЫЧИСЛЕНИЕ  СУММАРНЫХ ПОТОКОВ И ПЕРЕТОКОВ Б-Т
        LSS = LSS + LS;

        for (int i = 1; i <= N1; i++)
        {
            AVT[i] = AT[i] * (P[i + NZ] - P[i]);
            AVB[i] = AB[i] * (P[i + NZ] - P[i]);
        }

        for (int i = 2; i <= N; i++)
        {
            int INZ = i + NZ;
            BVT[i] = BT[i] * (P[INZ] - P[INZ - 1]) - BVT[i];
            BVB[i] = BB[i] * (P[INZ] - P[INZ - 1]) - BVB[i];
        }

        for (int i = 1; i <= N; i++)
            B[i] = -(AVB[i + NZ] - AVB[i] + BVB[i + 1] - BVB[i]);

        for (int i = 1; i <= NX; i++)
            for (int k = 1; k <= NB; k++)
                for (int m = 1 + NM[k - 1]; m <= NM[k]; m++)
                {
                    int M1 = m + (i - 1) * NZ;
                    int M2 = M1 + NZ;
                    B[M1] = B[M1] + HM[k] * HX * HX * (i - 0.5) * (P[M2] - P_0[M2]) / TU *
                        (Bet_oB[k] + SB[M2] * (Bet_wB[k] - Bet_oB[k]));
                }
    }

    public void Calculation_Of_Phases_Flows_By_Vertical_Grid_Lines(int i)
    {
        for (int k = 1; k <= NB; k++)
            for (int m = 1 + NM[k - 1]; m <= NM[k]; m++)
            {
                int m1 = m + (i - 1) * NZ;
                int m2 = m1 + NZ;
                if (B[m1] >= 0)
                {
                    double AMUF = WT[m2];
                    double R = ST[m2];
                    double R1 = 0.0;
                    double R2 = 0.0;
                    double R3 = 0.0;
                    SKFT(SNT[k], SVT[k], R, AMUF, ref R1, ref R2, ref R3);
                    A[m1] = R2 * B[m1];
                }
                else
                {
                    double AMUF = WB[m2];
                    double R = SB[m2];
                    double R1 = 0.0;
                    double R2 = 0.0;
                    double R3 = 0.0;
                    SKFB(SNB[k], SVB[k], R, AMUF, ref R1, ref R2, ref R3);
                    A[m1] = R2 * B[m1];
                }
            }
    }

    public void Calculation_Of_Phases_Flows()
    {
        for (int I = 1; I <= NX; I++)
            for (int K = 1; K <= NB; K++)
                for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
                {
                    int M1 = M + (I - 1) * NZ;
                    int M2 = M1 + NZ;
                    if (B[M1] >= 0)
                    {
                        double AMUF = WT[M2];
                        double R = ST[M2];
                        double R1 = 0.0;
                        double R2 = 0.0;
                        double R3 = 0.0;
                        SKFT(SNT[K], SVT[K], R, AMUF, ref R1, ref R2, ref R3);
                        A[M1] = R2 * B[M1];
                    }
                    else
                    {
                        double AMUF = WB[M2];
                        double R = SB[M2];
                        double R1 = 0.0;
                        double R2 = 0.0;
                        double R3 = 0.0;
                        SKFB(SNB[K], SVB[K], R, AMUF, ref R1, ref R2, ref R3);
                        A[M1] = R2 * B[M1];
                    }
                }
    }

    public void Saturations()
    {
        for (int K = 1; K <= NM[NB1]; K++)
        {
            QS_T[K] = 0.0;
            QS_B[K] = 0.0;
        }
        QP_TB = 0.0;
        QP_BT = 0.0;

        for (int L = 1; L <= N_Dr; L++)
        {
            Calculation_Of_Phases_Flows();

            int kk = 1 + NM[NB - 1];
            for (int I = 1; I <= NX; I++)
            {
                int M = kk + (I - 1) * NZ;
                BVST[M] = BVT[M];
                BVSB[M] = BVB[M];
            }

            for (int I = 1; I <= NX; I++)
                for (int K = 1; K <= NB - 1; K++)
                    for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
                    {
                        int M1 = M + (I - 1) * NZ;
                        int M2 = M1 + NZ;
                        double R = SB[M2];
                        double R1 = 0.0;
                        double R2 = 0.0;
                        double R3 = 0.0;
                        if (R < ESNB[K])
                        {
                            R2 = 0; R3 = 0;
                        }
                        else
                        {
                            double AMUF = WB[M2];
                            SKFB(SNB[K], SVB[K], R, AMUF, ref R1, ref R2, ref R3);
                        }
                        if (AVB[M1] >= 0) AVSB[M1] = R2 * AVB[M1];
                        if (AVB[M2] < 0) AVSB[M2] = R2 * AVB[M2];
                        if (M == 1) BVSB[M1] = 0;
                        else
                        {
                            BVSB[M1] = R2 * BVB[M1] - BPCB[M1] * R3;
                            if (BVSB[M1] <= 0)
                            {
                                double RS = SB[M2 - 1];
                                double AMUF = WB[M2 - 1];
                                int KK = K;
                                if (M == 1 + NM[K - 1])
                                    KK = K - 1;
                                SKFB(SNB[KK], SVB[KK], RS, AMUF, ref R1, ref R2, ref R3);
                                double RR1 = R2 * BVB[M1] - BPCB[M1 - 1] * R3;
                                if (RS < R) BVSB[M1] = Maths.Max(BVSB[M1], RR1);
                                else BVSB[M1] = Maths.Min(BVSB[M1], RR1);
                            }
                        }
                    }

            for (int K = 1; K <= NB - 1; K++)
                for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
                {
                    double AMUF = WB[M];
                    double R1 = 0.0;
                    double R2 = 0.0;
                    double R3 = 0.0;
                    SKFB(SNB[K], SVB[K], SB[M + NZ], AMUF, ref R1, ref R2, ref R3);
                    AVSB[M] = R2 * AVB[M];
                }
            for (int K = 1; K <= NM[NB - 1]; K++) AVSB[N + K] = 0;

            for (int K = 1; K <= NM[NB - 1]; K++)
                for (int I = 1; I <= NX; I++)
                {
                    int M = K + (I - 1) * NZ;
                    int M1 = M + NZ;
                    int M2 = 1;
                    if (K > NM[1])
                        for (int ii = 2; ii <= NB - 1; ii++)
                            if ((K >= NM[ii - 1]) && (K <= NM[ii]))
                            {
                                M2 = ii;
                                break;
                            }

                    double R = Tau_D / (VPIB[K] * (I - 0.5));
                    SB[M1] = SB[M1] + R * (A[M] + AVSB[M1] - AVSB[M] + BVSB[M + 1] - BVSB[M]);
                    if (SB[M1] < SNB[M2])
                        SB[M1] = SNB[M2];
                }

            for (int I = 1; I <= NX; I++)
                for (int K = 1; K <= NB - 1; K++)
                {
                    for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
                    {
                        int M1 = M + (I - 1) * NZ;
                        int M2 = M1 + NZ;
                        double R = ST[M2];
                        double R1 = 0.0;
                        double R2 = 0.0;
                        double R3 = 0.0;
                        if (R < ESNT[K])
                        {
                            R2 = 0; R3 = 0;
                        }
                        else
                        {
                            if (R > ESVT[K])
                            {
                                R2 = 1; R3 = 0;
                            }
                            else
                            {
                                double AMUF = WT[M2];
                                SKFT(SNT[K], SVT[K], R, AMUF, ref R1, ref R2, ref R3);
                            }
                        }
                        if (AVT[M1] >= 0) AVST[M1] = R2 * AVT[M1];
                        if (AVT[M2] < 0) AVST[M2] = R2 * AVT[M2];
                        if (M == 1) BVST[M1] = 0;
                        else
                        {
                            BVST[M1] = R2 * BVT[M1] - BPCT[M1] * R3;
                            if (BVST[M1] <= 0)
                            {
                                double RS = ST[M2 - 1];
                                double AMUF = WT[M2 - 1];
                                int KK = K; if (M == 1 + NM[K - 1]) KK = K - 1;
                                SKFT(SNT[KK], SVT[KK], RS, AMUF, ref R1, ref R2, ref R3);
                                double RR1 = R2 * BVT[M1] - BPCT[M1 - 1] * R3;
                                if (RS < R) BVST[M1] = Maths.Max(BVST[M1], RR1);
                                else BVST[M1] = Maths.Min(BVST[M1], RR1);
                            }
                        }
                    }
                }

            for (int K = 1; K <= NM[NB - 1]; K++) AVST[N + K] = 0;

            for (int K = NB - 1; K >= 1; K--)
                for (int m = NM[K]; m >= 1 + NM[K - 1]; m--)
                    for (int I = 1; I <= NX - 1; I++)
                    {
                        int M1 = m + I * NZ;
                        int M2 = M1 + NZ;
                        double R = Tau_D / (VPIT[m] * (I + 0.5));
                        ST[M2] = ST[M2] + R * (-A[M1] + AVST[M2] - AVST[M1] + BVST[M1 + 1] - BVST[M1]);
                        if (ST[M2] < SNT[K])
                            ST[M2] = SNT[K];
                        if (ST[M2] > SVT[K])
                        {
                            ST[M2 - 1] = ST[M2 - 1] + (ST[M2] - SVT[K]) * (VPIT[m] / VPIT[m - 1]);
                            ST[M2] = SVT[K];
                        }
                    }

            for (int K = 1; K <= NB - 1; K++)
                for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
                {
                    double AMUF = WT[M];
                    double R1 = 0.0;
                    double R2 = 0.0;
                    double R3 = 0.0;
                    SKFT(SNT[K], SVT[K], ST[M + NZ], AMUF, ref R1, ref R2, ref R3);
                    AVST[M] = R2 * AVT[M];
                }

            for (int K = NB - 1; K >= 1; K--)
                for (int m = NM[K]; m >= 1 + NM[K - 1]; m--)
                {
                    int M1 = m;
                    int M2 = M1 + NZ;
                    double R = 2 * Tau_D / VPIT[m];
                    ST[M2] = ST[M2] + R * (-A[M1] + AVST[M2] - AVST[M1] + BVST[M1 + 1] - BVST[M1]);
                    if (ST[M2] < SNT[K])
                        ST[M2] = SNT[K];
                    if (ST[M2] > SVT[K])
                    {
                        ST[M2 - 1] = ST[M2 - 1] + (ST[M2] - SVT[K]) * (VPIT[m] / VPIT[m - 1]);
                        ST[M2] = SVT[K];
                    }
                }

            for (int k = 1; k <= NM[NB1]; k++)
            {
                QS_T[k] = QS_T[k] + AVST[k];
                QS_B[k] = QS_B[k] + AVSB[k];
            }
            for (int k = 1; k <= N; k++)
            {
                if (A[k] > 0) QP_TB = QP_TB + A[k];
                else QP_BT = QP_BT - A[k];
            }
        }

        for (int k = 1; k <= NM[NB1]; k++)
        {
            AVST[k] = QS_T[k] / N_Dr;
            AVSB[k] = QS_B[k] / N_Dr;
        }

        for (int K = 1; K <= NZ; K++)
        {
            ST[K] = ST[K + NZ];
            SB[K] = SB[K + NZ];
            ST[K + N1] = ST[K + N];
            SB[K + N1] = SB[K + N];
        }
    }

    public void Main_Characts()
    {
        Q_TB = Q_TB + QP_TB / N_Dr * TU;
        Q_BT = Q_BT + QP_BT / N_Dr * TU;

        for (int K = 1; K <= N; K++)
            if (B[K] > 0) Pr_TB = Pr_TB + B[K] * TU;
            else Pr_BT = Pr_BT - B[K] * TU;

        for (int K = 1; K <= NB1; K++)
        {
            QSM_T[K] = 0;
            QSM_B[K] = 0;
            QTM[K] = 0;
            QBM[K] = 0;
        }

        QT = 0; QB = 0;
        double QST = 0;
        double QSB = 0;
        for (int k = 1; k <= NB1; k++)
        {
            for (int M = 1 + NM[k - 1]; M <= NM[k]; M++)
            {
                QSM_T[k] = QSM_T[k] + AVST[M];
                QSM_B[k] = QSM_B[k] + AVSB[M];
                QTM[k] = QTM[k] + AVT[M];
                QBM[k] = QBM[k] + AVB[M];
            }
            Q_SumSl_T[k] = Q_SumSl_T[k] + QTM[k] * TU;
            Qoil_SumSl_T[k] = Qoil_SumSl_T[k] + (QTM[k] - QSM_T[k]) * TU;
            Q_SumSl_B[k] = Q_SumSl_B[k] + QBM[k] * TU;
            Qoil_SumSl_B[k] = Qoil_SumSl_B[k] + (QBM[k] - QSM_B[k]) * TU;
            AIT_M[k] = QSM_T[k] / (QTM[k] + 1e-6) * 100;
            AIB_M[k] = QSM_B[k] / (QBM[k] + 1e-6) * 100;
            QT = QT + QTM[k];
            QB = QB + QBM[k];
            QST = QST + QSM_T[k];
            QSB = QSB + QSM_B[k];
        }
        AIT = QST / (QT + 1e-6) * 100;
        AIB = QSB / (QB + 1e-6) * 100;
        AI = (QSB + QST) / (Q_zab + 1e-6) * 100;
        if (QT < 0.1)
        {
            AIT = 0; AIB = 0; AI = 0;
        }

        TB = 0; TT = 0;
        for (int K = 1; K <= NB - 1; K++)
            for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
                for (int I = 1; I <= NX; I++)
                {
                    int M1 = M + I * NZ;
                    TB = TB + (SB[M1] - SNB[K]) * (VPIB[M] * (I - 0.5));
                    TT = TT + (ST[M1] - SNT[K]) * (VPIT[M] * (I - 0.5));
                }
        TBQ = TBQ + (QB - QSB) * TU;
        TTQ = TTQ + (QT - QST) * TU;
        Q_fld = Q_fld + 2 * Math.PI * (QB + QT) * TU;
        DISS = TT - TTQ - (Pr_TB - Pr_BT + Q_BT - Q_TB);
        DISQ = TB - TBQ - (Pr_BT - Pr_TB + Q_TB - Q_BT);

        TBT = 2 * Math.PI * (TB + TT) / VNE * 100;
        TB = 2 * Math.PI * TB / VNEB * 100;
        TT = 2 * Math.PI * TT / VNET * 100;
    }

    public void VISCOSITIES()
    {
        for (int K = 1; K <= NB - 1; K++)
            for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
            {
                for (int I = 1; I <= NX; I++)
                {
                    int M1 = M + (I - 1) * NZ;
                    double R1 = (AVT[M1 + NZ] + AVT[M1]) / HM[K];
                    double R2 = (BVT[M1 + 1] + BVT[M1]) / HX;
                    double R = Math.Sqrt(R1 * R1 + R2 * R2) / ((2 * I - 1) * HX);
                    WKF(R, ref R1);
                    WT[M1 + NZ] = R1;
                    R1 = (AVB[M1 + NZ] + AVB[M1]) / HM[K];
                    R2 = (BVB[M1 + 1] + BVB[M1]) / HX;
                    R = Math.Sqrt(R1 * R1 + R2 * R2) / ((2 * I - 1) * HX);
                    WKF(R, ref R1);
                    WB[M1 + NZ] = R1;
                }
                WT[M] = WT[M + NZ];
                WT[M + N1] = WT[M + N];
                WB[M] = WB[M + NZ];
                WB[M + N1] = WB[M + N];
            }

        double RR1 = HZM[1] * (AVST[1] + AVSB[1]) / (AVT[1] + AVB[1]);
        for (int K = 2; K <= NM[NB1]; K++)
        {
            double R2 = HZM[K] * (AVST[K] + AVSB[K]) / (AVT[K] + AVB[K]);
            P[K] = P[K - 1] + 0.5 * ROWO * (RR1 + R2);
            RR1 = R2;
        }
        for (int K = NM[NB1] + 1; K <= NZ; K++)
            P[K] = P[NM[NB1]];

        if (AI > OBV_P)
            if (Q_Izm_Fix == 0)
            {
            }
    }
}
