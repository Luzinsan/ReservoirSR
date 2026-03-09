using System;
using System.Collections.Generic;

namespace ClassLibrary_FissuredPorousOilReservoir;

public partial class ReservoirSimulationEngine
{
    public void ExportFieldTo(string fieldName, IList<double> destination)
    {
        string key = fieldName.Trim().ToUpperInvariant();
        switch (key)
        {
            case "P": CopyFieldForExport(P, destination); break;
            case "P0": CopyFieldForExport(P_0, destination); break;
            case "ST": CopyFieldForExport(ST, destination); break;
            case "SB": CopyFieldForExport(SB, destination); break;
            case "WT": CopyFieldForExport(WT, destination); break;
            case "WB": CopyFieldForExport(WB, destination); break;
            case "AX": CopyFieldForExport(AX, destination); break;
            case "AV": CopyFieldForExport(AV, destination); break;
            case "KABX": CopyFieldForExport(Kabx, destination); break;
            case "KABZ": CopyFieldForExport(Kabz, destination); break;
            case "AVST": CopyFieldForExport(AVST, destination); break;
            case "AVSB": CopyFieldForExport(AVSB, destination); break;
            case "AT": CopyFieldForExport(AT, destination); break;
            case "AB": CopyFieldForExport(AB, destination); break;
            case "BT": CopyFieldForExport(BT, destination); break;
            case "BB": CopyFieldForExport(BB, destination); break;
            case "BVT": CopyFieldForExport(BVT, destination); break;
            case "BVB": CopyFieldForExport(BVB, destination); break;
            case "CBET": CopyFieldForExport(CBet, destination); break;
            default: throw new ArgumentOutOfRangeException(nameof(fieldName), $"Unknown field: {fieldName}");
        }
    }

    private void CopyFieldForExport(double[] source, IList<double> destination)
    {
        bool isDynamic = !destination.IsReadOnly && !(destination is Array);
        if (isDynamic) destination.Clear();

        int idx = 0;
        for (int kz = 1; kz <= NZ; kz++)
        {
            for (int ix = 1; ix <= NX; ix++)
            {
                int m = kz + ix * NZ;
                if (isDynamic)
                {
                    destination.Add(source[m]);
                }
                else
                {
                    destination[idx++] = source[m];
                }
            }
        }
    }
}
