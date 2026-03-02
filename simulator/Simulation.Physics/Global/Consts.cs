using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace ClassLibrary_Global
{
    /// <summary>
    /// Класс констант (статический)
    /// </summary>
    public static class Consts
    {
        #region Физические

        /// <summary>
        /// Ускорение свободного падения (=9.81 м/с^2)
        /// </summary>
        public const double GE = 9.81;          
        /// <summary>
        /// Атмосферное давление (=0.1013 МПа)
        /// </summary>
        public const double P0 = 0.1013;

        private const double Ro_Med = 8900;
        private const double Ro_Stal = 7800;

        /// <summary>
        /// Плотность двигателя (Ср. между медью и сталью)
        /// </summary>
        public const double Ro_PED = 8200;


        private const double Cp_Stal = 0.462; // кДж / (кг * К)
        private const double Cp_Med = 0.385;
        /// <summary>
        /// Удельная теплоемкость двигателя
        /// </summary>
        public const double Cp_PED = 0.8;

        /// <summary>
        /// Теплоемкость двигателя (kДж / (кг * К))
        /// </summary>
        public static double C_PED = Cp_PED * Ro_PED;

        /// <summary>
        /// Максимальная доля газа (=0.9999)
        /// </summary>
        public const double Fi_G = 0.9999;
        /// <summary>
        /// Максимальная доля воды (=1.0)
        /// </summary>
        public const double Fi_W = 1.0; //0.99999;

        /// <summary>
        /// Теплопроводность нефти, Вт / (м*С)
        /// </summary>
        public const double Lmbd1 = 0.12;
        /// <summary>
        /// Теплопроводность газа, Вт / (м*С)
        /// </summary>
        public const double Lmbd2 = 0.02;
        /// <summary>
        /// Теплопроводность воды, Вт / (м*С)
        /// </summary>
        public const double Lmbd3 = 0.65;

        #endregion Физические

        #region Расчетные

        /// <summary>
        /// Вспомогательная переменная для параллельных циклов (=1)
        /// </summary>
        public const int ParAdd = 1;
        /// <summary>
        /// Точность расчета давления (=1e-6)
        /// </summary>
        public const double eps_New = 1e-6;         
        /// <summary>
        /// Максимальное количество итерация по давлению (=20)
        /// </summary>
        public const int Max_It = 20;                  
        /// <summary>
        /// Минимальный диаметр штуцера (=3)
        /// </summary>
        public const int Ds_Min = 3;

        #endregion Расчетные

        #region Режимы

        /// <summary>
        /// Стационарный режим потока в трубе (=false)
        /// </summary>
        public const bool SteadyReg = false;
        /// <summary>
        /// Нестационарный режим потока в трубе (=true)
        /// </summary>
        public const bool UnSteadyReg = true;

        /// <summary>
        /// Водяной поток в трубе (=true)
        /// </summary>
        public const bool WaterFlow = true;
        /// <summary>
        /// Трехфазный поток в трубе (=false)
        /// </summary>
        public const bool AllPhases = false;

        /// <summary>
        /// Пусковой режим (=true)
        /// </summary>
        public const bool Pusk_Reg = true;
        /// <summary>
        /// Рабочий режим (=false)
        /// </summary>
        public const bool Rab_Reg = false;

        
        /// <summary>
        /// Задержки - посекундно (=true)
        /// </summary>
        public const bool Delay_Yes = true;
        /// <summary>
        /// Задержки - быстро (=false)
        /// </summary>
        public const bool Delay_No = false;

        #endregion Режимы
    }
}
