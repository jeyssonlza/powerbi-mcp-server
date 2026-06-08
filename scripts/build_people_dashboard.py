"""Generador de dashboard HTML interactivo de People Analytics (NGN / Necta).

Lee el Excel de indicadores de P&C, limpia los datos, calcula KPIs y medidas
(incluyendo varias NUEVAS respecto al modelo original) y produce un dashboard
HTML autónomo e interactivo (Plotly) con tema corporativo verde.

Incluye 3 análisis de IA usando el propio servidor MCP:
  - Detección de anomalías salariales (Isolation Forest / IQR)
  - Clustering de empleados por perfil (edad, salario, antigüedad)
  - Correlaciones entre variables numéricas

Uso:
    python scripts/build_people_dashboard.py "<ruta xlsx>" "<carpeta salida>"
"""

from __future__ import annotations

import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

warnings.filterwarnings("ignore")

# --- Tema corporativo (verde Necta) ----------------------------------------
C = {
    "primary": "#1B7A3D",      # verde Necta
    "primary_dark": "#0E4D26",
    "accent": "#7DC242",       # verde claro
    "accent2": "#2EA6A6",      # teal
    "warn": "#E8A33D",
    "danger": "#D9534F",
    "ink": "#1f2d27",
    "muted": "#6b7c74",
    "bg": "#f4f7f5",
    "card": "#ffffff",
}
SEQ = ["#1B7A3D", "#7DC242", "#2EA6A6", "#4FB477", "#A7D88A", "#0E4D26", "#E8A33D", "#9bc1a8"]
REF_DATE = pd.Timestamp("2026-06-05")

pio.templates.default = "plotly_white"


# ===========================================================================
# Carga y limpieza
# ===========================================================================
def _clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    return df


def load_data(xlsx: str) -> dict[str, pd.DataFrame]:
    """Carga las hojas relevantes del Excel y normaliza encabezados."""
    sheets = ["Funcionarios", "Diversidade", "Banco de Horas", "Horas Extras", "Headcount"]
    data: dict[str, pd.DataFrame] = {}
    for s in sheets:
        try:
            data[s] = _clean_cols(pd.read_excel(xlsx, sheet_name=s))
        except Exception as exc:  # noqa: BLE001
            print(f"  ! No se pudo leer hoja {s}: {exc}")
    return data


