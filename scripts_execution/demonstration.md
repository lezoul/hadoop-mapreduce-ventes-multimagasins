# Démonstration en direct : de HDFS au tableau de bord

Démonstration de la soutenance UA2, environ **5 minutes**. Elle montre ce que l'énoncé demande : « le passage des données depuis HDFS jusqu'au tableau de bord, et une preuve que l'image Docker est publiée ».

- **Qui tape** : Yacine, sur son PC.
- **Qui parle** : le membre indiqué à chaque étape, qui explique ce que l'on voit.
- Chaque bloc se copie-colle d'un coup. La ligne « À dire » résume l'explication.

---

## Avant la soutenance (15 minutes avant)

### 1. Démarrer le cluster

**PowerShell** (`PS C:\Users\Admin>`) :

```powershell
docker start hadoop-worker1 hadoop-worker2 hadoop-master
docker exec -it hadoop-master bash
```

**hadoop-master** (`root@hadoop-master:~#`) :

```bash
start-dfs.sh
start-yarn.sh
mapred --daemon start historyserver
hdfs dfs -rm -r -f -skipTrash /projet_ventes/sorties/demo
clear
```

La 4e commande supprime la sortie d'une répétition précédente : le job de démonstration pourra s'exécuter sans erreur « Output directory already exists ».

### 2. Préparer l'écran

- **Terminal 1** : `root@hadoop-master:~#`, déjà ouvert à l'étape 1.
- **Terminal 2** : PowerShell, placé dans le projet :

  ```powershell
  cd "C:\Users\Admin\Desktop\Cours S1\S3\BDD massives\UA2\Projet"
  docker rm -f dashboard-ventes
  ```

- **Navigateur, 3 onglets** :
  - http://localhost:9870 (HDFS) ;
  - http://localhost:8088 (YARN) ;
  - https://hub.docker.com/r/yacinelezoul/dashboard-ventes (Docker Hub).
- **Agrandir la police des terminaux** (Ctrl + molette) pour que la salle puisse lire.

---

## Déroulé

### Étape 1 · Le cluster tourne (Mouncif, 30 s)

**Terminal 2 (PowerShell)** :

```powershell
docker ps
```

**Terminal 1 (hadoop-master)** :

```bash
jps
hdfs dfsadmin -report | grep -i "live datanodes"
yarn node -list
```

> **À dire** : 3 conteneurs. Le maître porte le NameNode et le ResourceManager. HDFS voit 2 DataNodes et YARN 2 NodeManagers en état RUNNING.

### Étape 2 · Les données sont dans HDFS, intactes (Mouncif, 45 s)

**Terminal 1** :

```bash
hdfs dfs -ls -R /projet_ventes/entree
md5sum /projet/donnees/ventes_multimagasin_2025.csv
hdfs dfs -cat /projet_ventes/entree/ventes_multimagasin_2025.csv | md5sum
hdfs fsck /projet_ventes/entree/ventes_multimagasin_2025.csv -files -blocks -locations | grep -E "Total blocks|Live_repl|Status"
```

> **À dire** : le chiffre 2 dans la liste est le nombre de répliques. Les deux empreintes md5 sont identiques, donc la copie dans HDFS est fidèle à l'octet près. `fsck` montre 1 bloc, répliqué sur les 2 workers, et l'état HEALTHY.

En parallèle, l'onglet http://localhost:9870 (Utilities, puis Browse the file system) peut montrer `/projet_ventes`.

### Étape 3 · Une paire clé-valeur (Adel, 30 s)

**Terminal 1** :

```bash
head -3 /projet/donnees/ventes_multimagasin_2025.csv | python3 /projet/sources/mapper_detail.py
```

> **À dire** : le Mapper ignore l'en-tête et émet, pour chaque vente validée, une clé `mois|magasin|ville|catégorie|produit` et une valeur, le montant net en cents. Tous les montants d'une même clé seront additionnés par le Reducer.

### Étape 4 · Un job MapReduce en direct, avec 2 Reducers (Adel puis Douyeri, 1 min 30)

**Terminal 1** :

```bash
mapred streaming \
  -D mapreduce.job.name="demo_ca_categorie_r2" \
  -D mapreduce.job.reduces=2 \
  -files /projet/sources/mapper_regroupe.py,/projet/sources/reducer_somme.py \
  -mapper "python3 mapper_regroupe.py categorie" \
  -reducer "python3 reducer_somme.py" \
  -input /projet_ventes/sorties/ca_detail/r1 \
  -output /projet_ventes/sorties/demo/ca_categorie_r2
```

