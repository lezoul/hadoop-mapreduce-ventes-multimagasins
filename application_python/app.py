import pandas as pd
import plotly.express as px
import streamlit as st

from lecture_resultats import DOSSIER, lire_job, provenance

# =====================================================================
# 1. RÉGLAGES : noms des mois, couleurs, format des montants
# =====================================================================
NOMS_MOIS = {"01": "janv.", "02": "févr.", "03": "mars", "04": "avr.", "05": "mai", "06": "juin",
             "07": "juil.", "08": "août", "09": "sept.", "10": "oct.", "11": "nov.", "12": "déc."}
ORDRE_MOIS = list(NOMS_MOIS.values())

# une couleur vive et fixe par ville et par catégorie : la même dans tous les graphiques
COULEURS_VILLE = {"Ottawa": "#2563EB", "Montréal": "#DC2626", "Toronto": "#059669",
                  "Québec": "#7C3AED", "Kingston": "#EA580C", "Gatineau": "#0891B2"}
COULEURS_CATEGORIE = {"Electronique": "#4F46E5", "Maison": "#E11D48",
                      "Sport": "#16A34A", "Bureau": "#F59E0B"}
COULEURS_MAGASIN = px.colors.qualitative.Bold


def dollars(montant, decimales=2):
    """1946613.14 -> '1 946 613,14 $' (format canadien français)."""
    texte = f"{montant:,.{decimales}f}"
    return texte.replace(",", " ").replace(".", ",") + " $"


def texte_md(texte):
    """Streamlit lit les textes comme du Markdown, où deux $ encadrent une formule mathématique :
    on les protège avec une barre oblique inverse."""
    return texte.replace("$", "\\$")


def mise_en_forme(fig, hauteur=380):
    """Format français (virgule décimale, espace des milliers) et style commun à tous les graphiques."""
    fig.update_layout(separators=", ", height=hauteur, margin=dict(l=10, r=10, t=30, b=10),
                      legend_title_text="", plot_bgcolor="white",
                      font=dict(size=13))
    fig.update_yaxes(gridcolor="#E5E7EB")
    return fig


# =====================================================================
# 2. LECTURE DES SORTIES MAPREDUCE (jamais le CSV)
# =====================================================================
st.set_page_config(page_title="Ventes multi-magasins 2025", layout="wide")

detail = lire_job("ca_detail")                       # 1 917 lignes : base de toutes les vues filtrées
detail["mois_affiche"] = detail["mois"].str[5:7].map(NOMS_MOIS)
detail["magasin_ville"] = detail["magasin"] + " " + detail["ville"]
CA_TOTAL_ANNEE = detail["ca"].sum()

# =====================================================================
# 3. FILTRES (barre latérale) : ils s'appliquent à toute la page
# =====================================================================
st.sidebar.header("Filtres")
villes = st.sidebar.multiselect("Ville", sorted(detail["ville"].unique()), placeholder="Toutes")
magasins_possibles = sorted(detail[detail["ville"].isin(villes)]["magasin"].unique()) if villes \
    else sorted(detail["magasin"].unique())
magasins = st.sidebar.multiselect("Magasin", magasins_possibles, placeholder="Tous")
categories = st.sidebar.multiselect("Catégorie", sorted(detail["categorie"].unique()), placeholder="Toutes")
debut, fin = st.sidebar.select_slider("Période", options=ORDRE_MOIS, value=("janv.", "déc."))
st.sidebar.caption("Un filtre vide = toutes les valeurs.")

mois_retenus = ORDRE_MOIS[ORDRE_MOIS.index(debut): ORDRE_MOIS.index(fin) + 1]
vue = detail[detail["mois_affiche"].isin(mois_retenus)]
if villes:
    vue = vue[vue["ville"].isin(villes)]
if magasins:
    vue = vue[vue["magasin"].isin(magasins)]
if categories:
    vue = vue[vue["categorie"].isin(categories)]

