using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace ClassLibrary_Global
{
    /// <summary>
    /// Класс вспомогательных (сервисных) функций (статический)
    /// </summary>
    public static class Service
    {
        /// <summary>
        /// Строковые разделители
        /// </summary>
        public static char[] charSeparators = new char[] { ' ', '|', '¦' };

        /// <summary>
        /// Формат вывода целого числа в строку
        /// </summary>
        /// <param name="Place">Место вывода</param>
        /// <param name="N_C">Количество символов</param>
        /// <returns>Возвращает формат вывода целого числа в строку</returns>
        public static string FormatBuilder(int Place, int N_C)
        {
            return (" {" + Place.ToString() + "," + N_C.ToString() + "}");
        }

        /// <summary>
        /// Формат вывода числа с плавающей запятой в строку
        /// </summary>
        /// <param name="Place">Место вывода</param>
        /// <param name="N_C">Количество символов</param>
        /// <param name="N_D">Количество разрядов после запятой</param>
        /// <returns>Возвращает формат вывода числа с плавающей запятой в строку</returns>
        public static string FormatBuilder(int Place, int N_C, int N_D)
        {
            return (" {" + Place.ToString() + "," + N_C.ToString() + ":F" + N_D.ToString() + "}");
        }

        /// <summary>
        /// Функция склеивания нескольких строк в одну
        /// </summary>
        /// <param name="strs">Массив строк, которые нужно склеить в одну</param>
        /// <returns>Строку <c>string</c></returns>
        public static string MergeStrings(string[] strs)
        {
            // Склеиваем строки в одну
            StringBuilder sb = new StringBuilder();
            foreach (string line in strs)
                sb.AppendLine(line);
            return sb.ToString();
        }

        public static string DigitToSubscript(int Digit)
        {
            switch (Digit)
            {
                case 0: return"₀";
                case 1: return"₁";
                case 2: return"₂";
                case 3: return"₃";
                case 4: return"₄";
                case 5: return"₅";
                case 6: return"₆";
                case 7: return"₇";
                case 8: return"₈";
                case 9: return"₉";
                default: return"";
            }            
        }

        public static string DigitToSuperscript(int Digit)
        {
            switch (Digit)
            {
                case 0: return"⁰";
                case 1: return"¹";
                case 2: return"²";
                case 3: return"³";
                case 4: return"⁴";
                case 5: return"⁵";
                case 6: return"⁶";
                case 7: return"⁷";
                case 8: return"₈";
                case 9: return "⁹";
                default: return "";
            }            
        }
    }
}
