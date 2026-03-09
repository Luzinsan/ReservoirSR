namespace ClassLibrary_FissuredPorousOilReservoir;

public partial class ReservoirSimulationEngine
{
    public void Create_Ini_Arrayes_Razm_NB()
    {
        int K_Uz = NB + 2;
        Array.Resize<int>(ref NZM, K_Uz); Array.Resize<int>(ref NM, K_Uz);
        Array.Resize<int>(ref LWN, K_Uz); Array.Resize<int>(ref LWD, K_Uz);
        Array.Resize<double>(ref VMT, K_Uz); Array.Resize<double>(ref VMB, K_Uz);
        Array.Resize<double>(ref SNT, K_Uz); Array.Resize<double>(ref SNB, K_Uz);
        Array.Resize<double>(ref SVT, K_Uz); Array.Resize<double>(ref SVB, K_Uz);
        Array.Resize<double>(ref AKT, K_Uz); Array.Resize<double>(ref AKB, K_Uz);
        Array.Resize<double>(ref ESNT, K_Uz); Array.Resize<double>(ref ESNB, K_Uz);
        Array.Resize<double>(ref ESVT, K_Uz); Array.Resize<double>(ref ESVB, K_Uz);
        Array.Resize<double>(ref VPORTM, K_Uz); Array.Resize<double>(ref VPORBM, K_Uz);
        Array.Resize<double>(ref VNETM, K_Uz); Array.Resize<double>(ref VNEBM, K_Uz);
        Array.Resize<double>(ref Bet_wB, K_Uz); Array.Resize<double>(ref Bet_oB, K_Uz);
        Array.Resize<double>(ref Bet_wT, K_Uz); Array.Resize<double>(ref Bet_oT, K_Uz);
        Array.Resize<double>(ref HM, K_Uz); Array.Resize<double>(ref HBM, K_Uz);
        Array.Resize<double>(ref VM, K_Uz); Array.Resize<double>(ref AKX, K_Uz);
        Array.Resize<double>(ref AKZ, K_Uz);
    }

    public void Free_Ini_Arrayes_Razm_NB()
    {
        NZM = null; NM = null;
        LWN = null; LWD = null;
        VMT = null; VMB = null;
        SNT = null; SNB = null;
        SVT = null; SVB = null;
        AKT = null; AKB = null;
        ESNT = null; ESNB = null;
        ESVT = null; ESVB = null;
        VPORTM = null; VPORBM = null;
        VNETM = null; VNEBM = null;
        Bet_wB = null; Bet_oB = null;
        Bet_wT = null; Bet_oT = null;
        HM = null; HBM = null;
        VM = null; AKX = null;
        AKZ = null;
    }

    public void Create_Work_Arrayes_AP_BP()
    {
        int K_Uz = (NX + 3) * (NZ + 3);
        Array.Resize<double>(ref AP, K_Uz); Array.Resize<double>(ref BP, K_Uz);
        Array.Resize<double>(ref APP, K_Uz); Array.Resize<double>(ref BPP, K_Uz);
    }

    public void Free_Work_Arrayes_AP_BP()
    {
        AP = null; Kabx = null; APP = null;
        BP = null; Kabz = null; BPP = null;
    }