# =====================================================================
# 4. EN-TÊTE ET INDICATEURS CLÉS
# =====================================================================
st.title("Ventes multi-magasins 2025")
st.caption(f"Période affichée : {debut} à {fin} 2025 · Unité : CA net en dollars canadiens hors taxes, "
           "ventes VALIDEE uniquement · Source : sorties MapReduce (fichiers part-*), jamais le CSV")

if vue.empty:
    st.warning("Aucune vente ne correspond à ces filtres.")
    st.stop()

par_mois = vue.groupby("mois_affiche")["ca"].sum().reindex(mois_retenus, fill_value=0)
par_magasin = vue.groupby("magasin_ville")["ca"].sum().sort_values(ascending=False)
croissance = (par_mois.iloc[-1] / par_mois.iloc[0] - 1) * 100 if par_mois.iloc[0] > 0 else 0

k1, k2, k3, k4 = st.columns(4)
part_annuelle = f"{vue['ca'].sum() / CA_TOTAL_ANNEE * 100:.1f}".replace(".", ",")
with k1.container(border=True):
    st.metric("CA net de la sélection", dollars(vue["ca"].sum(), 0))
    st.caption(f"{part_annuelle} % du CA annuel")
with k2.container(border=True):
    st.metric(f"Évolution {debut} à {fin}", f"{croissance:+.0f} %")
    st.caption(texte_md(f"{dollars(par_mois.iloc[0], 0)} en {debut}, {dollars(par_mois.iloc[-1], 0)} en {fin}"))
with k3.container(border=True):
    st.metric("Meilleur mois", par_mois.idxmax())
    st.caption(texte_md(dollars(par_mois.max(), 0)))
with k4.container(border=True):
    st.metric("Meilleur magasin", par_magasin.index[0])
    st.caption(texte_md(dollars(par_magasin.iloc[0], 0)))

onglet_analyses, onglet_jobs, onglet_tcd, onglet_prov = st.tabs(
    ["Analyses", "Résultats des jobs 2 à 5", "Tableau croisé par mois", "Provenance et contrôles"])

