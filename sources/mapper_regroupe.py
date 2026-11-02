import sys

# le niveau demandé est écrit après le nom du script :
# python3 mapper_regroupe.py categorie  ->  niveau = "categorie"
niveau = sys.argv[1]

# chaque ligne reçue vient de ca_detail : "2025-01|M01|Ottawa|Bureau|P006|Cahier A5<TAB>12709"
for ligne in sys.stdin:
    ligne = ligne.strip()
    if ligne == "":
        continue
    cle_detail, cents = ligne.split("\t")     # sépare la clé détaillée et le montant
    parties = cle_detail.split("|")           # découpe la clé en 6 morceaux
    mois = parties[0]
    magasin = parties[1]
    ville = parties[2]
    categorie = parties[3]
    id_produit = parties[4]
    nom_produit = parties[5]

    # on ne garde que la partie de la clé qui correspond au niveau demandé
    if niveau == "mois":
        cle = mois
    elif niveau == "magasin":
        cle = magasin + "|" + ville
    elif niveau == "categorie":
        cle = categorie
    elif niveau == "produit":
        cle = id_produit + "|" + nom_produit + "|" + categorie
    else:
        sys.exit("niveau inconnu : " + niveau)

    print(f"{cle}\t{cents}")
