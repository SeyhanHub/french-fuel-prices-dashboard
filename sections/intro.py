"""Introduction tab: why the topic matters, who it is for, the questions and the caveats."""
from __future__ import annotations

import streamlit as st

from utils.i18n import full_date, month_year, tr
from utils.io import licence_text


def render(tables: dict, f) -> None:
    nat = tables["national_weekly"]
    d = nat[nat["fuel"] == "Gazole"].set_index("week")["mean"]
    peak_week, peak = d.idxmax(), d.max()
    avg_2019 = d[d.index.year == 2019].mean()
    peak_2022 = d[d.index.year == 2022].max()
    brent = tables["brent_monthly"].set_index("month")["brent_eur_bbl"]
    feb, apr = brent.get("2026-02-01"), brent.get("2026-04-01")

    st.subheader(tr(f"In {month_year(peak_week)} diesel reached {peak:.2f} € per litre on average "
                    "in France, higher than the 2022 peak.",
                    f"En {month_year(peak_week)}, le gazole a atteint {peak:.2f} € le litre en "
                    "moyenne en France, plus haut que le pic de 2022."))
    st.markdown(tr(
        "Fuel prices are something almost everyone in France watches. People who live outside big "
        "cities depend on their car to get to work, truck drivers and farmers depend on diesel, and "
        "a rise in fuel taxes was what started the gilets jaunes protests in 2018. In 2026 the war in "
        "Iran and the disruption of traffic in the Strait of Hormuz pushed oil prices up again, and "
        "the usual explanation on TV is simply that oil got more expensive. I wanted to check how "
        "true that is, using the prices that every French station has to declare to the government "
        "since 2019 (around 36 million price updates) and the monthly price of Brent crude.",
        "Le prix de l'essence, presque tout le monde en France le regarde. Ceux qui vivent loin des "
        "grandes villes ont besoin de leur voiture pour aller travailler, les routiers et les "
        "agriculteurs dépendent du gazole, et c'est une hausse des taxes sur les carburants qui a "
        "lancé les gilets jaunes en 2018. En 2026, la guerre en Iran et les perturbations dans le "
        "détroit d'Ormuz ont fait remonter le pétrole, et à la télé l'explication est souvent juste "
        "que le pétrole est plus cher. J'ai voulu vérifier si c'est vrai, avec les prix que chaque "
        "station française doit déclarer à l'État depuis 2019 (environ 36 millions de mises à jour) "
        "et le prix mensuel du Brent."))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(tr("Diesel, highest weekly average", "Gazole, plus haute moyenne hebdo"),
              f"{peak:.3f} €/L", tr(f"week of {full_date(peak_week)}",
                                    f"semaine du {full_date(peak_week)}"), delta_color="off")
    c2.metric(tr("Diesel, 2019 average", "Gazole, moyenne 2019"), f"{avg_2019:.3f} €/L",
              tr(f"{(peak / avg_2019 - 1) * 100:+.0f} % at the record",
                 f"{(peak / avg_2019 - 1) * 100:+.0f} % au record"), delta_color="inverse")
    c3.metric(tr("Diesel, 2022 peak", "Gazole, pic de 2022"), f"{peak_2022:.3f} €/L")
    if feb and apr:
        c4.metric(tr("Brent crude, April 2026", "Brent, avril 2026"), f"{apr:.0f} €/bbl",
                  tr(f"{(apr / feb - 1) * 100:+.0f} % since February",
                     f"{(apr / feb - 1) * 100:+.0f} % depuis février"), delta_color="inverse")

    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### " + tr("Who this is for", "Pour qui"))
        st.markdown(tr(
            "The dashboard is meant for ordinary drivers, for local journalists and for anyone "
            "following the debate on fuel taxes and rebates. The goal is not to forecast prices but "
            "to give a correct picture of what a litre of fuel is made of.",
            "Le dashboard s'adresse aux automobilistes, aux journalistes locaux et à tous ceux qui "
            "suivent le débat sur les taxes et les remises sur les carburants. Le but n'est pas de "
            "prévoir les prix, mais de donner une bonne idée de ce qui compose un litre de carburant."))
        st.markdown("#### " + tr("Questions", "Questions"))
        st.markdown(tr(
            "The overview tab looks at when prices moved and by how much. The oil tab splits the "
            "pump price into crude oil, taxes and the rest, and checks whether prices go up faster "
            "than they come down. The regions tab compares departments and looks at motorway "
            "stations. Finally the scenarios tab lets you test what a more expensive barrel or a "
            "tax cut would change on a yearly fuel budget.",
            "L'onglet vue d'ensemble regarde quand les prix ont bougé et de combien. L'onglet "
            "pétrole découpe le prix à la pompe entre le brut, les taxes et le reste, et vérifie si "
            "les prix montent plus vite qu'ils ne baissent. L'onglet régions compare les "
            "départements et les stations d'autoroute. Enfin, l'onglet scénarios permet de tester "
            "ce que changerait un baril plus cher ou une baisse de taxe sur un budget annuel."))
        st.markdown("#### " + tr("How the story goes", "Le fil de l'histoire"))
        st.markdown(tr(
            "It starts with the 2026 record, then puts it next to the two previous shocks (the "
            "COVID collapse in 2020 and the war in Ukraine in 2022). The main finding is that crude "
            "oil is only about a quarter of the price, while the part that goes to refining and "
            "distribution has more than doubled for diesel. The last tab discusses what this means "
            "for drivers and for public policy.",
            "On part du record de 2026, puis on le compare aux deux chocs d'avant (la chute pendant "
            "le COVID en 2020 et la guerre en Ukraine en 2022). Le résultat principal, c'est que le "
            "pétrole brut ne fait qu'environ un quart du prix, alors que la part du raffinage et de "
            "la distribution a plus que doublé pour le gazole. Le dernier onglet explique ce que ça "
            "veut dire pour les automobilistes et pour les politiques publiques."))
    with right:
        st.markdown("#### " + tr("Data and caveats", "Données et limites"))
        st.info(tr(
            "Prices are declared by the stations themselves, which is a legal obligation since "
            "2007, so some come late or contain typos. These are cleaned and the rules are "
            "explained in the data quality tab. I only kept metropolitan France, because overseas "
            "departments have regulated prices. Weekly figures are averages over stations, not "
            "over litres sold, since the volume sold by each station is not published. Brent is a "
            "monthly average, and the tax breakdown relies on the official tax rates and on the "
            "2022 rebate calendar. Events shown on the charts are there for context and are not "
            "presented as proven causes.",
            "Les prix sont déclarés par les stations elles-mêmes, c'est obligatoire depuis 2007, "
            "donc certains arrivent en retard ou contiennent des fautes de frappe. Ils sont "
            "nettoyés et les règles sont expliquées dans l'onglet qualité des données. J'ai gardé "
            "seulement la France métropolitaine, parce que les prix sont réglementés dans les DOM. "
            "Les chiffres par semaine sont des moyennes sur les stations et pas sur les litres "
            "vendus, car le volume vendu par station n'est pas publié. Le Brent est une moyenne "
            "mensuelle, et la décomposition du prix repose sur les taux de taxe officiels et sur le "
            "calendrier de la remise de 2022. Les événements sur les graphiques sont là pour le "
            "contexte, pas comme des causes prouvées."))
        st.markdown("#### " + tr("Sources and licences", "Sources et licences"))
        st.markdown(licence_text())