Pendant les 30 secondes d'exécution, **montrer l'onglet http://localhost:8088** : le job `demo_ca_categorie_r2` passe de RUNNING à SUCCEEDED.

> **À dire (Adel)** : `-files` envoie les scripts Python sur chaque worker. `-input` est la sortie du job 1, `ca_detail` : c'est le chaînage, on ne relit pas le CSV. `-mapper` reçoit le niveau `categorie` : il ne garde que la catégorie dans la clé.

**Terminal 1**, une fois le job terminé :

```bash
hdfs dfs -ls /projet_ventes/sorties/demo/ca_categorie_r2
for f in $(hdfs dfs -ls -C /projet_ventes/sorties/demo/ca_categorie_r2/part-*); do echo "== $f"; hdfs dfs -cat $f; done
hdfs dfs -cat /projet_ventes/sorties/demo/ca_categorie_r2/part-* | awk -F'\t' '{s += $2} END {print s}'
```

> **À dire (Douyeri)** : 2 Reducers donnent 2 fichiers `part`. Chaque catégorie est envoyée à un seul Reducer, selon le hachage de sa clé : les 4 catégories sont donc réparties entre les 2 fichiers. La somme vaut toujours 194661314 cents, soit 1 946 613,14 $. Le nombre de Reducers ne change pas le résultat, seulement la répartition.

### Étape 5 · Des sorties HDFS au tableau de bord (Rimy, 1 min)

**Terminal 1** :

```bash
ls /projet/resultats
head -3 /projet/resultats/ca_detail/part-00000
```

> **À dire** : les sorties ont été copiées de HDFS vers le dossier `resultats` avec `hdfs dfs -get`. C'est ce dossier que le tableau de bord lit, pas le CSV.

**Terminal 2 (PowerShell)** :

```powershell
docker pull yacinelezoul/dashboard-ventes:1.0
docker run -d --name dashboard-ventes -p 8501:8501 -v "${PWD}\resultats:/app/resultats:ro" yacinelezoul/dashboard-ventes:1.0
```

Ouvrir **http://localhost:8501**, puis :

1. Onglet **Analyses** sans filtre : 1 946 613 $, le même total qu'à l'étape 4.
2. Filtrer **Ville = Ottawa et Gatineau** : les indicateurs et les graphiques se recalculent.
3. Onglet **Provenance et contrôles** : le dossier `/app/resultats`, les fichiers `part-00000` lus et leurs totaux.

> **À dire** : chaque chiffre affiché vient d'un fichier `part` produit par MapReduce. L'onglet Provenance le prouve.

### Étape 6 · L'image est publiée (Barnabe, 30 s)

- Dans PowerShell, revenir sur la sortie du `docker pull` de l'étape 5 : elle télécharge l'image depuis Docker Hub, ou indique « Image is up to date ».
- Montrer l'onglet **Docker Hub** : l'étiquette 1.0, la plateforme linux/amd64 et la commande `docker pull`.
- Montrer le **QR code** de la dernière diapositive : il ouvre la même application, déployée sur Streamlit Community Cloud.

> **À dire** : l'image est publique. N'importe qui peut la récupérer avec `docker pull` et lancer l'application avec un seul `docker run`.

---

## Plan de secours

| Problème | Solution |
| --- | --- |
| Le cluster ne démarre pas ou un job échoue | Montrer les captures 01 à 06 et les journaux 03 et 04 (`scripts_execution/journaux/`). La sortie de l'étape 4 existe déjà dans `ca_mois/r4` : `for f in $(hdfs dfs -ls -C /projet_ventes/sorties/ca_mois/r4/part-*); do echo "== $f"; hdfs dfs -cat $f; done` |
| `Output directory ... already exists` | `hdfs dfs -rm -r -f -skipTrash /projet_ventes/sorties/demo`, puis relancer le job |
| `docker run` : nom déjà utilisé | `docker rm -f dashboard-ventes`, puis relancer |
| `docker run` : port 8501 déjà pris | Fermer le Streamlit local (Ctrl + C), ou utiliser `-p 8502:8501` et ouvrir http://localhost:8502 |
| Pas d'Internet pour `docker pull` | L'image est déjà sur le PC : lancer directement le `docker run`, et montrer la capture 12 (Docker Hub) |
| Docker ne marche pas du tout | Ouvrir https://hadoop-mapreduce-ventes-multimagasins.streamlit.app |

## Après la soutenance

**PowerShell** :

```powershell
docker rm -f dashboard-ventes
docker stop hadoop-master hadoop-worker1 hadoop-worker2
```
