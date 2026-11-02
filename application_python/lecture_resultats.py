import os
from pathlib import Path

import pandas as pd

# Dossier des résultats MapReduce :
# - sur Windows : Projet\resultats (le dossier voisin de application_python)
# - dans Docker : la variable d'environnement DOSSIER_RESULTATS (ex. /app/resultats)
DOSSIER_PAR_DEFAUT = Path(__file__).resolve().parent.parent / "resultats"
DOSSIER = Path(os.environ.get("DOSSIER_RESULTATS", DOSSIER_PAR_DEFAUT))

# Pour chaque job : les noms des morceaux de la clé, séparés par |
COLONNES_CLE = {
    "ca_mois": ["mois"],
    "ca_magasin": ["magasin", "ville"],
    "ca_categorie": ["categorie"],
    "ca_produit": ["id_produit", "nom_produit", "categorie"],
    "ca_detail": ["mois", "magasin", "ville", "categorie", "id_produit", "nom_produit"],
}


def fichiers_part(job):
    """Liste les fichiers part-* d'un job (un par Reducer)."""
    return sorted((DOSSIER / job).glob("part-*"))


def lire_job(job):
    """Lit tous les part-* d'un job et renvoie un tableau : colonnes de la clé + ca (en $)."""
    lignes = []
    for fichier in fichiers_part(job):
        with open(fichier, encoding="utf-8") as f:
            for ligne in f:
                ligne = ligne.strip()
                if ligne == "":
                    continue
                cle, cents = ligne.split("\t")
                lignes.append(cle.split("|") + [int(cents)])
    tableau = pd.DataFrame(lignes, columns=COLONNES_CLE[job] + ["cents"])
    tableau["ca"] = tableau["cents"] / 100     # cents -> dollars, seulement pour l'affichage
    return tableau


def provenance():
    """Pour chaque job : les fichiers lus et leur nombre de lignes."""
    infos = []
    for job in COLONNES_CLE:
        for fichier in fichiers_part(job):
            with open(fichier, encoding="utf-8") as f:
                nb = sum(1 for _ in f)
            infos.append({"job": job, "fichier": fichier.name, "lignes": nb})
    return pd.DataFrame(infos)
