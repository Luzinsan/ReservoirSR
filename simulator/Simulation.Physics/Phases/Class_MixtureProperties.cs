using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

using System.IO;

using System.Threading;

using ClassLibrary_Global;

namespace ClassLibrary_PhasesProperties
{
    /// <summary>
    /// Класс свойств трехфазной смеси
    /// </summary>
    public class Class_MixtureProperties
    {
        /// <summary>
        /// Свойства нефти
        /// </summary>
        public Class_OilProperties OilProperties;
        /// <summary>
        /// Свойства воды
        /// </summary>
        public Class_WaterProperties WaterProperties;

        /// <summary>
        /// Разделитель для процедур чтения
        /// </summary>
        private char[] charSeparators = new char[] { ' ' };

        /// <summary>
        /// Конструктор класса свойств трехфазной смеси с базовыми данными
        /// </summary>
        public Class_MixtureProperties()
        {
            OilProperties = new Class_OilProperties();
            WaterProperties = new Class_WaterProperties();            
        }

        /// <summary>
        /// Конструктор класса свойств трехфазной смеси с чтением данных из файла
        /// </summary>
        /// <param name="FileName">Имя файла</param>
        public Class_MixtureProperties(string FileName)
        {
            OilProperties = new Class_OilProperties();
            WaterProperties = new Class_WaterProperties();

            LoadFromFile(FileName);
        }


        /// <summary>
        /// Присваивание пластовых давления и температуры
        /// </summary>
        /// <param name="P_PL">Пластовое давление</param>
        /// <param name="T_PL">Пластовая температура</param>
        public void Set_PpL_Tpl(double P_PL, double T_PL)
        {
            OilProperties.P_PL = P_PL;
            WaterProperties.P_PL = P_PL;

            OilProperties.T_PL = T_PL;
            WaterProperties.T_PL = T_PL;
        }

        /// <summary>
        /// Инициализация переменных базовыми данными
        /// </summary>
        public void ReferenceData()
        {
            ////=======================================                
            OilProperties.Ro1_PL = 806.0;
            OilProperties.Ro1_deg = 870.0;
            //OilProperties.Mu1_PL = 5.7;
            OilProperties.Mu1_PL = 40.0;
            OilProperties.Mu_Deg = 26.0;
            OilProperties.AP1 = 0.0009;
            OilProperties.AT1 = 0.00125;
            OilProperties.C_P_1 = 1.88;
            ////=======================================
            WaterProperties.Ro3_PL = 1160.0;
            WaterProperties.Mu3_PL = 1.6;            
            WaterProperties.C_P_3 = 4.15;
            WaterProperties.AP3 = 0.0004;
            WaterProperties.AT3 = 0.0008;
            //=======================================
            OilProperties.GasProperties.R00 = 1.12;
            OilProperties.GasProperties.C_P_2 = 2.7; 
            OilProperties.GasProperties.VesGMol = 16.04;
            OilProperties.GasProperties.YTAP2 = 0.0008;
            OilProperties.GasProperties.DZT = 0.0035;
            OilProperties.GasProperties.ZG = 0.941;
            //=======================================
            OilProperties.VG0 = 40.0;
            OilProperties.PH0 = 12.0;
            OilProperties.BT = 0.02;
            OilProperties.BG = 0.004; //Газовый фактор
            OilProperties.GasProperties.R_C_R = 1.0;
            OilProperties.GasProperties.QUNT_CR = 140.0;
            OilProperties.GasProperties.RADZ0 = 6.0;
            OilProperties.GasProperties.SM = 0.025;
            OilProperties.GasProperties.S_T_R = 167.5;
            //=======================================
        }

