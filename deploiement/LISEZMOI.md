# Mettre le site en ligne sur un VPS, avec Docker

Trois conteneurs : **Caddy** sert les fichiers et gère le certificat tout
seul, **PHP-FPM** exécute l'API, **MariaDB** garde les comptes et les
parties. Rien d'autre n'est installé sur la machine.

Calibre suffisant : 1 cœur, 2 Go de RAM, 20 Go de disque. En marche
l'ensemble occupe environ 800 Mo.

---

## Bêta : lancer sur l'IP, tout de suite

Sans domaine, pour essayer. Le jeu tourne entièrement ; seule la
connexion Discord est indisponible — elle exige du HTTPS, et aucune
autorité ne certifie une adresse IP.

```bash
apt update && apt install -y docker.io docker-compose-v2
ufw allow OpenSSH && ufw allow 80 && ufw enable
```

Envoie le dossier du projet sur le VPS, puis :

```bash
cd "Site - OnePiece"
cp api/config.exemple.php api/config.php
cd deploiement
cp .env.exemple .env
nano .env          # URL_PUBLIQUE : mettre l'IP. Deux mots de passe. Discord : laisser vide.
chmod 600 .env
docker compose up -d
docker compose exec php php outils/migrer.php
```

Ouvre `http://IP-DU-VPS`. C'est tout.

En bêta, **n'invite pas de joueurs à se connecter** : sans HTTPS, ce qui
circule est en clair. Le jeu se joue très bien sans compte — les séries
sont gardées par le navigateur.

### Passer en ligne, plus tard

Trois lignes à changer, rien à reconstruire :

1. Enregistrement DNS **A** vers l'IP du VPS, vérifié par `dig +short`
2. dans `.env` : `ADRESSE=mon-domaine.fr` et `URL_PUBLIQUE=https://mon-domaine.fr`
3. `python3 outils/domaine.py mon-domaine.fr` à la racine du projet
4. `docker compose up -d` — Caddy va chercher le certificat tout seul

Puis renseigner `DISCORD_ID` et `DISCORD_SECRET`, et coller
`https://mon-domaine.fr/api/retour.php` dans OAuth2 > Redirects.

---

## 1. Le domaine, avant tout

Crée un enregistrement **A** qui pointe vers l'IP du VPS, et attends
qu'il se propage :

```bash
dig +short mon-domaine.fr
```

Tant que cette commande ne renvoie pas l'IP du VPS, ne démarre pas :
Caddy demanderait un certificat, Let's Encrypt échouerait, et cinq échecs
d'affilée déclenchent une limite d'une heure.

## 2. Le VPS

```bash
apt update && apt upgrade -y
apt install -y docker.io docker-compose-v2 git
```

Un pare-feu qui ne laisse passer que l'essentiel :

```bash
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
```

## 3. Le site

Envoie le dossier du projet sur le VPS — par `git clone`, `scp` ou
`rsync` — puis :

```bash
cd "Site - OnePiece"
cp api/config.exemple.php api/config.php
cd deploiement
cp .env.exemple .env
nano .env          # domaine, mots de passe, Discord
chmod 600 .env
```

`api/config.php` n'a pas besoin d'être modifié : il lit les variables
d'environnement, que `compose.yml` lui transmet depuis `.env`. Aucun
secret n'est écrit dans un fichier du site.

Adapte aussi le domaine dans les pages, sinon les aperçus de partage et
le référencement pointent dans le vide :

```bash
cd .. && python3 outils/domaine.py mon-domaine.fr && cd deploiement
```

## 4. Démarrer

```bash
docker compose up -d
docker compose logs -f caddy      # le certificat arrive en ~10 secondes
```

Puis créer les tables :

```bash
docker compose exec php php outils/migrer.php
```

## 5. Vérifier

```bash
docker compose exec php php outils/verifier-discord.php
```

Cet outil contrôle d'un coup les identifiants, l'URL de redirection, la
base, les extensions PHP et la jointure TLS vers Discord. Tout doit être
au vert avant d'annoncer le site.

Ouvre ensuite `https://mon-domaine.fr` et joue une partie : si elle
apparaît dans le classement, la chaîne complète fonctionne.

---

## Mettre à jour

Le dépôt est monté en lecture seule dans les conteneurs : remplacer les
fichiers sur l'hôte suffit, il n'y a **rien à reconstruire**.