# =====================================================================
# 5. ONGLET « ANALYSES » : les 4 analyses obligatoires, filtrées
# =====================================================================
with onglet_analyses:
    # ---- 1. CA mensuel ----
    titre, choix = st.columns([3, 2])
    titre.subheader("1. CA mensuel")
    decoupage = choix.radio("Une courbe par", ["Total", "Ville", "Magasin", "Catégorie"],
                            horizontal=True, label_visibility="collapsed")
    colonne = {"Total": None, "Ville": "ville", "Magasin": "magasin_ville", "Catégorie": "categorie"}[decoupage]
    if colonne is None:
        courbes = par_mois.reset_index()
        fig = px.area(courbes, x="mois_affiche", y="ca", markers=True)
        fig.update_traces(line_color="#4F46E5", fillcolor="rgba(79,70,229,0.12)")
    else:
        # tri par mois (2025-01, 2025-02...) pour que chaque courbe relie les mois dans l'ordre
        courbes = vue.groupby(["mois", "mois_affiche", colonne], as_index=False)["ca"].sum().sort_values("mois")
        couleurs = {"ville": COULEURS_VILLE, "categorie": COULEURS_CATEGORIE}.get(colonne)
        fig = px.line(courbes, x="mois_affiche", y="ca", color=colonne, markers=True,
                      color_discrete_map=couleurs, color_discrete_sequence=COULEURS_MAGASIN)
    fig.update_xaxes(categoryorder="array", categoryarray=mois_retenus, title="")
    fig.update_yaxes(title="CA net", ticksuffix=" $", tickformat=",.0f")
    fig.update_traces(hovertemplate="%{x} : %{y:,.2f} $")
    st.plotly_chart(mise_en_forme(fig, 400))

    # ---- 2. CA par magasin et par ville ----
    st.subheader("2. CA par magasin et par ville")
    gauche, droite = st.columns([3, 2])
    magasins_tries = vue.groupby(["ville", "magasin_ville"], as_index=False)["ca"].sum()
    ordre_villes = magasins_tries.groupby("ville")["ca"].sum().sort_values(ascending=False).index
    magasins_tries["ordre"] = magasins_tries["ville"].map({v: i for i, v in enumerate(ordre_villes)})
    magasins_tries = magasins_tries.sort_values(["ordre", "ca"], ascending=[True, False])
    with gauche:
        fig = px.bar(magasins_tries, x="magasin_ville", y="ca", color="ville",
                     color_discrete_map=COULEURS_VILLE, text="ca")
        fig.update_traces(texttemplate="%{text:,.0f} $", textposition="outside",
                          hovertemplate="%{x} : %{y:,.2f} $")
        fig.update_xaxes(title="", categoryorder="array", categoryarray=magasins_tries["magasin_ville"])
        fig.update_yaxes(title="CA net", ticksuffix=" $", tickformat=",.0f")
        st.plotly_chart(mise_en_forme(fig, 420))
    with droite:
        fig = px.treemap(magasins_tries, path=["ville", "magasin_ville"], values="ca",
                         color="ville", color_discrete_map=COULEURS_VILLE)
        fig.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f} $<br>%{percentRoot:.1%}",
                          hovertemplate="%{label} : %{value:,.2f} $")
        st.plotly_chart(mise_en_forme(fig, 420))

    # ---- 3. CA par catégorie ----
    st.subheader("3. CA par catégorie de produits")
    gauche, droite = st.columns([2, 3])
    par_categorie = vue.groupby("categorie", as_index=False)["ca"].sum().sort_values("ca", ascending=False)
    with gauche:
        fig = px.pie(par_categorie, names="categorie", values="ca", hole=0.55,
                     color="categorie", color_discrete_map=COULEURS_CATEGORIE)
        fig.update_traces(textinfo="percent+label", hovertemplate="%{label} : %{value:,.2f} $")
        fig.update_layout(showlegend=False)
        st.plotly_chart(mise_en_forme(fig, 380))
    with droite:
        cat_ville = vue.groupby(["ville", "categorie"], as_index=False)["ca"].sum()
        fig = px.bar(cat_ville, y="ville", x="ca", color="categorie", orientation="h",
                     color_discrete_map=COULEURS_CATEGORIE,
                     category_orders={"ville": list(ordre_villes), "categorie": list(par_categorie["categorie"])})
        fig.update_traces(hovertemplate="%{y} : %{x:,.2f} $")
        fig.update_xaxes(title="CA net", ticksuffix=" $", tickformat=",.0f")
        fig.update_yaxes(title="", autorange="reversed")
        fig.update_layout(title_text="Poids des catégories dans chaque ville", title_font_size=14)
        st.plotly_chart(mise_en_forme(fig, 380))

    # ---- 4. Top produits ----
    titre, choix = st.columns([3, 2])
    titre.subheader("4. Top produits selon le CA net")
    nombre = choix.slider("Nombre de produits", 5, 20, 5)
    top = (vue.groupby(["nom_produit", "categorie"], as_index=False)["ca"].sum()
              .sort_values("ca", ascending=False).head(nombre))
    fig = px.bar(top, x="ca", y="nom_produit", color="categorie", orientation="h", text="ca",
                 color_discrete_map=COULEURS_CATEGORIE)
    fig.update_traces(texttemplate="%{text:,.0f} $", textposition="outside",
                      hovertemplate="%{y} : %{x:,.2f} $")
    fig.update_yaxes(title="", categoryorder="total ascending")
    fig.update_xaxes(title="CA net", ticksuffix=" $", tickformat=",.0f", range=[0, top["ca"].max() * 1.18])
    st.plotly_chart(mise_en_forme(fig, 120 + 38 * nombre))

# =====================================================================
# 6. ONGLET « TABLEAU CROISÉ » : hiérarchie en lignes, mois en colonnes
# =====================================================================
NIVEAUX = {"Ville": "ville", "Magasin": "magasin", "Catégorie": "categorie", "Produit": "nom_produit"}