        /// <summary>
        /// Инициализация переменных базовыми данными для теста насосов
        /// </summary>
        public void ReferenceData_ECP_Test_1()
        {
            ////=======================================                
            OilProperties.Ro1_PL = 800.0;       //|||806
            OilProperties.Ro1_deg = 850.0;      //|||870
            OilProperties.AP1 = 0.0009;         //|||
            OilProperties.AT1 = 0.0015;         //|||
            OilProperties.C_P_1 = 1.88;         //|||
            ////=======================================
            WaterProperties.Ro3_PL = 1020.0;        //||| 1020.0;
            WaterProperties.Mu3_PL = 1.05;           //||| 1.5
            WaterProperties.C_P_3 = 4.15;           //|||
            WaterProperties.AP3 = 0.0004;           //|||
            WaterProperties.AT3 = 0.0008;           //|||
            //WaterProperties.AP3 = 0.0009;         //||| Было до 02.03.15
            //WaterProperties.AT3 = 0.0015;         //||| Было до 02.03.15
            //=======================================
            OilProperties.GasProperties.R00 = 0.716;        //|||
            OilProperties.GasProperties.C_P_2 = 2.7;        //|||
            OilProperties.GasProperties.VesGMol = 16.04;    //|||
            OilProperties.GasProperties.YTAP2 = 0.0008;     //|||
            OilProperties.GasProperties.DZT = 0.00035;      //|||
            OilProperties.GasProperties.ZG = 0.94;          //|||
            //=======================================
            OilProperties.VG0 = 52;   //Газовый фактор     //|||
            OilProperties.PH0 = 8.0;                         //|||
            OilProperties.BT = 0.02;                         //|||
            OilProperties.BG = 0.003;                        //|||
            OilProperties.GasProperties.R_C_R = 1.0;         //|||
            OilProperties.GasProperties.QUNT_CR = 140.0;     //|||
            OilProperties.GasProperties.RADZ0 = 6.0;         //|||
            OilProperties.GasProperties.SM = 0.025;          //|||
            OilProperties.GasProperties.S_T_R = 167.5;       //|||
            //=======================================
        }

