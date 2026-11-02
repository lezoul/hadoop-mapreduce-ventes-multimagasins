import sys
from decimal import Decimal, ROUND_HALF_UP

# même début que mapper_mois.py : lecture, filtres, calcul du montant
for ligne in sys.stdin:
    ligne = ligne.strip()
    if ligne == "" or ligne.startswith("id_vente"):
        continue
    champs = ligne.split(",")
    if len(champs) != 12:
        continue
    if champs[10] != "VALIDEE":
        continue
    quantite = int(champs[7])
    prix = Decimal(champs[8])
    remise = Decimal(champs[9])
    montant = quantite * prix * (1 - remise / 100)
    cents = int((montant * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    # on récupère toutes les colonnes utiles à la clé
    mois = champs[1][:7]
    magasin = champs[2]
    ville = champs[3]
    id_produit = champs[4]
    nom_produit = champs[5]
    categorie = champs[6]

    # SEULE DIFFÉRENCE avec mapper_mois.py : la clé contient tout, séparé par |
    cle = mois + "|" + magasin + "|" + ville + "|" + categorie + "|" + id_produit + "|" + nom_produit
    print(f"{cle}\t{cents}")
