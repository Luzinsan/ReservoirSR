using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

using ClassLibrary_Global;

namespace ClassLibrary_PhasesProperties
{
    /// <summary>
    /// Класс свойств нефти
    /// </summary>
    public class Class_OilProperties
    {
        /// <summary>
        /// Cвойства газа, растворенного в нефтяной фазе
        /// </summary>
        public Class_GasProperties GasProperties;

        #region Свойства нефти
        /// <summary>
        /// Плотность нефти в пластовых условиях, кг/м^3
        /// </summary>
        public double Ro1_PL;
        /// <summary>
        /// Вязкость нефти в пластовых условиях, мПа*с
        /// </summary>
        public double Mu1_PL;
        /// <summary>
        /// Пластовая температура, град С
        /// </summary>
        public double T_PL;
        /// <summary>
        /// Пластовое давление, МПа
        /// </summary>
        public double P_PL;
        /// <summary>
        /// Вязкость дегазированной нефти при норм. условиях, мПа*с
        /// </summary>
        public double Mu_Deg;
        /// <summary>
        /// Удельная изобарная теплоемкость нефти, кДж/(кг*град С)
        /// </summary>
        public double C_P_1;
        ///// <summary>
        ///// Теплопроводность нефти, Вт / (м*С)
        ///// </summary>
        //public const double Lmbd1 = 0.12;
        /// <summary>
        /// К-т теплового расширения нефти, 1/град С
        /// </summary>
        public double AP1;
        /// <summary>
        /// К-т объемной упругости нефти, 1/МПа
        /// </summary>
        public double AT1;
        /// <summary>
        /// Плотность дегазированной нефти при норм.усл., кг/м^3
        /// </summary>
        public double Ro1_deg;
        /// <summary>
        /// Газовый фактор Vo пластовой нефти при норм.усл., м^3/м^3
        /// </summary>
        public double VG0;
        /// <summary>
        /// Давление Pно насыщения нефти газом при н.усл., МПа
        /// </summary>
        public double PH0;
        /// <summary>
        /// К-т B температурной зависимости Pн=Pно+B*(t-to), МПа/град С
        /// </summary>
        public double BT;
        /// <summary>
        /// К-т A температурной зависимости Vг=Vо(1+A(t-to)), 1/град С
        /// </summary>
        public double BG;
        /// <summary>
        /// Харатерное значение температуры эксперимента
        /// </summary>
        public double T_xar;
        /// <summary>
        /// ????
        /// </summary>
        public int pr_FP0 = 1;
        #endregion Свойства нефти

        /// <summary>
        /// Конструктор класса свойств нефтяной фазы
        /// </summary>
        public Class_OilProperties()
        {
            // Вызываем конструктор класса свойств газа
            GasProperties = new Class_GasProperties();
        }

        #region Расчетные ффункции
        /// <summary>
        /// Удельная изобарная теплоемкость нефти при заданной температуре, кДж/(кг*град С)
        /// </summary>
        /// <param name="Temp">Температура, град С</param>
        /// <returns>Возвращает удельную изобарную теплоемкость нефти, кДж/(кг*град С)</returns>
        public double CP1(double Temp)
        {
            return (C_P_1);
        }

        /// <summary>
        /// Коэффициент растворимости газа в нефти при заданных давлении и температуре
        /// </summary>
        /// <param name="P">Давление, МПа</param>
        /// <param name="T">Температура, град С</param>
        /// <param name="K_Out">Признак правильности выполнения</param>
        /// <returns>Возвращает коэффициент растворимости газа в нефти</returns>
        public double F(double P, double T, ref int K_Out)
        {
            double Ufg, Fsv, DL;
            try
            {
                K_Out = 1;
                if (P >= 1.0)
                {
                    return (0.0);
                };
                Fsv = 1.0; DL = 0.0;
                if ((P > 0.0) && (P < 1.0))
                {
                    DL = 0.007 * (1.0 - P) * P * Math.Exp(-1.556 * P);
                    Fsv = 1.0 - Math.Pow(P, 1.0 / 3.0);
                };
                Ufg = Fsv + DL * (T - T_xar);
                return (Math.Min(Ufg, 1.0));
            }
            catch
            {
                K_Out = -1;
                return (0.0);
            };
        }

