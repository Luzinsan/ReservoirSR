using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

using System.IO;

using System.Threading.Tasks;
using System.Threading;
using System.Globalization;

using ClassLibrary_Global;
using ClassLibrary_PhasesProperties;
using Simulation.Core;

namespace ClassLibrary_FissuredPorousOilReservoir
{
    /// <summary>
    /// Класс фильтрации в трещинвато0пористом пласте
    /// </summary>
    public class Class_FPOR
    {
        /// <summary>
        /// Конструктор класса фильтрации в трещинвато0пористом пласте
        /// </summary>
        public Class_FPOR()
        {
            MixtureProperties = new Class_MixtureProperties();
        }

        public void ApplyConfig(SimulationConfig config)
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

            Q_zab = config.Q_zab;
            OBV_P = config.OBV_P;
            QQ = config.QQ;
            P32 = config.P32;

            TVK = config.TVK;
            TK = config.TK;
            LTVK = config.LTVK;
            LTK = config.LTK;
            DSO = config.DSO;

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

            ROW = MixtureProperties.WaterProperties.Ro3_PL / 1000.0;
            ROO = MixtureProperties.OilProperties.Ro1_PL / 1000.0;

            c_ = X_A / Math.Pow(X_A - X_D, 2.0);
            b_ = c_ * X_A;
            a_ = (1.0 / MU_pazp - 1.0 / MixtureProperties.OilProperties.Mu1_PL) * Math.Pow(X_A, -b_) * Math.Exp(c_ * X_A);

            MixtureProperties.Set_PpL_Tpl(P32 / 10.0, 40.0);

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

            Free_Ini_Arrayes_Razm_NB();
            Create_Ini_Arrayes_Razm_NB();

            for (int i = 0; i < NB; i++)
            {
                var layer = config.Layers[i];
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
            
            Calc_NZ_My_And_HL_My(NB, HBM, NZM);
            
            Pr_Count = 1;
            S_min = 0; 
            S_max = 1;
        }

        #region Unit TRBL_TYP

        #region Переменные класса Class_FPOR

        /// <summary>
        /// Параметры трехфазной смеси
        /// </summary>
        public Class_MixtureProperties MixtureProperties;

        public const int LKM_Max = 6000;

        public double
            //+++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            ROWO, ROW, ROO, ENT, ENB, EVT, EVB, VPORT, VPORB, VNET, VNEB,
            VNE, RC, R_Skv, MU_pazp,
            //+++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            SMIN, AIT, AIB, AI, QT, QB, DISS, DISQ, DS,
            VL, P32, Q_zab, DSO, TTK, TVK, TK, TT, TT_Read, TB, TBT, TBQ, TTQ,
            TV, TU, Tu_icx, Tau_S, T_for_S,
            HX, T, HL_My, Pr_TB, Pr_BT,
            EPSP = 0.000001,
            VPOR,

            P_S, DL, DL1,


            S_min, S_max, DQ1, DQ2, RBP, RBP1, RBV, St_TU,
            Q1Mk, Q2Mk, QS1MK, QS2MK, TT2Mk, AITMk, QP1k, QP2k,
            QPS1k, QPS2k, QPT1k, QPT2k, QPTS1k, QPTS2k, QB1Mk, QB2Mk,
            Q1VMk, Q2VMk, QBS2Mk, AX_Min, AV_Min, AX_Max, AV_Max,
            X_blok0, X_blok1, X__a, Y__a, X__b, Y__b,
            AMU, HPL, a_, b_, c_,
            Tim_0, Tim_1, Tim_2, Tim_k, T_Tek,
            TQPR,

            X_A, X_D, QQ_ICX, PP_ICX, P_zab_Krv, Q_new,
            DHX, EPSC, Tau_D, QP_TB, QP_BT, Q_TB, Q_BT, OBV_P, QQ, Q_fld, Q_Dob,
            //------------------------------------------------------------
            Bt_Cp, Bt_Tr, Step_WT = 1;

        /// <summary>
        /// Забойное давление на доб.скважине (при r=R_Skv), atm
        /// </summary>
        public double P_zab_DC;


        public byte
            Y__N, Erase_file, View_Not_Open, OutPut_QP, Interv;

        public int
            NB1, N_Dr, NB, NX, LOD, LS0, LIZ, LPQ = 1, LPK, LTTK, LTVK, LTK,
            NT,

            Q_Izm, N_Dr_new,
            NZ, N, N1, N2, NZ2, LST, LTB, LK, LKK, Q_Izm_Fix,
            LKB, NKON, LPQ1, LKM = 50,
            ParReg, Cod_Exit, Nz_My, N_Dr_ICX,
            I_blok0, I_blok1, Y_blok0, Y_blok1, Pr_Count,
            NX1, NX2, N_1D,
            N_itr_Out = 0;


        public int LSS, LS;

        public string Name_Dat, Demo_Help;

        public StreamWriter f14;
        public StreamReader f10;

        private string sf10, sf14;

        public int[] NM, NZM, LWN, LWD;

        public double[]
            //{-----------------------------------------------}
            HM, HBM, VM, VPORM, AKX, AKZ, SCK,
            //{-----------------------------------------------}
            HZM, VPIT, VPIB, FI, ZM, SIG_P, CS,
            ESNT, ESNB, ESVT, ESVB, SNT, SNB, SVT, SVB,
            AVST, AVSB, VPORTM, VPORBM, VMT, VMB,
            VNETM, VNEBM, AKT, AKB, ST, SB, WT, WB,
            APT, APB, BPT, BPCT, BPB, BPCB, AT, AB, BT, BB, BVT,
            BVB, AVT, AVB, BVSB, BVST, QS_T, QS_B, QSM_T, QSM_B,
            Q_SumSl_T, Qoil_SumSl_T, Q_SumSl_B, Qoil_SumSl_B,
            QTM, QBM, AIT_M, AIB_M, Bet_wB, Bet_oB, Bet_wT, Bet_oT,
            //{-----------------------------------------------}
            B, BG, AP, BP, Kabx, Kabz, C, AY, BM, FG, CBet,
            AVS, BVS, P, P_0, A, AG, AX, GM, BV, AV, APP, BPP;

        public double[]
            T_Mass,
            // обводненность
            AIT_Mass, AIB_Mass, AI_Mass,
            // нефтеотдача
            TBT_Mass, TB_Mass, TT_Mass,
            // Количество добытой нефти
            Q_TBT_Mass, Q_TB_Mass, Q_TT_Mass, Q_W_Mass,
            // Объем добытой нефти по слоям
            Qoil_SumSl_1, Qoil_SumSl_2, Qoil_SumSl_3;

        #endregion Переменные класса Class_FPOR

        public void Create_Ini_Arrayes_Razm_NB()
        {
            //.......................................................
            int K_Uz = NB + 2;
            // Массивы размерности NB = число слоев:
            //.......................................................
            // целочисленные
            //.......................................................
            Array.Resize<int>(ref NZM, K_Uz); Array.Resize<int>(ref NM, K_Uz);
            Array.Resize<int>(ref LWN, K_Uz); Array.Resize<int>(ref LWD, K_Uz);
            //.......................................................
            // вещественные
            //.......................................................
            Array.Resize<double>(ref VMT, K_Uz); Array.Resize<double>(ref VMB, K_Uz);
            //.......................................................
            Array.Resize<double>(ref SNT, K_Uz); Array.Resize<double>(ref SNB, K_Uz);
            Array.Resize<double>(ref SVT, K_Uz); Array.Resize<double>(ref SVB, K_Uz);
            Array.Resize<double>(ref AKT, K_Uz); Array.Resize<double>(ref AKB, K_Uz);
            Array.Resize<double>(ref ESNT, K_Uz); Array.Resize<double>(ref ESNB, K_Uz);
            Array.Resize<double>(ref ESVT, K_Uz); Array.Resize<double>(ref ESVB, K_Uz);
            Array.Resize<double>(ref VPORTM, K_Uz); Array.Resize<double>(ref VPORBM, K_Uz);
            Array.Resize<double>(ref VNETM, K_Uz); Array.Resize<double>(ref VNEBM, K_Uz);
            //.......................................................
            Array.Resize<double>(ref Bet_wB, K_Uz); Array.Resize<double>(ref Bet_oB, K_Uz);
            Array.Resize<double>(ref Bet_wT, K_Uz); Array.Resize<double>(ref Bet_oT, K_Uz);
            //.......................................................            
            Array.Resize<double>(ref HM, K_Uz); Array.Resize<double>(ref HBM, K_Uz);
            Array.Resize<double>(ref VM, K_Uz); Array.Resize<double>(ref AKX, K_Uz);
            Array.Resize<double>(ref AKZ, K_Uz);
            //.......................................................          
        }

        public void Free_Ini_Arrayes_Razm_NB()
        {
            //.......................................................
            NZM = null; NM = null;
            LWN = null; LWD = null;
            //.......................................................
            VMT = null; VMB = null;
            //.......................................................
            SNT = null; SNB = null;
            SVT = null; SVB = null;
            AKT = null; AKB = null;
            ESNT = null; ESNB = null;
            ESVT = null; ESVB = null;
            VPORTM = null; VPORBM = null;
            VNETM = null; VNEBM = null;
            //.......................................................
            Bet_wB = null; Bet_oB = null;
            Bet_wT = null; Bet_oT = null;
            //.......................................................
            HM = null; HBM = null;
            VM = null; AKX = null;
            AKZ = null;
            //.......................................................
        }

