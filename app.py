"""French fuel prices 2019-2026: oil, taxes and margins.

Run with: streamlit run app.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run from any working directory
from sections import conclusions, data_quality, deep_dives, intro, overview  # noqa: E402
from utils.constants import FUELS, REGIONS, ROOT  # noqa: E402
from utils.i18n import fuel_name, pick, tr  # noqa: E402
from utils.io import load_data  # noqa: E402

st.set_page_config(page_title="French fuel prices 2019-2026",
                   layout="wide", initial_sidebar_state="expanded")

STUDENT = {"name": "Seyhan KARA", "email": "seyhan.kara@efrei.net",
           "program": "Data Engineering", "year": "2026-2027"}
COURSE = {"name": "Data Visualization", "prof": "Mano Mathew",
          "linkedin": "https://www.linkedin.com/in/manomathew/"}


@dataclass(frozen=True)
class Filters:
    fuels: tuple
    main_fuel: str
    start: pd.Timestamp
    end: pd.Timestamp
    regions: tuple
    road: str
    measure: str


def sidebar_header():
    st.markdown(f"**{tr('Name', 'Nom')}:** {STUDENT['name']}  \n"
                f"**Email:** {STUDENT['email']}  \n"
                f"**{tr('Program', 'Programme')}:** {STUDENT['program']}  \n"
                f"**{tr('Year', 'Année')}:** {STUDENT['year']}")
    st.radio("Language / Langue", ["en", "fr"], key="lang", horizontal=True,
             format_func=lambda x: {"en": "English", "fr": "Français"}[x])
    st.divider()


def sidebar_footer():
    st.divider()
    st.markdown(f"**{tr('Course', 'Cours')}:** {COURSE['name']}  \n"
                f"**Prof.** [{COURSE['prof']}]({COURSE['linkedin']})")
    st.image(str(ROOT / "assets" / "efrei_logo.png"), width="stretch")


def sidebar(tables: dict) -> Filters:
    weeks = tables["national_weekly"]["week"]
    wmin, wmax = weeks.min().date(), weeks.max().date()
    with st.sidebar:
        sidebar_header()
        st.header(tr("Filters", "Filtres"))
        fuels = st.multiselect(
            tr("Fuel(s)", "Carburant(s)"), FUELS, default=["Gazole", "E10", "SP98"],
            format_func=fuel_name, key="fuels",
            help=tr("Diesel, SP95-E10 and SP98 are the fuels sold by the most stations. Each fuel "
                    "keeps the same colour whatever you select.",
                    "Gazole, SP95-E10 et SP98 sont les carburants vendus par le plus de stations. "
                    "Chaque carburant garde la même couleur quelle que soit la sélection."))
        if not fuels:
            st.warning(tr("No fuel selected, showing diesel.",
                          "Aucun carburant choisi, j'affiche le gazole."))
            fuels = ["Gazole"]
        main_fuel = st.selectbox(tr("Main fuel (figures, map, price breakdown)",
                                    "Carburant principal (chiffres, carte, décomposition)"),
                                 fuels, format_func=fuel_name, key="main_fuel")
        start, end = st.slider(tr("Date range (weeks)", "Période (semaines)"),
                               min_value=wmin, max_value=wmax, value=(wmin, wmax),
                               format="MMM YYYY", key="dates")
        regions = st.multiselect(tr("Region(s)", "Région(s)"), list(REGIONS), default=[], key="regions",
                                 placeholder=tr("All metropolitan France",
                                                "Toute la France métropolitaine"),
                                 help=tr("Leave empty for all of metropolitan France.",
                                         "Laisser vide pour toute la France métropolitaine."))
        road_labels = {"All": tr("All", "Toutes"), "Road": tr("Road", "Route"),
                       "Motorway": tr("Motorway", "Autoroute")}
        road = pick(st.radio, tr("Station type", "Type de station"), list(road_labels),
                    road_labels, "road", horizontal=True,
                        help=tr("Motorway means stations on the toll motorway network (pop = A "
                                "in the source files).",
                                "Autoroute veut dire les stations du réseau autoroutier à péage "
                                "(pop = A dans les fichiers source)."))
        measures = {m: measure_label(m) for m in ["price", "index", "yoy"]}
        measure = pick(st.selectbox, tr("Measure for trend charts", "Mesure pour les courbes"),
                       list(measures), measures, "measure")
        st.caption(tr("Fuel prices from prix-carburants.gouv.fr on data.gouv.fr (Licence Ouverte "
                      "2.0). Brent from INE Portugal on data.europa.eu (CC BY 4.0).",
                      "Prix des carburants : prix-carburants.gouv.fr sur data.gouv.fr (Licence "
                      "Ouverte 2.0). Brent : INE Portugal sur data.europa.eu (CC BY 4.0)."))
        sidebar_footer()
    return Filters(tuple(fuels), main_fuel, pd.Timestamp(start), pd.Timestamp(end),
                   tuple(regions), road, measure)


def measure_label(m):
    return {"price": tr("Price (€/L)", "Prix (€/L)"),
            "index": tr("Index (first week = 100)", "Indice (première semaine = 100)"),
            "yoy": tr("Year-on-year change (%)", "Variation sur un an (%)")}[m]


def main() -> None:
    tables = load_data()
    f = sidebar(tables)

    st.title(tr("What really drives fuel prices in France, 2019 to 2026",
                "Ce qui fait vraiment le prix des carburants en France, de 2019 à 2026"))
    st.caption(tr("Sources: Prix des carburants en France, prix-carburants.gouv.fr on data.gouv.fr, "
                  "Licence Ouverte v2.0. Brent oil price in euros per barrel, INE Portugal on "
                  "data.europa.eu, CC BY 4.0. About 36 million price updates from 15 400 stations.",
                  "Sources : Prix des carburants en France, prix-carburants.gouv.fr sur "
                  "data.gouv.fr, Licence Ouverte v2.0. Prix du Brent en euros par baril, INE "
                  "Portugal sur data.europa.eu, CC BY 4.0. Environ 36 millions de prix déclarés "
                  "par 15 400 stations."))

    tabs = st.tabs([tr("Introduction", "Introduction"), tr("Overview", "Vue d'ensemble"),
                    tr("Oil and the pump price", "Pétrole et prix à la pompe"),
                    tr("Regions", "Régions"), tr("Scenarios", "Scénarios"),
                    tr("Data quality", "Qualité des données"), tr("Conclusion", "Conclusion")])
    with tabs[0]:
        intro.render(tables, f)
    with tabs[1]:
        overview.render(tables, f)
    with tabs[2]:
        deep_dives.render_drivers(tables, f)
    with tabs[3]:
        deep_dives.render_geography(tables, f)
    with tabs[4]:
        deep_dives.render_what_if(tables, f)
    with tabs[5]:
        data_quality.render(tables, f)
    with tabs[6]:
        conclusions.render(tables, f)


if __name__ == "__main__":
    main()