        /// <summary>
        /// Производная dF/dP при заданных давлении и температуре
        /// </summary>
        /// <param name="P">Давление, МПа</param>
        /// <param name="T">Температура, град С</param>
        /// <param name="K_Out">Признак правильности выполнения</param>
        /// <returns>Возвращает значение производной dF/dP</returns>
        public double fDifF(double P, double T, ref int K_Out)
        {
            double PH, y_, difF, difDelta;
            try
            {
                K_Out = 1;
                PH = PN(T);
                y_ = P / (PH);
                if (y_ >= 1.0) return (0.0);
                else
                {
                    if (y_ < 1e-3) difF = -Math.Pow(1e-3, -2.0 / 3.0) / 3.0;
                    else difF = -Math.Pow(y_, -2.0 / 3.0) / 3.0;
                    difDelta = 0.007 * Math.Exp(-1.556 * y_) * (1.556 * y_ * y_ - 3.556 * y_ + 1.0);
                    return ((difF + difDelta * (T - T_xar)) / PH);
                };
            }
            catch
            {
                K_Out = -1;
                return 0.0;
            };
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="P">Давление, МПа</param>
        /// <returns></returns>
        public double DL(double P)
        {
            if (P >= 1.0) return (0.0);
            else return (0.007 * Math.Exp(-1.556 * P) * P * (1.0 - P));
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="P">Давление, МПа</param>
        /// <returns></returns>
        public double DDL(double P)
        {
            if (P >= 0.95) return (0.0);
            else return (0.007 * Math.Exp(-1.556 * P) * (1.556 * P * P - 3.556 * P + 1.0));
        }

        /// <summary>
        /// Производная dF/dP при заданном давлении
        /// </summary>
        /// <param name="P">Давление, МПа</param>
        /// <param name="K_Out">Признак правильности выполнения</param>
        /// <returns>Возвращает значение производной dF/dP</returns>
        public double DFS(double P, ref int K_Out)
        {
            K_Out = 1;
            try
            {
                if (P >= 1.0) return (0.0);
                else
                {
                    if (P < 1e4) return (-Math.Pow(1e4, -2.0 / 3.0) / 3.0);
                    else return (-Math.Pow(P, -2.0 / 3.0) / 3.0);
                };
            }
            catch
            {
                K_Out = -1;
                return 0.0;
            }
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="Xgz"></param>
        /// <param name="DLV"></param>
        /// <param name="P1_"></param>
        /// <param name="T_"></param>
        /// <param name="Ro2_"></param>
        /// <param name="APZ"></param>
        /// <param name="CPZ"></param>
        /// <param name="K_Out">Признак правильности выполнения</param>
        public void DIFX(double Xgz, double DLV, double P1_, double T_, double Ro2_, ref double APZ, ref double CPZ, ref int K_Out)
        {
            double P, CH, PH, FP, FP0 = 0, V0, DFDP2, DFDT, DCHDT,
                RX, RY, RZ, DXDT, DXDP2;
            try
            {
                K_Out = 1;
                PH = PN(T_);
                CH = C_H(DLV, PH, T_, ref K_Out);
                if (pr_FP0 == 1) FP0 = 1;
                else F(Consts.P0 / PH, T_, ref K_Out);
                FP = F(P1_ / PH, T_, ref K_Out);
                V0 = VG(DLV, T_) / FP0;
                P = P1_ / PH;
                DFDP2 = (DFS(P, ref K_Out) + (T_ - T_xar) * DDL(P)) / PH;
                if (K_Out == -1) return;
                DFDT = DL(P) - BT * P * DFDP2;
                P = Consts.P0 / PH;
                DCHDT = (DFS(P, ref K_Out) + (T_ - T_xar) * DDL(P)) * P * BT / PH;
                if (K_Out == -1) return;
                DCHDT = CH / FP0 * (VG0 * BG / V0 - (DL(P) - DCHDT));
                RX = (1.0 - GasProperties.DZT * P1_) / P1_;
                RY = 1.0 + GasProperties.YTAP2 * (T_ + 273.0);
                RZ = CH / (1.0 - DLV);
                DXDT = RZ * DFDT + FP * DCHDT / (1.0 - DLV);
                DXDP2 = RZ * DFDP2;
                // РАЗМЕРНОСТЬ ВЕЛИЧИН:
                // (F1)=1; (F2)=МПА/ГРАД С; (F3)=1/MПA; (F4)=1/ГPAД С
                // (CPZ)=кдж; (APZ)=m**3/кг
                CPZ = GasProperties.S_T_R * DXDT;
                APZ = (Xgz * RY) / Ro2_ - GasProperties.S_T_R * 0.001 * DXDP2;
            }
            catch
            {
                K_Out = -1;
            }
        }
        
        /// <summary>
        /// Давление насыщения нефти газом при заданной температуре, МПа
        /// </summary>
        /// <param name="Temp">Температура, град С</param>
        /// <returns>Давление насыщения нефти газом, МПа</returns>
        public double PN(double Temp)
        {
            return (PH0 + BT * (Temp - 20.0));
        }

        /// <summary>
        /// Плотность нефти при заданном давлении, температуре, 
        /// </summary>
        /// <param name="Pres">Давление, МПа</param>
        /// <param name="Temp">Температура, град С</param>
        /// <param name="C"></param>
        /// <param name="CH"></param>
        /// <returns>Плотность нефти, кг/м^3</returns>
        public double ROIL(double Pres, double Temp, double C, double CH)
        {
            double R_o, Roo, Rim;
            R_o = Ro1_PL * (1.0 - AP1 * (Temp - T_PL) + AT1 * (Pres - P_PL));
            if (CH > 0.0)
            {// New!! 27.02.10
                Roo = (Ro1_PL / Ro1_deg) * (1.0 - AP1 * (20.0 - T_PL) + AT1 * (Consts.P0 - P_PL));
                Rim = C / CH;
                return (R_o / (Rim + (1.0 - Rim) * Roo));
            }
            else return (R_o);  // New!! 27.02.10    
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="DLV"></param>
        /// <param name="PH"></param>
        /// <param name="T"></param>
        /// <param name="K_Out">Признак правильности выполнения</param>
        /// <returns></returns>
        public double C_H(double DLV, double PH, double T, ref int K_Out)
        {
            double FP0;
            K_Out = 1;
            try
            {
                if (pr_FP0 == 1) FP0 = 1.0;
                else FP0 = F(Consts.P0 / PH, T, ref K_Out);
                if (K_Out == -1) return (0.0);
                return (GasProperties.R00 * VG(DLV, T) / (FP0 * Ro1_PL));
            }
            catch
            {
                K_Out = -1;
                return 0.0;
            };
        }

        /// <summary>
        /// Газовый фактор V пластовой нефти при заданной температуре, м^3/м^3
        /// </summary>
        /// <param name="DLV"></param>
        /// <param name="Temp">Температура, град С</param>
        /// <returns>Газовый фактор V пластовой нефти, м^3/м^3</returns>
        public double VG(double DLV, double Temp)
        {
            return (VG0 * (1.0 + BG * (Temp - 20.0)) * (1.0 - DLV));
        }

        /// <summary>
        /// Вязкость нефти при заданной температуре
        /// </summary>
        /// <param name="T">Температура, град С</param>
        /// <param name="F"></param>
        /// <param name="K_Out">Признак правильности выполнения</param>
        /// <returns></returns>
        public double Vis_Oil(double T, double F, ref int K_Out)
        {
            double VZ0, VZH, V_Z;
            try
            {
                K_Out = 1;
                VZ0 = Mu_Deg * Math.Exp(-(T - T_PL) / (T_PL + 15.0)); 
                double vvv;
                vvv = 8.0;

                VZH = /*Mu1_PL*/ vvv * Math.Exp(-(T - T_PL) / (T_PL - 10.0));  //!!!!!!!!!!!!!!!!!!!! 2018
                V_Z = VZH * Math.Pow(VZH / VZ0, Maths.Min(1.0, F));
                V_Z = VZH * Math.Pow(VZH / VZ0, 4*F);
                //V_Z = 5; // Для ЭЦН5-80-800_Ляп_3                
                
                //return (V_Z * 1e-3);
                //VZ0 = Mu_Deg * Math.Exp(4.96-0.019*(T+273));
                //VZH = Mu_PL * Math.Exp(8.03-0.03*(T+273));
                //V_Z = VZH * Math.Pow(VZ0 / VZH, 1.5 * F);//Maths.Min(1.0, F));
                //V_Z = 6;
                return (V_Z * 1e-3);
            }
            catch
            {
                K_Out = -1;
                return 0.0;
            };
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="DLV"></param>
        /// <param name="T"></param>
        /// <param name="P"></param>
        /// <param name="K_Out">Признак правильности выполнения</param>
        /// <returns></returns>
        public double CH_F(double DLV, double T, double P, ref int K_Out)
        {
            double P_n;
            try
            {
                P_n = PN(T);
                return (C_H(DLV, P_n, T, ref K_Out) * F(P / P_n, T, ref K_Out));
            }
            catch
            {
                K_Out = -1;
                return 0.0;
            };
        }
        #endregion Расчетные ффункции
    }
}