def lignes_tcd(donnees, niveaux, profondeur=0):
    """Construit les lignes du tableau croisé avec un sous-total à chaque niveau."""
    lignes = []
    totaux_groupes = donnees.groupby(niveaux[0])["ca"].sum().sort_values(ascending=False)
    for valeur in totaux_groupes.index:
        groupe = donnees[donnees[niveaux[0]] == valeur]
        par_mois_groupe = groupe.groupby("mois_affiche")["ca"].sum()
        ligne = {"Ligne": "\u2003" * profondeur + str(valeur), "profondeur": profondeur}
        for m in mois_retenus:
            ligne[m] = par_mois_groupe.get(m, 0)
        lignes.append(ligne)
        if len(niveaux) > 1:
            lignes += lignes_tcd(groupe, niveaux[1:], profondeur + 1)
    return lignes


with onglet_tcd:
    st.subheader("Tableau croisé dynamique : CA net par mois (en $)")
    choix_niveaux = st.multiselect("Niveaux en lignes (dans l'ordre choisi)", list(NIVEAUX),
                                   default=["Ville", "Magasin", "Catégorie"])
    if not choix_niveaux:
        st.info("Choisis au moins un niveau.")
    else:
        niveaux = [NIVEAUX[n] for n in choix_niveaux]
        tcd = pd.DataFrame(lignes_tcd(vue, niveaux))
        total = {"Ligne": "TOTAL GÉNÉRAL", "profondeur": -1}
        for m in mois_retenus:
            total[m] = par_mois.get(m, 0)
        tcd = pd.concat([tcd, pd.DataFrame([total])], ignore_index=True)
        tcd["Total"] = tcd[mois_retenus].sum(axis=1)
        dernier = len(niveaux) - 1

        def style_ligne(ligne):
            if ligne["profondeur"] == -1:
                return ["font-weight: 700; background-color: #E0E7FF"] * len(ligne)
            if ligne["profondeur"] < dernier:
                teinte = ["#EEF2FF", "#F5F7FF", "#FAFBFF"][min(ligne["profondeur"], 2)]
                return [f"font-weight: 600; background-color: {teinte}"] * len(ligne)
            return [""] * len(ligne)

        colonnes = ["Ligne"] + mois_retenus + ["Total"]
        tableau = (tcd.style.apply(style_ligne, axis=1)
                   .format(lambda x: dollars(x, 0)[:-2], subset=mois_retenus + ["Total"]))
        st.dataframe(tableau, hide_index=True, column_order=colonnes,
                     height=min(38 * (len(tcd) + 1), 700))

    st.subheader("Détail par ville (cliquer pour ouvrir)")
    for ville, ca_ville in vue.groupby("ville")["ca"].sum().sort_values(ascending=False).items():
        part = f"{ca_ville / vue['ca'].sum() * 100:.1f}".replace(".", ",")
        with st.expander(texte_md(f"{ville} · {dollars(ca_ville, 0)} · {part} % de la sélection")):
            dans_ville = vue[vue["ville"] == ville]
            sous_tcd = pd.DataFrame(lignes_tcd(dans_ville, ["magasin", "categorie"]))
            sous_tcd["Total"] = sous_tcd[mois_retenus].sum(axis=1)
            st.dataframe(sous_tcd.style.apply(
                lambda l: ["font-weight: 600; background-color: #EEF2FF" if l["profondeur"] == 0 else ""] * len(l),
                axis=1).format(lambda x: dollars(x, 0)[:-2], subset=mois_retenus + ["Total"]),
                hide_index=True, column_order=["Ligne"] + mois_retenus + ["Total"])

