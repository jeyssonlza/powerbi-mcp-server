"""Explora un archivo Excel: hojas, columnas, tipos y muestra de datos."""

from __future__ import annotations

import sys

import pandas as pd


def main(path: str) -> int:
    xls = pd.ExcelFile(path)
    print(f"ARCHIVO: {path}")
    print(f"HOJAS ({len(xls.sheet_names)}): {xls.sheet_names}\n")

    for sheet in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet)
        print("=" * 80)
        print(f"HOJA: {sheet}  ->  {df.shape[0]} filas x {df.shape[1]} columnas")
        print("=" * 80)
        for col in df.columns:
            dtype = str(df[col].dtype)
            nn = int(df[col].notna().sum())
            distinct = int(df[col].nunique())
            sample = df[col].dropna().head(3).tolist()
            sample_str = ", ".join(str(s)[:30] for s in sample)
            print(f"  - {col!s:35} | {dtype:12} | nn={nn:5} | distintos={distinct:5} | ej: {sample_str}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