```bash
git pull
docker compose exec php php outils/migrer.php   # si le schéma a bougé
```

Un changement dans `deploiement/` — Caddyfile, Dockerfile, compose —
demande en revanche :

```bash
docker compose up -d --build
```

## Déménager sur un autre VPS

`migrer-vps.sh` fait le voyage en deux temps. Il ne touche à rien sur
l'ancien serveur : il lit et il archive. L'ancien reste debout tant que
le nouveau n'est pas vérifié.

**Ce qui voyage** — et ce qui se perdrait sans lui :

| | pourquoi |
|---|---|
| le projet | 23 Mo, portraits compris |
| `deploiement/.env` | mots de passe et clés Discord — **dans aucun dépôt** |
| `api/config.php` | créé sur place à l'installation |
| la base | **vidangée**, jamais copiée à chaud |
| `caddy_data` | compte Let's Encrypt et certificats émis |
| `php_sessions` | les connexions Discord ouvertes |

Recopier `/var/lib/mysql` pendant que MariaDB écrit dedans donne une base
qu'on croit saine et qui ne l'est pas : d'où la vidange.

### 1. Sur l'ancien serveur

```bash
cd /opt/bureau-des-primes/deploiement
sh migrer-vps.sh exporter
```

Il écrit `/root/bdp-migration-<date>.tgz` et affiche son empreinte.

### 2. Le transport

```bash
scp root@ANCIENNE-IP:/root/bdp-migration-....tgz .
scp bdp-migration-....tgz root@NOUVELLE-IP:/root/
```

Compare les empreintes des deux côtés avant d'importer. L'archive
contient les mots de passe : elle est en `chmod 600`, ne la laisse pas
traîner dans un dossier partagé.

### 3. Sur le nouveau serveur

```bash
apt update && apt install -y docker.io docker-compose-v2
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
tar xzf /root/bdp-migration-....tgz -C /tmp projet.tgz
tar xzf /tmp/projet.tgz -C /tmp
sh /tmp/bureau-des-primes/deploiement/migrer-vps.sh importer /root/bdp-migration-....tgz
```

Le script démarre la base seule, attend qu'elle réponde, restaure les
données, remonte les volumes, lance le tout et joue les migrations de
schéma.

### 4. Vérifier avant de basculer

```bash
curl -I http://localhost/                         # 200
curl -s "http://localhost/api/classement.php?univers=pokemon&mode=classique"
```

Puis, depuis un navigateur, sur la **nouvelle IP** : joue une partie
entière. Si elle se termine et que la fiche s'affiche, la chaîne complète
tient.

Alors seulement :

1. dans `.env`, `URL_PUBLIQUE` prend la nouvelle adresse
2. `docker compose up -d`
3. si un domaine existe déjà, le DNS pointe vers la nouvelle IP, puis
   `python3 outils/domaine.py mon-domaine.fr` à la racine du projet
4. **garde l'ancien VPS allumé 48 h.** Tant qu'il tourne, une erreur se
   rattrape en repointant le DNS.

### Le bon moment

Tant que le site vit sur une IP sans domaine, un déménagement se résume à
copier une archive : pas de propagation DNS à attendre, pas de certificat
à réémettre. Une fois le domaine posé, il faut ajouter les deux. **Migrer
avant le domaine coûte une heure ; après, une demi-journée d'attente.**

## Sauvegarder

La base est minuscule : une ligne par partie jouée. Un cron d'une ligne
suffit.

```bash
docker compose exec -T db mariadb-dump -u root -p"$BD_ROOT" \
  --single-transaction bureau_des_primes | gzip > /root/bdp-$(date +%F).sql.gz
```

Le volume `caddy_data` contient les certificats : le garder évite de
redemander à Let's Encrypt après une réinstallation.

## Si quelque chose cloche

| Symptôme | Regarder |
|---|---|
| Pas de certificat | `docker compose logs caddy` — le DNS pointe-t-il bien ? Le port 80 est-il ouvert ? |
| Page blanche sur l'API | `docker compose logs php` |
| « base injoignable » | `docker compose ps` — le service `db` est-il *healthy* ? |
| Connexion Discord refusée | l'URL de redirection du portail Discord doit être **exactement** `https://<domaine>/api/retour.php` |

Le jeu est écrit pour survivre à la panne : si l'API ne répond pas,
`compte.js` efface la couche compte et le jeu continue en local. Un
problème de base ne met jamais le site à terre.
