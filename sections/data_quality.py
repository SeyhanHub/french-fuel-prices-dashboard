"""Data quality tab: cleaning steps, missing values, duplicates, checks and limits."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.constants import METRO_DEPTS, SEEDS
from utils.i18n import fuel_name, tr
from utils.io import load_quality
from utils.viz import FUEL_COLORS, base_layout, show


def num(x):
    return f"{x:,}".replace(",", " ")


def render(tables: dict, f) -> None:
    q = load_quality()
    py = pd.DataFrame(q["per_year"]).set_index("year")
    raw = py["rows_raw"].sum()
    share = (raw - py["rows_clean"].sum()) / raw * 100
    weeks = SEEDS["ffill_max_weeks"]
    st.subheader(tr(f"{raw / 1e6:.1f} million price updates, of which {share:.2f} % had to be removed.",
                    f"{raw / 1e6:.1f} millions de prix déclarés, dont {share:.2f} % ont dû être "
                    "retirés."))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(tr("Raw price updates", "Prix bruts déclarés"), num(raw))
    c2.metric(tr("Exact duplicates removed", "Doublons retirés"), num(py["rows_exact_duplicates"].sum()))
    c3.metric(tr("Implausible prices removed", "Prix aberrants retirés"),
              num((py["rows_out_of_bounds"] + py["rows_far_from_weekly_median"]).sum()))
    c4.metric(tr("Different stations", "Stations différentes"), num(q["stations"]["total_unique"]))

    st.markdown("#### " + tr("Cleaning steps per year", "Étapes du nettoyage par année"))
    cols = {
        "rows_raw": tr("raw", "brut"),
        "rows_unparseable": tr("unparseable", "illisibles"),
        "rows_outside_year": tr("outside year", "hors année"),
        "rows_exact_duplicates": tr("exact duplicates", "doublons"),
        "rows_out_of_bounds": tr("out of bounds", "hors bornes"),
        "rows_far_from_weekly_median": tr("far from weekly median", "loin de la médiane"),
        "rows_clean": tr("clean", "propres"),
        "rows_in_thousandths": tr("in thousandths", "en millièmes"),
        "rows_same_day_resubmission": tr("same day resubmission", "renvoyés le même jour"),
        "stockouts_started": tr("stock-outs", "ruptures"),
    }
    st.dataframe(py[list(cols)].rename(columns=cols), width="stretch")
    lo, hi, dev = SEEDS["price_min_eur_l"], SEEDS["price_max_eur_l"], \
        SEEDS["max_rel_deviation_from_weekly_median"] * 100
    st.caption(tr(
        f"The thresholds are stored in seeds.json. Prices below {lo} or above {hi} €/L are dropped, "
        f"and so are prices more than {dev:.0f} % away from the national median of the same fuel "
        "that week, which catches typos like 0.71 instead of 1.71. Until 2021 prices were "
        "published in thousandths of a euro (1328 meaning 1.328 €), so they are converted. When a "
        "station sends the same price twice on the same day, both rows are kept because it does "
        "not change the weekly value.",
        f"Les seuils sont dans seeds.json. Les prix sous {lo} ou au-dessus de {hi} €/L sont "
        f"retirés, comme ceux à plus de {dev:.0f} % de la médiane nationale du même carburant cette "
        "semaine-là, ce qui attrape les fautes de frappe comme 0.71 au lieu de 1.71. Jusqu'en 2021 "
        "les prix étaient publiés en millièmes d'euro (1328 pour 1,328 €), donc ils sont convertis. "
        "Quand une station envoie deux fois le même prix le même jour, les deux lignes sont gardées "
        "car ça ne change pas la valeur de la semaine."))

    st.markdown("#### " + tr("How many stations report each week",
                             "Combien de stations déclarent chaque semaine"))
    cov = tables["coverage_weekly"]
    cov = cov[(cov["fuel"] == f.main_fuel) & cov["week"].between(f.start, f.end)]
    fig = go.Figure()
    for fuel, g in cov.groupby("fuel", sort=False):
        fig.add_trace(go.Scatter(x=g["week"], y=g["observed"], mode="lines",
                                 name=tr("Changed their price that week",
                                         "Ont changé leur prix cette semaine"),
                                 line={"color": FUEL_COLORS[fuel], "width": 1.2, "dash": "dot"}))
        fig.add_trace(go.Scatter(x=g["week"], y=g["after_ffill"], mode="lines",
                                 name=tr(f"Including prices carried over up to {weeks} weeks "
                                         "(used in the averages)",
                                         f"Avec les prix reportés jusqu'à {weeks} semaines "
                                         "(utilisé dans les moyennes)"),
                                 line={"color": FUEL_COLORS[fuel], "width": 2}))
    base_layout(fig, tr(f"Stations with a {fuel_name(f.main_fuel, True)} price each week",
                        f"Stations avec un prix du {fuel_name(f.main_fuel, True)} chaque semaine"),
                tr("number of stations", "nombre de stations"), height=380)
    show(fig, alt=tr(
        "Line chart of the number of stations with a price each week. The dotted line counts "
        "stations that changed their price that week and the solid line also counts stations whose "
        f"last price is carried over for up to {weeks} weeks.",
        "Courbes du nombre de stations avec un prix chaque semaine. Le pointillé compte les "
        "stations qui ont changé leur prix cette semaine, le trait plein compte aussi celles dont "
        f"le dernier prix est reporté jusqu'à {weeks} semaines."), key="dq_coverage")
    st.caption(tr(
        "Stations only send an update when their price changes, so a station with a stable price "
        f"sends nothing. That is why I carry the last known price forward for up to {weeks} weeks. "
        "Longer gaps are left empty rather than filled with a guess.",
        "Une station n'envoie un prix que quand il change, donc une station au prix stable "
        "n'envoie rien. C'est pour ça que je reporte le dernier prix connu jusqu'à "
        f"{weeks} semaines. Les trous plus longs restent vides au lieu d'être remplis au hasard."))

    st.markdown("#### " + tr("Checks on the processed tables", "Contrôles sur les tables finales"))
    nat, grp, snap = tables["national_weekly"], tables["dept_road_weekly"], tables["stations_snapshot"]
    mb = tables["monthly_with_brent"]
    checks = [
        (tr("No duplicate key in the department table (fuel, department, road type, week)",
            "Pas de clé en double dans la table des départements (carburant, département, type, "
            "semaine)"),
         not grp.duplicated(["fuel", "dept", "road", "week"]).any()),
        (tr("All weekly averages are within the cleaning limits",
            "Toutes les moyennes par semaine sont dans les bornes du nettoyage"),
         bool(nat["mean"].between(SEEDS["price_min_eur_l"], SEEDS["price_max_eur_l"]).all())),
        (tr("10th percentile below median below 90th percentile every week",
            "10e centile sous la médiane, elle-même sous le 90e centile, chaque semaine"),
         bool(((nat["p10"] <= nat["median"]) & (nat["median"] <= nat["p90"])).all())),
        (tr("All 96 metropolitan departments are present",
            "Les 96 départements de métropole sont présents"),
         set(grp["dept"].astype(str).unique()) >= METRO_DEPTS),
        (tr("No missing week in the diesel series", "Aucune semaine manquante pour le gazole"),
         bool((nat[nat["fuel"] == "Gazole"]["week"].diff().dropna() == pd.Timedelta(weeks=1)).all())),
        (tr("Brent available for every month except the current one",
            "Brent disponible pour chaque mois sauf le mois en cours"),
         int(mb[mb["fuel"] == "Gazole"]["brent_eur_bbl"].isna().sum()) <= 1),
        (tr("Share of stations with valid coordinates", "Part des stations avec des coordonnées "
            "valides"), f"{snap['coords_valid'].mean() * 100:.1f} %"),
    ]
    ok, ko = tr("pass", "ok"), tr("fail", "échec")
    st.dataframe(pd.DataFrame([(c, ok if v is True else (ko if v is False else v)) for c, v in checks],
                              columns=[tr("Check", "Contrôle"), tr("Result", "Résultat")]),
                 width="stretch", hide_index=True)

    st.markdown("#### " + tr("Missing values in the processed tables (%)",
                             "Valeurs manquantes dans les tables finales (%)"))
    miss = pd.DataFrame({name: tables[name].isna().mean() * 100 for name in
                         ["national_weekly", "dept_road_weekly", "stations_snapshot",
                          "monthly_with_brent"]}).round(2)  # empty cell = column not in that table
    st.dataframe(miss, width="stretch")
    st.caption(tr("The only real gap is brent_eur_bbl for the current month, because Brent is "
                  "published about a month late.",
                  "Le seul vrai manque est brent_eur_bbl pour le mois en cours, parce que le Brent "
                  "est publié avec environ un mois de retard."))

    s = q["stations"]
    roads = s["road_type_counts"]
    st.markdown("#### " + tr("Station information", "Informations sur les stations"))
    st.markdown(tr(
        f"Over 2019 to 2026 the files contain {num(s['total_unique'])} different stations, "
        f"{num(s['metropolitan'])} of them in metropolitan France. The "
        f"{s['overseas_or_unknown_dept']} others are left out. {s['invalid_coordinates_metro']} "
        "metropolitan stations have coordinates that fall outside France, usually because latitude "
        "and longitude are swapped or empty. They are hidden on the station map but still used in "
        f"the averages. By type, the split is {num(roads.get('Road', 0))} road stations and "
        f"{num(roads.get('Motorway', 0))} motorway stations.",
        f"De 2019 à 2026 les fichiers contiennent {num(s['total_unique'])} stations différentes, "
        f"dont {num(s['metropolitan'])} en France métropolitaine. Les "
        f"{s['overseas_or_unknown_dept']} autres sont mises de côté. "
        f"{s['invalid_coordinates_metro']} stations de métropole ont des coordonnées hors de "
        "France, souvent parce que latitude et longitude sont inversées ou vides. Elles sont "
        "cachées sur la carte des stations mais gardées dans les moyennes. Par type, il y a "
        f"{num(roads.get('Road', 0))} stations hors autoroute et {num(roads.get('Motorway', 0))} "
        "stations d'autoroute."))

    st.markdown("#### " + tr("Limits and possible biases", "Limites et biais possibles"))
    st.warning(tr(
        "The averages give the same weight to every station, so a quiet village station counts as "
        "much as a busy supermarket one, and the real average price paid per litre is probably a "
        "bit lower. Prices are declared by the stations and some declare late, which the carry-over "
        "rule can hide. Brent is a monthly average in euros, so weekly timing and the effect of the "
        "dollar exchange rate are smoothed out. The tax breakdown uses the official rates, frozen "
        "since 2018, and ignores regional variations, biofuel incentives and discounts offered by "
        "companies (one major retailer ran its own rebate in 2022), so all of these end up in the "
        "refining and retail part. The events on the charts are context: the dashboard shows "
        "things moving together, it does not prove what caused them. Finally, the data is about "
        "businesses and contains no personal information.",
        "Les moyennes donnent le même poids à chaque station, donc une petite station de village "
        "compte autant qu'une grosse station de supermarché, et le vrai prix moyen payé par litre "
        "est sûrement un peu plus bas. Les prix sont déclarés par les stations et certaines "
        "déclarent en retard, ce que le report des prix peut cacher. Le Brent est une moyenne "
        "mensuelle en euros, donc le timing semaine par semaine et l'effet du taux de change avec "
        "le dollar sont lissés. La décomposition utilise les taux officiels, gelés depuis 2018, et "
        "ne tient pas compte des variations régionales, des aides aux biocarburants ni des remises "
        "des entreprises (un grand distributeur a fait sa propre remise en 2022), donc tout ça "
        "finit dans la part raffinage et distribution. Les événements sur les graphiques sont du "
        "contexte : le dashboard montre des choses qui bougent ensemble, il ne prouve pas ce qui "
        "les cause. Enfin, les données portent sur des entreprises et ne contiennent aucune "
        "information personnelle."))
