# Commandes d'exécution du projet UA2

Toutes les commandes du projet, dans l'ordre où nous les avons exécutées, avec leur explication et le résultat attendu. Les sorties réelles sont dans [`journaux/`](journaux/) ; l'explication détaillée de chaque option est dans `rapport_detaille.pdf`, annexe A.

**Où taper les commandes**

| Invite | Endroit | Commandes |
| --- | --- | --- |
| `PS C:\...>` (ou `$` sous Ubuntu) | Hôte, la machine qui a Docker | `docker`, `git`, `python` |
| `root@hadoop-master:~#` | Terminal Linux du conteneur maître | `hdfs`, `yarn`, `mapred`, `python3` |

Le dossier du projet sur l'hôte est visible dans le maître sous `/projet` (montage `-v`). Sous PowerShell, une commande sur plusieurs lignes se poursuit avec `` ` `` au lieu de `\`, et `$(pwd)` s'écrit `${PWD}`.

**Résultat de contrôle attendu partout** : `194661314` cents, soit 1 946 613,14 $.

---

## Étape 0 : récupérer le projet et vérifier l'image Hadoop

Où : **hôte**

```bash
git clone https://github.com/lezoul/hadoop-mapreduce-ventes-multimagasins.git   # copie le dépôt (code, données, résultats)
cd hadoop-mapreduce-ventes-multimagasins                                         # se placer à la racine du projet
docker images                                                                    # l'image ous1/hadoop-cluster:latest doit apparaître
```

## Étape 1 : créer le réseau et les 3 conteneurs

Où : **hôte**, à la racine du projet

```bash
docker network create --driver bridge reseau-hadoop        # réseau privé : les conteneurs se joignent par leur nom
docker run -itd --name hadoop-worker1 --hostname hadoop-worker1 --network reseau-hadoop -p 8040:8042 ous1/hadoop-cluster:latest
docker run -itd --name hadoop-worker2 --hostname hadoop-worker2 --network reseau-hadoop -p 8041:8042 ous1/hadoop-cluster:latest
docker run -itd --name hadoop-master --hostname hadoop-master --network reseau-hadoop \
  -p 9870:9870 -p 8088:8088 -p 19888:19888 \
  -v "$(pwd):/projet" ous1/hadoop-cluster:latest           # le dossier du projet apparaît dans le maître sous /projet
docker ps                                                  # attendu : 3 conteneurs à l'état Up
```

- `-itd` : garde un terminal ouvert (`-it`) pour que le conteneur ne s'arrête pas, et le lance en arrière-plan (`-d`).
- `--name` / `--hostname` : nom pour Docker / nom de machine pour Hadoop, identiques au fichier `workers` de l'image.
- `-p HÔTE:CONTENEUR` : 9870 interface HDFS, 8088 interface YARN, 19888 historique des jobs, 8040 et 8041 NodeManagers.

## Étape 2 : démarrer et vérifier HDFS et YARN

Où : **hôte** pour entrer, puis **hadoop-master**

```bash
docker exec -it hadoop-master bash          # ouvre un terminal Linux dans le maître
```

```bash
hdfs namenode -format                       # PREMIÈRE FOIS SEULEMENT : crée un HDFS vide
start-dfs.sh                                # NameNode (maître), DataNodes (workers), SecondaryNameNode
start-yarn.sh                               # ResourceManager (maître), NodeManagers (workers)
mapred --daemon start historyserver         # historique des jobs terminés
jps                                         # attendu : NameNode, SecondaryNameNode, ResourceManager, JobHistoryServer
hdfs dfsadmin -report                       # attendu : Live datanodes (2)
yarn node -list                             # attendu : Total Nodes:2, état RUNNING
cat /etc/os-release                         # Ubuntu 22.04.1 LTS
exit                                        # revenir sur l'hôte
```

```bash
docker exec hadoop-worker1 jps              # attendu : DataNode, NodeManager (même chose pour hadoop-worker2)
docker exec hadoop-worker1 python3 --version   # Python 3.10.12 : les tâches Python tournent sur les workers
```

- Interfaces : http://localhost:9870 (HDFS) et http://localhost:8088 (YARN).
- **Arrêt** : dans le maître `mapred --daemon stop historyserver`, `stop-yarn.sh`, `stop-dfs.sh`, puis sur l'hôte `docker stop hadoop-master hadoop-worker1 hadoop-worker2`.
- **Redémarrage** : `docker start hadoop-worker1 hadoop-worker2 hadoop-master`, puis les 3 commandes `start` ci-dessus, sans reformater.

## Étape 3 : contrôler la qualité du CSV

Où : **hadoop-master**

```bash
python3 /projet/sources/controle_qualite.py /projet/donnees/ventes_multimagasin_2025.csv \
  | tee /projet/resultats/controle_qualite.txt     # affiche le contrôle et l'enregistre
```

