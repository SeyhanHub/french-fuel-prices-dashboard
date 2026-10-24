"""Overview tab: KPIs that follow the filters and the long-term trend."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.i18n import fuel_name, full_date, month_year, tr
from utils.prep import add_measure, compute_kpis, filtered_weekly
from utils.viz import PALETTE, add_events, bar_chart, base_layout, line_chart, show

MEASURES = {"price": ("Price (€/L)", "Prix (€/L)"),
            "index": ("Index (first week = 100)", "Indice (première semaine = 100)"),
            "yoy": ("Year-on-year change (%)", "Variation sur un an (%)")}


def scope_label(f) -> str:
    where = ", ".join(f.regions) if f.regions else tr("metropolitan France", "France métropolitaine")
    road = ""
    if f.road != "All":
        road = tr(f", {f.road.lower()} stations only",
                  ", stations d'autoroute uniquement" if f.road == "Motorway"
                  else ", stations hors autoroute uniquement")
    return (f"{where}{road}, " + tr(f"{month_year(f.start, True)} to {month_year(f.end, True)}",
                                    f"de {month_year(f.start, True)} à {month_year(f.end, True)}"))


def render(tables: dict, f) -> None:
    wk = filtered_weekly(tables["dept_road_weekly"], f.fuels, f.regions, f.road, f.start, f.end)
    k = compute_kpis(wk, f.main_fuel)
    if k is None:
        st.warning(tr("No data for this combination of filters.",
                      "Pas de données pour cette combinaison de filtres."))
        return
    change = k.price_now - k.price_start
    cents = abs(change) * 100
    st.subheader(tr(
        f"{fuel_name(f.main_fuel)} ends the period at {k.price_now:.3f} €/L, "
        f"{'up' if change >= 0 else 'down'} {cents:.0f} cents per litre since {month_year(f.start)}.",
        f"Le {fuel_name(f.main_fuel, True)} finit la période à {k.price_now:.3f} €/L, soit "
        f"{cents:.0f} centimes de {'plus' if change >= 0 else 'moins'} par litre qu'en "
        f"{month_year(f.start)}."))
    st.caption(tr("Scope: ", "Périmètre : ") + scope_label(f))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(tr(f"Latest week ({full_date(k.last_week)})",
                 f"Dernière semaine ({full_date(k.last_week)})"), f"{k.price_now:.3f} €/L",
              tr(f"{change:+.3f} € vs first week", f"{change:+.3f} € vs première semaine"),
              delta_color="inverse",
              help=tr("Average over stations of the last price each station reported that week.",
                      "Moyenne sur les stations du dernier prix déclaré par chacune cette semaine."))
    c2.metric(tr("Highest in period", "Plus haut de la période"), f"{k.peak:.3f} €/L",
              tr(f"week of {full_date(k.peak_week)}", f"semaine du {full_date(k.peak_week)}"),
              delta_color="off")
    c3.metric(tr("Lowest in period", "Plus bas de la période"), f"{k.low:.3f} €/L",
              tr(f"week of {full_date(k.low_week)}", f"semaine du {full_date(k.low_week)}"),
              delta_color="off")
    c4.metric(tr("Cost of a 50 L tank", "Prix d'un plein de 50 L"), f"{k.tank_cost:.0f} €",
              tr(f"{(k.price_now - k.low) * 50:+.0f} € vs the lowest week",
                 f"{(k.price_now - k.low) * 50:+.0f} € vs la semaine la moins chère"),
              delta_color="inverse")
    c5.metric(tr("Stations reporting", "Stations qui déclarent"), f"{k.stations:,}".replace(",", " "),
              help=tr("Stations with a price for this fuel this week, or a price carried over from "
                      "the previous three weeks.",
                      "Stations avec un prix pour ce carburant cette semaine, ou un prix reporté "
                      "des trois semaines d'avant."))

    measure = tr(*MEASURES[f.measure])
    data = add_measure(wk, f.measure)
    nat = tables["national_weekly"]
    band = None
    if f.measure == "price" and len(f.fuels) == 1 and not f.regions and f.road == "All":
        band = nat[(nat["fuel"] == f.main_fuel) & nat["week"].between(f.start, f.end)]
    fmt = {"price": ".3f", "index": ".1f", "yoy": "+.1f"}
    fig = line_chart(data, "value", measure,
                     tr(f"Weekly average pump price, {measure}",
                        f"Prix moyen à la pompe par semaine, {measure}"),
                     f.start, f.end, band=band, hover_fmt=fmt[f.measure])
    fuels_txt = ", ".join(fuel_name(x) for x in f.fuels)
    show(fig,
         alt=tr(f"Line chart of the weekly {measure.lower()} for {fuels_txt}, {scope_label(f)}. "
                "Dotted vertical lines mark the COVID lockdown, the invasion of Ukraine, the "
                "refinery strikes and the 2026 war in Iran, and a shaded area shows the 2022 State "
                "rebate. All fuels follow the same pattern: a drop in spring 2020, a rise during "
                "2021, a peak in 2022, a slow decline until 2025 and a new jump from March 2026."
                + (" The blue band shows the range where 80 % of stations priced (10th to 90th "
                   "percentile)." if band is not None else ""),
                f"Courbes de la mesure « {measure.lower()} » par semaine pour {fuels_txt}, "
                f"{scope_label(f)}. Les lignes verticales en pointillé marquent le confinement, "
                "l'invasion de l'Ukraine, les grèves des raffineries et la guerre en Iran de 2026, "
                "et la zone ombrée montre la remise de l'État en 2022. Tous les carburants suivent "
                "le même schéma : une baisse au printemps 2020, une hausse en 2021, un pic en 2022, "
                "une lente baisse jusqu'en 2025 et un nouveau saut à partir de mars 2026."
                + (" La bande bleue montre où se situent 80 % des stations (du 10e au 90e "
                   "centile)." if band is not None else "")),
         data=data.pivot_table(index="week", columns="fuel", values="value", observed=True)
                  .reset_index(),
         key="overview_trend")
    nf = nat[nat["fuel"] == f.main_fuel]
    spread = (nf["p90"] - nf["p10"]).median() * 100
    st.info(tr(
        "If you keep a single fuel and no region filter, the chart also shows the range between "
        f"cheap and expensive stations, which is usually around {spread:.0f} c€/L for "
        f"{fuel_name(f.main_fuel, True)}. The measure selector in the sidebar can switch to an "
        "index, which is easier for comparing fuels, or to the change over one year, which makes "
        "the shocks stand out.",
        "Avec un seul carburant et sans filtre de région, le graphique montre aussi l'écart entre "
        f"les stations pas chères et les chères, en général autour de {spread:.0f} c€/L pour le "
        f"{fuel_name(f.main_fuel, True)}. Dans la barre latérale, on peut passer à un indice, plus "
        "pratique pour comparer les carburants, ou à la variation sur un an, qui fait bien "
        "ressortir les chocs."))

    st.markdown("#### " + tr("Year by year", "Année par année"))
    y = (wk[wk["fuel"] == f.main_fuel].assign(year=lambda x: x["week"].dt.year)
           .groupby("year")["price"].mean().reset_index())
    y["label"] = y["year"].astype(str)
    y = y.iloc[::-1]
    col1, col2 = st.columns([2, 3])
    with col1:
        fig = bar_chart(y, "price", "label",
                        tr(f"Yearly average, {fuel_name(f.main_fuel)}",
                           f"Moyenne par année, {fuel_name(f.main_fuel)}"),
                        tr("€ per litre", "€ par litre"), color=PALETTE[0], height=360)
        fig.update_xaxes(range=[0, y["price"].max() * 1.15])
        fig.update_yaxes(type="category")
        hi = y.loc[y["price"].idxmax()]
        lo = y.loc[y["price"].idxmin()]
        show(fig, alt=tr(f"Horizontal bars with the yearly average price of "
                         f"{fuel_name(f.main_fuel, True)}. The highest year is {hi['label']} at "
                         f"{hi['price']:.3f} €/L and the lowest is {lo['label']} at "
                         f"{lo['price']:.3f} €/L.",
                         f"Barres horizontales avec le prix moyen du {fuel_name(f.main_fuel, True)} "
                         f"par année. L'année la plus chère est {hi['label']} à {hi['price']:.3f} "
                         f"€/L et la moins chère {lo['label']} à {lo['price']:.3f} €/L."),
             key="overview_years")
    with col2:
        stock = tables["stockouts_weekly"]
        s = (stock[stock["week"].between(f.start, f.end) & stock["fuel"].isin(f.fuels)]
             .groupby("week")["stockouts_started"].sum().reset_index())
        if not s.empty:
            fig = go.Figure(go.Bar(x=s["week"], y=s["stockouts_started"],
                                   marker={"color": PALETTE[7]},
                                   hovertemplate="%{x|%d/%m/%Y}: %{y:,}<extra></extra>"))
            base_layout(fig, tr("Stock-outs declared by stations each week",
                                "Ruptures de stock déclarées par semaine"),
                        tr("stock-out declarations", "déclarations de rupture"),
                        height=360, legend=False)
            add_events(fig, f.start, f.end)
            top = s.loc[s["stockouts_started"].idxmax()]
            top_week, top_n = pd.Timestamp(top["week"]), int(top["stockouts_started"])
            show(fig, alt=tr(f"Weekly bars of the stock-outs declared by stations for the selected "
                             f"fuels. The biggest week is {full_date(top_week)} with {top_n:,} "
                             "declarations.",
                             f"Barres des ruptures de stock déclarées chaque semaine pour les "
                             f"carburants choisis. La pire semaine est celle du {full_date(top_week)} "
                             f"avec {top_n:,} déclarations.".replace(",", " ")),
                 key="overview_stockouts")
    st.caption(tr("A shock is not only a price problem. In October 2022 the refinery strikes left "
                  "thousands of stations without fuel, at a time when prices were held down by the "
                  "State rebate.",
                  "Un choc, ce n'est pas que le prix. En octobre 2022, les grèves des raffineries ont "
                  "laissé des milliers de stations à sec, alors que les prix étaient tenus par la "
                  "remise de l'État."))