    public void Create_Work_Dyn_Arrayes()
    {
        int K_Uz;
        Free_Work_Dyn_Arrayes();
        K_Uz = (NX + 3) * (NZ + 3);
        Array.Resize<double>(ref AVST, K_Uz); Array.Resize<double>(ref AVSB, K_Uz); Array.Resize<double>(ref ST, K_Uz);
        Array.Resize<double>(ref SB, K_Uz); Array.Resize<double>(ref WT, K_Uz); Array.Resize<double>(ref WB, K_Uz);
        Array.Resize<double>(ref A, K_Uz); Array.Resize<double>(ref AT, K_Uz); Array.Resize<double>(ref AB, K_Uz);
        Array.Resize<double>(ref BB, K_Uz); Array.Resize<double>(ref BT, K_Uz); Array.Resize<double>(ref BVT, K_Uz);
        Array.Resize<double>(ref BVB, K_Uz); Array.Resize<double>(ref AVT, K_Uz); Array.Resize<double>(ref AVB, K_Uz);
        Array.Resize<double>(ref BVSB, K_Uz); Array.Resize<double>(ref BVST, K_Uz); Array.Resize<double>(ref CBet, K_Uz);

        Array.Resize<double>(ref APT, K_Uz); Array.Resize<double>(ref BPT, K_Uz);
        Array.Resize<double>(ref APB, K_Uz); Array.Resize<double>(ref BPB, K_Uz);
        Array.Resize<double>(ref BPCT, K_Uz); Array.Resize<double>(ref BPCB, K_Uz);
        Array.Resize<double>(ref Kabx, K_Uz); Array.Resize<double>(ref Kabz, K_Uz);

        Array.Resize<double>(ref B, K_Uz); Array.Resize<double>(ref BG, K_Uz); Array.Resize<double>(ref C, K_Uz);
        Array.Resize<double>(ref AY, K_Uz); Array.Resize<double>(ref BM, K_Uz); Array.Resize<double>(ref FG, K_Uz);
        Array.Resize<double>(ref AVS, K_Uz); Array.Resize<double>(ref BVS, K_Uz); Array.Resize<double>(ref P_0, K_Uz);
        Array.Resize<double>(ref P, K_Uz); Array.Resize<double>(ref AG, K_Uz); Array.Resize<double>(ref AV, K_Uz);
        Array.Resize<double>(ref AX, K_Uz); Array.Resize<double>(ref GM, K_Uz); Array.Resize<double>(ref BV, K_Uz);

        K_Uz = NZ + 3;
        Array.Resize<double>(ref HZM, K_Uz); Array.Resize<double>(ref VPIT, K_Uz); Array.Resize<double>(ref VPIB, K_Uz);
        Array.Resize<double>(ref QS_T, K_Uz); Array.Resize<double>(ref QS_B, K_Uz);

        K_Uz = (NX + 3) * (NZ + 3);
        Array.Resize<double>(ref FI, K_Uz); Array.Resize<double>(ref ZM, K_Uz);
        Array.Resize<double>(ref SIG_P, K_Uz); Array.Resize<double>(ref CS, K_Uz);

        K_Uz = NB + 2;
        Array.Resize<double>(ref VPORM, K_Uz); Array.Resize<double>(ref SCK, K_Uz);
        Array.Resize<double>(ref QSM_T, K_Uz); Array.Resize<double>(ref QSM_B, K_Uz);
        Array.Resize<double>(ref Q_SumSl_T, K_Uz); Array.Resize<double>(ref Qoil_SumSl_T, K_Uz);
        Array.Resize<double>(ref Q_SumSl_B, K_Uz); Array.Resize<double>(ref Qoil_SumSl_B, K_Uz);
        Array.Resize<double>(ref QTM, K_Uz); Array.Resize<double>(ref QBM, K_Uz);
        Array.Resize<double>(ref AIT_M, K_Uz); Array.Resize<double>(ref AIB_M, K_Uz);
    }

    public void Free_Work_Dyn_Arrayes()
    {
        AVST = null; AVSB = null; ST = null; SB = null; WT = null; WB = null;
        A = null; AT = null; AB = null; BB = null; BT = null; BVT = null;
        BVB = null; AVT = null; AVB = null; BVSB = null; BVST = null;
        APT = null; APB = null; BPT = null; BPB = null;
        BPCT = null; BPCB = null;

        B = null; BG = null; C = null; AY = null; BM = null; FG = null;
        AVS = null; BVS = null; P = null; P_0 = null; AG = null;
        AX = null; GM = null; BV = null; AV = null;

        HZM = null; VPIB = null; VPIT = null;
        FI = null; ZM = null; SIG_P = null; CS = null; CBet = null;

        VPORM = null; SCK = null; QSM_T = null; QSM_B = null; QSM_T = null;
        QSM_B = null; AIT_M = null; AIB_M = null; QTM = null; QBM = null;
        Q_SumSl_T = null; Qoil_SumSl_T = null; Q_SumSl_B = null; Qoil_SumSl_B = null;
    }

