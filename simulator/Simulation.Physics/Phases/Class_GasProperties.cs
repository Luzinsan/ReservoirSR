using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

using ClassLibrary_Global;

namespace ClassLibrary_PhasesProperties
{
    /// <summary>
    /// Класс свойств газа 
    /// </summary>
    public class Class_GasProperties
    {
        #region Свойства газа
        /// <summary>
        /// Плотность газа при нормальных условиях, кг/м^3
        /// </summary>
        public double R00;
        /// <summary>
        /// Удельная изобарная теплоемкость газа, кДж/(кг*град С)
        /// </summary>
        public double C_P_2;
        ///// <summary>
        ///// Теплопроводность газа, Вт / (м*С)
        ///// </summary>
        //public static double Lmbd2 = 0.02;
        /// <summary>
        /// Молекулярный вес газа
        /// </summary>
        public double VesGMol;
        /// <summary>
        /// Параметр к-та объемной упругости газа, 1/МПа
        /// </summary>
        public double DZT;
        /// <summary>
        /// Параметр к-та теплового расширения газа, 1/град С
        /// </summary>
        public double YTAP2;
        /// <summary>
        /// К-т сверхсжимаемости газа
        /// </summary>
        public double ZG;
        /// <summary>
        /// Радиус пузырьков-зародышей в начале дегазации, мк
        /// </summary>
        public double R_C_R;
        /// <summary>
        /// Счетная концентрация пузырьков-зародышей, тыс.ед/мм^3
        /// </summary>
        public double QUNT_CR;
        /// <summary>
        /// К-т поверхностного натяжения между нефтью и газом, н/м
        /// </summary>
        public double SM;
        /// <summary>
        /// Скрытая теплота растворения газа в нефти, кДж/кг
        /// </summary>
        public double S_T_R;
        /// <summary>
        /// Радиус пузырьков после дробления в ЭЦН
        /// </summary>
        public double RECN;
        /// <summary>
        /// Радиус пузырьков на забое
        /// </summary>
        public double RADZ0;

        #endregion Свойства газа
        
        /// <summary>
        /// Конструктор класса свойств газа
        /// </summary>
        public Class_GasProperties() { }

        /// <summary>
        /// Плотность газа при заданном давлении и температуре, кг/м^3
        /// </summary>
        /// <param name="Pres">Давление, МПа</param>
        /// <param name="Temp">Температура, град С</param>
        /// <returns>Возвращает плотность газа, кг/м^3</returns>
        public double RGAS(double Pres, double Temp)        
        {
            return (Pres * 1e6 * VesGMol / ((Temp + 273.0) * 848.0 * Consts.GE * ZG));
        }

        /// <summary>
        /// Удельная изобарная теплоемкость газа, кДж/(кг*град С)
        /// </summary>
        /// <param name="Temp">Температура, град С</param>
        /// <returns>Возвращает удельную изобарнаю теплоемкость газа, кДж/(кг*град С)</returns>
        public double CP2(double Temp)
        {
            return (C_P_2);
        }
    }
}
