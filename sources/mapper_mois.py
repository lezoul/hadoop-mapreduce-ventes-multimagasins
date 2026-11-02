import sys
from decimal import Decimal, ROUND_HALF_UP

# Hadoop envoie les lignes du CSV une par une au script
for ligne in sys.stdin:
    ligne = ligne.strip()                      # enlève le retour à la ligne

    # on saute l'en-tête et les lignes vides
    if ligne == "" or ligne.startswith("id_vente"):
        continue

    champs = ligne.split(",")                  # découpe la ligne en 12 colonnes
    if len(champs) != 12:                      # ligne abîmée : on l'ignore
        continue
    if champs[10] != "VALIDEE":                # colonne statut : on ignore les annulées
        continue

    quantite = int(champs[7])                  # colonne quantite
    prix = Decimal(champs[8])                  # colonne prix_unitaire_cad (nombre exact)
    remise = Decimal(champs[9])                # colonne remise_pct

    montant = quantite * prix * (1 - remise / 100)
    # arrondi au cent, 0,5 vers le haut, puis conversion en cents entiers
    cents = int((montant * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    mois = champs[1][:7]                       # "2025-08-08" devient "2025-08"

    # la paire clé-valeur : mois, tabulation, montant en cents
    print(f"{mois}\t{cents}")
