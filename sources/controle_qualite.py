import sys
import csv
from datetime import date
from decimal import Decimal, InvalidOperation

# le chemin du CSV est donné après le nom du script
chemin = sys.argv[1]

COLONNES = ["id_vente", "date_vente", "id_magasin", "ville", "id_produit", "nom_produit",
            "categorie", "quantite", "prix_unitaire_cad", "remise_pct", "statut", "mode_paiement"]
REMISES_PERMISES = {"0", "5", "10", "15", "20"}
STATUTS_PERMIS = {"VALIDEE", "ANNULEE"}

def titre(texte):
    print()
    print("== " + texte)

# ---------- 1. Lecture : le fichier doit être en UTF-8 ----------
with open(chemin, encoding="utf-8", newline="") as f:
    lecteur = csv.reader(f)
    entete = next(lecteur)
    lignes = list(lecteur)

titre("1. Structure")
print("En-tête conforme au dictionnaire :", entete == COLONNES)
print("Lignes de données :", len(lignes))
mal_formees = [l for l in lignes if len(l) != 12]
print("Lignes qui n'ont pas 12 colonnes :", len(mal_formees))
lignes = [l for l in lignes if len(l) == 12]

# ---------- 2. Valeurs manquantes ----------
titre("2. Valeurs manquantes par colonne")
for i, nom in enumerate(COLONNES):
    vides = sum(1 for l in lignes if l[i].strip() == "")
    print(f"{nom:<18} {vides}")

# ---------- 3. Doublons ----------
titre("3. Doublons")
ids = [l[0] for l in lignes]
print("id_vente en double :", len(ids) - len(set(ids)))
print("Lignes entières en double :", len(lignes) - len(set(tuple(l) for l in lignes)))
sans_id = [tuple(l[1:]) for l in lignes]
print("Lignes identiques hors id_vente :", len(sans_id) - len(set(sans_id)))

# ---------- 4. Dates ----------
titre("4. Dates")
dates, invalides = [], 0
for l in lignes:
    try:
        dates.append(date.fromisoformat(l[1]))
    except ValueError:
        invalides += 1
print("Dates invalides :", invalides)
print("Période :", min(dates), "au", max(dates))

# ---------- 5. Cohérence des référentiels ----------
titre("5. Cohérence magasins et produits")
villes_par_magasin, fiche_produit = {}, {}
for l in lignes:
    villes_par_magasin.setdefault(l[2], set()).add(l[3])
    fiche_produit.setdefault(l[4], set()).add((l[5], l[6], l[8]))
print("Magasins :", len(villes_par_magasin), "| villes :", len({l[3] for l in lignes}))
print("Magasins avec plus d'une ville :", sum(1 for v in villes_par_magasin.values() if len(v) > 1))
print("Produits :", len(fiche_produit), "| catégories :", sorted({l[6] for l in lignes}))
print("Produits avec plusieurs noms, catégories ou prix :", sum(1 for v in fiche_produit.values() if len(v) > 1))

# ---------- 6. Valeurs numériques et codes ----------
titre("6. Valeurs numériques et codes")
quantites, prix = [], []
qte_invalides = prix_invalides = 0
for l in lignes:
    try:
        q = int(l[7])
        if q < 1:
            qte_invalides += 1
        quantites.append(q)
    except ValueError:
        qte_invalides += 1
    try:
        p = Decimal(l[8])
        if p <= 0:
            prix_invalides += 1
        prix.append(p)
    except InvalidOperation:
        prix_invalides += 1
print("quantite : de", min(quantites), "à", max(quantites), "| invalides :", qte_invalides)
print("prix_unitaire_cad : de", min(prix), "à", max(prix), "| invalides :", prix_invalides)
print("remise_pct hors {0, 5, 10, 15, 20} :", sum(1 for l in lignes if l[9] not in REMISES_PERMISES))
print("statut hors {VALIDEE, ANNULEE} :", sum(1 for l in lignes if l[10] not in STATUTS_PERMIS))

# ---------- 7. Répartitions ----------
titre("7. Répartitions")
for i, nom in [(10, "statut"), (11, "mode_paiement"), (2, "id_magasin")]:
    compte = {}
    for l in lignes:
        compte[l[i]] = compte.get(l[i], 0) + 1
    print(nom, ":", dict(sorted(compte.items())))