# =====================================================================
# 7. ONGLET « PROVENANCE ET CONTRÔLES »
# =====================================================================
with onglet_prov:
    gauche, droite = st.columns(2)
    with gauche:
        st.subheader("Fichiers MapReduce lus")
        st.write(f"Dossier : `{DOSSIER}`")
        st.dataframe(provenance().rename(columns={"job": "Job", "fichier": "Fichier", "lignes": "Lignes"}),
                     hide_index=True)
    with droite:
        st.subheader("Contrôle de cohérence (année complète)")
        controle = pd.DataFrame([
            {"Job": job, "Total": dollars(lire_job(job)["ca"].sum())}
            for job in ["ca_detail", "ca_mois", "ca_magasin", "ca_categorie", "ca_produit"]
        ])
        st.dataframe(controle, hide_index=True)
        if controle["Total"].nunique() == 1:
            st.success("Les 5 jobs donnent le même total : aucune vente perdue ni comptée deux fois.")
        else:
            st.error("Les totaux diffèrent entre les jobs : vérifier les sorties MapReduce.")

    st.subheader("Règles de calcul")
    st.markdown(
        "- Montant net d'une vente = quantité × prix unitaire × (1 − remise_pct / 100)\n"
        "- Arrondi au cent par vente (0,5 arrondi vers le haut), avant toute somme\n"
        "- Ventes ANNULEE exclues\n"
        "- Toutes les agrégations sont faites par MapReduce (Hadoop Streaming). L'application lit les "
        "1 917 lignes de `ca_detail` et ne fait que filtrer et regrouper ces lignes déjà agrégées ; "
        "l'onglet « Résultats des jobs 2 à 5 » affiche les sorties des 4 jobs chaînés telles quelles."
    )


# =====================================================================
# 8. ONGLET « RÉSULTATS DES JOBS 2 À 5 » : les sorties agrégées, telles quelles
# =====================================================================
def tableau_job(job, colonnes, tri=None):
    """Sortie d'un job agrégé, prête à afficher : morceaux de la clé, CA en $ et en cents."""
    tableau = lire_job(job)
    if tri == "ca":
        tableau = tableau.sort_values("cents", ascending=False)
    tableau = tableau.rename(columns=colonnes)
    tableau["CA net"] = tableau["ca"].map(dollars)
    tableau = tableau.rename(columns={"cents": "Valeur (cents)"})
    return tableau[list(colonnes.values()) + ["CA net", "Valeur (cents)"]]


with onglet_jobs:
    st.caption("Sorties des jobs 2 à 5, chaînés sur ca_detail, affichées telles que MapReduce les a écrites "
               "(fichiers part-*, année complète, sans filtre). Clé et valeur : clé<TAB>montant en cents.")
    haut_g, haut_d = st.columns(2)
    with haut_g:
        st.subheader("Job 2 · ca_mois")
        st.caption("Clé : mois · 12 lignes · resultats/ca_mois/part-00000")
        mois = tableau_job("ca_mois", {"mois": "Mois"})
        mois["Mois"] = mois["Mois"].str[5:7].map(NOMS_MOIS) + " 2025"
        st.dataframe(mois, hide_index=True, width="stretch")
    with haut_d:
        st.subheader("Job 3 · ca_magasin")
        st.caption("Clé : magasin|ville · 8 lignes · resultats/ca_magasin/part-00000")
        st.dataframe(tableau_job("ca_magasin", {"magasin": "Magasin", "ville": "Ville"}, tri="ca"),
                     hide_index=True, width="stretch")
        st.subheader("Job 4 · ca_categorie")
        st.caption("Clé : categorie · 4 lignes · resultats/ca_categorie/part-00000")
        st.dataframe(tableau_job("ca_categorie", {"categorie": "Catégorie"}, tri="ca"),
                     hide_index=True, width="stretch")
    st.subheader("Job 5 · ca_produit")
    st.caption("Clé : id_produit|nom_produit|categorie · 20 lignes · resultats/ca_produit/part-00000 · "
               "les 5 premières lignes forment le Top 5")
    produits = tableau_job("ca_produit", {"id_produit": "Produit", "nom_produit": "Nom", "categorie": "Catégorie"},
                           tri="ca")
    produits.insert(0, "Rang", range(1, len(produits) + 1))
    st.dataframe(produits, hide_index=True, width="stretch")
