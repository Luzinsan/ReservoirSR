using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

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
    public partial class ReservoirSimulationEngine
    {
        /// <summary>
        /// Конструктор класса фильтрации в трещинвато-пористом пласте
        /// </summary>
        public ReservoirSimulationEngine()
        {
            MixtureProperties = new Class_MixtureProperties();
        }

        #region Unit TRBL_TYP

        #region Переменные класса ReservoirSimulationEngine

        /// <summary>
        /// Параметры трехфазной смеси
        /// </summary>
        public Class_MixtureProperties MixtureProperties;
        public double ConfiguredQZab { get; private set; }

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
            Y__N, Interv;

        public int
            NB1, N_Dr, NB, NX, LOD, LS0, LIZ, LPQ = 1, LPK, LTTK, LTVK, LTK,
            NT,

            Q_Izm, N_Dr_new,
            NZ, N, N1, N2, NZ2, LST, LTB, LK, LKK, Q_Izm_Fix,
            LKB, NKON, LPQ1, LKM = 50,
            ParReg, Cod_Exit, Nz_My, N_Dr_ICX,
            I_blok0, I_blok1, Y_blok0, Y_blok1, Pr_Count,
            NX1, NX2,
            N_itr_Out = 0;


        public int LSS, LS;

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

        #endregion Переменные класса ReservoirSimulationEngine

        /// <summary>
        /// 
        /// </summary>
        /// <param name="K_Out"></param>
        /// <remarks>Функция с параллельным кодом</remarks> 
        /// Параллельный цикл в конце затормаживает счет - параллелить только 1ый
        #endregion Unit TRBL_PRC
    }
}