    public void Calc_NZ_My_And_HL_My(int n_b, double[] h_bm, int[] n_zm)
    {
        Nz_My = 0;
        HL_My = 0.0;
        for (int i = 1; i <= n_b; i++)
        {
            HL_My += h_bm[i];
            Nz_My += n_zm[i];
        }

        NZ = Nz_My;
    }

    public void Prepaire_Of_Constants()
    {
        Tim_k = Tim_0;
        Interv = 0;
        RC = 0.01;
        LSS = 0;
        NB1 = 0;
        Tau_D = TU / N_Dr;
        Tu_icx = TU;
        for (int i = 1; i <= NB; i++)
            NB1 = NB1 + LWN[i];
        for (int i = 1; i <= NB; i++)
        {
            Bet_wB[i] = Bt_Cp + VMB[i] * MixtureProperties.WaterProperties.AT3 / 10.0;
            Bet_oB[i] = Bt_Cp + VMB[i] * MixtureProperties.OilProperties.AT1 / 10.0;
            Bet_wT[i] = Bt_Tr + VMT[i] * MixtureProperties.WaterProperties.AT3 / 10.0;
            Bet_oT[i] = Bt_Tr + VMT[i] * MixtureProperties.OilProperties.AT1 / 10.0;
        }

        HX = VL / NX; NM[0] = 0;
        N_Dr_ICX = N_Dr;
        for (int i = 1; i <= NB; i++)
        {
            NM[i] = NM[i - 1] + NZM[i];
            HM[i] = HBM[i] / NZM[i];
        }
        ROWO = (ROW - ROO) * 0.1;
        NZ = NM[NB];

        LPQ = 1; LPQ1 = LPQ - 1;
        for (int K = 1; K <= NB; K++)
        {
            ESNT[K] = SNT[K] + ENT;
            ESNB[K] = SNB[K] + ENB;
            ESVT[K] = SVT[K] - EVT;
            ESVB[K] = SVB[K] - EVB;
            Q_SumSl_T[K] = 0;
            Qoil_SumSl_T[K] = 0;
            Q_SumSl_B[K] = 0;
            Qoil_SumSl_B[K] = 0;
        }

        N = NX * NZ; N1 = N + NZ; N2 = N1 + NZ;
        NZ2 = NZ + NZ; NKON = 1 + N - NZ2; LST = 0; LTB = 0;

        DS = DSO - 0.01;
        SMIN = 0.01; LK = 1; LKK = 0;
        TBQ = 0.0; TTQ = 0.0; Pr_TB = 0; Pr_BT = 0;
        Q_TB = 0.0; Q_BT = 0.0; Q_fld = 0.0;
        Q_Izm = 0;
        Q_Izm_Fix = 0;
    }

    public void Evaluate_Of_Parameters()
    {
        VPORT = 0.0; VPORB = 0.0; VNET = 0.0; VNEB = 0.0;
        for (int i = 1; i <= NB; i++)
        {
            double R = Math.PI * VL * VL * HBM[i];
            VPORTM[i] = R * VMT[i];
            VPORBM[i] = R * VMB[i];
            VPORT = VPORT + VPORTM[i];
            VPORB = VPORB + VPORBM[i];
            VNETM[i] = VPORTM[i] * (1 - SNT[i]);
            VNEBM[i] = VPORBM[i] * (1 - SNB[i]);
            if (i == NB)
            {
                VNETM[i] = 0.0;
                VNEBM[i] = 0.0;
            }
            VNET = VNET + VNETM[i];
            VNEB = VNEB + VNEBM[i];
        }
        VNE = VNET + VNEB;
        VPOR = VPORT + VPORB;
    }

