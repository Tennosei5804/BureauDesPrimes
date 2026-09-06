#!/bin/sh
# Bureau des Primes — déménager le site d'un VPS à un autre.
#
#   Sur l'ANCIEN serveur :   sh migrer-vps.sh exporter
#   Sur le NOUVEAU serveur : sh migrer-vps.sh importer /root/bdp-migration-....tgz
#
# Ce qui voyage, et pourquoi chaque chose :
#
#   le projet          /opt/bureau-des-primes, 23 Mo, portraits compris
#   .env               les mots de passe de la base et les clés Discord ;
#                      il n'est dans aucun dépôt, il ne se retrouve pas
#   api/config.php     créé sur place à l'installation
#   la base            VIDANGÉE, jamais copiée à chaud : recopier
#                      /var/lib/mysql pendant que MariaDB écrit dedans
#                      donne une base qu'on croit saine et qui ne l'est pas
#   caddy_data         le compte Let's Encrypt et les certificats émis ;
#                      le reprendre évite de redemander, et Let's Encrypt
#                      limite à cinq échecs par heure
#   php_sessions       les sessions Discord ouvertes ; sans elles, tout le
#                      monde est déconnecté au réveil
#
# Le script ne touche à rien sur l'ancien serveur : il lit et il archive.
# L'ancien reste debout jusqu'à ce que le nouveau soit vérifié.

set -eu

ICI=$(cd "$(dirname "$0")" && pwd)
PROJET=$(dirname "$ICI")
PREFIXE=$(basename "$ICI")          # le nom de projet Docker, "deploiement"

rouge()  { printf '\033[31m%s\033[0m\n' "$*"; }
vert()   { printf '\033[32m%s\033[0m\n' "$*"; }
etape()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }

# --------------------------------------------------------------- export

exporter() {
    cd "$ICI"
    [ -f .env ] || { rouge "Pas de .env ici. Es-tu bien sur l'ancien serveur ?"; exit 1; }

    HORO=$(date +%F-%H%M)
    ATELIER=$(mktemp -d)
    trap 'rm -rf "$ATELIER"' EXIT

    etape "1/4  Vidange de la base"
    # Les valeurs viennent du .env ; « set -a » les exporte le temps de
    # la lecture, sans quoi mariadb-dump ne les verrait pas.
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
    docker compose exec -T db mariadb-dump \
        -u root -p"$BD_ROOT" \
        --single-transaction --routines --events \
        "$BD_BASE" > "$ATELIER/base.sql"
    LIGNES=$(wc -l < "$ATELIER/base.sql")
    [ "$LIGNES" -gt 10 ] || { rouge "Vidange vide ou tronquée ($LIGNES lignes). On s'arrête."; exit 1; }
    vert "   base « $BD_BASE » : $LIGNES lignes"

    etape "2/4  Volumes Docker"
    for V in caddy_data php_sessions; do
        if docker volume inspect "${PREFIXE}_${V}" >/dev/null 2>&1; then
            docker run --rm \
                -v "${PREFIXE}_${V}":/src:ro \
                -v "$ATELIER":/out \
                alpine tar czf "/out/${V}.tgz" -C /src . 2>/dev/null
            vert "   ${V} : $(du -h "$ATELIER/${V}.tgz" | cut -f1)"
        else
            printf '   %s : absent, ignoré\n' "$V"
        fi
    done

    etape "3/4  Le projet"
    # --exclude .git : inutile et volumineux. Le reste part entier,
    # .env et api/config.php compris — c'est tout l'intérêt.
    tar czf "$ATELIER/projet.tgz" -C "$(dirname "$PROJET")" \
        --exclude='.git' --exclude='__pycache__' \
        "$(basename "$PROJET")"
    vert "   projet : $(du -h "$ATELIER/projet.tgz" | cut -f1)"

    etape "4/4  Archive finale"
    SORTIE="/root/bdp-migration-${HORO}.tgz"
    tar czf "$SORTIE" -C "$ATELIER" .
    chmod 600 "$SORTIE"             # elle contient les mots de passe

    printf '\n'
    vert "Archive : $SORTIE  ($(du -h "$SORTIE" | cut -f1))"
    printf 'Empreinte : %s\n' "$(sha256sum "$SORTIE" | cut -c1-64)"
    printf '\nÀ rapatrier depuis ta machine :\n'
    printf '  scp root@ANCIENNE-IP:%s .\n' "$SORTIE"
    printf '  scp %s root@NOUVELLE-IP:/root/\n' "$(basename "$SORTIE")"
    printf '\nVérifie l empreinte des deux côtés avant d importer.\n'
}

