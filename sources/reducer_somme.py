import sys

cle_courante = None     # la clé qu'on est en train d'additionner (ex. "2025-03")
total = 0               # le total en cours pour cette clé

# Hadoop envoie les paires TRIÉES par clé : tous les "2025-03" arrivent à la suite
for ligne in sys.stdin:
    ligne = ligne.strip()
    if ligne == "":
        continue

    cle, valeur = ligne.split("\t")    # sépare la clé et la valeur (tabulation)
    valeur = int(valeur)               # "801" devient le nombre 801

    if cle == cle_courante:
        # même clé que la ligne précédente : on ajoute au total
        total = total + valeur
    else:
        # nouvelle clé : on écrit le total de la clé précédente...
        if cle_courante is not None:
            print(f"{cle_courante}\t{total}")
        # ...puis on recommence à compter pour la nouvelle clé
        cle_courante = cle
        total = valeur

# à la fin, on écrit le total de la dernière clé
if cle_courante is not None:
    print(f"{cle_courante}\t{total}")
