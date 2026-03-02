using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

using ClassLibrary_Global;

namespace ClassLibrary_PhasesProperties
{
    /// <summary>
    /// Класс свойств воды
    /// </summary>
    public class Class_WaterProperties
    {
        #region Свойства воды
        /// <summary>
        /// Плотность воды в пластовых условиях, кг/м^3
        /// </summary>
        public double Ro3_PL;
        /// <summary>
        /// Пластовая температура, град С
        /// </summary>
        public double T_PL;
        /// <summary>
        /// Пластовое давление, МПа
        /// </summary>
        public double P_PL;
        /// <summary>
        /// Удельная изобарная теплоемкость воды, кДж/(кг*град С)
        /// </summary>
        public double C_P_3;
        ///// <summary>
        ///// Теплопроводность воды, Вт / (м*С)
        ///// </summary>
        //public static double Lmbd3 = 0.65;
        /// <summary>
        /// К-т теплового расширения воды, 1/град С
        /// </summary>
        public double AP3;
        /// <summary>
        /// К-т объемной упругости воды, 1/МПа
        /// </summary>
        public double AT3;
        /// <summary>
        /// К-т динамической вязкости воды, мПа*с
        /// </summary>
        public double Mu3_PL;      

        #endregion Свойства воды

        /// <summary>
        /// Плотность воды при заданном давлении и температуре, кг/м^3
        /// </summary>
        /// <param name="Pres">Давление, МПа</param>
        /// <param name="Temp">Температура, град С</param>
        /// <returns>Возвращает плотность воды, кг/м^3</returns>
        public double RH2O(double Pres, double Temp)
        {
            return (Ro3_PL * (1.0 - AP3 * (Temp - T_PL) + AT3 * (Pres - P_PL)));
        }

        /// <summary>
        /// К-т динамической вязкости воды при заданном давлении и температуре, Па*с
        /// </summary>
        /// <param name="P">Давление, Мпа</param>
        /// <param name="T">Температура, град С</param>
        /// <returns>Возвращает к-т динамической вязкости воды, Па*с</returns>
        public double Vis_H2O(double P, double T)
        {
            return (Mu3_PL * 1e-3);
        }

        /// <summary>
        /// Удельная изобарная теплоемкость воды при заданной температуре, кДж/(кг*град С)
        /// </summary>
        /// <param name="Temp">Температура, град С</param>
        /// <returns>Возвращает удельную изобарную теплоемкость воды, кДж/(кг*град С)</returns>
        public double CP3(double Temp)
        {
            return (C_P_3);
        }
    }
}