    public void Boundary_Conditions_And_Initial_Appr()
    {
        for (int K = 1; K <= NM[NB - 1]; K++) P[N1 + K] = P32;
        int M = 0;
        for (int K = 1 + NM[NB - 1]; K <= NZ; K++)
        {
            M = M + 1;
            P[N1 + K] = P32 + ROWO * (M - 0.5) * HM[NB];
        }
        double RR = 0.0;
        for (int K = 1; K <= NB1; K++)
            RR = RR + (AKT[K] + AKB[K]) * HBM[K];
        RR = Q_zab / 8.64 * MixtureProperties.OilProperties.Mu1_PL / RR;
        double R = P32 - RR * Math.Log(NX);
        double R1 = R + RR * Math.Log(RC / HX);
        for (int K = 1; K <= NZ; K++) P[K] = R1;

        for (int I = 1; I <= NX; I++)
        {
            R1 = R + RR * Math.Log(I - 0.5);
            for (int K = 1; K <= NM[NB]; K++)
                P[K + I * NZ] = R1;
        }
        for (int K = 1; K <= NZ; K++)
            for (int i = 1; i <= NX + 1; i++)
                P_0[K + (i - 1) * NZ] = P[N1 + K];
    }

    public void Initialization_Of_S0(bool FromFile)
    {
        if (!FromFile)
        {
            for (int I = 1; I <= NX + 2; I++)
                for (int K = 1; K <= NB - 1; K++)
                    for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
                    {
                        int M1 = M + (I - 1) * NZ;
                        ST[M1] = SNT[K];
                        SB[M1] = SNB[K];
                    }

            for (int I = 1; I <= NX + 2; I++)
                for (int M = 1 + NM[NB - 1]; M <= NM[NB]; M++)
                {
                    int M1 = M + (I - 1) * NZ;
                    ST[M1] = 1.0; SB[M1] = 1.0;
                }
            for (int K = 1; K <= N2; K++)
            {
                WT[K] = MixtureProperties.OilProperties.Mu1_PL;
                WB[K] = MixtureProperties.OilProperties.Mu1_PL;
            }
        }
    }

    public void Prepeare_Of_Array_Abs_Permeability()
    {
        double R = 1.0 / Math.Log(HX / (2.0 * RC));
        for (int K = 1; K <= NB; K++)
            for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
            {
                double R1 = AKT[K] * 8.64 * HM[K];
                APT[M] = R1 * R;
                double R2 = AKB[K] * 8.64 * HM[K];
                APB[M] = R2 * R;
                double R3 = AKT[K] * 8.64 * HX * HX / HM[K];
                double R4 = AKB[K] * 8.64 * HX * HX / HM[K];
                for (int I = 1; I <= NX + 2; I++)
                {
                    int M1 = M + (I - 1) * NZ;
                    int M2 = M1 + NZ;
                    APT[M2] = R1 * I;
                    APB[M2] = R2 * I;
                    Kabx[M1] = AKT[K];
                    Kabz[M1] = AKB[K];
                    BPT[M1] = R3 * (I - 0.5);
                    BPCT[M1] = BPT[M1] * ROWO * HM[K];
                    BPB[M1] = R4 * (I - 0.5);
                    BPCB[M1] = BPB[M1] * ROWO * HM[K];
                }

                for (int I = 1; I <= 2; I++)
                {
                    int M3 = M + I * NZ;
                    APT[M3] = APT[M3] * 1.0 / Math.Log((2.0 * I + 1.0) / (2.0 * I - 1.0)) / I;
                    APB[M3] = APB[M3] * 1.0 / Math.Log((2.0 * I + 1.0) / (2.0 * I - 1.0)) / I;
                }
            }

        for (int K = 1; K <= NB; K++)
            for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
            {
                int NK = N + M;
                APT[M] = LWN[K] * APT[M];
                APT[NK] = LWD[K] * APT[NK];
                APB[M] = LWN[K] * APB[M];
                APB[NK] = LWD[K] * APB[NK];
            }
    }
}