def prepare_employees(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara la tabla de funcionarios con campos derivados (edad, tenure...)."""
    df = df.copy()
    df["Admissão"] = pd.to_datetime(df.get("Admissão"), errors="coerce")
    df["Data Nascimento"] = pd.to_datetime(df.get("Data Nascimento"), errors="coerce")
    df["Data  Desligamento"] = pd.to_datetime(df.get("Data  Desligamento"), errors="coerce")
    df["Salário"] = pd.to_numeric(df.get("Salário"), errors="coerce")

    df["Ativo"] = df.get("Status Funcionário", "").astype(str).str.upper().eq("ATV")
    df["Idade"] = ((REF_DATE - df["Data Nascimento"]).dt.days / 365.25).round(1)
    fim = df["Data  Desligamento"].fillna(REF_DATE)
    df["Tenure"] = ((fim - df["Admissão"]).dt.days / 365.25).round(2)
    df["AnoAdmissao"] = df["Admissão"].dt.year
    df["AnoDesligamento"] = df["Data  Desligamento"].dt.year

    motivo = df.get("Motivo Rescisao", "").astype(str).str.lower()
    df["TipoSaida"] = np.where(
        df["Data  Desligamento"].notna(),
        np.where(motivo.str.contains("volunt"), "Voluntário", "Involuntário"),
        "",
    )

    bins = [0, 25, 35, 45, 55, 120]
    labels = ["18-25", "26-35", "36-45", "46-55", "56+"]
    df["FaixaEtaria"] = pd.cut(df["Idade"], bins=bins, labels=labels)
    return df


# ===========================================================================
# KPIs y nuevas medidas
# ===========================================================================
def compute_kpis(emp: pd.DataFrame) -> list[dict]:
    """Calcula los KPIs principales (incluye medidas nuevas)."""
    activos = emp[emp["Ativo"]]
    hc = len(activos)
    admit = int(emp["Admissão"].notna().sum())
    deslig = int(emp["Data  Desligamento"].notna().sum())
    headcount_medio = (hc + (hc + deslig)) / 2 or 1
    turnover = round(((emp[emp["Data  Desligamento"].notna()].shape[0]) / (hc + deslig)) * 100, 1)

    folha = activos["Salário"].sum()
    sal_medio = activos["Salário"].mean()
    sal_mediana = activos["Salário"].median()
    idade_media = activos["Idade"].mean()
    tenure_medio = activos["Tenure"].mean()

    # Nuevas medidas de diversidad
    pct_mujeres = (activos.get("Sexo", pd.Series(dtype=str)).astype(str).str.upper().eq("F").mean()) * 100
    pcd_col = activos.get("Pessoa com deficiência - PCD", pd.Series(dtype=str)).astype(str).str.upper()
    pct_pcd = pcd_col.str.startswith("S").mean() * 100
    lgbt_col = activos.get("Parte da comunidade LGBTQIAPN+", pd.Series(dtype=str)).astype(str).str.upper()
    pct_lgbt = lgbt_col.str.startswith("S").mean() * 100

    def card(label, value, sub=""):
        return {"label": label, "value": value, "sub": sub}

    return [
        card("Headcount Ativo", f"{hc:,}".replace(",", "."), "colaboradores"),
        card("Admissões", f"{admit:,}".replace(",", "."), "histórico"),
        card("Desligamentos", f"{deslig:,}".replace(",", "."), "histórico"),
        card("Turnover", f"{turnover:.1f}%", "acumulado"),
        card("Folha Salarial", f"R$ {folha/1000:,.0f}k".replace(",", "."), "ativos"),
        card("Salário Médio", f"R$ {sal_medio:,.0f}".replace(",", "."), "ativos"),
        card("Idade Média", f"{idade_media:.1f}", "anos"),
        card("Tempo de Casa", f"{tenure_medio:.1f}", "anos médio"),
        card("% Mulheres", f"{pct_mujeres:.1f}%", "diversidade ★"),
        card("% PCD", f"{pct_pcd:.1f}%", "inclusão ★"),
        card("% LGBTQIA+", f"{pct_lgbt:.1f}%", "diversidade ★"),
        card("Mediana Salarial", f"R$ {sal_mediana:,.0f}".replace(",", "."), "novo ★"),
    ]


# ===========================================================================
# Gráficos
# ===========================================================================
def _style(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=48, b=10),
        font=dict(family="Segoe UI, system-ui, sans-serif", color=C["ink"], size=12),
        title_font=dict(size=15, color=C["primary_dark"]),
        colorway=SEQ,
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
    )
    return fig


def fig_movimentacao(emp: pd.DataFrame) -> go.Figure:
    adm = emp.dropna(subset=["AnoAdmissao"]).groupby("AnoAdmissao").size()
    des = emp.dropna(subset=["AnoDesligamento"]).groupby("AnoDesligamento").size()
    years = sorted(set(adm.index) | set(des.index))
    fig = go.Figure()
    fig.add_bar(x=years, y=[int(adm.get(y, 0)) for y in years], name="Admissões", marker_color=C["accent"])
    fig.add_bar(x=years, y=[-int(des.get(y, 0)) for y in years], name="Desligamentos", marker_color=C["danger"])
    fig.add_scatter(
        x=years,
        y=[int(adm.get(y, 0)) - int(des.get(y, 0)) for y in years],
        name="Saldo líquido", mode="lines+markers", line=dict(color=C["primary_dark"], width=3),
    )
    fig.update_layout(title="Movimentação de Pessoal por Ano", barmode="relative")
    return _style(fig)


def fig_headcount_area(emp: pd.DataFrame) -> go.Figure:
    activos = emp[emp["Ativo"]]
    col = "Centro de custo" if "Centro de custo" in activos else "Cargo"
    top = activos[col].value_counts().head(12).sort_values()
    fig = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h", marker_color=C["primary"]))
    fig.update_layout(title=f"Headcount Ativo por {col}")
    return _style(fig, height=380)


def fig_turnover_tipo(emp: pd.DataFrame) -> go.Figure:
    saidas = emp[emp["TipoSaida"] != ""]
    counts = saidas["TipoSaida"].value_counts()
    fig = go.Figure(go.Pie(
        labels=counts.index, values=counts.values, hole=0.55,
        marker=dict(colors=[C["warn"], C["danger"]]),
    ))
    fig.update_layout(title="Desligamentos: Voluntário vs Involuntário")
    return _style(fig)


def fig_piramide(emp: pd.DataFrame) -> go.Figure:
    activos = emp[emp["Ativo"]].copy()
    sexo = activos.get("Sexo", pd.Series(dtype=str)).astype(str).str.upper()
    activos = activos.assign(Sexo=sexo)
    order = ["18-25", "26-35", "36-45", "46-55", "56+"]
    h = activos[activos["Sexo"] == "M"]["FaixaEtaria"].value_counts().reindex(order, fill_value=0)
    m = activos[activos["Sexo"] == "F"]["FaixaEtaria"].value_counts().reindex(order, fill_value=0)
    fig = go.Figure()
    fig.add_bar(y=order, x=-h.values, name="Homens", orientation="h", marker_color=C["accent2"])
    fig.add_bar(y=order, x=m.values, name="Mulheres", orientation="h", marker_color=C["accent"])
    fig.update_layout(title="Pirâmide Etária por Gênero", barmode="relative")
    return _style(fig)


def fig_diversidade_raca(emp: pd.DataFrame, div: pd.DataFrame | None) -> go.Figure:
    col = "Raça Cor"
    source = div if (div is not None and col in div.columns) else emp
    if col not in source.columns:
        return _style(go.Figure().update_layout(title="Diversidade (sin datos)"))
    counts = source[col].astype(str).value_counts().head(8).sort_values()
    fig = go.Figure(go.Bar(x=counts.values, y=counts.index, orientation="h", marker_color=C["accent"]))
    fig.update_layout(title="Diversidade — Raça/Cor")
    return _style(fig)


def fig_pay_gap(emp: pd.DataFrame) -> go.Figure:
    activos = emp[emp["Ativo"]].copy()
    activos["Sexo"] = activos.get("Sexo", pd.Series(dtype=str)).astype(str).str.upper()
    g = activos.groupby("Sexo")["Salário"].mean().reindex(["M", "F"]).dropna()
    labels = {"M": "Homens", "F": "Mulheres"}
    fig = go.Figure(go.Bar(
        x=[labels.get(i, i) for i in g.index], y=g.values,
        marker_color=[C["accent2"], C["accent"]], text=[f"R$ {v:,.0f}" for v in g.values],
        textposition="outside",
    ))
    gap = (1 - g.get("F", np.nan) / g.get("M", np.nan)) * 100 if len(g) == 2 else np.nan
    title = "Brecha Salarial por Gênero (Pay Gap ★)"
    if not np.isnan(gap):
        title += f" — gap {gap:.1f}%"
    fig.update_layout(title=title)
    return _style(fig)


def fig_salario_dist(emp: pd.DataFrame) -> go.Figure:
    activos = emp[emp["Ativo"]].copy()
    activos["Sexo"] = activos.get("Sexo", pd.Series(dtype=str)).astype(str).str.upper()
    fig = px.box(activos, x="Sexo", y="Salário", color="Sexo",
                 color_discrete_sequence=[C["accent2"], C["accent"]])
    fig.update_layout(title="Distribuição Salarial por Gênero", showlegend=False)
    return _style(fig)


def fig_escolaridade(emp: pd.DataFrame) -> go.Figure:
    if "Escolaridade" not in emp.columns:
        return _style(go.Figure().update_layout(title="Escolaridade (sin datos)"))
    counts = emp[emp["Ativo"]]["Escolaridade"].astype(str).value_counts().sort_values()
    fig = go.Figure(go.Bar(x=counts.values, y=counts.index, orientation="h", marker_color=C["primary"]))
    fig.update_layout(title="Escolaridade (Ativos)")
    return _style(fig)


def fig_horas_extras(he: pd.DataFrame | None) -> go.Figure:
    if he is None or "Data_Marcação" not in he.columns:
        return _style(go.Figure().update_layout(title="Horas Extras (sin datos)"))
    he = he.copy()
    he["Data_Marcação"] = pd.to_datetime(he["Data_Marcação"], errors="coerce")
    he["HE_h"] = he["Horas_Extras"].apply(_hhmm_to_hours)
    he["Mes"] = he["Data_Marcação"].dt.to_period("M").dt.to_timestamp()
    serie = he.groupby("Mes")["HE_h"].sum()
    fig = go.Figure(go.Scatter(x=serie.index, y=serie.values, mode="lines+markers",
                               fill="tozeroy", line=dict(color=C["warn"], width=2)))
    fig.update_layout(title="Horas Extras — Total por Mês (h)")
    return _style(fig)


def fig_banco_horas(bh: pd.DataFrame | None) -> go.Figure:
    if bh is None or "Nome da Verba" not in bh.columns:
        return _style(go.Figure().update_layout(title="Banco de Horas (sin datos)"))
    bh = bh.copy()
    bh["Mes e Ano"] = pd.to_datetime(bh["Mes e Ano"], errors="coerce")
    bh["Mes"] = bh["Mes e Ano"].dt.to_period("M").dt.to_timestamp()
    pos = bh[bh["Nome da Verba"].str.contains("Positivo", na=False)].groupby("Mes")["Quantidade"].sum()
    neg = bh[bh["Nome da Verba"].str.contains("Negativo", na=False)].groupby("Mes")["Quantidade"].sum()
    fig = go.Figure()
    fig.add_bar(x=pos.index, y=pos.values, name="Positivo", marker_color=C["accent"])
    fig.add_bar(x=neg.index, y=neg.values, name="Negativo", marker_color=C["danger"])
    fig.update_layout(title="Banco de Horas — Positivo vs Negativo", barmode="relative")
    return _style(fig)


def fig_filial(emp: pd.DataFrame) -> go.Figure:
    if "Filial" not in emp.columns:
        return _style(go.Figure().update_layout(title="Filial (sin datos)"))
    counts = emp[emp["Ativo"]]["Filial"].astype(str).value_counts().head(10).sort_values()
    fig = go.Figure(go.Bar(x=counts.values, y=counts.index, orientation="h", marker_color=C["accent2"]))
    fig.update_layout(title="Headcount Ativo por Filial")
    return _style(fig)


def _hhmm_to_hours(v) -> float:
    try:
        s = str(v)
        if ":" in s:
            parts = s.split(":")
            return int(parts[0]) + int(parts[1]) / 60
        return float(s)
    except (ValueError, TypeError, IndexError):
        return 0.0


# ===========================================================================
# Gráficos de IA (usando el servidor MCP)
# ===========================================================================
def fig_ia_anomalias(emp: pd.DataFrame) -> tuple[go.Figure, str]:
    from powerbi_mcp.ai.anomaly import detect_anomalies

    activos = emp[emp["Ativo"]].dropna(subset=["Salário", "Idade", "Tenure"])
    records = activos[["Idade", "Salário", "Tenure"]].to_dict("records")
    result = detect_anomalies(records, columns=["Salário", "Idade", "Tenure"], method="iqr", iqr_factor=2.0)
    rows = pd.DataFrame(result.table)
    fig = px.scatter(
        rows, x="Idade", y="Salário", color="is_anomaly",
        color_discrete_map={True: C["danger"], False: C["accent2"]},
        labels={"is_anomaly": "Anomalia"},
    )
    fig.update_layout(title="IA — Anomalias Salariais (Idade × Salário)")
    n = result.summary["anomalies_detected"]
    note = f"{n} colaboradores con perfil salarial atípico detectados por IA."
    return _style(fig), note


def fig_ia_clustering(emp: pd.DataFrame) -> tuple[go.Figure, str]:
    from powerbi_mcp.ai.clustering import run_clustering

    activos = emp[emp["Ativo"]].dropna(subset=["Salário", "Idade", "Tenure"])
    records = activos[["Idade", "Salário", "Tenure"]].to_dict("records")
    result = run_clustering(records, columns=["Idade", "Salário", "Tenure"], algorithm="kmeans", n_clusters=4)
    rows = pd.DataFrame(result.table)
    rows["cluster"] = rows["cluster"].astype(str)
    fig = px.scatter(
        rows, x="Idade", y="Salário", color="cluster", size="Tenure",
        color_discrete_sequence=SEQ,
    )
    fig.update_layout(title="IA — Clusters de Colaboradores (perfil)")
    note = f"4 perfiles de colaboradores identificados (silueta={result.summary['silhouette_score']})."
    return _style(fig), note


def fig_ia_correlacao(emp: pd.DataFrame) -> tuple[go.Figure, str]:
    activos = emp[emp["Ativo"]][["Idade", "Salário", "Tenure"]].dropna()
    corr = activos.corr().round(2)
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.columns, text=corr.values,
        texttemplate="%{text}", colorscale="Greens", zmin=-1, zmax=1,
    ))
    fig.update_layout(title="IA — Correlação entre Variáveis")
    return _style(fig), "Relación entre edad, salario y antigüedad."


# ===========================================================================
# Ensamblado del HTML
# ===========================================================================
def build_html(kpis: list[dict], sections: list[tuple[str, list[tuple]]], out_path: Path) -> None:
    """Ensambla el dashboard HTML final."""
    first = True
    kpi_html = "".join(
        f'<div class="kpi"><div class="kpi-val">{k["value"]}</div>'
        f'<div class="kpi-lab">{k["label"]}</div><div class="kpi-sub">{k["sub"]}</div></div>'
        for k in kpis
    )

    body_parts: list[str] = []
    for section_title, charts in sections:
        body_parts.append(f'<h2 class="section">{section_title}</h2><div class="grid">')
        for item in charts:
            fig, note = (item if isinstance(item, tuple) else (item, ""))
            div = fig.to_html(full_html=False, include_plotlyjs=("inline" if first else False))
            first = False
            note_html = f'<div class="note">💡 {note}</div>' if note else ""
            body_parts.append(f'<div class="card">{div}{note_html}</div>')
        body_parts.append("</div>")
    body = "\n".join(body_parts)

    html = _TEMPLATE.format(
        kpis=kpi_html, body=body,
        generated=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
    out_path.write_text(html, encoding="utf-8")


_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>People Analytics — NGN / Necta</title>
<style>
  :root {{ --p:#1B7A3D; --pd:#0E4D26; --a:#7DC242; --bg:#f4f7f5; --card:#fff; --ink:#1f2d27; --muted:#6b7c74; }}
  *{{box-sizing:border-box}}
  body{{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--ink)}}
  header{{background:linear-gradient(120deg,var(--pd),var(--p));color:#fff;padding:28px 40px}}
  header h1{{margin:0;font-size:26px;letter-spacing:.5px}}
  header p{{margin:6px 0 0;opacity:.85;font-size:14px}}
  .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;padding:24px 40px}}
  .kpi{{background:var(--card);border-radius:14px;padding:16px 18px;box-shadow:0 2px 10px rgba(14,77,38,.08);border-left:4px solid var(--a)}}
  .kpi-val{{font-size:24px;font-weight:700;color:var(--pd)}}
  .kpi-lab{{font-size:13px;font-weight:600;margin-top:2px}}
  .kpi-sub{{font-size:11px;color:var(--muted);margin-top:2px}}
  .section{{margin:24px 40px 4px;color:var(--pd);border-left:5px solid var(--a);padding-left:12px;font-size:19px}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:18px;padding:8px 40px}}
  .card{{background:var(--card);border-radius:14px;padding:10px 12px 6px;box-shadow:0 2px 10px rgba(14,77,38,.08)}}
  .note{{font-size:12px;color:var(--muted);padding:4px 8px 8px;border-top:1px dashed #e3ece6;margin-top:4px}}
  footer{{text-align:center;color:var(--muted);font-size:12px;padding:30px}}
  .badge{{display:inline-block;background:rgba(255,255,255,.18);padding:3px 10px;border-radius:20px;font-size:12px;margin-top:8px}}
</style></head>
<body>
<header>
  <h1>👥 People Analytics — NGN / Necta</h1>
  <p>Dashboard interactivo generado con powerbi-mcp · datos mock de Indicadores P&amp;C</p>
  <span class="badge">★ = medida nueva respecto al modelo original · 🤖 incluye análisis de IA</span>
</header>
<div class="kpis">{kpis}</div>
{body}
<footer>Generado el {generated} por <b>powerbi-mcp</b> · Dashboard HTML interactivo (Plotly)</footer>
</body></html>
"""


def main(xlsx: str, out_dir: str) -> int:
    print("==> Cargando datos...")
    data = load_data(xlsx)
    emp = prepare_employees(data["Funcionarios"])
    div = data.get("Diversidade")
    he = data.get("Horas Extras")
    bh = data.get("Banco de Horas")

    print("==> Calculando KPIs y medidas...")
    kpis = compute_kpis(emp)

    print("==> Generando gráficos...")
    sections = [
        ("📈 Headcount & Turnover", [
            fig_movimentacao(emp), fig_headcount_area(emp),
            fig_turnover_tipo(emp), fig_filial(emp),
        ]),
        ("🌍 Demografia & Diversidade", [
            fig_piramide(emp), fig_diversidade_raca(emp, div),
            fig_escolaridade(emp),
        ]),
        ("💰 Compensação", [
            fig_pay_gap(emp), fig_salario_dist(emp),
        ]),
        ("⏱️ Jornada", [
            fig_horas_extras(he), fig_banco_horas(bh),
        ]),
        ("🤖 Inteligência Artificial", [
            fig_ia_anomalias(emp), fig_ia_clustering(emp), fig_ia_correlacao(emp),
        ]),
    ]

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    out_path = out / "PeopleAnalytics_Dashboard.html"
    print("==> Ensamblando HTML...")
    build_html(kpis, sections, out_path)
    print(f"\nOK -> {out_path}")
    print(f"   Tamaño: {out_path.stat().st_size/1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