# --------------------------------------------------------------- import

importer() {
    ARCHIVE=${1:-}
    [ -n "$ARCHIVE" ] || { rouge "Usage : sh migrer-vps.sh importer /root/bdp-migration-....tgz"; exit 1; }
    [ -f "$ARCHIVE" ] || { rouge "Archive introuvable : $ARCHIVE"; exit 1; }

    command -v docker >/dev/null 2>&1 || {
        rouge "Docker n'est pas installé. Avant tout :"
        printf '  apt update && apt install -y docker.io docker-compose-v2\n'
        printf '  ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable\n'
        exit 1
    }

    ATELIER=$(mktemp -d)
    trap 'rm -rf "$ATELIER"' EXIT

    etape "1/6  Ouverture de l'archive"
    tar xzf "$ARCHIVE" -C "$ATELIER"
    [ -f "$ATELIER/projet.tgz" ] || { rouge "Archive incomplète : projet.tgz manquant."; exit 1; }
    [ -f "$ATELIER/base.sql" ]   || { rouge "Archive incomplète : base.sql manquant."; exit 1; }
    vert "   contenu vérifié"

    etape "2/6  Pose du projet dans /opt"
    [ -e /opt/bureau-des-primes ] && {
        rouge "/opt/bureau-des-primes existe déjà. Écarte-le d'abord :"
        printf '  mv /opt/bureau-des-primes /opt/bureau-des-primes.ancien\n'
        exit 1
    }
    tar xzf "$ATELIER/projet.tgz" -C /opt
    chmod 600 /opt/bureau-des-primes/deploiement/.env
    vert "   $(du -sh /opt/bureau-des-primes | cut -f1) posés"

    cd /opt/bureau-des-primes/deploiement

    etape "3/6  Démarrage de la base seule"
    docker compose up -d db
    printf '   attente que MariaDB réponde'
    N=0
    while [ "$N" -lt 60 ]; do
        if docker compose exec -T db healthcheck.sh --connect --innodb_initialized >/dev/null 2>&1; then
            printf '\n'; vert "   base prête"; break
        fi
        printf '.'; sleep 2; N=$((N + 1))
    done
    [ "$N" -lt 60 ] || { printf '\n'; rouge "La base n'a pas démarré. docker compose logs db"; exit 1; }

    etape "4/6  Restauration des données"
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
    docker compose exec -T db mariadb -u root -p"$BD_ROOT" "$BD_BASE" < "$ATELIER/base.sql"
    vert "   base « $BD_BASE » restaurée"

    etape "5/6  Volumes"
    for V in caddy_data php_sessions; do
        [ -f "$ATELIER/${V}.tgz" ] || continue
        docker volume create "${PREFIXE}_${V}" >/dev/null
        docker run --rm \
            -v "${PREFIXE}_${V}":/dst \
            -v "$ATELIER":/in:ro \
            alpine sh -c "tar xzf /in/${V}.tgz -C /dst" 2>/dev/null
        vert "   ${V} restauré"
    done

    etape "6/6  Démarrage complet"
    docker compose up -d
    sleep 5
    docker compose exec -T php php outils/migrer.php || true
    docker compose ps

    printf '\n'
    vert "Migration terminée."
    printf '\nÀ vérifier maintenant, dans cet ordre :\n'
    printf '  1. curl -I http://localhost/            -> 200\n'
    printf '  2. curl -s http://localhost/api/classement.php?univers=pokemon&mode=classique\n'
    printf '  3. depuis ton navigateur, sur la NOUVELLE IP, joue une partie\n'
    printf '\nEnsuite seulement :\n'
    printf '  - change URL_PUBLIQUE dans .env pour la nouvelle adresse\n'
    printf '  - docker compose up -d\n'
    printf '  - et garde l ancien VPS debout 48 h, au cas ou\n'
}

case "${1:-}" in
    exporter) exporter ;;
    importer) shift; importer "$@" ;;
    *)
        printf 'Bureau des Primes — migration de VPS\n\n'
        printf '  Sur l ANCIEN serveur   sh %s exporter\n' "$(basename "$0")"
        printf '  Sur le NOUVEAU serveur sh %s importer /root/bdp-migration-....tgz\n\n' "$(basename "$0")"
        exit 1
        ;;
esac