        public void Create_Work_Arrayes_AP_BP()
        {
            // Массивы размерности (NX+1)*(NZ+1) = общее число узлов сетки:
            int K_Uz = (NX + 3) * (NZ + 3);
            // вещественные
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
            // Массивы размерности (NX+1)*(NZ+1) = общее число узлов сетки:
            K_Uz = (NX + 3) * (NZ + 3);
            // вещественные
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
            //{---------------------------------------------------------------------------}
            // Массивы размерности NZ = число узлов по оси Z:
            K_Uz = NZ + 3;
            //{ вещественные } 
            Array.Resize<double>(ref HZM, K_Uz); Array.Resize<double>(ref VPIT, K_Uz); Array.Resize<double>(ref VPIB, K_Uz);
            Array.Resize<double>(ref QS_T, K_Uz); Array.Resize<double>(ref QS_B, K_Uz);
            //{---------------------------------------------------------------------------}
            //// Массивы размерности NX = число узлов по оси Z:
            // вещественные
            K_Uz = (NX + 3) * (NZ + 3); //K_Uz:=NX+5;
            Array.Resize<double>(ref FI, K_Uz); Array.Resize<double>(ref ZM, K_Uz);
            Array.Resize<double>(ref SIG_P, K_Uz); Array.Resize<double>(ref CS, K_Uz);
            //{---------------------------------------------------------------------------}
            // Массивы размерности NB = число слоев:
            // вещественные
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
            // Массивы размерности (NX+1)*(NZ+1) = общее число узлов сетки:
            //{ вещественные }
            AVST = null; AVSB = null; ST = null; SB = null; WT = null; WB = null;
            A = null; AT = null; AB = null; BB = null; BT = null; BVT = null;
            BVB = null; AVT = null; AVB = null; BVSB = null; BVST = null;
            APT = null; APB = null; BPT = null; BPB = null;
            BPCT = null; BPCB = null;

            B = null; BG = null; C = null; AY = null; BM = null; FG = null;
            AVS = null; BVS = null; P = null; P_0 = null; AG = null;
            AX = null; GM = null; BV = null; AV = null;
            //{ целочисленные}
            //{---------------------------------------------------------------------------}
            // Массивы размерности NZ = число узлов по оси Z:
            //{ вещественные}
            HZM = null; VPIB = null; VPIT = null;
            //{---------------------------------------------------------------------------}
            // Массивы размерности NX = число узлов по оси Z:
            //{ вещественные }
            FI = null; ZM = null; SIG_P = null; CS = null; CBet = null;
            //{---------------------------------------------------------------------------}
            // Массивы размерности NB = число слоев:
            //{ вещественные }
            VPORM = null; SCK = null; QSM_T = null; QSM_B = null; QSM_T = null;
            QSM_B = null; AIT_M = null; AIB_M = null; QTM = null; QBM = null;
            Q_SumSl_T = null; Qoil_SumSl_T = null; Q_SumSl_B = null; Qoil_SumSl_B = null;
            //{---------------------------------------------------------------------------}
        }

        public void Read__Data(ref int Cod)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";
            string[] str;

