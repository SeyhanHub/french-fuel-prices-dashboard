"""Conclusion tab: findings computed from the data, what they mean and what could come next."""
from __future__ import annotations

import streamlit as st

from utils.i18n import month_year, tr
from utils.prep import asymmetry_significant, decompose, pass_through, road_premium


def render(tables: dict, f) -> None:
    dec = decompose(tables["monthly_with_brent"], "Gazole").set_index("month")
    comps = ["Crude oil (Brent)", "Refining, logistics & retail", "TICPE excise", "VAT 20%"]
    share = dec[comps].div(dec[comps].sum(axis=1), axis=0).mean()
    crude = share["Crude oil (Brent)"] * 100
    taxes = (share["TICPE excise"] + share["VAT 20%"]) * 100
    margin = dec["Refining, logistics & retail"]
    m_old, m_new = margin["2019":"2021"].mean() * 100, margin.iloc[-12:].mean() * 100
    pt = pass_through(dec.reset_index())
    rp = road_premium(tables["dept_road_weekly"], "Gazole", (), dec.index.min(),
                      tables["national_weekly"]["week"].max())
    nat = tables["national_weekly"]
    g = nat[nat["fuel"] == "Gazole"].set_index("week")["mean"]
    spread = (nat[nat["fuel"] == "Gazole"]["p90"] - nat[nat["fuel"] == "Gazole"]["p10"]).median()
    motorway = rp["premium"].iloc[-12:].mean()

    if asymmetry_significant(pt):
        asym = tr("Diesel prices do seem to go up faster than they come down, and the difference "
                  "is significant, but it rests on monthly data only.",
                  "Les prix du gazole semblent bien monter plus vite qu'ils ne baissent, et la "
                  "différence est significative, mais ça repose seulement sur des données mensuelles.")
    else:
        asym = tr("The idea that prices go up faster than they come down is not clearly supported "
                  "with monthly data.",
                  "L'idée que les prix montent plus vite qu'ils ne baissent n'est pas vraiment "
                  "confirmée avec des données mensuelles.")

    st.subheader(tr("Oil explains the swings, taxes explain most of the level, and margins explain "
                    "the trend.",
                    "Le pétrole explique les variations, les taxes expliquent l'essentiel du niveau, "
                    "et les marges expliquent la tendance."))
    st.markdown("#### " + tr("What the data shows", "Ce que montrent les données"))
    st.markdown(tr(
        f"There were three shocks in seven years. Diesel fell to {g['2020'].min():.2f} €/L during "
        f"the 2020 lockdowns, climbed to {g['2022'].max():.2f} € in 2022 and reached a record of "
        f"{g.max():.2f} €/L in {month_year(g.idxmax())}, after the war in Iran disrupted the Strait "
        "of Hormuz.",
        f"Il y a eu trois chocs en sept ans. Le gazole est descendu à {g['2020'].min():.2f} €/L "
        f"pendant les confinements de 2020, est monté à {g['2022'].max():.2f} € en 2022 et a "
        f"atteint un record de {g.max():.2f} €/L en {month_year(g.idxmax())}, après que la guerre en "
        "Iran a perturbé le détroit d'Ormuz."))
    st.markdown(tr(
        f"On average crude oil is only about {crude:.0f} % of the price of diesel, and taxes are "
        f"about {taxes:.0f} %. Because the excise is a fixed amount per litre, it softens the "
        "percentage changes: if crude doubles, the pump price is far from doubling.",
        f"En moyenne le pétrole brut ne fait qu'environ {crude:.0f} % du prix du gazole, et les "
        f"taxes environ {taxes:.0f} %. Comme la TICPE est un montant fixe par litre, elle amortit "
        "les variations en pourcentage : si le brut double, le prix à la pompe est loin de doubler."))
    st.markdown(tr(
        "The least visible change is also the most lasting one. The part between crude and the "
        f"pump went from about {m_old:.0f} cents per litre in 2019 to 2021 to about {m_new:.0f} "
        "cents over the last twelve months.",
        "Le changement le moins visible est aussi le plus durable. La part entre le brut et la "
        f"pompe est passée d'environ {m_old:.0f} centimes par litre en 2019 à 2021 à environ "
        f"{m_new:.0f} centimes sur les douze derniers mois."))
    st.markdown(tr(
        "Changes in crude reach the pump quickly, mostly within the same month (pass-through of "
        f"{pt.up:.2f} for increases and {pt.down:.2f} for decreases). {asym}",
        "Les variations du brut arrivent vite à la pompe, surtout dans le même mois (répercussion "
        f"de {pt.up:.2f} pour les hausses et {pt.down:.2f} pour les baisses). {asym}"))
    st.markdown(tr(
        f"Where you fill up matters too. In a normal week there are about {spread * 100:.0f} cents "
        "per litre between the cheapest and the most expensive 10 % of stations, and motorway "
        f"stations charge around {motorway * 100:.0f} cents more than the others, roughly "
        f"{motorway * 50:.0f} € on a full tank.",
        f"L'endroit où on fait le plein compte aussi. Une semaine normale, il y a environ "
        f"{spread * 100:.0f} centimes par litre entre les 10 % de stations les moins chères et les "
        f"10 % les plus chères, et les stations d'autoroute sont environ {motorway * 100:.0f} "
        f"centimes plus chères que les autres, soit à peu près {motorway * 50:.0f} € sur un plein."))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### " + tr("What it means", "Ce que ça veut dire"))
        st.markdown(tr(
            "For a driver, the easiest saving is to avoid motorway stations and compare the "
            "stations nearby, instead of waiting for oil to get cheaper. For policy makers, the "
            "2022 flat rebate worked fast and everybody saw it, but it was expensive and helped "
            "everyone the same way. Since crude is a minority of the price, taxes are a strong "
            "lever, and the refining and retail part deserves more attention than it gets, even if "
            "this dataset cannot break it down. For journalists, the price of oil explains why "
            "prices move, not why they are this high.",
            "Pour un automobiliste, l'économie la plus simple est d'éviter les stations d'autoroute "
            "et de comparer les stations autour de chez soi, plutôt que d'attendre que le pétrole "
            "baisse. Pour les décideurs, la remise de 2022 a marché vite et tout le monde l'a vue, "
            "mais elle a coûté cher et aidé tout le monde pareil. Comme le brut ne fait qu'une "
            "petite partie du prix, les taxes sont un levier fort, et la part raffinage et "
            "distribution mérite plus d'attention qu'elle n'en a, même si ces données ne permettent "
            "pas de la détailler. Pour les journalistes, le prix du pétrole explique pourquoi les "
            "prix bougent, pas pourquoi ils sont aussi hauts."))
    with c2:
        st.markdown("#### " + tr("What could be done next", "Ce qu'on pourrait faire ensuite"))
        st.markdown(tr(
            "The obvious next step would be to add the market prices of refined diesel and "
            "gasoline, to separate refinery margins from station margins. Weighting stations by the "
            "volumes they sell would give the real average price paid. Daily prices around each "
            "shock would show how many days it takes for crude to reach the pump. It would also be "
            "interesting to cross the prices with income and car use by department (INSEE data) to "
            "see who is hit hardest.",
            "La suite logique serait d'ajouter les prix de marché du gazole et de l'essence "
            "raffinés, pour séparer la marge des raffineries de celle des stations. Pondérer les "
            "stations par les volumes vendus donnerait le vrai prix moyen payé. Les prix au jour "
            "près autour de chaque choc montreraient en combien de jours le brut arrive à la pompe. "
            "Ce serait aussi intéressant de croiser les prix avec les revenus et l'usage de la "
            "voiture par département (données INSEE) pour voir qui est le plus touché."))
    st.markdown("#### " + tr("Ethics and transparency", "Éthique et transparence"))
    st.info(tr("The data is about stations, not people. All cleaning rules and assumptions are "
               "described in the data quality tab and in utils/constants.py, and the events on the "
               "charts are context rather than proven causes. The code is under the MIT licence "
               "and the data keeps its original licences (Licence Ouverte 2.0 and CC BY 4.0).",
               "Les données portent sur des stations, pas sur des personnes. Toutes les règles de "
               "nettoyage et les hypothèses sont décrites dans l'onglet qualité des données et dans "
               "utils/constants.py, et les événements sur les graphiques sont du contexte, pas des "
               "causes prouvées. Le code est sous licence MIT et les données gardent leurs licences "
               "d'origine (Licence Ouverte 2.0 et CC BY 4.0)."))
    st.caption(tr(f"Computed on {len(g):,} weeks and {len(dec)} months of data. The pass-through "
                  f"model uses {pt.n} months. The station spread is the median weekly gap between "
                  "the 90th and 10th percentiles.",
                  f"Calculé sur {len(g)} semaines et {len(dec)} mois de données. Le modèle de "
                  f"répercussion utilise {pt.n} mois. L'écart entre stations est la médiane de "
                  "l'écart hebdomadaire entre le 90e et le 10e centile."))