Attendu : 24 000 lignes, 12 colonnes, 0 valeur manquante, 0 doublon d'identifiant, 334 lignes identiques hors identifiant, VALIDEE 22 576 / ANNULEE 1 424.

## Étape 4 : déposer le CSV dans HDFS et prouver son intégrité

Où : **hadoop-master**

```bash
md5sum /projet/donnees/ventes_multimagasin_2025.csv      # empreinte locale : 4ae57ed472eb5c10dd07814deba2c37b
wc -l  /projet/donnees/ventes_multimagasin_2025.csv      # 24001 (en-tête compris)
hdfs dfs -mkdir -p /projet_ventes/entree /projet_ventes/entree_blocs_1m /projet_ventes/tests /projet_ventes/sorties
hdfs dfs -put /projet/donnees/ventes_multimagasin_2025.csv /projet_ventes/entree/       # Linux -> HDFS
hdfs dfs -D dfs.blocksize=1048576 -put /projet/donnees/ventes_multimagasin_2025.csv /projet_ventes/entree_blocs_1m/   # copie à blocs de 1 Mo (expérience Mappers)
hdfs dfs -ls -R /projet_ventes                                                          # 2e colonne = 2 répliques
hdfs dfs -cat /projet_ventes/entree/ventes_multimagasin_2025.csv | wc -l               # 24001
hdfs dfs -cat /projet_ventes/entree/ventes_multimagasin_2025.csv | md5sum              # même empreinte qu'en local
hdfs fsck /projet_ventes/entree/ventes_multimagasin_2025.csv -files -blocks -locations          # 1 bloc, Live_repl=2, HEALTHY
hdfs fsck /projet_ventes/entree_blocs_1m/ventes_multimagasin_2025.csv -files -blocks -locations # 2 blocs : 1048576 + 937219 octets
```

## Étape 5 : tester en local, puis lancer les jobs MapReduce

Où : **hadoop-master**

**5.1 Test local** : `sort` imite le Shuffle & Sort ; `LC_ALL=C` trie octet par octet comme Hadoop.

```bash
head -4 /projet/donnees/ventes_multimagasin_2025.csv | python3 /projet/sources/mapper_detail.py
#   2025-08|M05|Toronto|Bureau|P007|Lot de stylos    801      (clé, tabulation, montant en cents)
python3 /projet/sources/mapper_detail.py < /projet/donnees/ventes_multimagasin_2025.csv | wc -l     # 22576 ventes VALIDEE
python3 /projet/sources/mapper_detail.py < /projet/donnees/ventes_multimagasin_2025.csv | LC_ALL=C sort \
  | python3 /projet/sources/reducer_somme.py | awk -F'\t' '{s += $2} END {print s}'                 # 194661314
```

**5.2 Job 1 : CSV vers `ca_detail`**

```bash
mapred streaming \
  -D mapreduce.job.name="ca_detail_r1" \
  -D mapreduce.job.reduces=1 \
  -files /projet/sources/mapper_detail.py,/projet/sources/reducer_somme.py \
  -mapper "python3 mapper_detail.py" \
  -reducer "python3 reducer_somme.py" \
  -input /projet_ventes/entree/ventes_multimagasin_2025.csv \
  -output /projet_ventes/sorties/ca_detail/r1
hdfs dfs -cat /projet_ventes/sorties/ca_detail/r1/part-00000 | wc -l                                 # 1917
hdfs dfs -cat /projet_ventes/sorties/ca_detail/r1/part-00000 | awk -F'\t' '{s += $2} END {print s}'  # 194661314
```