            Cod = 0;
            try
            {
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out Step_WT);

                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[0], out NB);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out VL);

                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[0], out LOD);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[0], out LIZ);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out R_Skv);
                //.......................................................
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out ROW);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out ROO);
                if (ROO == ROW) ROO = ROW + 1e-8;

                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out MixtureProperties.WaterProperties.Mu3_PL);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out MixtureProperties.OilProperties.Mu1_PL);

                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out MU_pazp);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out X_A);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out X_D);
                //.......................................................
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out Bt_Cp);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out Bt_Tr);

                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out MixtureProperties.OilProperties.AT1);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out MixtureProperties.WaterProperties.AT3);

                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out Tim_0);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out Tim_1);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out Tim_2);
                //.......................................................
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out Q_zab);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out P32);

                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out QQ);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out OBV_P);
                //.......................................................
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out TVK);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out TK); LPQ = 1; LKM = 50;

                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[0], out LTVK);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[0], out LTK);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out DSO);
                //.......................................................
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out TU);
                TU = TU / 86400.0;  // Новое

                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[0], out N_Dr);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[0], out NX);

                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out EPSP);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out ENB);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out EVB);

                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out ENT);
                str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[0], out EVT);
                //.......................................................
                // Создание массивов размерности NB = число слоев
                Free_Ini_Arrayes_Razm_NB();
                Create_Ini_Arrayes_Razm_NB();

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int.TryParse(str[0], out NZM[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[0], out HBM[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[0], out VMB[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[0], out VMT[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[0], out SVB[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[0], out SVT[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[0], out SNB[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[0], out SNT[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[0], out AKB[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[0], out AKT[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int.TryParse(str[0], out LWN[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = f10.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int.TryParse(str[0], out LWD[i]);
                }

                Pr_Count = 0;
                Calc_NZ_My_And_HL_My(NB, HBM, NZM);
            }
            catch
            {
                Cod = 1;
            }
        }

        public void LoadFromStream(ref StreamReader fff, ref int Error)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";
            string[] str;

            Name_Dat = "test_TB.s_i";

            Error = 0;
            try
            {
                Load_FPOR_Params_From_Stream(ref fff, ref Error);
                if (Error == 1) return;

                Pr_Count = 0;
                Calc_NZ_My_And_HL_My(NB, HBM, NZM);

                MixtureProperties.LoadFromStream(ref fff, ref Error);
                if (Error == 1) return;
                MixtureProperties.Set_PpL_Tpl(P32 / 10.0, 40.0);

                X_A = 1; X_D = 0.25;
                c_ = X_A / Maths.Sqr(X_A - X_D);
                b_ = c_ * X_A;
                a_ = (1.0 / MU_pazp - 1.0 / MixtureProperties.OilProperties.Mu1_PL) * Math.Pow(X_A, -b_) * Math.Exp(c_ * X_A);

                Create_Work_Dyn_Arrayes();
                Load_S0_FromStream(ref fff, ref Error);
                if (Error == 1) return;
                P_zab_DC = P[1];
            }
            catch
            {
                Error = 1;
            }
        }

        public void Load_FPOR_Params_From_Stream(ref StreamReader fff, ref int Error)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";
            string[] str;

            Error = 0;
            try
            {
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out T);

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out Step_WT);

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[str.Length - 1], out NB);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out VL);

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[str.Length - 1], out LOD);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[str.Length - 1], out LIZ);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out R_Skv);
                //.......................................................
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out ROW);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out ROO);
                if (ROO == ROW) ROO = ROW + 1e-8;

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out MixtureProperties.WaterProperties.Mu3_PL);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out MixtureProperties.OilProperties.Mu1_PL);

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out MU_pazp);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out X_A);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out X_D);
                //.......................................................
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out Bt_Cp);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out Bt_Tr);

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out MixtureProperties.OilProperties.AT1);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out MixtureProperties.WaterProperties.AT3);

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out Tim_0);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out Tim_1);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out Tim_2);
                //.......................................................
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out Q_zab);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out P32);

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out QQ_ICX);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OBV_P);
                //.......................................................
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out TVK);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out TK); LPQ = 1; LKM = 50;

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[str.Length - 1], out LTVK);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[str.Length - 1], out LTK);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out DSO);
                //.......................................................
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out TU);
                TU = TU / 86400.0;  // Новое

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[str.Length - 1], out N_Dr);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                int.TryParse(str[str.Length - 1], out NX);

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out EPSP);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out ENB);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out EVB);

                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out ENT);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out EVT);
                //.......................................................
                // Создание массивов размерности NB = число слоев
                Free_Ini_Arrayes_Razm_NB();
                Create_Ini_Arrayes_Razm_NB();

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int.TryParse(str[str.Length - 1], out NZM[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[str.Length - 1], out HBM[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[str.Length - 1], out VMB[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[str.Length - 1], out VMT[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[str.Length - 1], out SVB[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[str.Length - 1], out SVT[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[str.Length - 1], out SNB[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[str.Length - 1], out SNT[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[str.Length - 1], out AKB[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    double.TryParse(str[str.Length - 1], out AKT[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int.TryParse(str[str.Length - 1], out LWN[i]);
                }

                for (int i = 1; i <= NB; i++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int.TryParse(str[str.Length - 1], out LWD[i]);
                }
            }
            catch
            {
                Error = 1;
            }
        }

        public void Write__Data(ref StreamWriter F1)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";

            F1.WriteLine(Service.FormatBuilder(0, 12, 3) + "   ST  - показатель степени", Step_WT);
            F1.WriteLine(Service.FormatBuilder(0, 12) + "   NB  - число слоев", NB);

            F1.WriteLine(Service.FormatBuilder(0, 12, 3) + "   VL  - длина пласта", VL);
            F1.WriteLine(Service.FormatBuilder(0, 12) + "  LOD  - (0-пласт по X однородный, 1-пласт неоднородный)", LOD);
            F1.WriteLine(Service.FormatBuilder(0, 12) + "  LIZ  - (0-пласт изотропный, 1-анизотропный)", LIZ);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Rc   - радиус скважины", R_Skv);
            //.......................................................
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Rов  - плотность воды", ROW);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Rон  - плотность нефти", ROO);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Muв  - вязкость воды", MixtureProperties.WaterProperties.Mu3_PL);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Muн  - вязкость нефти", MixtureProperties.OilProperties.Mu1_PL);

            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Mрзр - вязкость разрушения нефти", MU_pazp);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  X_a  - к-т зависимости вязкости нефти", X_A);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  X_d  - к-т зависимости вязкости нефти", X_D);
            //.......................................................
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Bt_Cp - упругоемкость среды", Bt_Cp);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Bt_Тp - упругоемкость трещин", Bt_Tr);

            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Bt_oil - упругоемкость нефти", MixtureProperties.OilProperties.AT1);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Bt_Wat - упругоемкость воды", MixtureProperties.WaterProperties.AT3);

            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  T_0 - период работы с пост. дебитом", Tim_0);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  T_1 - период форсированной работы", Tim_1);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  T_2 - период простоя скважины", Tim_2);
            //.......................................................
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Q    - начальный дебит скважины", Q_zab);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Pкон - давление на контуре питания", P32);

            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Q_и  - интенсифицированный дебит скважины", QQ);
            F1.WriteLine(Service.FormatBuilder(0, 12, 6) + "  Обв_и  - обводненность начала интенсификации добычи", OBV_P);
            //.......................................................
            F1.WriteLine(Service.FormatBuilder(0, 12, 2) + "  TVK  - пpедельное значение обводненности", TVK);
            F1.WriteLine(Service.FormatBuilder(0, 12, 2) + "  TK   - момент окончания по вpемени", TK);

            F1.WriteLine(Service.FormatBuilder(0, 12) + "  LTVK - (1-окончание pасчетов по заданному TVK )", LTVK);
            F1.WriteLine(Service.FormatBuilder(0, 12) + "  LTK  - (1-окончание pасчетов по заданному  TK )", LTK);
            F1.WriteLine(Service.FormatBuilder(0, 12, 4) + "  DSO  - шаг выдачи инфоpмации", DSO);
            //.......................................................
            F1.WriteLine(Service.FormatBuilder(0, 12, 4) + "  Tau  - временной шаг", TU * 86400);

            F1.WriteLine(Service.FormatBuilder(0, 12) + "  N_др - число дроблений временного шага", N_Dr);
            F1.WriteLine(Service.FormatBuilder(0, 12) + "  NX   - число узлов по длине (четное число)", NX);

            F1.WriteLine(Service.FormatBuilder(0, 12, 8) + "  EPSP - погpешность итеpаций Р", EPSP);

            F1.WriteLine(Service.FormatBuilder(0, 12, 8) + "  EnB  - зпсилон нижнее для блоков", ENB);
            F1.WriteLine(Service.FormatBuilder(0, 12, 8) + "  EvB  - зпсилон верхнее для блоков", EVB);
            F1.WriteLine(Service.FormatBuilder(0, 12, 8) + "  EnT  - зпсилон нижнее для блоков", ENT);
            F1.WriteLine(Service.FormatBuilder(0, 12, 8) + "  EvT  - зпсилон верхнее для блоков", EVT);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 3), NZM[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 3) + "                  NZM(I) - количество узлов в пpопластках", NZM[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 10, 3), HBM[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 10, 3) + "           HBM(I) - толщина пpопластков", HBM[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 10, 3), VMB[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 10, 3) + "           Мб (I) - поpистость блоков в пpопластках", VMB[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 10, 3), VMT[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 10, 3) + "           Мтр(I) - поpистость трещин в пpопластках", VMT[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 10, 3), SVB[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 10, 3) + "           SVб(I) - пpедельная насыщенность блоков", SVB[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 10, 3), SVT[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 10, 3) + "           SVт(I) - пpедельная насыщенность трещин", SVT[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 10, 3), SNB[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 10, 3) + "           SNб(I) - связанная насыщенность блоков", SNB[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 10, 3), SNT[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 10, 3) + "           SNт(I) - связанная насыщенность трещин", SNT[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 10, 3), AKB[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 10, 3) + "           Kбл(I) - абс. проницаемость блоков", AKB[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 10, 3), AKT[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 10, 3) + "           Kтр(I) - абс. проницаемость трещин", AKT[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 3), LWN[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 3) + "                  LWN(I) - признак вскрытия пропластка на входе", LWN[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1) F1.WriteLine(Service.FormatBuilder(0, 3), LWD[i]);
                else
                    F1.WriteLine(Service.FormatBuilder(0, 3) + "                  LWD(I) - признак вскрытия пропластка на выходе", LWD[i]);
        }

        public void SaveToStream(ref StreamWriter fff)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";

            fff.WriteLine("----------------------------  Параметры пласта  -----------------------------");
            fff.WriteLine(" Текущее время                                     ¦    сут    ¦ " + Service.FormatBuilder(0, 12, 3), T);
            fff.WriteLine(" Показатель степени                                ¦           ¦ " + Service.FormatBuilder(0, 12, 3), Step_WT);
            fff.WriteLine(" Число слоев                                       ¦           ¦ " + Service.FormatBuilder(0, 12), NB);
            fff.WriteLine(" Длина пласта                                      ¦           ¦ " + Service.FormatBuilder(0, 12, 3), VL);
            fff.WriteLine(" Признаки: (0-пласт по X однородный, 1-пласт неоднородный)     ¦ " + Service.FormatBuilder(0, 12), LOD);
            fff.WriteLine("           (0-пласт изотропный, 1-анизотропный)                ¦ " + Service.FormatBuilder(0, 12), LIZ);
            fff.WriteLine(" Радиус скважины Rc                                ¦           ¦ " + Service.FormatBuilder(0, 12, 6), R_Skv);
            //.......................................................
            fff.WriteLine(" Плотность воды Rов                                ¦           ¦ " + Service.FormatBuilder(0, 12, 6), ROW);
            fff.WriteLine(" Плотность нефти Rон                               ¦           ¦ " + Service.FormatBuilder(0, 12, 6), ROO);
            fff.WriteLine(" Вязкость воды Muв                                 ¦           ¦ " + Service.FormatBuilder(0, 12, 6), MixtureProperties.WaterProperties.Mu3_PL);
            fff.WriteLine(" Вязкость нефти Muн                                ¦           ¦ " + Service.FormatBuilder(0, 12, 6), MixtureProperties.OilProperties.Mu1_PL);
            fff.WriteLine(" Вязкость разрушения нефти Mрзр                    ¦           ¦ " + Service.FormatBuilder(0, 12, 6), MU_pazp);
            fff.WriteLine(" К-т зависимости вязкости нефти X_a                ¦           ¦ " + Service.FormatBuilder(0, 12, 6), X_A);
            fff.WriteLine(" К-т зависимости вязкости нефти X_d                ¦           ¦ " + Service.FormatBuilder(0, 12, 6), X_D);
            //.......................................................
            fff.WriteLine(" Упругоемкость среды Bt_Cp                         ¦           ¦ " + Service.FormatBuilder(0, 12, 6), Bt_Cp);
            fff.WriteLine(" Упругоемкость трещин Bt_Тp                        ¦           ¦ " + Service.FormatBuilder(0, 12, 6), Bt_Tr);

            fff.WriteLine(" Упругоемкость нефти Bt_oil                        ¦           ¦ " + Service.FormatBuilder(0, 12, 6), MixtureProperties.OilProperties.AT1);
            fff.WriteLine(" Упругоемкость воды Bt_Wat                         ¦           ¦ " + Service.FormatBuilder(0, 12, 6), MixtureProperties.WaterProperties.AT3);

            fff.WriteLine(" Период работы с пост. дебитом T_0                 ¦           ¦ " + Service.FormatBuilder(0, 12, 6), Tim_0);
            fff.WriteLine(" Период форсированной работы T_1                   ¦           ¦ " + Service.FormatBuilder(0, 12, 6), Tim_1);
            fff.WriteLine(" Период  простоя скважины T_2                      ¦           ¦ " + Service.FormatBuilder(0, 12, 6), Tim_2);
            //.......................................................
            fff.WriteLine(" Начальный дебит скважины Q                        ¦           ¦ " + Service.FormatBuilder(0, 12, 6), Q_zab);
            fff.WriteLine(" Давление на контуре питания Pкон                  ¦           ¦ " + Service.FormatBuilder(0, 12, 6), P32);
            fff.WriteLine(" Aмплитуда дебита скважины Q_и                     ¦           ¦ " + Service.FormatBuilder(0, 12, 6), QQ_ICX);
            fff.WriteLine(" Обводненность начала интенсификации добычи Обв_и  ¦           ¦ " + Service.FormatBuilder(0, 12, 6), OBV_P);
            //.......................................................
            fff.WriteLine(" Пpедельное значение обводненности TVK             ¦           ¦ " + Service.FormatBuilder(0, 12, 6), TVK);
            fff.WriteLine(" Момент окончания по вpемени TK                    ¦           ¦ " + Service.FormatBuilder(0, 12, 6), TK);

            fff.WriteLine(" Признаки: (1-окончание pасчетов по заданному TVK) LTVK        ¦ " + Service.FormatBuilder(0, 12), LTVK);
            fff.WriteLine(" Признаки: (1-окончание pасчетов по заданному  TK) LTK         ¦ " + Service.FormatBuilder(0, 12), LTK);
            fff.WriteLine(" Шаг выдачи инфоpмации DSO                         ¦           ¦ " + Service.FormatBuilder(0, 12, 4), DSO);
            //.......................................................
            fff.WriteLine(" Временной шаг Tau                                 ¦           ¦ " + Service.FormatBuilder(0, 12, 4), TU * 86400);
            fff.WriteLine(" Число слоев дроблений временного шага N_др        ¦           ¦ " + Service.FormatBuilder(0, 12), N_Dr);
            fff.WriteLine(" Число узлов по длине (четное число) NX            ¦           ¦ " + Service.FormatBuilder(0, 12), NX);

            fff.WriteLine(" Погpешность итеpаций Р EPSP                       ¦           ¦ " + Service.FormatBuilder(0, 12, 8), EPSP);
            fff.WriteLine(" Эпсилон нижнее для блоков EnB                     ¦           ¦ " + Service.FormatBuilder(0, 12, 8), ENB);
            fff.WriteLine(" Эпсилон верхнее для блоков EvB                    ¦           ¦ " + Service.FormatBuilder(0, 12, 8), EVB);
            fff.WriteLine(" Эпсилон нижнее для трещин EnT                     ¦           ¦ " + Service.FormatBuilder(0, 12, 8), ENT);
            fff.WriteLine(" Эпсилон верхнее для трещин EvT                    ¦           ¦ " + Service.FormatBuilder(0, 12, 8), EVT);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 3), NZM[i]);
                else
                    fff.WriteLine(" NZM(I) - количество узлов в пpопластках           ¦    шт     ¦ " + Service.FormatBuilder(0, 3), NZM[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 10, 3), HBM[i]);
                else
                    fff.WriteLine(" HBM(I) - толщина пропластков                      ¦     м     ¦ " + Service.FormatBuilder(0, 10, 3), HBM[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 10, 3), VMB[i]);
                else
                    fff.WriteLine(" Мб(I) - поpистость блоков в пpопластках           ¦           ¦ " + Service.FormatBuilder(0, 10, 3), VMB[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 10, 3), VMT[i]);
                else
                    fff.WriteLine(" Мтр(I) - поpистость трещин в пpопластках          ¦           ¦ " + Service.FormatBuilder(0, 10, 3), VMT[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 10, 3), SVB[i]);
                else
                    fff.WriteLine(" SVб(I) - пpедельная насыщенность блоков           ¦           ¦ " + Service.FormatBuilder(0, 10, 3), SVB[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 10, 3), SVT[i]);
                else
                    fff.WriteLine(" SVт(I) - пpедельная насыщенность трещин           ¦           ¦ " + Service.FormatBuilder(0, 10, 3), SVT[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 10, 3), SNB[i]);
                else
                    fff.WriteLine(" SNб(I) - связанная насыщенность блоков            ¦           ¦ " + Service.FormatBuilder(0, 10, 3), SNB[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 10, 3), SNT[i]);
                else
                    fff.WriteLine(" SNт(I) - связанная насыщенность трещин            ¦           ¦ " + Service.FormatBuilder(0, 10, 3), SNT[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 10, 3), AKB[i]);
                else
                    fff.WriteLine(" Kбл(I) - абс. проницаемость блоков                ¦           ¦ " + Service.FormatBuilder(0, 10, 3), AKB[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 10, 3), AKT[i]);
                else
                    fff.WriteLine(" Kтр(I) - абс. проницаемость трещин                ¦           ¦ " + Service.FormatBuilder(0, 10, 3), AKT[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 3), LWN[i]);
                else
                    fff.WriteLine(" LWN(I) - признак вскрытия пропластка на входе     ¦           ¦ " + Service.FormatBuilder(0, 3), LWN[i]);
            //.......................................................
            for (int i = 1; i <= NB; i++)
                if (i > 1)
                    fff.WriteLine("                                                                 " + Service.FormatBuilder(0, 3), LWD[i]);
                else
                    fff.WriteLine(" LWD(I) - признак вскрытия пропластка на выходе    ¦           ¦ " + Service.FormatBuilder(0, 3), LWD[i]);

            MixtureProperties.SaveToStream(ref fff);
        }


        public void Write__Data_f14()
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";

            f14.WriteLine("                  И С Х О Д Н Ы Е    Д А Н Н Ы Е");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            Write__Data(ref f14);
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.Flush();
        }

        public void Write_Mas_S_Or_P(ref StreamWriter fff, double[] A,
            int N_C, int N_D, int N_S, int I_s, int N_b)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";
            int K_I;
            string Format = Service.FormatBuilder(0, N_C, N_D);

            K_I = 1;
            for (int i = I_s; i <= N_b; i++)
            {
                fff.Write(Format, A[i]);
                K_I = K_I + 1;
                if (K_I == N_S + 1)
                {
                    if (i < N_b) fff.WriteLine();
                    K_I = 1;
                }
            }
            ;
            fff.WriteLine();
        }

        public void Print_Mas_P_S()
        {
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ P(K),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, P, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ Sтр(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, ST, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ Sбл(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, SB, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ WB(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, WB, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ WT(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, WT, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ AVB(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, AVB, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ AVT(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, AVT, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ BVB(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, BVB, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ BVT(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, BVT, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }
        }

        public void SaveToStream_P_S(ref StreamWriter fff)
        {
            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            fff.WriteLine("            МАССИВ P(K),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                fff.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref fff, P, 17, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            fff.WriteLine("            МАССИВ Sтр(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                fff.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref fff, ST, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            fff.WriteLine("            МАССИВ Sбл(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                fff.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref fff, SB, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            fff.WriteLine("            МАССИВ WB(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                fff.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref fff, WB, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            fff.WriteLine("            МАССИВ WT(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                fff.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref fff, WT, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            fff.WriteLine("            МАССИВ AVB(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                fff.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref fff, AVB, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            fff.WriteLine("            МАССИВ AVT(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                fff.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref fff, AVT, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            fff.WriteLine("            МАССИВ BVB(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                fff.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref fff, BVB, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            fff.WriteLine("            МАССИВ BVT(I),  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) fff.Write("-"); fff.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                fff.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref fff, BVT, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

        }

        public void Print_Mas_Rab()
        {

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ 1,  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, BVT, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ 2,  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, BPCT, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ 3,  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, BVST, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }

            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("            МАССИВ 4,  I=1,NZ*(NX+2),K=1,NZ");
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            for (int i = 1; i <= NX + 2; i++)
            {
                f14.WriteLine("  I =  " + Service.FormatBuilder(0, 4), i);
                Write_Mas_S_Or_P(ref f14, AVST, 16, 12, 8, 1 + (i - 1) * NZ, i * NZ);
            }
        }

        public void Read_Write_Data(ref int Cod)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";

            //{--------------------}
            //Read__Data(ref Cod);
            //{--------------------}
            if (Cod == 1)
            {
                Close_All_Files();

                if (File.Exists(sf14))
                    File.Delete(sf14);

                return;
            }
            //{--------------------}
            Write__Data_f14();
            S_min = 0; S_max = 1;
            Calc_NZ_My_And_HL_My(NB, HBM, NZM);
            X__a = 0; Y__a = 0; X__b = VL; Y__b = HL_My;
        }

        public void Read_S0_Mas_From_Dat_File()
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";
            string[] str;

            try
            {
                string FileName = "test_P_S_TB.dat";
                StreamReader Fl = new StreamReader(File.Open(FileName, FileMode.Open), Encoding.Default);
                ////++++++++++++++++++++++++++++
                //// P
                str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out P[i]);
                            i = i + 1;
                        }
                    }
                }
                ////++++++++++++++++++++++++++++
                //// ST
                str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out ST[i]);
                            i = i + 1;
                        }
                    }
                }
                ////++++++++++++++++++++++++++++
                //// SB
                str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = Fl.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out SB[i]);
                            i = i + 1;
                        }
                    }
                }

                Fl.Close();

                //..............................................
                for (int k = 1; k <= NZ; k++)
                    for (int i = 1; i <= NX + 1; i++)
                        P_0[k + (i - 1) * NZ] = P[N1 + k];
                //..............................................
            }
            catch
            {
            }
        }

        public void Load_S0_FromStream(ref StreamReader fff, ref int Error)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";
            string[] str;

            try
            {
                Error = 0;
                ////++++++++++++++++++++++++++++
                //// P
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out P[i]);
                            P_0[i] = P[i];
                            i = i + 1;
                        }
                    }
                }
                ////++++++++++++++++++++++++++++
                //// Stp
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out ST[i]);
                            i = i + 1;
                        }
                    }
                }
                ////++++++++++++++++++++++++++++
                //// SB
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out SB[i]);
                            i = i + 1;
                        }
                    }
                }

                ////++++++++++++++++++++++++++++
                //// WB
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out WB[i]);
                            i = i + 1;
                        }
                    }
                }

                ////++++++++++++++++++++++++++++
                //// WT
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out WT[i]);
                            i = i + 1;
                        }
                    }
                }

                ////++++++++++++++++++++++++++++
                //// AVB
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out AVB[i]);
                            i = i + 1;
                        }
                    }
                }

                ////++++++++++++++++++++++++++++
                //// AVT
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out AVT[i]);
                            i = i + 1;
                        }
                    }
                }

                ////++++++++++++++++++++++++++++
                //// BVB
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out BVB[i]);
                            i = i + 1;
                        }
                    }
                }

                ////++++++++++++++++++++++++++++
                //// BVT
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);

                for (int k = 1; k <= NX + 2; k++)
                {
                    str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                    int k1;
                    int.TryParse(str[str.Length - 1], out k1);
                    int i = 1 + (k1 - 1) * NZ;
                    while (i <= k1 * NZ)
                    {
                        str = fff.ReadLine().Split(Service.charSeparators, StringSplitOptions.RemoveEmptyEntries);
                        for (int m = 0; m < str.Length; m++)
                        {
                            double.TryParse(str[m], out BVT[i]);
                            i = i + 1;
                        }
                    }
                }

            }
            catch
            {
                Error = 1;
            }
        }

        //public void Form_Ax_Az_Mas(ref int Cod, int N_B, int N_X, int IZOTR, int Lod, int[] N_Zm, double[] H_Bm, double[] A_KX, double[] A_KZ)
        //{
        //    Cod = 0;
        //    try
        //    {
        //        NM[0] = 0;
        //        for (int i = 1; i <= N_B; i++)
        //        {
        //            NM[i] = NM[i - 1] + N_Zm[i];
        //            HM[i] = H_Bm[i] / N_Zm[i];
        //        }
        //        Nz_My = NM[N_B];
        //        NZ = Nz_My;
        //        N = N_X * Nz_My;
        //        // if LOD = 0 then Exit;
        //        AX_Min = 100000;
        //        AV_Min = 100000;
        //        AX_Max = -10000;
        //        AV_Max = -10000;

        //        for (int K = 1; K <= N_B; K++)
        //            for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
        //            {
        //                for (int I = 1; I <= N_X; I++)
        //                {
        //                    int M1 = M + (I - 1) * Nz_My;
        //                    AP[M1] = A_KX[K];
        //                    Kabx[M1] = AP[M1];
        //                    if (IZOTR == 1) BP[M1] = A_KZ[K];
        //                    if (IZOTR == 0) BP[M1] = A_KX[K];
        //                    Kabz[M1] = BP[M1];
        //                    if (AP[M1] > AX_Max) AX_Max = AP[M1];
        //                    if (AP[M1] < AX_Min) AX_Min = AP[M1];
        //                    if (BP[M1] > AV_Max) AV_Max = BP[M1];
        //                    if (BP[M1] < AV_Min) AV_Min = BP[M1];
        //                }
        //                AP[M + N] = A_KX[K];
        //                if (IZOTR == 1) BP[M + N] = A_KZ[K];
        //                if (IZOTR == 0) BP[M + N] = A_KX[K];
        //                Kabz[M + N] = BP[M + N];
        //                if (AP[M + N] > AX_Max) AX_Max = AP[M + N];
        //                if (AP[M + N] < AX_Min) AX_Min = AP[M + N];
        //                if (BP[M + N] > AV_Max) AV_Max = BP[M + N];
        //                if (BP[M + N] < AV_Min) AV_Min = BP[M + N];
        //            }
        //    }
        //    catch
        //    {
        //        Cod = 1;
        //    }
        //}

        //public void Form_Ax_Az_NonUnif(ref byte Cod, int N_b, int N_x, int KxKz, int j1, int IZOTR, double V_L, double r)
        //{
        //    // i,m,m1 :integer;
        //    Cod = 0;
        //    // Формирование неоднородностей
        //    try
        //    {
        //        for (int M = 1 + NM[j1 - 1]; M <= NM[j1]; M++)
        //            for (int I = 1; I <= N_x; I++)
        //            {
        //                int M1 = M + (I - 1) * Nz_My;
        //                if (KxKz == 1)
        //                    if ((X_blok0 <= I * V_L / N_x) && (X_blok1 >= I * V_L / N_x))
        //                    {
        //                        AP[M1] = r;
        //                        Kabx[M1] = AP[M1];
        //                        if (AP[M1] > AX_Max) AX_Max = AP[M1];
        //                        if (AP[M1] < AX_Min) AX_Min = AP[M1];
        //                        if (IZOTR == 0)
        //                        {
        //                            BP[M1] = AP[M1];
        //                            Kabz[M1] = BP[M1];
        //                            AV_Max = AX_Max;
        //                            AV_Min = AX_Min;
        //                        }
        //                    }
        //                if ((KxKz == 2) && (IZOTR == 1))
        //                    if ((X_blok0 <= I * V_L / N_x) && (X_blok1 >= I * V_L / N_x))
        //                    {
        //                        BP[M1] = r;
        //                        Kabz[M1] = BP[M1];
        //                        if (BP[M1] > AV_Max) AV_Max = BP[M1];
        //                        if (BP[M1] < AV_Min) AV_Min = BP[M1];
        //                    }
        //            }
        //    }
        //    catch
        //    {
        //        Cod = 1;
        //    }
        //}

        public void Write_Int_Mas(ref StreamWriter fff, int[] A, int N_D, int N_S, int N_b)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";
            string Format = Service.FormatBuilder(0, N_D);

            int K_I = 1;
            for (int i = 1; i <= N_b; i++)
            {

                fff.Write(Format, A[i]);
                K_I = K_I + 1;
                if (K_I == N_S + 1)
                {
                    if (i < N_b) fff.WriteLine();
                    K_I = 1;
                }
            }
            ;
            fff.WriteLine();
        }

        public void Write_Real_Mas(ref StreamWriter fff, int[] A, int N_C, int N_D, int N_S, int N_b)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";
            int K_I;
            string Format = Service.FormatBuilder(0, N_C, N_D);

            K_I = 1;
            for (int i = 1; i <= N_b; i++)
            {

                fff.Write(Format, A[i]);
                K_I = K_I + 1;
                if (K_I == N_S + 1)
                {
                    if (i < N_b) fff.WriteLine();
                    K_I = 1;
                }
            }
            ;
            fff.WriteLine();
        }

        public void Write_Mas_S_Or_P(ref StreamWriter fff, int[] A, int N_C, int N_D, int N_S, int I_s, int N_b)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";
            int K_I;
            string Format = Service.FormatBuilder(0, N_C, N_D);

            K_I = 1;
            for (int i = I_s; i <= N_b; i++)
            {

                fff.Write(Format, A[i] * P_S, " ");
                K_I = K_I + 1;
                if (K_I == N_S + 1)
                {
                    if (i < N_b) fff.WriteLine();
                    K_I = 1;
                }
            }
            ;
            fff.WriteLine();

        }

        public void Open_And_Assign_Files(string Inp_Res, string Out_Res)
        {
            string NNNN = Name_Dat;
            NNNN = Path.ChangeExtension(Name_Dat, "");
            string s = Path.GetFullPath(NNNN);

            //string iFileName = NNNN + Inp_Res;
            //sf10 = iFileName;
            //f10 = new StreamReader(File.Open(iFileName, FileMode.Open), Encoding.Default);

            string oFileName = NNNN + Out_Res;
            if (File.Exists(oFileName))
                File.Delete(oFileName);
            sf14 = oFileName;
            FileStream FS = new FileStream(oFileName, FileMode.CreateNew, FileAccess.Write);
            f14 = new StreamWriter(FS, Encoding.Default);
        }

        public void Close_All_Files()
        {
            //f10.Close();
            f14.Close();
        }

        public void Calc_NZ_My_And_HL_My(int N_b, double[] H_bm, int[] N_zm)
        {
            Nz_My = 0;
            HL_My = 0.0;
            for (int i = 1; i <= N_b; i++)
            {
                HL_My = HL_My + H_bm[i];
                Nz_My = Nz_My + N_zm[i];
            }
            NZ = Nz_My;
        }

        public void OutPut_Rezult_In_Moment_To_File_f14()
        {
            f14.WriteLine();

            f14.WriteLine(" М О М Е Н Т   П Р О Р Ы В А: T = " + Service.FormatBuilder(0, 8, 3) + "  сут; Q_fld = " + Service.FormatBuilder(1, 12, 6) + " м3", T, Q_fld);
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();

            f14.WriteLine("| Обв_П = " + Service.FormatBuilder(0, 12, 6) + " | Обв._T = " + Service.FormatBuilder(1, 12, 6) + " | Обв._Б = " + Service.FormatBuilder(2, 12, 6) + " | ", AI, AIT, AIB);
            f14.WriteLine("| Н.о_П = " + Service.FormatBuilder(0, 12, 6) + " | Н.о._T = " + Service.FormatBuilder(1, 12, 6) + " | Н.о._Б = " + Service.FormatBuilder(2, 12, 6) + " | ", TBT, TT, TB);
            f14.WriteLine("| Но_Пи = " + Service.FormatBuilder(0, 12, 2) + " | Но_T_и = " + Service.FormatBuilder(1, 12, 2) + " | Но_Б_и = " + Service.FormatBuilder(2, 12, 2) + " | ",
                TBT * VNE / 100.0, TT * VNET / 100.0, TB * VNEB / 100.0);
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();

            double ppk = P[1 + NZ] + Math.Log(R_Skv / HX) / Math.Log(RC / HX) * (P[1] - P[1 + NZ]);
            f14.WriteLine(" Забойное давление Pзаб = " + Service.FormatBuilder(0, 12, 6) + " МПа,  Pзаб[+NZ] = " + Service.FormatBuilder(1, 12, 6) + " МПа", ppk, P[1 + NZ]);
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();

            f14.Flush();
            f14.Close();
            FileStream FS = new FileStream(sf14, FileMode.Append, FileAccess.Write);
            f14 = new StreamWriter(FS, Encoding.Default);
        }

        public void OutPut_QP_Rezult_To_File_f14()
        {
            f14.WriteLine();

            f14.WriteLine(" К О Н Е Ц   Р А С Ч Е Т О В: T = " + Service.FormatBuilder(0, 8, 3) + "  сут; Q_fld = " + Service.FormatBuilder(1, 12, 6) + " м3", T, Q_fld);
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();

            f14.WriteLine("| Обв_П = " + Service.FormatBuilder(0, 12, 6) + " | Обв._T = " + Service.FormatBuilder(1, 12, 6) + " | Обв._Б = " + Service.FormatBuilder(2, 12, 6) + " | ", AI, AIT, AIB);
            f14.WriteLine("| Н.о_П = " + Service.FormatBuilder(0, 12, 6) + " | Н.о._T = " + Service.FormatBuilder(1, 12, 6) + " | Н.о._Б = " + Service.FormatBuilder(2, 12, 6) + " | ", TBT, TT, TB);
            f14.WriteLine("| Но_Пи = " + Service.FormatBuilder(0, 12, 2) + " | Но_T_и = " + Service.FormatBuilder(1, 12, 2) + " | Но_Б_и = " + Service.FormatBuilder(2, 12, 2) + " | ",
                TBT * VNE / 100.0, TT * VNET / 100.0, TB * VNEB / 100.0);

            f14.WriteLine("| Пт->б = " + Service.FormatBuilder(0, 12, 6) + " | ПBт->б = " + Service.FormatBuilder(1, 12, 6) + " | ПHт->б = " + Service.FormatBuilder(2, 12, 6) + " | ", Pr_TB, Q_TB, (Pr_TB - Q_TB));
            f14.WriteLine("| Пб->т = " + Service.FormatBuilder(0, 12, 6) + " | ПBб->т = " + Service.FormatBuilder(1, 12, 6) + " | ПНб->т = " + Service.FormatBuilder(2, 12, 6) + " | ", Pr_BT, Q_BT, (Pr_BT - Q_BT));
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();

            double ppk = P[1 + NZ] + Math.Log(R_Skv / HX) / Math.Log(RC / HX) * (P[1] - P[1 + NZ]);
            f14.WriteLine(" Забойное давление Pзаб = " + Service.FormatBuilder(0, 12, 6) + " МПа,  Pзаб[+NZ] = " + Service.FormatBuilder(1, 12, 6) + " МПа", ppk, P[1 + NZ]);
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("| k |   QTM[k]   |   QBM[k]   |  QSM_T[k]  |  QSM_B[k]  | AIT_M[k] | AIB_M[k] |");
            for (int i = 1; i <= 78; i++) f14.Write("-"); f14.WriteLine();
            for (int k = 1; k <= NB1; k++)
            {
                f14.WriteLine("| " + Service.FormatBuilder(0, 1) + " |" + Service.FormatBuilder(1, 11, 3) + " |" + Service.FormatBuilder(2, 11, 3) + " |" + Service.FormatBuilder(3, 11, 3) + " |" +
                    Service.FormatBuilder(4, 11, 3) + " |" + Service.FormatBuilder(5, 9, 3) + " |" + Service.FormatBuilder(6, 9, 3) + " |",
                    k, QTM[k] * 2.0 * Math.PI, QBM[k] * 2.0 * Math.PI, QSM_T[k] * 2.0 * Math.PI, QSM_B[k] * 2.0 * Math.PI, AIT_M[k], AIB_M[k]);
            }
            for (int i = 1; i <= 78; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("| k | Q_SumSl_T[k] | Qoil_SumSl_T[k]  |  Q_SumSl_B[k]   |   Qoil_SumSl_B[k]   |");
            for (int i = 1; i <= 78; i++) f14.Write("-"); f14.WriteLine();
            for (int k = 1; k <= NB1; k++)
            {
                f14.WriteLine("| " + Service.FormatBuilder(0, 1) + " |  " + Service.FormatBuilder(1, 11, 3) + " |  " +
                    Service.FormatBuilder(2, 11, 3) + " |  " + Service.FormatBuilder(3, 11, 3) + " |  " + Service.FormatBuilder(4, 11, 3) + " |  ", // "      |"
                    k, Q_SumSl_T[k] * 2.0 * Math.PI, Qoil_SumSl_T[k] * 2.0 * Math.PI, Q_SumSl_B[k] * 2.0 * Math.PI, Qoil_SumSl_B[k] * 2.0 * Math.PI);
            }
            for (int i = 1; i <= 78; i++) f14.Write("-"); f14.WriteLine();

            f14.WriteLine(" LS= " + Service.FormatBuilder(0, 3) + "   LSS= " + Service.FormatBuilder(1, 5) + "   LST= " + Service.FormatBuilder(2, 3) +
                "  TU= " + Service.FormatBuilder(3, 6, 2) + " N_др = " + Service.FormatBuilder(4, 6), LS, LSS, LST, TU, N_Dr);

            f14.WriteLine(" DISS= " + DISS.ToString() + "   DISQ = " + DISQ.ToString());
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();
            f14.Flush();
        }

        public void OutPut_QP_T_DSO_REZ_To_File_f14()
        {
            f14.WriteLine();
            f14.WriteLine("                              T = " + Service.FormatBuilder(0, 8, 3) + "  сут; Q_fld = " + Service.FormatBuilder(1, 12, 6) + " м3", T, Q_fld);
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();

            f14.WriteLine("| Обв_П = " + Service.FormatBuilder(0, 12, 6) + " | Обв._T = " + Service.FormatBuilder(1, 12, 6) + " | Обв._Б = " + Service.FormatBuilder(2, 12, 6) + " | ", AI, AIT, AIB);
            f14.WriteLine("| Н.о_П = " + Service.FormatBuilder(0, 12, 6) + " | Н.о._T = " + Service.FormatBuilder(1, 12, 6) + " | Н.о._Б = " + Service.FormatBuilder(2, 12, 6) + " | ", TBT, TT, TB);
            f14.WriteLine("| Но_Пи = " + Service.FormatBuilder(0, 12, 2) + " | Но_T_и = " + Service.FormatBuilder(1, 12, 2) + " | Но_Б_и = " + Service.FormatBuilder(2, 12, 2) + " | ",
                TBT * VNE / 100.0, TT * VNET / 100.0, TB * VNEB / 100.0);

            f14.WriteLine("| Пт->б = " + Service.FormatBuilder(0, 12, 6) + " | ПBт->б = " + Service.FormatBuilder(1, 12, 6) + " | ПHт->б = " + Service.FormatBuilder(2, 12, 6) + " | ", Pr_TB, Q_TB, (Pr_TB - Q_TB));
            f14.WriteLine("| Пб->т = " + Service.FormatBuilder(0, 12, 6) + " | ПBб->т = " + Service.FormatBuilder(1, 12, 6) + " | ПНб->т = " + Service.FormatBuilder(2, 12, 6) + " | ", Pr_BT, Q_BT, (Pr_BT - Q_BT));
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();

            double ppk = P[1 + NZ] + Math.Log(R_Skv / HX) / Math.Log(RC / HX) * (P[1] - P[1 + NZ]);
            f14.WriteLine(" Забойное давление Pзаб = " + Service.FormatBuilder(0, 12, 6) + " МПа,  Pзаб[+NZ] = " + Service.FormatBuilder(1, 12, 6) + " МПа", ppk, P[1 + NZ]);
            for (int i = 1; i <= 78; i++) f14.Write("-"); f14.WriteLine();

            f14.WriteLine("| k |   QTM[k]   |   QBM[k]   |  QSM_T[k]  |  QSM_B[k]  | AIT_M[k] | AIB_M[k] |");
            for (int i = 1; i <= 78; i++) f14.Write("-"); f14.WriteLine();
            for (int k = 1; k <= NB1; k++)
            {
                f14.WriteLine("| " + Service.FormatBuilder(0, 1) + " |" + Service.FormatBuilder(1, 11, 3) + " |" + Service.FormatBuilder(2, 11, 3) + " |" + Service.FormatBuilder(3, 11, 3) + " |" +
                    Service.FormatBuilder(4, 11, 3) + " |" + Service.FormatBuilder(5, 9, 3) + " |" + Service.FormatBuilder(6, 9, 3) + " |",
                    k, QTM[k] * 2.0 * Math.PI, QBM[k] * 2.0 * Math.PI, QSM_T[k] * 2.0 * Math.PI, QSM_B[k] * 2.0 * Math.PI, AIT_M[k], AIB_M[k]);
            }
            for (int i = 1; i <= 78; i++) f14.Write("-"); f14.WriteLine();
            f14.WriteLine("| k | Q_SumSl_T[k] | Qoil_SumSl_T[k]  |  Q_SumSl_B[k]   |   Qoil_SumSl_B[k]   |");
            for (int i = 1; i <= 78; i++) f14.Write("-"); f14.WriteLine();
            for (int k = 1; k <= NB1; k++)
            {
                f14.WriteLine("| " + Service.FormatBuilder(0, 1) + " |  " + Service.FormatBuilder(1, 11, 3) + " |  " +
                    Service.FormatBuilder(2, 11, 3) + " |  " + Service.FormatBuilder(3, 11, 3) + " |  " + Service.FormatBuilder(4, 11, 3) + " |  ", // "      |"
                    k, Q_SumSl_T[k] * 2.0 * Math.PI, Qoil_SumSl_T[k] * 2.0 * Math.PI, Q_SumSl_B[k] * 2.0 * Math.PI, Qoil_SumSl_B[k] * 2.0 * Math.PI);
            }
            for (int i = 1; i <= 78; i++) f14.Write("-"); f14.WriteLine();

            f14.WriteLine(" LS= " + Service.FormatBuilder(0, 3) + "   LSS= " + Service.FormatBuilder(1, 5) + "   LST= " + Service.FormatBuilder(2, 3) +
                "  TU= " + Service.FormatBuilder(3, 6, 2) + " N_др = " + Service.FormatBuilder(4, 6), LS, LSS, LST, TU, N_Dr);

            f14.WriteLine(" DISS= " + DISS.ToString() + "   DISQ = " + DISQ.ToString());
            for (int i = 1; i <= 72; i++) f14.Write("-"); f14.WriteLine();

            //!!!!!!!!!!!!!!!!
            Print_Mas_P_S();
            //!!!!!!!!!!!!!!!

            f14.Flush();
            OutPut_QP = 1;
        }


        #endregion Unit TRBL_TYP


        #region Unit TRBL_PRC

        public void Prepaire_Of_Constants()
        {
            // 1.ПОДГОТОВКА КОНСТАНТ
            Tim_k = Tim_0;
            Interv = 0;
            RC = 0.01;
            LSS = 0;
            NB1 = 0;
            Tau_D = TU / N_Dr;
            Tu_icx = TU;
            for (int i = 1; i <= NB; i++)
                NB1 = NB1 + LWN[i];
            //.......................................................
            for (int i = 1; i <= NB; i++)
            {
                Bet_wB[i] = Bt_Cp + VMB[i] * MixtureProperties.WaterProperties.AT3 / 10.0;
                Bet_oB[i] = Bt_Cp + VMB[i] * MixtureProperties.OilProperties.AT1 / 10.0;
                Bet_wT[i] = Bt_Tr + VMT[i] * MixtureProperties.WaterProperties.AT3 / 10.0;
                Bet_oT[i] = Bt_Tr + VMT[i] * MixtureProperties.OilProperties.AT1 / 10.0;
            }
            //.......................................................

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
            // 2.ВЫЧИСЛЕНИЕ ВСПОМОГАТЕЛЬНЫХ ВЕЛИЧИН
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
            // 3. ПЕРЕНОС ГРАНИЧНЫХ ЗНАЧЕНИЙ
            //     И ПОСТРОЕНИЕ НУЛЕВОГО ПРИБЛИЖЕНИЯ
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
            //..............................................
            for (int K = 1; K <= NZ; K++)
                for (int i = 1; i <= NX + 1; i++)
                    P_0[K + (i - 1) * NZ] = P[N1 + K];
            //..............................................
        }

        public void Initialization_Of_S0(bool FromFile)
        {
            //var M1,m,i,k:integer;
            // 4. ФОРМИРОВАНИЕ ST(k),SB(K), WT(K), WB(K)

            // !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 2018
            //for (int K = 1; K <= N2; K++)
            //{
            //    WT[K] = MixtureProperties.OilProperties.Mu1_PL;
            //    WB[K] = MixtureProperties.OilProperties.Mu1_PL;
            //}


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
            // 5.ПОДГОТОВКА МАССИВОВ АБСОЛЮТНОЙ ПРОНИЦАЕМОСТИ
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
                        Kabx[M1] = AKT[K];   //абс. прон. по трещинам
                        Kabz[M1] = AKB[K];  //абс. прон. по блокам
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

        public void SKFB(double S1, double S2, double X, double AMUF, ref double BKF, ref double FK, ref double Psik)
        {
            double SK1, SK2;
            if (X <= S1) SK1 = 0.0;
            else
                //SK1 = Maths.Sqr((X - S1) / S2) * (X - S1) / S2 / MixtureProperties.WaterProperties.Mu3_PL;
                SK1 = Math.Pow((X - S1) / S2, 3.13) / MixtureProperties.WaterProperties.Mu3_PL;
            if (X >= S2) SK2 = 0.0;
            else
                //SK2 = Maths.Sqr((S2 - X) / (S2 - S1)) * (S2 - X) / (S2 - S1) / AMUF;
                SK2 = Math.Pow((S2 - X) / (S2 - S1), 2.73) / AMUF;
            BKF = SK1 + SK2;
            FK = SK1 / BKF;
            Psik = FK * SK2;
        }

        public void SKFT(double S1, double S2, double X, double AMUF, ref double BKF, ref double FK, ref double Psik)
        {
            double SK1, SK2;
            if (X <= S1) SK1 = 0.0;
            else SK1 = (X - S1) / MixtureProperties.WaterProperties.Mu3_PL;  //Math.Pow((X - S1), Step_WT) / AMUB;
            if (X >= S2) SK2 = 0.0;
            else SK2 = (S2 - X) / AMUF; //=0.1;
            BKF = SK1 + SK2;
            FK = SK1 / BKF;
            Psik = FK * SK2;
        }

        public void WKF(double ModV, ref double Vis)
        {
            //Vis = MixtureProperties.OilProperties.Mu1_PL;   // Новое
            if (ModV < X_A)
                Vis = 1.0 / (1.0 / MixtureProperties.OilProperties.Mu1_PL + a_ * Math.Pow(ModV, b_) * Math.Exp(-c_ * ModV));
            else
                Vis = MU_pazp;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="K_Out"></param>
        /// <remarks>Функция с параллельным кодом</remarks> 
        /// Параллельный цикл в конце затормаживает счет - параллелить только 1ый
        public void Array_Of_Coefficients_On_SubPoints(ref int K_Out)
        {
            try
            {
                K_Out = 1;

                // 5.1 ПОДГОТОВКА МАССИВОВ КОЭФФИЦИЕНТОВ В ПОЛУУЗЛАХ


                #region Последовательный режим

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

                // 5.2. Вычисление правой части разностного уравнения
                for (int K = 1; K <= N; K++)
                    FG[K] = BVB[K + 1] + BVT[K + 1] - BVB[K] - BVT[K];
                //.......................................................
                for (int I = 1; I <= NX; I++)
                    for (int k = 1; k <= NB; k++)
                        for (int M = 1 + NM[k - 1]; M <= NM[k]; M++)                //  Новый массив CBet[]
                        {
                            int M1 = M + (I - 1) * NZ;
                            int M2 = M1 + NZ;
                            CBet[M1] = HM[k] * HX * HX * (I - 0.5) / TU *
                                (Bet_oB[k] + SB[M2] * (Bet_wB[k] - Bet_oB[k]) +
                                Bet_oT[k] + ST[M2] * (Bet_wT[k] - Bet_oT[k]));
                            FG[M1] = FG[M1] - CBet[M1] * P_0[M2];
                        }
                //.......................................................

                #endregion Последовательный режим
            }
            catch
            {
                K_Out = -1;
            }
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="K_Out"></param>
        /// <remarks>Функция с параллельным кодом</remarks>
        /// Параллельный цикл затормаживает счет
        public void Coefficients_For_Evaluate_Pressure(ref int K_Out)
        {
            try
            {
                K_Out = 1;

                #region Последовательный режим
                // 6.ВЫЧИСЛЕНИЕ ДАВЛЕНИЯ_______
                // 6.0 ПОДГОТОВКА КОЭФФИЦИЕНТОВ ДЛЯ СУММАРНОЙ ПРОГОНКИ
                for (int I = 1; I <= NX + 1; I++)
                {
                    SIG_P[I] = 0.0;
                    for (int k = 1; k <= NZ; k++)
                    {
                        int M = k + (I - 1) * NZ;
                        SIG_P[I] = SIG_P[I] + A[M];
                    }
                }

                //.......................................................
                for (int I = 2; I <= NX + 1; I++)
                {
                    CS[I] = 0;
                    for (int k = 1; k <= NZ; k++)
                    {
                        int M = k + (I - 2) * NZ;
                        CS[I] = CS[I] + CBet[M];
                    }
                }
                //.......................................................

                // ВЫЧИСЛЕНИЕ ПРОГОНОЧНЫХ КОЭФФИЦИЕНТОВ ДЛЯ СУММАРНОЙ ПРОГОНКИ
                CS[1] = 1.0 / SIG_P[1];
                CS[2] = 1.0 / (SIG_P[2] + CS[2] + LPQ1 * SIG_P[1]);
                for (int I = 2; I <= NX; I++)
                {
                    int I1 = I + 1;
                    CS[I1] = 1.0 / (SIG_P[I1] + CS[I1] + (1 - SIG_P[I] * CS[I]) * SIG_P[I]);
                }
                // 6.1. Подготовка коэффициентов для пятиточечной прогонки
                for (int I = 1; I <= N; I++)
                    C[I] = A[I] + A[I + NZ] + B[I] + B[I + 1] + CBet[I];
                //.......................................................
                #endregion Последовательный режим

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
                    // 6.2. Прогоночные коэффициенты
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

        public void Circular_Pass(ref int K_Out)
        {
            try
            {
                K_Out = 1;
                DL = 0.0;
                // 6.3.2. Вычисление правой части для прогонки
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
                    // Пятиточечная прогонка
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

        public void Do_Iteration(ref int K_Out)
        {
            try
            {
                K_Out = 1;

                // 6.6 УТОЧНЕНИЕ ИТЕРАЦИЙ
                DL1 = 0.0;
                for (int K = 1; K <= NX + 1; K++)
                {
                    FI[K] = 0.0;
                    for (int I = 1 + (K - 1) * NZ; I <= K * NZ; I++)
                        FI[K] = FI[K] + A[I] * (P[I + NZ] - P[I]);
                }

                for (int K = NX; K >= 1; K--)
                {
                    //RR=0;
                    //  for I:=1+(K-1)*NZ to K*NZ do RR:=RR+FG[i];
                    int K1 = K + 1;
                    FI[K1] = FI[K1] - FI[K];//{-RR}
                }


                //.......................................................
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

        /// <summary>
        /// 
        /// </summary>
        /// <remarks>Функция с параллельным кодом</remarks>
        /// Параллельный цикл затормаживает счет
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
                B[i] = -(AVB[i + NZ] - AVB[i] + BVB[i + 1] - BVB[i]);//   {суммарный переток}

            #region Последовательный режим
            //.......................................................
            for (int i = 1; i <= NX; i++)
                for (int k = 1; k <= NB; k++)
                    for (int m = 1 + NM[k - 1]; m <= NM[k]; m++)
                    {
                        int M1 = m + (i - 1) * NZ;
                        int M2 = M1 + NZ;
                        B[M1] = B[M1] + HM[k] * HX * HX * (i - 0.5) * (P[M2] - P_0[M2]) / TU *
                            (Bet_oB[k] + SB[M2] * (Bet_wB[k] - Bet_oB[k]));
                    }
            //.......................................................
            #endregion Последовательный режим
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="i"></param>
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
                    //{фазовый переток(изменяется при дроблении шага)}
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
        /// <summary>
        /// 
        /// </summary>
        /// <remarks>Функция с параллельным кодом</remarks>        
        public void Calculation_Of_Phases_Flows()
        {
            #region Последовательный режим

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
                        //{фазовый переток(изменяется при дроблении шага)}
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

            #endregion Последовательный режим
        }

        /// <summary>
        /// Вычисление насыщенности
        /// </summary>
        /// <remarks>Функция с параллельным кодом</remarks>
        /// Ошибка в параллельных расчетах
        public void Saturations()
        {

            #region Sequental

            for (int K = 1; K <= NM[NB1]; K++)
            {
                QS_T[K] = 0.0;
                QS_B[K] = 0.0;
            }
            QP_TB = 0.0;
            QP_BT = 0.0;

            //   Print_Mas_Rab();

            //-----------------------------------------------------
            for (int L = 1; L <= N_Dr; L++)
            {
                Calculation_Of_Phases_Flows();

                //   Print_Mas_Rab();

                // вычисления в блоках
                int kk = 1 + NM[NB - 1];
                for (int I = 1; I <= NX; I++)
                {
                    int M = kk + (I - 1) * NZ;
                    BVST[M] = BVT[M];
                    BVSB[M] = BVB[M];     //значения на верхней границе нижнего слоя//
                }


                //    Print_Mas_Rab();

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
                //for I:=1 to NX do BVSB[1+(I-1)*NZ]:=0;
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

                // {вычисления в трещинах}                    
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

                //     Print_Mas_Rab();

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
                // Новая явная - 24.11.07
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
                // Новая явная - 24.11.07
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
                //-----------------------------
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

            //    Print_Mas_Rab();

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

            #endregion Sequental

        }

        public void Main_Characts()
        {
            //var M1,j,k,i,m:integer; QST, QSB : Real;

            // 10. ВЫЧИСЛЕНИЕ ОСНОВНЫХ ХАРАКТЕРИСТИК
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
            // обводненность
            AIT = QST / (QT + 1e-6) * 100;
            AIB = QSB / (QB + 1e-6) * 100;
            AI = (QSB + QST) / (Q_zab + 1e-6) * 100;
            if (QT < 0.1)
            {
                AIT = 0; AIB = 0; AI = 0;
            }
            N_1D = N_1D + 1;
            Array.Resize<double>(ref T_Mass, N_1D + 2); T_Mass[N_1D] = T;
            // обводненность
            Array.Resize<double>(ref AIT_Mass, N_1D + 2); AIT_Mass[N_1D] = AIT;
            Array.Resize<double>(ref AIB_Mass, N_1D + 2); AIB_Mass[N_1D] = AIB;
            Array.Resize<double>(ref AI_Mass, N_1D + 2); AI_Mass[N_1D] = AI;

            // нефтеотдача
            TB = 0; TT = 0;
            for (int K = 1; K <= NB - 1; K++)
                for (int M = 1 + NM[K - 1]; M <= NM[K]; M++)
                    for (int I = 1; I <= NX; I++)
                    {
                        int M1 = M + I * NZ;
                        TB = TB + (SB[M1] - SNB[K]) * (VPIB[M] * (I - 0.5));
                        TT = TT + (ST[M1] - SNT[K]) * (VPIT[M] * (I - 0.5));
                    }
            // 11. ВЫЧИСЛЕНИЕ  ДИСБАЛАНСА
            TBQ = TBQ + (QB - QSB) * TU;
            TTQ = TTQ + (QT - QST) * TU;
            Q_fld = Q_fld + 2 * Math.PI * (QB + QT) * TU;
            DISS = TT - TTQ - (Pr_TB - Pr_BT + Q_BT - Q_TB);
            DISQ = TB - TBQ - (Pr_BT - Pr_TB + Q_TB - Q_BT);

            // ОБЪЕМ ДОБ. НЕФТИ ПО СЛОЯМ
            Array.Resize<double>(ref Qoil_SumSl_1, N_1D + 2); Qoil_SumSl_1[N_1D] = 2 * Math.PI * (Qoil_SumSl_T[1] + Qoil_SumSl_B[1]) / 1000;
            Array.Resize<double>(ref Qoil_SumSl_2, N_1D + 2); Qoil_SumSl_2[N_1D] = 2 * Math.PI * (Qoil_SumSl_T[2] + Qoil_SumSl_B[2]) / 1000;
            Array.Resize<double>(ref Qoil_SumSl_3, N_1D + 2); Qoil_SumSl_3[N_1D] = 2 * Math.PI * (Qoil_SumSl_T[3] + Qoil_SumSl_B[3]) / 1000;

            // Количество добытой нефти
            Array.Resize<double>(ref Q_TBT_Mass, N_1D + 2); Q_TBT_Mass[N_1D] = 2 * Math.PI * (TB + TT) / 1000;
            Array.Resize<double>(ref Q_TB_Mass, N_1D + 2); Q_TB_Mass[N_1D] = 2 * Math.PI * TB / 1000;
            Array.Resize<double>(ref Q_TT_Mass, N_1D + 2); Q_TT_Mass[N_1D] = 2 * Math.PI * TT / 1000;
            Array.Resize<double>(ref Q_W_Mass, N_1D + 2); Q_W_Mass[N_1D] = Q_fld / 1000;

            TBT = 2 * Math.PI * (TB + TT) / VNE * 100;
            TB = 2 * Math.PI * TB / VNEB * 100;
            TT = 2 * Math.PI * TT / VNET * 100;

            // нефтеотдача
            Array.Resize<double>(ref TBT_Mass, N_1D + 2); TBT_Mass[N_1D] = TBT;
            Array.Resize<double>(ref TB_Mass, N_1D + 2); TB_Mass[N_1D] = TB;
            Array.Resize<double>(ref TT_Mass, N_1D + 2); TT_Mass[N_1D] = TT;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <remarks>Функция с параллельным кодом</remarks>
        /// Нет ошибок в распараллеливании
        public void VISCOSITIES()
        {
            #region Последовательный режим
            // вычисление вязкости WT и WB
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

            //Граничное значение P
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
                    //  Q=QQ/(2*Math.PI);
                    //  Q_Izm_Fix=1;
                    //    Tu:=min(Tu_icx, Tu_icx*QQ_ICX/(Q+1.e-3) );
                    //   N_Dr:=Trunc(N_Dr_ICX*Q/QQ_ICX)+1;
                }
            #endregion Последовательный режим
        }

        public void Prepear_To_Go_New_Time_Sublayer(ref int Cod_Out)
        {
            // 12. ПОДГОТОВКА И ПЕРЕХОД НА НОВЫЙ ВРЕМЕННОЙ СЛОЙ
            LST = LST + 1;
            Cod_Out = 1;
            T_Tek = T_Tek + TU;
            T = T + TU;
            if (T_Tek + TU / 4 > DSO)
            {
                //OutPut_QP_T_DSO_REZ_To_File_f14();
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
                            //Print_Mas_P_S();
                            //OutPut_Rezult_In_Moment_To_File_f14();
                            LTB = 1;
                        }
                        Cod_Out = -1;
                        break;
                    //{===================  13.-14. ПЕЧАТЬ РЕЗУЛЬТАТОВ ========================}
                    case 7:
                        Print_Mas_P_S();
                        //OutPut_QP_Rezult_To_File_f14();
                        Cod_Out = 0;
                        break;
                }
            }
            //{---------------------------------------------------------------------------}
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="Tim_Tek"></param>
        /// <param name="K_Out"></param>

        /// <summary>
        /// Вычисление давления
        /// </summary>
        /// <param name="DoExternalInterations"></param>
        /// <param name="K_Out">Признак правильности выполнения</param>
        public void Calc_Filt_Process_Pressure(bool DoExternalInterations, ref int K_Out)
        {
            try
            {
                K_Out = 1;
                // Выч-ие к-тов в дробных точках:
                Array_Of_Coefficients_On_SubPoints(ref K_Out);
                if (K_Out == -1) return;
                // ----------------------------------
                // Вычисление давления. =========
                // Подготовка коэффициентов :
                Coefficients_For_Evaluate_Pressure(ref K_Out);
                if (K_Out == -1) return;
                // ----------------------------------
                LS = 0;
                do
                {
                    if (DoExternalInterations)
                    {
                        // Выч-ие к-тов в дробных точках:
                        Array_Of_Coefficients_On_SubPoints(ref K_Out);
                        if (K_Out == -1) return;
                        // ----------------------------------
                        // Вычисление давления. =========
                        // Подготовка коэффициентов :
                        Coefficients_For_Evaluate_Pressure(ref K_Out);
                        if (K_Out == -1) return;
                        // ----------------------------------
                        Circular_Pass(ref K_Out);
                        if (K_Out == -1) return;
                        // ----------------------------------
                        Do_Iteration(ref K_Out);
                        if (K_Out == -1) return;
                        // ----------------------------------
                        if (NB1 < NB)
                            for (int i = NM[NB1] + 1; i <= NM[NB]; i++)
                                P[i] = P[i + NZ];
                        //{ ---------------------------------------------------- }
                        //{ 7.  }
                        Calculation_Of_Total_Flows();
                        VISCOSITIES();
                        //// ----------------------------------
                    }
                    else
                    {
                        // ----------------------------------
                        Circular_Pass(ref K_Out);
                        if (K_Out == -1) return;
                        // ----------------------------------
                        Do_Iteration(ref K_Out);
                        if (K_Out == -1) return;
                        // ----------------------------------
                    }
                }
                while (!(DL + DL1 <= EPSP));
                // ----------------------------------
                // Присвоение Pзаб для скважины:
                // ----------------------------------
                P_zab_DC = P[1]; //???????

            }
            catch
            {
                K_Out = -1;
            }
            ;
        }

        public void Clc_Of_Qz_At_Pz_Fix(bool DoExternalInterations,
            double P_Zb_Fix,
            ref int K_Out)
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
                    ;

                    Q_zab = (Qzab_A + Qzab_B) / 2;
                    N_itr_Pz = N_itr_Pz + 1;
                    N_itr = N_itr_Pz;

                    if (N_itr > 30)
                    {
                        K_Out = -2;
                        return;
                    }
                }
                ;

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
                        ;
                        if (Ra >= Rb)
                        {
                            P_zab_DC = Pz_A;
                        }
                        ;
                        break;
                    }
                    ;

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
                    ;
                    N_itr_Pz = N_itr_Pz + 1;
                }
                ;

                N_itr_Out = N_itr_Pz;
                Q_Dob = Q_zab * 2.0 * Math.PI;
            }
            catch
            {
                K_Out = -1;
            }
            ;
        }

        /// <summary>
        /// Фильтрация к скважине в вертикальном разрезе ТПП
        /// </summary>
        /// <param name="Tim_Tek">Текущее время</param>
        /// <param name="K_Out">Признак правильности выполнения</param>
        public void HorWell_Razrez_TB(bool FromFile, ref double Tim_Tek, ref int K_Out)
        {
            try
            {
                K_Out = 1;

                T_Tek = 0;
                // Создание Остальных рабочих массивов
                if (!FromFile)
                    Create_Work_Dyn_Arrayes();

                OutPut_QP = 0;

                N_1D = 1;
                T_Mass = null; Array.Resize<double>(ref T_Mass, N_1D + 2); T_Mass[1] = 0;
                // обводненность
                AIT_Mass = null; Array.Resize<double>(ref AIT_Mass, N_1D + 2); AIT_Mass[1] = 0;
                AIB_Mass = null; Array.Resize<double>(ref AIB_Mass, N_1D + 2); AIB_Mass[1] = 0;
                AI_Mass = null; Array.Resize<double>(ref AI_Mass, N_1D + 2); AI_Mass[1] = 0;
                // нефтеотдача
                TBT_Mass = null; Array.Resize<double>(ref TBT_Mass, N_1D + 2); TBT_Mass[1] = 0;
                TB_Mass = null; Array.Resize<double>(ref TB_Mass, N_1D + 2); TB_Mass[1] = 0;
                T_Mass = null; Array.Resize<double>(ref TT_Mass, N_1D + 2); TT_Mass[1] = 0;
                // Количество добытой нефти
                Q_TBT_Mass = null; Array.Resize<double>(ref Q_TBT_Mass, N_1D + 2); Q_TBT_Mass[1] = 0;
                Q_TB_Mass = null; Array.Resize<double>(ref Q_TB_Mass, N_1D + 2); Q_TB_Mass[1] = 0;
                Q_TT_Mass = null; Array.Resize<double>(ref Q_TT_Mass, N_1D + 2); Q_TT_Mass[1] = 0;
                Q_W_Mass = null; Array.Resize<double>(ref Q_W_Mass, N_1D + 2); Q_W_Mass[1] = 0;
                // ОБЪЕМ ДОБ. НЕФТИ ПО СЛОЯМ
                Qoil_SumSl_1 = null; Array.Resize<double>(ref Qoil_SumSl_1, N_1D + 2); Qoil_SumSl_1[1] = 0;
                Qoil_SumSl_2 = null; Array.Resize<double>(ref Qoil_SumSl_2, N_1D + 2); Qoil_SumSl_2[1] = 0;
                Qoil_SumSl_3 = null; Array.Resize<double>(ref Qoil_SumSl_3, N_1D + 2); Qoil_SumSl_3[1] = 0;

                //{ 1.  }
                if (!FromFile)
                {
                    T = 0.0;
                    Q_zab = Q_zab / (2.0 * Math.PI);
                    QQ_ICX = Q_zab / 5.0;
                }
                Prepaire_Of_Constants();

                for (int k = 1; k <= NB; k++)
                    for (int i = 1 + NM[k - 1]; i <= NM[k]; i++)
                    {
                        HZM[i] = HM[k];
                        VPIT[i] = VMT[k] * HM[k] * HX * HX;
                        VPIB[i] = VMB[k] * HM[k] * HX * HX;
                    }
                VPIT[0] = VPIT[1]; VPIB[0] = VPIB[1];

                HZM[NZ + 1] = 0;
                //{ 2.  }     
                Evaluate_Of_Parameters();
                //{ 3.  }      
                if (!FromFile)
                    Boundary_Conditions_And_Initial_Appr();
                //{ 4.  }      
                Initialization_Of_S0(FromFile);
                //{ 5.  } 
                Prepeare_Of_Array_Abs_Permeability();

                Cod_Exit = 15;
            }
            catch
            {
                K_Out = -1;
            }
        }

        public void Saturation_and_Main_Characts(bool DoExternalInterations, ref int K_Out)
        {
            //return;
            K_Out = 1;
            try
            {
                if (DoExternalInterations)
                {
                    if (NB1 < NB)
                        for (int i = NM[NB1] + 1; i <= NM[NB]; i++)
                            P[i] = P[i + NZ];
                    //{ ---------------------------------------------------- }
                    //{ 7.1.}
                    Saturations();
                    //{ ---------------------------------------------------- }
                    //{ 10.  }
                    Main_Characts();
                    //{ --------------------------------- }
                }
                else
                {
                    if (NB1 < NB)
                        for (int i = NM[NB1] + 1; i <= NM[NB]; i++)
                            P[i] = P[i + NZ];
                    //{ ---------------------------------------------------- }
                    //{ 7.  }
                    Calculation_Of_Total_Flows();
                    //{ ---------------------------------------------------- }
                    //{ 7.1.}
                    Saturations();
                    //{ ---------------------------------------------------- }
                    //{ 10.  }
                    Main_Characts();
                    VISCOSITIES();
                    //{ --------------------------------- }
                }
            }
            catch
            {
                K_Out = -1;
            }
        }


        #endregion Unit TRBL_PRC
    }
}
