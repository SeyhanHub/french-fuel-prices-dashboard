"""Detailed tabs: price breakdown and pass-through, regional comparison, scenarios."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.constants import DECOMPOSABLE, LITRES_PER_BARREL, SEEDS, TICPE_EUR_L, VAT
from utils.i18n import comp_name, fuel_name, full_date, month_year, pick, tr
from utils.io import load_geojson
from utils.prep import (asymmetry_significant, decompose, dept_period, lag_correlation,
                        pass_through, region_weekly, road_premium, what_if_price)
from utils.viz import (COMPONENT_COLORS, FUEL_COLORS, MUTED, PALETTE, add_events, bar_chart,
                       base_layout, choropleth, show, small_multiples, stacked_area)

COMPONENTS = ["Crude oil (Brent)", "Refining, logistics & retail", "TICPE excise", "VAT 20%"]


def eur_l():
    return tr("€ per litre", "€ par litre")


def _decomposable_fuel(f) -> str:
    if f.main_fuel in DECOMPOSABLE:
        return f.main_fuel
    st.info(tr(f"{fuel_name(f.main_fuel)} is not made from crude oil in the same way and is taxed "
               "differently, so this tab shows diesel instead.",
               f"Le {fuel_name(f.main_fuel)} n'est pas fabriqué à partir du pétrole de la même "
               "façon et n'a pas les mêmes taxes, donc cet onglet montre le gazole à la place."))
    return "Gazole"


# oil and pump
def render_drivers(tables: dict, f) -> None:
    fuel = _decomposable_fuel(f)
    fi = fuel_name(fuel, True)
    dec_all = decompose(tables["monthly_with_brent"], fuel)
    dec = dec_all[dec_all["month"].between(f.start - pd.offsets.MonthBegin(1), f.end)]
    if len(dec) < 6:
        st.warning(tr("This tab needs a date range of at least 6 months.",
                      "Cet onglet a besoin d'une période d'au moins 6 mois."))
        return
    shares = dec[COMPONENTS].div(dec[COMPONENTS].sum(axis=1), axis=0).mean()
    crude_share = shares["Crude oil (Brent)"] * 100
    tax_share = (shares["TICPE excise"] + shares["VAT 20%"]) * 100
    margin = dec_all.set_index("month")["Refining, logistics & retail"]
    m_1921 = margin["2019":"2021"].mean()
    m_last = margin.iloc[-12:].mean()

    st.subheader(tr(f"Crude oil is only about {crude_share:.0f} % of the price of {fi}, while "
                    f"taxes make up about {tax_share:.0f} %.",
                    f"Le pétrole brut ne fait qu'environ {crude_share:.0f} % du prix du {fi}, "
                    f"alors que les taxes en font environ {tax_share:.0f} %."))
    st.markdown(tr(
        "Each litre sold in France pays a fixed excise tax called TICPE, and then 20 % VAT on the "
        "whole amount, the excise included. What is left is the crude oil itself plus everything "
        "needed to refine it, transport it, store it and sell it, margins included. I rebuilt this "
        "split for every month from the average pump price and the Brent price.",
        "Chaque litre vendu en France paie une taxe fixe, la TICPE, puis 20 % de TVA sur le tout, "
        "TICPE comprise. Le reste, c'est le pétrole brut et tout ce qu'il faut pour le raffiner, le "
        "transporter, le stocker et le vendre, marges comprises. J'ai refait ce découpage pour "
        "chaque mois à partir du prix moyen à la pompe et du prix du Brent."))
    with st.expander(tr("Method and assumptions", "Méthode et hypothèses"), expanded=False):
        st.markdown(tr(
            f"The crude oil part is the monthly Brent price in euros per barrel divided by "
            f"{LITRES_PER_BARREL} litres. The excise is {TICPE_EUR_L[fuel]:.4f} €/L for {fi}, "
            "which is the metropolitan rate including the regional part; it has not changed since "
            "2018 and I assume it stayed constant. VAT is 20 % of the price before VAT, which means "
            "one sixth of the pump price. In 2022 the State paid a rebate of 18, then 30, then 10 "
            "cents per litre, and the prices declared by stations already include it, so I add it "
            "back before splitting the price. The refining, logistics and retail part is simply "
            "what remains. It includes the refining margin, the cost of blending biofuels, storage "
            "obligations, transport and the station's gross margin, so it should not be read as a "
            "profit.",
            f"La part du pétrole brut, c'est le prix mensuel du Brent en euros par baril divisé par "
            f"{LITRES_PER_BARREL} litres. La TICPE est de {TICPE_EUR_L[fuel]:.4f} €/L pour le {fi}, "
            "c'est le taux métropolitain avec la part régionale ; il n'a pas bougé depuis 2018 et je "
            "le considère constant. La TVA fait 20 % du prix hors TVA, donc un sixième du prix à la "
            "pompe. En 2022 l'État a payé une remise de 18, puis 30, puis 10 centimes par litre, et "
            "les prix déclarés par les stations l'incluent déjà, donc je la rajoute avant de "
            "découper le prix. La part raffinage, logistique et distribution est juste ce qui "
            "reste. Elle comprend la marge de raffinage, le coût des biocarburants, les obligations "
            "de stockage, le transport et la marge brute de la station, donc ce n'est pas un "
            "bénéfice."))
    fig = stacked_area(dec, COMPONENTS, tr(f"What a litre of {fi} is made of, monthly (€/L)",
                                           f"Ce qui compose un litre de {fi}, par mois (€/L)"))
    show(fig, alt=tr(
        f"Stacked area chart of the monthly price of {fi} split into four layers, from bottom to "
        "top: crude oil, refining and retail, excise and VAT. A dotted line shows the actual pump "
        "price, which goes below the stack in 2022 because of the State rebate. The excise layer "
        "is flat, so almost all the variation comes from crude oil and from the refining and "
        "retail layer.",
        f"Aires empilées du prix mensuel du {fi} découpé en quatre couches, de bas en haut : "
        "pétrole brut, raffinage et distribution, TICPE et TVA. La ligne en pointillé montre le "
        "vrai prix à la pompe, qui passe sous l'empilement en 2022 à cause de la remise de l'État. "
        "La couche TICPE est plate, donc presque toute la variation vient du brut et de la couche "
        "raffinage et distribution."),
         data=dec[["month", "pump", "rebate"] + COMPONENTS], key="drivers_stack")

    c1, c2, c3 = st.columns(3)
    c1.metric(tr("Refining and retail, 2019 to 2021", "Raffinage et distribution, 2019 à 2021"),
              f"{m_1921 * 100:.0f} c€/L")
    c2.metric(tr("Refining and retail, last 12 months", "Raffinage et distribution, 12 derniers mois"),
              f"{m_last * 100:.0f} c€/L", f"{(m_last - m_1921) * 100:+.0f} c€/L",
              delta_color="inverse")
    c3.metric(tr("Taxes per litre, latest month", "Taxes par litre, dernier mois"),
              f"{(dec['TICPE excise'].iloc[-1] + dec['VAT 20%'].iloc[-1]):.2f} €")
    st.warning(tr(
        "Oil explains most of the ups and downs, but the part between the barrel and the pump has "
        f"grown from about {m_1921 * 100:.0f} to about {m_last * 100:.0f} cents per litre. For "
        "diesel this fits with the tight European diesel market since 2022, made worse when the EU "
        "stopped importing refined products from Russia in February 2023. The data cannot tell "
        "refinery margins apart from station margins, so this is a limit of the analysis and not an "
        "accusation against anyone.",
        "Le pétrole explique la plupart des hausses et des baisses, mais la part entre le baril et "
        f"la pompe est passée d'environ {m_1921 * 100:.0f} à environ {m_last * 100:.0f} centimes "
        "par litre. Pour le gazole, ça colle avec le marché européen du diesel tendu depuis 2022, "
        "encore plus quand l'UE a arrêté d'importer des produits raffinés russes en février 2023. "
        "Les données ne permettent pas de séparer la marge des raffineries de celle des stations, "
        "donc c'est une limite de l'analyse et pas une accusation."))

    st.markdown("---")
    st.subheader(tr("Do prices rise faster than they fall?",
                    "Les prix montent-ils plus vite qu'ils ne baissent ?"))
    st.markdown(tr(
        "Economists call this the rockets and feathers effect: prices would shoot up when oil gets "
        "more expensive and drift down slowly when it gets cheaper. Each dot below is one month.",
        "Les économistes appellent ça l'effet fusée et plume : les prix monteraient d'un coup quand "
        "le pétrole augmente et redescendraient lentement quand il baisse. Chaque point ci-dessous "
        "est un mois."))
    pt = pass_through(dec_all)
    left, right = st.columns([3, 2])
    with left:
        d = pt.data
        d["direction"] = np.where(d["db"] >= 0, "up", "down")
        names = {"up": tr("Crude went up", "Le brut a monté"),
                 "down": tr("Crude went down", "Le brut a baissé")}
        fig = go.Figure()
        for key, col in [("up", PALETTE[7]), ("down", PALETTE[0])]:
            g = d[d["direction"] == key]
            fig.add_trace(go.Scatter(
                x=g["db"] * 100, y=g["dp"] * 100, mode="markers", name=names[key],
                marker={"size": 9, "color": col, "line": {"width": 1.5, "color": "white"}},
                customdata=g["month"].dt.strftime("%m/%Y"),
                hovertemplate="%{customdata}<br>" + tr("Change in crude", "Variation du brut")
                              + " %{x:+.1f} c€/L<br>" + tr("Change in pre-tax price",
                                                            "Variation du prix hors taxes")
                              + " %{y:+.1f} c€/L<extra></extra>"))
            if len(g) > 2:
                b = np.polyfit(g["db"], g["dp"], 1)
                xs = np.linspace(g["db"].min(), g["db"].max(), 10)
                fig.add_trace(go.Scatter(x=xs * 100, y=np.polyval(b, xs) * 100, mode="lines",
                                         line={"color": col, "width": 2, "dash": "dash"},
                                         name=tr(f"Fit, {names[key].lower()} (slope {b[0]:.2f})",
                                                 f"Droite, {names[key].lower()} (pente {b[0]:.2f})"),
                                         hoverinfo="skip"))
        lim = max(abs(d["db"]).max(), abs(d["dp"]).max()) * 100 * 1.05
        fig.add_trace(go.Scatter(x=[-lim, lim], y=[-lim, lim], mode="lines",
                                 name=tr("Full pass-through (one for one)",
                                         "Répercussion totale (un pour un)"),
                                 line={"color": MUTED, "width": 1, "dash": "dot"}, hoverinfo="skip"))
        base_layout(fig, tr("Monthly change in crude cost and in the pre-tax pump price (c€/L)",
                            "Variation mensuelle du brut et du prix hors taxes (c€/L)"),
                    tr("Change in pre-tax pump price (c€/L)", "Variation du prix hors taxes (c€/L)"),
                    tr("Change in crude oil cost (c€/L)", "Variation du coût du brut (c€/L)"),
                    height=460)
        fig.update_layout(hovermode="closest")
        show(fig, alt=tr(
            "Scatter plot with one dot per month. The horizontal axis is the change in the cost of "
            "crude per litre and the vertical axis is the change in the pump price before taxes. "
            "Red dots are months when crude went up, blue dots months when it went down, each group "
            "with its own dashed fitted line. The dotted diagonal is what full pass-through would "
            "look like.",
            "Nuage de points avec un point par mois. L'axe horizontal est la variation du coût du "
            "brut par litre et l'axe vertical la variation du prix à la pompe hors taxes. Les points "
            "rouges sont les mois où le brut a monté, les bleus ceux où il a baissé, chaque groupe "
            "avec sa droite en tirets. La diagonale en pointillé montre une répercussion totale."),
             data=d[["month", "db", "dp"]].rename(columns={
                 "db": tr("change in crude €/L", "variation du brut €/L"),
                 "dp": tr("change in pre-tax price €/L", "variation du prix HT €/L")}),
             key="drivers_scatter")
    with right:
        st.metric(tr("Pass-through when crude rises (same and next month)",
                     "Répercussion quand le brut monte (mois même et suivant)"),
                  f"{pt.up:.2f}", tr(f"± {1.96 * pt.up_se:.2f} (95 % interval)",
                                     f"± {1.96 * pt.up_se:.2f} (intervalle à 95 %)"),
                  delta_color="off",
                  help=tr("1.00 means that each cent of increase in crude reaches the pump within "
                          "two months.",
                          "1,00 veut dire que chaque centime de hausse du brut arrive à la pompe en "
                          "deux mois."))
        st.metric(tr("Pass-through when crude falls (same and next month)",
                     "Répercussion quand le brut baisse (mois même et suivant)"),
                  f"{pt.down:.2f}", tr(f"± {1.96 * pt.down_se:.2f} (95 % interval)",
                                       f"± {1.96 * pt.down_se:.2f} (intervalle à 95 %)"),
                  delta_color="off")
        lc = lag_correlation(dec_all)

        def lag_label(k):
            if k == 0:
                return tr("same month", "même mois")
            return tr(f"{k} month{'s' if k > 1 else ''} later", f"{k} mois après")

        fig = bar_chart(lc.assign(lab=lc["lag_months"].map(lag_label)), "correlation", "lab",
                        tr("Correlation between pump and crude changes",
                           "Corrélation entre pompe et brut"),
                        tr("correlation coefficient", "coefficient de corrélation"),
                        color=PALETTE[0], text_fmt=".2f", height=280)
        fig.update_xaxes(range=[min(-0.35, lc["correlation"].min() - 0.25), 1.1])
        show(fig, alt=tr(
            "Bars with the correlation between monthly changes in the pump price and changes in "
            "crude 0 to 4 months earlier. The same-month correlation is much higher than the "
            "others, so most of the reaction happens within a month.",
            "Barres avec la corrélation entre les variations mensuelles du prix à la pompe et "
            "celles du brut 0 à 4 mois plus tôt. Celle du même mois est bien plus haute que les "
            "autres, donc l'essentiel de la réaction se fait dans le mois."), key="drivers_lag")
    if asymmetry_significant(pt):
        verdict = tr(
            f"The gap between the two is statistically significant (difference "
            f"{pt.up - pt.down:.2f} ± {1.96 * pt.diff_se:.2f}), which supports the rockets and "
            "feathers idea, but with monthly data only I would not push it too far.",
            f"L'écart entre les deux est statistiquement significatif (différence "
            f"{pt.up - pt.down:.2f} ± {1.96 * pt.diff_se:.2f}), ce qui va dans le sens de l'effet "
            "fusée et plume, mais avec des données mensuelles je ne pousserais pas trop loin.")
    else:
        verdict = tr("The two confidence intervals overlap, so with monthly data I cannot really "
                     "say that prices rise faster than they fall.",
                     "Les deux intervalles de confiance se chevauchent, donc avec des données "
                     "mensuelles je ne peux pas vraiment dire que les prix montent plus vite qu'ils "
                     "ne baissent.")
    st.info(tr(
        f"Over {pt.n} months of {fi}, increases in crude are passed on at {pt.up:.2f} and "
        f"decreases at {pt.down:.2f}. {verdict} Most of the adjustment happens in the same month, "
        "as the bars on the right show. A value above 1 means that refined fuel prices moved even "
        "more than crude, which is what happened to diesel in 2022.",
        f"Sur {pt.n} mois de {fi}, les hausses du brut sont répercutées à {pt.up:.2f} et les "
        f"baisses à {pt.down:.2f}. {verdict} L'essentiel de l'ajustement se fait dans le mois, "
        "comme le montrent les barres à droite. Une valeur au-dessus de 1 veut dire que le prix du "
        "carburant raffiné a bougé encore plus que le brut, ce qui est arrivé au gazole en 2022."))


# regions
def render_geography(tables: dict, f) -> None:
    fuel = f.main_fuel
    fn, fi = fuel_name(fuel), fuel_name(fuel, True)
    geo = load_geojson()
    names = {ft["properties"]["code"]: ft["properties"]["nom"] for ft in geo["features"]}
    dp = dept_period(tables["dept_road_weekly"], fuel, f.road, f.start, f.end)
    if dp.empty:
        st.warning(tr("No data for this selection.", "Pas de données pour cette sélection."))
        return
    dp["name"] = dp["dept"].map(names).fillna(dp["dept"])
    nat_mean = np.average(dp["price"], weights=dp["n"])
    dp["gap"] = dp["price"] - nat_mean
    dp_view = dp[dp["region"].isin(f.regions)] if f.regions else dp
    if dp_view.empty:
        st.warning(tr("No station matches this region and station type. Brittany for example has "
                      "no toll motorway, so it has no motorway stations. Try another station type.",
                      "Aucune station ne correspond à cette région et ce type de station. La "
                      "Bretagne par exemple n'a pas d'autoroute à péage, donc pas de station "
                      "d'autoroute. Essaie un autre type de station."))
        return
    hi, lo = dp_view.loc[dp_view["price"].idxmax()], dp_view.loc[dp_view["price"].idxmin()]
    diff = (hi["price"] - lo["price"]) * 100
    st.subheader(tr(f"The same litre of {fi} costs {diff:.0f} cents more in {hi['name']} than in "
                    f"{lo['name']}.",
                    f"Entre {hi['name']} et {lo['name']}, le même litre de {fi} a "
                    f"{diff:.0f} centimes d'écart."))
    stations = {"All": tr("all stations", "toutes les stations"),
                "Road": tr("road stations", "stations hors autoroute"),
                "Motorway": tr("motorway stations", "stations d'autoroute")}[f.road]
    st.caption(tr(
        f"Average over the last 4 weeks of the selected period (up to {full_date(f.end)}), "
        f"{stations}. Corsica has its own fuel taxes (VAT is 13 % there) and higher transport "
        "costs, so its position changes a lot over time, as the small charts further down show.",
        f"Moyenne sur les 4 dernières semaines de la période (jusqu'au {full_date(f.end)}), "
        f"{stations}. La Corse a ses propres taxes sur les carburants (TVA à 13 %) et un transport "
        "plus cher, donc sa position change beaucoup dans le temps, comme le montrent les petits "
        "graphiques plus bas."))

    views = {"gap": tr("Gap to national average (c€/L)", "Écart à la moyenne nationale (c€/L)"),
             "price": tr("Average price (€/L)", "Prix moyen (€/L)"),
             "change": tr(f"Change since {month_year(f.start, True)} (c€/L)",
                          f"Évolution depuis {month_year(f.start, True)} (c€/L)")}
    view = pick(st.radio, tr("Map shows", "La carte montre"), list(views), views, "map_view",
                horizontal=True)
    m = dp_view.copy()
    if view == "gap":
        m["z"] = m["gap"] * 100
        fig = choropleth(m, geo, "z", tr(f"{fn}, gap to the national average",
                                         f"{fn}, écart à la moyenne nationale"),
                         tr("c€/L vs national", "c€/L vs national"), diverging=True)
        alt_tail = tr("Blue departments are cheaper than the national average and orange ones "
                      "dearer.", "Les départements en bleu sont moins chers que la moyenne "
                      "nationale et ceux en orange plus chers.")
    elif view == "price":
        m["z"] = m["price"]
        fig = choropleth(m, geo, "z", tr(f"{fn}, average price by department",
                                         f"{fn}, prix moyen par département"), "€/L")
        alt_tail = tr("The darker the blue, the more expensive.", "Plus le bleu est foncé, plus "
                      "c'est cher.")
    else:
        m["z"] = m["change"] * 100
        fig = choropleth(m, geo, "z", tr(f"{fn}, price change by department",
                                         f"{fn}, évolution du prix par département"), "c€/L",
                         diverging=True)
        alt_tail = tr("Orange departments went up more than the others, blue ones less.",
                      "Les départements en orange ont plus augmenté que les autres, ceux en bleu "
                      "moins.")
    left, right = st.columns([3, 2])
    with left:
        show(fig, alt=tr(f"Map of the {len(m)} metropolitan departments coloured by "
                         f"{views[view].lower()}. The most expensive is {hi['name']} at "
                         f"{hi['price']:.3f} €/L and the cheapest is {lo['name']} at "
                         f"{lo['price']:.3f} €/L. {alt_tail}",
                         f"Carte des {len(m)} départements de métropole colorés selon "
                         f"« {views[view].lower()} ». Le plus cher est {hi['name']} à "
                         f"{hi['price']:.3f} €/L et le moins cher {lo['name']} à "
                         f"{lo['price']:.3f} €/L. {alt_tail}"),
             data=m[["dept", "name", "region", "price", "gap", "change", "n"]]
                  .sort_values("price", ascending=False),
             key="geo_map")
    with right:
        n_top = st.slider(tr("Number of departments at each end",
                             "Nombre de départements de chaque côté"), 5, 15, 8,
                          key="n_top")
        kinds = {"top": tr("Most expensive", "Les plus chers"), "bottom": tr("Cheapest", "Les moins chers")}
        r = pd.concat([m.nlargest(n_top, "price").assign(kind="top"),
                       m.nsmallest(n_top, "price").assign(kind="bottom")])
        r["label"] = r["name"] + " (" + r["dept"] + ")"
        r["gap_c"] = r["gap"] * 100
        fig = go.Figure()
        for kind, col in [("top", PALETTE[1]), ("bottom", PALETTE[0])]:
            g = r[r["kind"] == kind]
            fig.add_trace(go.Bar(x=g["gap_c"], y=g["label"], orientation="h", name=kinds[kind],
                                 marker={"color": col, "cornerradius": 4},
                                 text=g["price"].map(lambda v: f"{v:.3f} €"), textposition="auto",
                                 hovertemplate="%{y}: %{x:+.1f} c€/L<extra></extra>"))
        base_layout(fig, tr("Departments furthest from the national average",
                            "Départements les plus loin de la moyenne nationale"), "",
                    tr("c€/L compared with the national average",
                       "c€/L par rapport à la moyenne nationale"), height=560)
        fig.update_layout(hovermode="closest")
        fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
        show(fig, alt=tr(f"Bars for the {n_top} most expensive departments (orange, to the right) "
                         f"and the {n_top} cheapest (blue, to the left), measured as the gap to the "
                         "national average in cents per litre. The labels give the actual price.",
                         f"Barres pour les {n_top} départements les plus chers (orange, à droite) "
                         f"et les {n_top} moins chers (bleu, à gauche), en écart à la moyenne "
                         "nationale en centimes par litre. Les étiquettes donnent le vrai prix."),
             key="geo_rank")

    st.markdown("---")
    st.subheader(tr("How much more you pay on the motorway", "Combien on paie de plus sur l'autoroute"))
    rp = road_premium(tables["dept_road_weekly"], fuel, f.regions, f.start, f.end)
    if not rp.empty:
        latest = rp["premium"].iloc[-4:].mean()
        c1, c2 = st.columns([1, 3])
        c1.metric(tr("Motorway extra cost, last 4 weeks", "Surcoût autoroute, 4 dernières semaines"),
                  f"{latest * 100:.0f} c€/L",
                  tr(f"about {latest * 50:.0f} € for a 50 L tank",
                     f"environ {latest * 50:.0f} € sur un plein de 50 L"), delta_color="off")
        c1.caption(tr("Motorway stations are run under concessions, have few competitors and have "
                      "to stay open day and night. The gap is there all the time, not only during "
                      "crises.",
                      "Les stations d'autoroute sont en concession, ont peu de concurrents et "
                      "doivent rester ouvertes jour et nuit. L'écart est là tout le temps, pas "
                      "seulement pendant les crises."))
        fig = go.Figure(go.Scatter(x=rp["week"], y=rp["premium"] * 100, mode="lines",
                                   line={"color": FUEL_COLORS.get(fuel, PALETTE[0]), "width": 2},
                                   name=tr("Motorway minus road", "Autoroute moins route"),
                                   hovertemplate="%{y:.1f} c€/L"))
        base_layout(fig, tr(f"Motorway price minus road price, {fi} (weekly, c€/L)",
                            f"Prix autoroute moins prix route, {fi} (par semaine, c€/L)"),
                    "c€/L", legend=False, height=340)
        add_events(fig, f.start, f.end)
        with c2:
            show(fig, alt=tr(f"Line showing the weekly gap between motorway stations and other "
                             f"stations for {fi}. It is currently about {latest * 100:.0f} cents "
                             "per litre.",
                             f"Courbe de l'écart chaque semaine entre les stations d'autoroute et "
                             f"les autres pour le {fi}. Il est en ce moment d'environ "
                             f"{latest * 100:.0f} centimes par litre."),
                 data=rp, key="geo_premium")

    st.markdown("---")
    st.subheader(tr("Each region compared with the national average",
                    "Chaque région comparée à la moyenne nationale"))
    rw = region_weekly(tables["dept_road_weekly"], fuel, f.road, f.start, f.end)
    if f.regions:
        rw = rw[rw["region"].isin(f.regions)]
    if rw.empty:
        return
    fig = small_multiples(rw, tr(f"{fn}, regional price minus national average (c€/L)",
                                 f"{fn}, prix régional moins moyenne nationale (c€/L)"))
    gaps = rw.groupby("region")["gap"].mean().sort_values()
    nreg = rw["region"].nunique()
    show(fig, alt=tr(
        f"Grid of {nreg} small line charts, one per region, all on the same scale, showing each "
        "week how far the region is from the national average in cents per litre. On average the "
        f"cheapest region is {gaps.index[0]} ({gaps.iloc[0] * 100:+.1f} c€) and the most expensive "
        f"is {gaps.index[-1]} ({gaps.iloc[-1] * 100:+.1f} c€).",
        f"Grille de {nreg} petites courbes, une par région, toutes à la même échelle, qui montrent "
        "chaque semaine l'écart de la région à la moyenne nationale en centimes par litre. En "
        f"moyenne la région la moins chère est {gaps.index[0]} ({gaps.iloc[0] * 100:+.1f} c€) et "
        f"la plus chère {gaps.index[-1]} ({gaps.iloc[-1] * 100:+.1f} c€)."),
         data=gaps.mul(100).rename(tr("average gap in c€/L", "écart moyen en c€/L")).reset_index(),
         key="geo_multiples")

    st.markdown("---")
    st.subheader(tr("Station by station, latest price", "Station par station, dernier prix"))
    snap = tables["stations_snapshot"]
    s = snap[(snap["fuel"] == fuel) & snap["coords_valid"]]
    if f.regions:
        s = s[s["region"].isin(f.regions)]
    if f.road != "All":
        s = s[s["road"] == f.road]
    if s.empty:
        st.info(tr("No station with a recent price for this selection.",
                   "Aucune station avec un prix récent pour cette sélection."))
        return
    c1, c2 = st.columns([2, 1])
    with c2:
        fig = go.Figure(go.Histogram(x=s["price"], xbins={"size": 0.01}, marker={"color": PALETTE[0]},
                                     hovertemplate="%{x} €/L: %{y} stations<extra></extra>"))
        med = s["price"].median()
        fig.add_vline(x=med, line_dash="dot", line_color=MUTED,
                      annotation_text=tr(f"median {med:.3f} €", f"médiane {med:.3f} €"),
                      annotation_position="top right")
        base_layout(fig, tr("Distribution of station prices", "Répartition des prix des stations"),
                    tr("number of stations", "nombre de stations"), eur_l(), legend=False, height=380)
        fig.update_layout(hovermode="closest", bargap=0.05)
        p10, p90 = s["price"].quantile(.1), s["price"].quantile(.9)
        show(fig, alt=tr(f"Histogram of the latest price at {len(s):,} stations. The median is "
                         f"{med:.3f} €/L, the 10th percentile {p10:.3f} and the 90th percentile "
                         f"{p90:.3f}.",
                         f"Histogramme du dernier prix de {len(s):,} stations. La médiane est à "
                         f"{med:.3f} €/L, le 10e centile à {p10:.3f} et le 90e à {p90:.3f}."
                         .replace(",", " ")), key="geo_hist")
    with c1:
        sample = s.sample(min(len(s), SEEDS["map_sample_stations"]), random_state=SEEDS["random_seed"])
        road_names = {"Road": tr("road", "route"), "Motorway": tr("motorway", "autoroute"),
                      "Unknown": "?"}
        fig = go.Figure(go.Scattermap(
            lat=sample["lat"], lon=sample["lon"], mode="markers",
            marker={"size": 6, "color": sample["price"],
                    "colorscale": [[0, "#cde2fb"], [0.5, "#3987e5"], [1, "#0d366b"]],
                    "cmin": s["price"].quantile(.05), "cmax": s["price"].quantile(.95),
                    "colorbar": {"title": "€/L", "thickness": 12}},
            customdata=np.stack([sample["city"].fillna(""), sample["road"].map(road_names),
                                 sample["price"]], axis=1),
            hovertemplate="%{customdata[0]}, %{customdata[1]}<br>%{customdata[2]:.3f} €/L<extra></extra>"))
        n_s = f"{len(sample):,}".replace(",", " ")
        fig.update_layout(map={"style": "carto-positron", "center": {"lat": 46.6, "lon": 2.4},
                               "zoom": 4.4}, height=520, margin={"l": 0, "r": 0, "t": 40, "b": 0},
                          title={"text": tr(f"Random sample of {n_s} stations (seed {SEEDS['random_seed']})",
                                            f"Échantillon aléatoire de {n_s} stations (graine "
                                            f"{SEEDS['random_seed']})"),
                                 "x": 0, "font": {"size": 16}})
        by_region = s.groupby("region")["price"].median().sort_values()
        show(fig, alt=tr(f"Map of {n_s} stations picked at random and coloured by their latest "
                         "price, darker meaning more expensive. You can zoom in. The region with the "
                         f"highest median is {by_region.index[-1]} ({by_region.iloc[-1]:.3f} €/L) "
                         f"and the lowest is {by_region.index[0]} ({by_region.iloc[0]:.3f} €/L).",
                         f"Carte de {n_s} stations tirées au hasard et colorées selon leur dernier "
                         "prix, plus foncé voulant dire plus cher. On peut zoomer. La région avec "
                         f"la médiane la plus haute est {by_region.index[-1]} "
                         f"({by_region.iloc[-1]:.3f} €/L) et la plus basse {by_region.index[0]} "
                         f"({by_region.iloc[0]:.3f} €/L)."), key="geo_stations")


# scenarios
def render_what_if(tables: dict, f) -> None:
    fuel = _decomposable_fuel(f)
    fi = fuel_name(fuel, True)
    dec = decompose(tables["monthly_with_brent"], fuel)
    last = dec.iloc[-1]
    margin_last = last["Refining, logistics & retail"]
    margin_12m = dec["Refining, logistics & retail"].iloc[-12:].mean()
    margin_1921 = dec.set_index("month")["Refining, logistics & retail"]["2019":"2021"].mean()

    st.subheader(tr("What would your fuel bill look like if things changed?",
                    "À quoi ressemblerait ta facture de carburant si les choses changeaient ?"))
    st.markdown(tr(
        f"The sliders let you build a scenario for {fi}. The calculation is the same as in the "
        "price breakdown: crude, plus refining and retail, plus excise, with VAT on top. By default "
        f"everything is set to the latest month for which Brent is available "
        f"({month_year(last['month'])}).",
        f"Les curseurs permettent de construire un scénario pour le {fi}. Le calcul est le même que "
        "dans la décomposition du prix : brut, plus raffinage et distribution, plus TICPE, avec la "
        "TVA par-dessus. Par défaut tout est réglé sur le dernier mois où le Brent est disponible "
        f"({month_year(last['month'])})."))
    c1, c2 = st.columns([2, 3])
    with c1:
        brent = st.slider(tr("Brent crude (€/barrel)", "Brent (€/baril)"), 20, 160,
                          int(round(last["brent_eur_bbl"])), 1,
                          help=tr("Between 2019 and 2026 Brent went from about 20 € (April 2020) "
                                  "to about 100 € (2022 and 2026).",
                                  "Entre 2019 et 2026 le Brent est allé d'environ 20 € (avril "
                                  "2020) à environ 100 € (2022 et 2026)."))
        choices = {
            "last": tr(f"Latest month ({margin_last * 100:.0f} c€/L)",
                       f"Dernier mois ({margin_last * 100:.0f} c€/L)"),
            "12m": tr(f"Average of the last 12 months ({margin_12m * 100:.0f} c€/L)",
                      f"Moyenne des 12 derniers mois ({margin_12m * 100:.0f} c€/L)"),
            "1921": tr(f"2019 to 2021 level ({margin_1921 * 100:.0f} c€/L)",
                       f"Niveau 2019 à 2021 ({margin_1921 * 100:.0f} c€/L)"),
            "custom": tr("Custom", "Personnalisé"),
        }
        choice = pick(st.radio, tr("Refining and retail part", "Part raffinage et distribution"),
                      list(choices), choices, "margin_choice")
        if choice == "last":
            margin = margin_last
        elif choice == "12m":
            margin = margin_12m
        elif choice == "1921":
            margin = margin_1921
        else:
            margin = st.slider(tr("Custom value (c€/L)", "Valeur choisie (c€/L)"), 10, 90,
                               int(margin_last * 100)) / 100
        ticpe = st.slider(tr("TICPE excise (c€/L)", "TICPE (c€/L)"), 0.0, 80.0,
                          TICPE_EUR_L[fuel] * 100, 0.5,
                          help=tr("Current metropolitan rate. Lower it to simulate a tax cut.",
                                  "Taux actuel en métropole. Baisse-le pour simuler une baisse "
                                  "de taxe.")) / 100
        vat = st.slider(tr("VAT rate (%)", "Taux de TVA (%)"), 0.0, 20.0, VAT * 100, 0.5) / 100
        st.markdown("**" + tr("Your driving", "Ta conduite") + "**")
        km = st.number_input(tr("Kilometres per year", "Kilomètres par an"), 1000, 60000, 13000, 500,
                             help=tr("A private car in France does around 12 000 to 13 000 km a year.",
                                     "Une voiture particulière fait environ 12 000 à 13 000 km par "
                                     "an en France."))
        cons = st.number_input(tr("Consumption (L/100 km)", "Consommation (L/100 km)"),
                               3.0, 15.0, 6.0, 0.1)

    # the baseline uses the latest month, so it gives back the observed average pump price
    base = what_if_price(last["brent_eur_bbl"], margin_last, TICPE_EUR_L[fuel], VAT)
    scen = what_if_price(brent, margin, ticpe, vat)
    litres = km * cons / 100
    taxes = scen["TICPE excise"] + scen["VAT"]
    with c2:
        k1, k2, k3 = st.columns(3)
        k1.metric(tr("Scenario pump price", "Prix à la pompe du scénario"), f"{scen['pump']:.3f} €/L",
                  tr(f"{(scen['pump'] - base['pump']) * 100:+.1f} c€ vs {month_year(last['month'], True)}",
                     f"{(scen['pump'] - base['pump']) * 100:+.1f} c€ vs {month_year(last['month'], True)}"),
                  delta_color="inverse")
        k2.metric(tr("Your yearly fuel bill", "Ta facture annuelle"),
                  f"{scen['pump'] * litres:,.0f} €".replace(",", " "),
                  tr(f"{(scen['pump'] - base['pump']) * litres:+,.0f} € per year",
                     f"{(scen['pump'] - base['pump']) * litres:+,.0f} € par an").replace(",", " "),
                  delta_color="inverse")
        k3.metric(tr("Taxes in that bill", "Taxes dans cette facture"),
                  f"{taxes * litres:,.0f} €".replace(",", " "),
                  tr(f"{taxes / scen['pump'] * 100:.0f} % of the price",
                     f"{taxes / scen['pump'] * 100:.0f} % du prix"), delta_color="off")
        parts = ["Crude oil (Brent)", "Refining, logistics & retail", "TICPE excise", "VAT"]
        today, scenario = tr("Today", "Aujourd'hui"), tr("Scenario", "Scénario")
        comp = pd.DataFrame({"component": [comp_name(p) for p in parts],
                             today: [base[c] for c in parts],
                             scenario: [scen[c] for c in parts]})
        fig = go.Figure()
        for p, (_, row) in zip(parts, comp.iterrows()):
            fig.add_trace(go.Bar(y=[today, scenario], x=[row[today], row[scenario]],
                                 orientation="h", name=row["component"],
                                 marker={"color": COMPONENT_COLORS[p]},
                                 hovertemplate=f"{row['component']}: %{{x:.3f}} €/L<extra></extra>"))
        base_layout(fig, tr("What the litre is made of (€/L)", "Ce qui compose le litre (€/L)"),
                    "", eur_l(), height=300)
        fig.update_layout(barmode="stack", hovermode="closest", bargap=0.35)
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
        show(fig, alt=tr(f"Two stacked bars comparing the current price ({base['pump']:.3f} €/L) "
                         f"with the scenario ({scen['pump']:.3f} €/L), each split into crude, "
                         "refining and retail, excise and VAT.",
                         f"Deux barres empilées qui comparent le prix actuel ({base['pump']:.3f} "
                         f"€/L) au scénario ({scen['pump']:.3f} €/L), chacune découpée en brut, "
                         "raffinage et distribution, TICPE et TVA."),
             data=comp, key="whatif_bars")
        sens = pd.DataFrame({"brent": np.arange(20, 161, 10)})
        sens["pump"] = sens["brent"].map(lambda b: what_if_price(b, margin, ticpe, vat)["pump"])
        fig = go.Figure(go.Scatter(x=sens["brent"], y=sens["pump"], mode="lines+markers",
                                   line={"color": FUEL_COLORS.get(fuel), "width": 2},
                                   marker={"size": 8},
                                   hovertemplate="Brent %{x} € : %{y:.3f} €/L<extra></extra>"))
        fig.add_vline(x=brent, line_dash="dot", line_color=MUTED,
                      annotation_text=tr("your scenario", "ton scénario"),
                      annotation_position="top left")
        base_layout(fig, tr("Pump price for each Brent level, other settings unchanged",
                            "Prix à la pompe selon le Brent, autres réglages inchangés"),
                    eur_l(), tr("Brent crude (€/barrel)", "Brent (€/baril)"), height=300, legend=False)
        fig.update_layout(hovermode="closest")
        per10 = 10 / LITRES_PER_BARREL * (1 + vat) * 100
        show(fig, alt=tr(f"Straight line showing that each extra 10 € per barrel adds about "
                         f"{per10:.1f} cents per litre at the pump.",
                         f"Droite qui montre que chaque tranche de 10 € de plus sur le baril ajoute "
                         f"environ {per10:.1f} centimes par litre à la pompe."), key="whatif_sens")
    rule = 10 / LITRES_PER_BARREL * 1.2
    st.info(tr(
        f"As a rough rule, 10 € more on a barrel of Brent adds about {rule * 100:.1f} cents per "
        f"litre at the pump once VAT is included, which is around {rule * litres:.0f} € a year for "
        "the driver described on the left. Cutting the excise by 10 cents saves 12 cents per litre "
        "because of VAT. The model assumes that the refining and retail part stays fixed and that "
        "crude is passed on in full, which is not always true in practice.",
        f"En gros, 10 € de plus sur un baril de Brent ajoutent environ {rule * 100:.1f} centimes "
        f"par litre à la pompe avec la TVA, soit environ {rule * litres:.0f} € par an pour le "
        "conducteur décrit à gauche. Baisser la TICPE de 10 centimes fait gagner 12 centimes par "
        "litre à cause de la TVA. Le modèle suppose que la part raffinage et distribution ne bouge "
        "pas et que le brut est répercuté en entier, ce qui n'est pas toujours vrai en pratique."))