        /// <summary>
        /// Инициализация переменных данными из файла
        /// </summary>
        /// <param name="FileName">Имя файла</param>
        public void LoadFromFile(string FileName)
        {
            Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";

            string[] str;

            StreamReader fff = new StreamReader(File.Open(FileName, FileMode.Open), Encoding.Default);
            
            // Свойства нефтяной фазы  ---------------------------
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.Ro1_PL);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.Mu_Deg);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.Mu1_PL);            
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.C_P_1);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.AP1);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.AT1);
            // Свойства водяной фазы  -----------------------------
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out WaterProperties.Ro3_PL);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out WaterProperties.C_P_3);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out WaterProperties.AP3);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out WaterProperties.AT3);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out WaterProperties.Mu3_PL);            
            // Свойства газовой фазы  -----------------------------
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);            
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.R00);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.C_P_2);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.Ro1_deg);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.VesGMol);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.DZT);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.YTAP2);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.ZG);
            // Параметры процесса разгазирования  ------------
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.VG0);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.PH0);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.BT);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.BG);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.R_C_R);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.QUNT_CR);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.SM);
            str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
            double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.S_T_R);
            //======================================================

            fff.Close();
        }

        /// <summary>
        /// Инициализация переменных данными из файлового потока
        /// </summary>
        /// <param name="FileName">Файловый поток</param>
        public void LoadFromStream(ref StreamReader fff, ref int Error)
        {
            try
            {
                Error = 0;
                Thread.CurrentThread.CurrentCulture.NumberFormat.NumberDecimalSeparator = ".";

                string[] str;

                // Свойства нефтяной фазы  ---------------------------
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.Ro1_PL);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.Mu_Deg);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.Mu1_PL);                
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.C_P_1);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.AP1);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.AT1);
                // Свойства водяной фазы  -----------------------------
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out WaterProperties.Ro3_PL);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out WaterProperties.C_P_3);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out WaterProperties.AP3);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out WaterProperties.AT3);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out WaterProperties.Mu3_PL);                
                // Свойства газовой фазы  -----------------------------
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.R00);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.C_P_2);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.Ro1_deg);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.VesGMol);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.DZT);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.YTAP2);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.ZG);
                // Параметры процесса разгазирования  ------------
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.VG0);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.PH0);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.BT);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.BG);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.R_C_R);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.QUNT_CR);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.SM);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                double.TryParse(str[str.Length - 1], out OilProperties.GasProperties.S_T_R);
                str = fff.ReadLine().Split(charSeparators, StringSplitOptions.RemoveEmptyEntries);
                //======================================================            
            }
            catch
            {
                Error = 1;
            }
        }


        /// <summary>
        /// Запись значений переменных в файловый поток
        /// </summary>
        /// <param name="fff">Файловый поток</param>
        public void SaveToStream(ref StreamWriter fff)
        {
            fff.WriteLine("-------------------------  Параметры нефтяной фазы  -------------------------");
            fff.WriteLine(" Плотность нефти в пластовых условиях              ¦   кг/м^3  ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.Ro1_PL);
            fff.WriteLine(" Вязкость дегазированной нефти при норм. условиях  ¦    мПа*с  ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.Mu_Deg);
            fff.WriteLine(" Вязкость нефти в пластовых условиях               ¦    мПа*с  ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.Mu1_PL);
            fff.WriteLine(" Удельная изобарная теплоемкость нефти       ¦ кДж/(кг*град С) ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.C_P_1);
            fff.WriteLine(" К-т теплового расширения нефти                    ¦ 1/град С  ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.AP1);
            fff.WriteLine(" К-т объемной упругости нефти                      ¦   1/МПа   ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.AT1);
            fff.WriteLine("-------------------------  Параметры водяной фазы  --------------------------");
            fff.WriteLine(" Плотность воды в пластовых условиях               ¦   кг/м^3  ¦ " + Service.FormatBuilder(0, 12, 6), WaterProperties.Ro3_PL);
            fff.WriteLine(" Удельная изобарная теплоемкость воды        ¦ кДж/(кг*град С) ¦ " + Service.FormatBuilder(0, 12, 6), WaterProperties.C_P_3);
            fff.WriteLine(" К-т теплового расширения воды                     ¦ 1/град С  ¦ " + Service.FormatBuilder(0, 12, 6), WaterProperties.AP3);
            fff.WriteLine(" К-т объемной упругости воды                       ¦   1/МПа   ¦ " + Service.FormatBuilder(0, 12, 6), WaterProperties.AT3);
            fff.WriteLine(" К-т динамической вязкости воды                    ¦   мПа*с   ¦ " + Service.FormatBuilder(0, 12, 6), WaterProperties.Mu3_PL);
            fff.WriteLine("-------------------------  Параметры газовой фазы  --------------------------");
            fff.WriteLine(" Плотность газа при нормальных условиях            ¦   кг/м^3  ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.GasProperties.R00);
            fff.WriteLine(" Удельная изобарная теплоемкость газа        ¦ кДж/(кг*град С) ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.GasProperties.C_P_2);
            fff.WriteLine(" Плотность дегазированной нефти при норм.усл.      ¦   кг/м^3  ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.Ro1_deg);            
            fff.WriteLine(" Молекулярный вес газа                                         ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.GasProperties.VesGMol);
            fff.WriteLine(" Параметр к-та объемной упругости газа             ¦   1/МПа   ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.GasProperties.DZT);
            fff.WriteLine(" Параметр к-та теплового расширения газа           ¦ 1/град С  ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.GasProperties.YTAP2);
            fff.WriteLine(" К-т сверхсжимаемости газа                                     ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.GasProperties.ZG);
            fff.WriteLine("-----------------  Параметры процесса разгазирования нефти  -----------------");
            fff.WriteLine(" Газовый фактор Vo пластовой нефти при норм.усл.   ¦  м^3/м^3  ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.VG0);
            fff.WriteLine(" Давление Pно насыщения нефти газом при н.усл.     ¦    МПа    ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.PH0);
            fff.WriteLine(" К-т B температурной зависимости Pн=Pно+B*(t-to)   ¦ МПа/град С¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.BT);
            fff.WriteLine(" К-т A температурной зависимости Vг=Vо(1+A(t-to))  ¦  1/град С ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.BG);
            fff.WriteLine(" Радиус пузырьков-зародышей в начале дегазации     ¦     мк    ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.GasProperties.R_C_R);
            fff.WriteLine(" Счетная концентрация пузырьков-зародышей          ¦тыс.ед/мм^3¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.GasProperties.QUNT_CR);
            fff.WriteLine(" К-т поверхностного натяжения между нефтью и газом ¦    н/м    ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.GasProperties.SM);
            fff.WriteLine(" Скрытая теплота растворения газа в нефти          ¦   кДж/кг  ¦ " + Service.FormatBuilder(0, 12, 6), OilProperties.GasProperties.S_T_R);
            fff.WriteLine("=============================================================================");
        }

        
        /// <summary>
        /// ???
        /// </summary>
        /// <param name="Re">??</param>
        /// <param name="Fist">??</param>
        /// <returns>??</returns>
        public double CoZuber(double Re, double Fist)
        {
            return (1.05); //if Fist>0.7 then Result:=1.2;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="A"></param>
        /// <param name="X"></param>
        /// <returns></returns>
        public double Fst( double A, double X)
        {
            return(1.0/(Maths.Sqr(1-A)*(1-A))*(A*A*(3-A)-X*(6*A-3*(1+A)*X+2*X*X)));
        }

        /// <summary>
        /// Параметр Зубера C0
        /// </summary>
        /// <param name="Fi_"></param>
        /// <param name="Re_"></param>
        /// <returns>Возвращает значение параметра Зубера C0</returns>
        public double C0_Param(double Fi_, double Re_)
        {
            const double
                Fi1 = 0.56,
                Fi2 = 0.64,
                ReA = 8500,
                ReB = 12500;            
                      
            if (Fi_==0) return (1.0);

            if ((Fi_ <= Fi1) && (Re_ <= ReA))            
               return(1.08);
            
            if ((Fi_ <= Fi1) && (Re_ >= ReB))            
               return(1.0);
            
            if ( Fi_ >= Fi2)
                return(1.2);            
                ////////////////////////////////
            if ( Re_ <= ReA )                            
                return( 1.08 + 0.12 * Fst(0.875, Fi_/Fi2));                  
            
            if ( Re_ >= ReB )                            
                return(1 + 0.2 * Fst(0.875, Fi_/Fi2));                
            
            if ( Fi_ <= Fi1 )                
                return(1.08 - 0.08 * Fst(0.68, Re_ /ReB));                
            
            if ( Fi_ <= Fi2 )
            {
                double X = Fi_/Fi2;
                double RB = Fst(0.875, X);
                double Y = Re_/ReB;
                return(1.08 + 0.12 * RB - 0.08 * Fst(0.68,Y)*(1-RB));
            }

            return 1.0;
        }
        
        /// <summary>
        /// Вязкость трехфазной смеси
        /// </summary>
        /// <param name="F_g"></param>
        /// <param name="F_w"></param>
        /// <param name="Pres">Давление</param>
        /// <param name="Temp">Температура</param>
        /// <param name="F_P"></param>
        /// <param name="K_Out">Признак правильности выполнения</param>
        /// <returns>Возвращает вязкость трехфазной смеси, кг/(м*сек)</returns>
        /// <remarks>Размерность = кг/(м*сек), вязкость уже умножена на 10-3</remarks>
        public double VIS_3FASE (double F_g, double F_w, double Pres, double Temp, double F_P, ref int K_Out)
        {
        	double XI, Bsum, Mu_DinSM, VS;
        	// Mu_DinSM:=Vis_Oil(Temp,F_P, K_Out);
        	if (F_w<=0.0)  // газонефтяной поток
        	{
                VS=OilProperties.Vis_Oil (Temp,F_P, ref K_Out);
                Mu_DinSM=VS*VIS(F_g);                
                //Mu_DinSM = VS * VIS_SIMHA(F_g, 0, 1.0);
                //Mu_DinSM = VS * Math.Pow((1.0-F_g), -3);
        	}
            else // водонефтегазовый поток
        	{
                if (F_w <= 0.5) // нефть - несущая фаза  // 0.66 для теста насоса!!!!!!!!!!!!!!!!!!!!!!!!!
        		{
                   VS=OilProperties.Vis_Oil (Temp,F_P,ref K_Out);
        		   Bsum=F_w;
                   XI=WaterProperties.Vis_H2O(Pres,Temp)/VS;
        		   Mu_DinSM=VS*VIS(Bsum);                   
                   //Mu_DinSM=VS*VIS_SIMHA (Bsum,XI,1.0);
                   // обычнпя формула
        		}
                else // вода - несущая фаза
        		{
                   Bsum=1.0-F_w;
                   if (Bsum<0.0) Bsum=0.0;
                   VS = WaterProperties.Vis_H2O(Pres, Temp);
                   XI = OilProperties.Vis_Oil(Temp, F_P, ref K_Out) / VS;
        		   Mu_DinSM=VS*VIS(Bsum);
                   //Mu_DinSM=VS*VIS_SIMHA (Bsum,XI,1.0);                      
                   // твердые шарики
        		};
        	};
        	return(Mu_DinSM);
            // размерность = кг/(м*сек), вязкость уже умножена на 10-3
        } 
        
        /// <summary>
        /// 
        /// </summary>
        /// <param name="F"></param>
        /// <returns></returns>
        public double VIS (double F)
        {
            const double F_Max = 0.5;
        	const double Deg=-1.5;
        	double Rab;
        
        	if (F<=0.0)  return(1.0);
        	if (F<=F_Max)
        	{
        		Rab=Math.Pow(F_Max,7.0/3.0);
        		Rab=1.0+0.55*F*(4.0-60.0/11.0*Rab)/((1.0-F)*(1.0-Rab));
        		return(Rab);
        	}
            else
        	{
        		Rab=Math.Pow(F_Max,7.0/3.0);
        		Rab=1.0+0.55*F_Max*(4.0-60.0/11.0*Rab)/((1.0-F_Max)*(1.0-Rab));
        		Rab=Rab*Math.Pow((1.0-(F-F_Max)),Deg);
        		return(Rab);
        	};
        }

        /// <summary>
        /// Вязкость Симхи
        /// </summary>
        /// <param name="F"></param>
        /// <param name="XI"></param>
        /// <param name="SLD"></param>
        /// <returns></returns>
        public double VIS_SIMHA (double F, double XI, double SLD)
        {
        	double R5, R7, R10, Rab;
        	if (F<=0.0) return(1.0);
        	R5 =Math.Pow(F, 5.0/3.0);
        	R7 =Math.Pow(F, 7.0/3.0);
        	R10=Math.Pow(F, 10.0/3.0);
        	Rab=XI*(4.0*(1.0+R10)-25.0*(F+R7)+42.0*R5);
        	Rab=Rab+SLD*(4.0*(1.0-R10)-10.0*(F-R7));
        	Rab=1.0+F*(XI*10.0*(1.0-R7)+SLD*(4.0+10.0*R7))/Rab;
        	return(Rab);
        }

        /// <summary>
        /// ???
        /// </summary>
        /// <param name="Q_liq"></param>
        /// <param name="Fi"></param>
        /// <param name="Ro1"></param>
        /// <param name="Ro2"></param>
        /// <param name="W"></param>
        /// <param name="T"></param>
        /// <param name="P"></param>
        /// <param name="K_Out">Признак правильности выполнения</param>
        /// <returns></returns>
        public double Dlt_Drift (double Q_liq, double Fi, double Ro1, double Ro2, double W, double T,
        	double P, ref int K_Out)
        {
        	double V, FP, Rad, Dlt;
        	try
        	{
        		K_Out=1;
        /*{Rad:=RECN*1e-6;
        FP:=F(P/PN(T),T, K_Out);
        Result:=0;
        if FP=0 then Exit;
        if (w<>0) and (Q_liq<>0) then  begin
        V:=Vis_Oil(T,FP, K_Out);
        if K_Out=-1 then Exit;
        V:=Sqr(RAD)*GE*(Ro1-Ro2)*(1-Fi/2)/(3*V*(1+4*Fi)*W);
        Result:=V/(V+0.6*Q_liq/(Pi*(Sqr(RD1)-Sqr(RD0))));
                                        end
                                 else Result:=1;}*/
        		return(0.0);
        	}
        	catch
        	{
        		K_Out=-1;
                return 0.0;
        	};        
        }        
    }
}
