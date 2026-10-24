"""English / French texts. The language is chosen in the sidebar and kept in session_state."""
import streamlit as st

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"],
}
MONTHS_SHORT = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "fr": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.",
           "nov.", "déc."],
}

# menu labels are the same in both languages (French fuel names), only the names used
# inside sentences change
FUEL_LABELS = {"Gazole": "Gazole (diesel)", "E10": "SP95-E10", "SP98": "SP98",
               "SP95": "SP95 (E5)", "E85": "E85", "GPLc": "GPLc (LPG)"}
FUEL_INLINE = {
    "Gazole": ("diesel", "gazole"), "E10": ("SP95-E10", "SP95-E10"), "SP98": ("SP98", "SP98"),
    "SP95": ("SP95", "SP95"), "E85": ("E85", "E85"), "GPLc": ("LPG", "GPLc"),
}
COMPONENT_NAMES = {
    "Crude oil (Brent)": "Pétrole brut (Brent)",
    "Refining, logistics & retail": "Raffinage, logistique et distribution",
    "TICPE excise": "TICPE",
    "VAT 20%": "TVA 20 %",
    "VAT": "TVA",
}


def lang():
    return st.session_state.get("lang", "en")


def tr(en, fr):
    return fr if lang() == "fr" else en


def fuel_name(fuel, inline=False):
    if inline:
        return FUEL_INLINE[fuel][lang() == "fr"]
    return FUEL_LABELS[fuel]


def pick(widget, label, options, labels, name, **kw):
    """radio or selectbox whose option labels change with the language.

    the key depends on the language (so streamlit does not mix up old and new labels) and the
    chosen value is saved separately, so switching language keeps the selection.
    """
    saved = st.session_state.get(f"{name}_saved")
    index = options.index(saved) if saved in options else kw.pop("index", 0)
    kw.pop("index", None)
    value = widget(label, options, index=index, format_func=labels.get, key=f"{name}_{lang()}", **kw)
    st.session_state[f"{name}_saved"] = value
    return value


def comp_name(comp):
    return COMPONENT_NAMES[comp] if lang() == "fr" else comp


def month_year(ts, short=False):
    months = (MONTHS_SHORT if short else MONTHS)[lang()]
    return f"{months[ts.month - 1]} {ts.year}"


def full_date(ts):
    return f"{ts.day} {MONTHS_SHORT[lang()][ts.month - 1]} {ts.year}"