| Option | Rôle |
| --- | --- |
| `mapred streaming` | job MapReduce dont le Mapper et le Reducer sont des programmes quelconques (ici Python) |
| `-D mapreduce.job.name` | nom affiché dans YARN (http://localhost:8088) |
| `-D mapreduce.job.reduces` | nombre de Reducers, donc de fichiers `part-*` |
| `-files` | chemins **Linux** des scripts, copiés sur chaque worker |
| `-mapper`, `-reducer` | commandes exécutées dans les conteneurs YARN |
| `-input`, `-output` | chemins **HDFS** ; le dossier de sortie ne doit pas exister (sinon `hdfs dfs -rm -r <dossier>`) |

Compteurs attendus : Map input records 24001, Map output records 22576, Reduce output records 1917.

**5.3 Jobs 2 à 5 : chaînage sur `ca_detail`**

```bash
for niveau in mois magasin categorie produit
do
  mapred streaming \
    -D mapreduce.job.name="ca_${niveau}_r1" -D mapreduce.job.reduces=1 \
    -files /projet/sources/mapper_regroupe.py,/projet/sources/reducer_somme.py \
    -mapper "python3 mapper_regroupe.py ${niveau}" -reducer "python3 reducer_somme.py" \
    -input /projet_ventes/sorties/ca_detail/r1 \
    -output /projet_ventes/sorties/ca_${niveau}/r1
done
for niveau in mois magasin categorie produit; do
  hdfs dfs -cat /projet_ventes/sorties/ca_${niveau}/r1/part-00000 | wc -l     # 12, 8, 4, 20
done
```

- `for ... do ... done` répète le job pour chaque niveau ; `${niveau}` est passé au Mapper, qui le lit avec `sys.argv[1]`.
- `-input` désigne le dossier du job 1 : Hadoop lit ses `part-*` et ignore `_SUCCESS`.

**5.4 Contrôle indépendant** : CA mensuel calculé directement sur le CSV, comparé au chaînage.

```bash
mapred streaming -D mapreduce.job.name="ca_mensuel_r1" -D mapreduce.job.reduces=1 \
  -files /projet/sources/mapper_mois.py,/projet/sources/reducer_somme.py \
  -mapper "python3 mapper_mois.py" -reducer "python3 reducer_somme.py" \
  -input /projet_ventes/entree/ventes_multimagasin_2025.csv \
  -output /projet_ventes/sorties/controle_ca_mensuel_direct/r1
hdfs dfs -cat /projet_ventes/sorties/ca_mois/r1/part-00000 | md5sum
hdfs dfs -cat /projet_ventes/sorties/controle_ca_mensuel_direct/r1/part-00000 | md5sum   # même empreinte : db30e50f...
```

**5.5 Récupérer les résultats** pour le tableau de bord (HDFS vers le dossier `resultats/` du projet).

```bash
mkdir -p /projet/resultats
for job in detail mois magasin categorie produit; do
  hdfs dfs -get /projet_ventes/sorties/ca_${job}/r1 /projet/resultats/ca_${job}
done
ls -R /projet/resultats                       # un part-00000 et un _SUCCESS par job
```

## Étape 6 : expériences Reducers, Mappers et YARN

Où : **hadoop-master**

**6.1 Avec 2 puis 4 Reducers**

```bash
for r in 2 4; do
  mapred streaming -D mapreduce.job.name="ca_mois_r${r}" -D mapreduce.job.reduces=${r} \
    -files /projet/sources/mapper_regroupe.py,/projet/sources/reducer_somme.py \
    -mapper "python3 mapper_regroupe.py mois" -reducer "python3 reducer_somme.py" \
    -input /projet_ventes/sorties/ca_detail/r1 -output /projet_ventes/sorties/ca_mois/r${r}
done
for f in $(hdfs dfs -ls -C /projet_ventes/sorties/ca_mois/r4/part-*); do echo "== $f"; hdfs dfs -cat $f; done   # contenu de chaque partition
hdfs dfs -cat /projet_ventes/sorties/ca_mois/r4/part-* | awk -F'\t' '{s += $2} END {print s}'                 # toujours 194661314
```

Attendu : 2 fichiers (7 et 5 mois), puis 4 fichiers (4, 2, 3 et 3 mois) ; durées 23, 27 et 34 s pour 1, 2 et 4 Reducers. Dans chaque journal, relever `Launched reduce tasks`, `Shuffled Maps` et la mémoire utilisée.

**6.2 Nombre de Mappers et InputSplits**

```bash
for m in 1 4; do
  mapred streaming -D mapreduce.job.name="exp_maps${m}" -D mapreduce.job.maps=${m} -D mapreduce.job.reduces=1 \
    -files /projet/sources/mapper_detail.py,/projet/sources/reducer_somme.py \
    -mapper "python3 mapper_detail.py" -reducer "python3 reducer_somme.py" \
    -input /projet_ventes/entree/ventes_multimagasin_2025.csv -output /projet_ventes/sorties/exp_mappers/maps${m}
done
mapred streaming -D mapreduce.job.name="exp_blocs1m_maps1" -D mapreduce.job.maps=1 -D mapreduce.job.reduces=1 \
  -files /projet/sources/mapper_detail.py,/projet/sources/reducer_somme.py \
  -mapper "python3 mapper_detail.py" -reducer "python3 reducer_somme.py" \
  -input /projet_ventes/entree_blocs_1m/ventes_multimagasin_2025.csv \
  -output /projet_ventes/sorties/exp_mappers/blocs1m_maps1
```

Attendu (lignes `number of splits` et `Launched map tasks`) : 1 et 4 Mappers sur le fichier à 1 bloc ; 2 Mappers sur le fichier à 2 blocs malgré `maps=1` ; 2 Mappers sans option (valeur par défaut de Streaming).

**6.3 Ressources YARN**

```bash
yarn node -list -showDetails                                   # Configured Resources : <memory:8192, vCores:8> par worker
yarn application -status application_1793588531268_0010        # remplacer par l'identifiant affiché par le job
```

Relever `Aggregate Resource Allocation` (Mo·s et vCore·s) et `AM Host` ; dans le journal du job, `Physical memory snapshot`, `megabyte-milliseconds` et `vcore-milliseconds`.

## Étape 7 : lancer le tableau de bord en local

Où : **hôte**, dans le dossier `application_python`

```bash
cd application_python
python -m pip install -r requirements.txt      # streamlit 1.66.1, plotly 7.1.0, pandas 3.1.0
python -m streamlit run app.py                 # ouvre http://localhost:8501 ; arrêt : Ctrl + C
```

L'application lit `../resultats` (ou le dossier de la variable `DOSSIER_RESULTATS`). Attendu sans filtre : 1 946 613 $, +86 %, meilleur mois décembre, meilleur magasin M05 Toronto.

## Étape 8 : rejouer le cas de test

Où : **hadoop-master**

```bash
python3 -c "print(round(6.50 * 0.95, 2))"      # 6.17 au lieu de 6.18 : le piège des flottants
python3 /projet/sources/mapper_detail.py < /projet/tests/echantillon_test.csv | LC_ALL=C sort \
  | python3 /projet/sources/reducer_somme.py | diff - /projet/tests/attendu_ca_detail.txt && echo "TEST LOCAL DETAIL : REUSSI"
hdfs dfs -put /projet/tests/echantillon_test.csv /projet_ventes/tests/
mapred streaming -D mapreduce.job.name="test_ca_detail" -D mapreduce.job.reduces=1 \
  -files /projet/sources/mapper_detail.py,/projet/sources/reducer_somme.py \
  -mapper "python3 mapper_detail.py" -reducer "python3 reducer_somme.py" \
  -input /projet_ventes/tests/echantillon_test.csv -output /projet_ventes/sorties/tests/ca_detail
hdfs dfs -cat /projet_ventes/sorties/tests/ca_detail/part-* | diff - /projet/tests/attendu_ca_detail.txt && echo "TEST HADOOP DETAIL : REUSSI"
mapred streaming -D mapreduce.job.name="test_ca_mois" -D mapreduce.job.reduces=1 \
  -files /projet/sources/mapper_regroupe.py,/projet/sources/reducer_somme.py \
  -mapper "python3 mapper_regroupe.py mois" -reducer "python3 reducer_somme.py" \
  -input /projet_ventes/sorties/tests/ca_detail -output /projet_ventes/sorties/tests/ca_mois
hdfs dfs -cat /projet_ventes/sorties/tests/ca_mois/part-* | diff - /projet/tests/attendu_ca_mois.txt && echo "TEST HADOOP CHAINAGE : REUSSI"
```

`diff - fichier` compare la sortie reçue au résultat calculé à la main et n'affiche rien s'ils sont identiques ; `&&` n'affiche REUSSI que dans ce cas. Attendu : 3 × REUSSI, total 77 348 cents.

## Étape 9 : construire, tester et publier l'image Docker

Où : **hôte**, dans le dossier `application_python` (port 8501 libre : arrêter le Streamlit local)

```bash
docker build -t yacinelezoul/dashboard-ventes:1.0 .                 # construit l'image selon le Dockerfile
docker run -d --name dashboard-ventes -p 8501:8501 \
  -v "$(pwd)/../resultats:/app/resultats:ro" yacinelezoul/dashboard-ventes:1.0   # résultats MapReduce montés en lecture seule
docker logs dashboard-ventes                                        # en cas de problème
docker login                                                        # connexion par le navigateur ; aucun jeton écrit dans un fichier
docker push yacinelezoul/dashboard-ventes:1.0                       # publie l'image et affiche son digest
docker rm -f dashboard-ventes                                       # supprime le conteneur
docker rmi yacinelezoul/dashboard-ventes:1.0                        # supprime l'image locale
docker pull yacinelezoul/dashboard-ventes:1.0                       # la retélécharge depuis Docker Hub : même digest
docker run -d --name dashboard-ventes -p 8501:8501 \
  -v "$(pwd)/../resultats:/app/resultats:ro" yacinelezoul/dashboard-ventes:1.0
docker ps                                                           # 0.0.0.0:8501->8501/tcp ; ouvrir http://localhost:8501
```

L'onglet Provenance doit afficher `/app/resultats`. Preuve complète dans `preuve_docker.txt`.

## Étape 10 : versionner le projet

Où : **hôte**, à la racine du projet

```bash
git add .                                      # prépare les fichiers nouveaux ou modifiés
git commit -m "description de la modification" # les enregistre dans l'historique
git push                                       # les envoie sur GitHub
```

`.gitattributes` impose des fins de ligne Unix aux scripts et interdit toute conversion du CSV, pour que son md5 reste identique chez chaque membre.
