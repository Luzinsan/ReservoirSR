using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace ClassLibrary_Global
{
    /// <summary>
    /// Класс математических функций (статичесикий)
    /// </summary>
    public static class Maths
    {
        /// <summary>
        /// Класс, выдающий произвольное число
        /// </summary>
        private static Random Randomizer = new Random();

        #region double

        /// <summary>
        /// Модуль числа <c>double</c>
        /// </summary>
        /// <param name="x">Число</param>
        /// <returns>Модуль числа</returns>
        public static double Abs(double x)
        {
            if (x >= 0.0) return x;
            else return -x;
        }

        /// <summary>
        /// Максимум из двух <c>double</c> чисел
        /// </summary>
        /// <param name="x">Первое число</param>
        /// <param name="y">Второе число</param>
        /// <returns>Максимум</returns>
        public static double Max(double x, double y)
        {
            if (x >= y) return x;
            else return y;
        }

        /// <summary>
        /// Минимум из двух <c>double</c> чисел
        /// </summary>
        /// <param name="x">Первое число</param>
        /// <param name="y">Второе число</param>
        /// <returns>Минимум</returns>
        public static double Min(double x, double y)
        {
            if (x <= y) return x;
            else return y;
        }

        /// <summary>
        /// Квадрат числа <c>double</c>
        /// </summary>
        /// <param name="x">Число</param>
        /// <returns>Квадрат числа</returns>
        public static double Sqr(double x)
        {
            return x * x;
        }

        #endregion double

        #region int

        /// <summary>
        /// Эквивалент функции Random в Delphi
        /// </summary>
        /// <param name="x">Максимальное значение</param>
        /// <returns>Возвращает произвольное int от 0 до max</returns>
        public static int Random(int max)
        {
            return Randomizer.Next(max);
        }

        /// <summary>
        /// Модуль числа <c>int</c>
        /// </summary>
        /// <param name="x">Число</param>
        /// <returns>Модуль числа</returns>
        public static int Abs(int x)
        {
            if (x >= 0) return x;
            else return -x;
        }

        /// <summary>
        /// Максимум из двух <c>int</c> чисел
        /// </summary>
        /// <param name="x">Первое число</param>
        /// <param name="y">Второе число</param>
        /// <returns>Максимум</returns>
        public static int Max(int x, int y)
        {
            if (x >= y) return x;
            else return y;
        }

        /// <summary>
        /// Минимум из двух <c>int</c> чисел
        /// </summary>
        /// <param name="x">Первое число</param>
        /// <param name="y">Второе число</param>
        /// <returns>Минимум</returns>
        public static int Min(int x, int y)
        {
            if (x <= y) return x;
            else return y;
        }

        /// <summary>
        /// Квадрат числа <c>int</c>
        /// </summary>
        /// <param name="x">Число</param>
        /// <returns>Квадрат числа</returns>
        public static int Sqr(int x)
        {
            return x * x;
        }

        #endregion int
    }
}
