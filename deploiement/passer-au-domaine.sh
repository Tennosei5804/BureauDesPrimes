#!/bin/sh
# Passer les deux projets d'une IP nue à un vrai domaine.
#
#   sh passer-au-domaine.sh pokepension.fr
#   sh passer-au-domaine.sh pokepension.fr jeu.autre-domaine.fr
#
# Le premier argument est le domaine de PokéPension. Le site prend le
# domaine et son « www », l'API prend « api. ».
#
# Le second, facultatif, est celui de Bureau des Primes. SANS LUI, LE JEU
# NE BOUGE PAS : il reste servi en clair sur l'IP du VPS, et sa connexion
# Discord reste indisponible. C'est le cas courant — les deux projets
# n'ont aucune raison de partager un nom de domaine.
#
# POURQUOI UN SCRIPT ET NON UNE LISTE D'ÉTAPES. Le domaine se pose à SIX
# endroits, dans trois fichiers, et en oublier un ne casse rien de
# visible : le site répond, et c'est la connexion qui échoue, une heure
# plus tard, sans message clair. Les six vont ensemble ou pas du tout.
#
# CE QUE LE SCRIPT NE FAIT PAS, ET QUE TOI SEUL PEUX FAIRE :
#   1. le DNS. Trois enregistrements A vers l'IP de ce VPS, propagés
#      AVANT de lancer ce script — Caddy demanderait sinon un certificat
#      pour un nom qui ne pointe nulle part, et Let's Encrypt bloque une
#      heure après cinq échecs.
#   2. les deux portails Discord, où il faut coller les adresses de
#      retour. Le script te les affiche à la fin, prêtes à copier.

set -eu

ICI=$(cd "$(dirname "$0")" && pwd)
PA=${PA_CHEMIN:-/opt/pokepension}

vert()  { printf '\033[32m%s\033[0m\n' "$*"; }
rouge() { printf '\033[31m%s\033[0m\n' "$*"; }
etape() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

DOM=${1:-}
[ -n "$DOM" ] || { rouge "Usage : sh passer-au-domaine.sh pokepension.fr [domaine-du-jeu]"; exit 1; }
D_PA="$DOM, www.$DOM"          # forme Caddy : deux hotes, un seul bloc
# Forme CORS : une liste d'origines completes, separees par des virgules
# SANS espace. Melanger les deux formes casserait la connexion du site
# sans message clair — le navigateur refuserait chaque appel.
D_ORIGINES="https://$DOM,https://www.$DOM"
D_API="api.$DOM"
D_JEU=${2:-}                    # vide = Bureau des Primes ne bouge pas

printf 'PokéPension         https://%s  (et www)\n' "$DOM"
printf 'API PokéPension     https://%s\n' "$D_API"
if [ -n "$D_JEU" ]; then
    printf 'Bureau des Primes   https://%s\n' "$D_JEU"
else
    printf 'Bureau des Primes   inchangé — reste en clair sur son IP\n'
fi

# --- 1. le DNS pointe-t-il bien ici ? ---------------------------------
etape "1/6  Vérification du DNS"
MOI=$(curl -s --max-time 10 https://api.ipify.org 2>/dev/null || echo '')
[ -n "$MOI" ] && printf '   cette machine : %s\n' "$MOI"
MANQUE=0
for N in "$DOM" "www.$DOM" "$D_API" $D_JEU; do
    R=$(getent hosts "$N" 2>/dev/null | awk '{print $1}' | head -1)
    if [ -z "$R" ]; then
        rouge "   $N ne résout pas encore"
        MANQUE=1
    elif [ -n "$MOI" ] && [ "$R" != "$MOI" ]; then
        rouge "   $N pointe vers $R, pas vers cette machine"
        MANQUE=1
    else
        vert "   $N -> $R"
    fi
done
if [ "$MANQUE" = 1 ]; then
    rouge ""
    rouge "Le DNS n'est pas prêt. Pose les enregistrements A, attends la"
    rouge "propagation, et relance. Démarrer maintenant grillerait cinq"
    rouge "tentatives Let's Encrypt et bloquerait une heure."
    exit 1
fi

# --- 2. Bureau des Primes ---------------------------------------------
etape "2/6  Bureau des Primes"
cd "$ICI"
if [ -z "$D_JEU" ]; then
    printf '   pas de domaine donné : le jeu reste sur son IP, inchangé\n'
else
    cp .env .env.avant-domaine
    sed -i "s|^ADRESSE=.*|ADRESSE=$D_JEU|" .env
    sed -i "s|^URL_PUBLIQUE=.*|URL_PUBLIQUE=https://$D_JEU|" .env
    vert "   .env : ADRESSE et URL_PUBLIQUE"
    # Les pages portent le domaine dans leurs apercus de partage et leur
    # plan de site : un outil du projet s'en charge.
    if [ -f ../outils/domaine.py ] && command -v python3 >/dev/null 2>&1; then
        (cd .. && python3 outils/domaine.py "$D_JEU" >/dev/null) \
            && vert "   pages : apercus de partage et sitemap"
    fi
fi

# --- 3. les adresses des deux services PokéPension ---------------------
etape "3/6  Adresses de PokéPension dans la pile"
for L in "PA_ADRESSE_SITE=$D_PA" "PA_ADRESSE_API=$D_API"; do
    C=${L%%=*}
    if grep -q "^$C=" .env; then sed -i "s|^$C=.*|$L|" .env
    else printf '%s\n' "$L" >> .env; fi
done
vert "   .env : PA_ADRESSE_SITE et PA_ADRESSE_API"

# --- 4. la configuration de l'API PokéPension -------------------------
etape "4/6  API PokéPension"
F="$PA/api/.env"
[ -f "$F" ] || { rouge "   $F introuvable"; exit 1; }
cp "$F" "$F.avant-domaine"
sed -i "s|^API_URL=.*|API_URL=https://$D_API|" "$F"
sed -i "s|^SITE_ORIGINES=.*|SITE_ORIGINES=$D_ORIGINES|" "$F"
chmod 600 "$F"
vert "   API_URL et SITE_ORIGINES"

# --- 5. l'adresse inscrite dans le site --------------------------------
# Elle est posée à l'assemblage, dans une seule balise de index.html.
# La réécrire ici évite d'avoir à réassembler le site sur le serveur —
# ce qui demanderait d'y déployer aussi les sources et app/src.
etape "5/6  Adresse de l'API inscrite dans le site"
I="$PA/site/public/index.html"
if [ -f "$I" ] && grep -qE 'POKE(ARCHIVE|PENSION)_API = ' "$I"; then
    cp "$I" "$I.avant-domaine"
    sed -i -E "s|POKE(ARCHIVE\|PENSION)_API = \"[^\"]*\"|POKEPENSION_API = \"https://$D_API\"|" "$I"
    vert "   $(grep -oE 'POKE(ARCHIVE|PENSION)_API = \"[^\"]*\"' "$I" | head -1)"
else
    rouge "   index.html introuvable ou déjà différent — à vérifier à la main"
fi

# --- 6. redémarrage ----------------------------------------------------
etape "6/6  Redémarrage"
docker compose up -d
printf '   Caddy demande les certificats'
N=0
while [ "$N" -lt 30 ]; do
    if curl -sk --max-time 5 "https://$DOM/" -o /dev/null 2>/dev/null; then
        printf '\n'; vert "   HTTPS répond sur $DOM"; break
    fi
    printf '.'; sleep 4; N=$((N + 1))
done
[ "$N" -lt 30 ] || { printf '\n'; rouge "   pas encore — docker compose logs caddy"; }

printf '\n'
vert "Bascule terminée."
printf '
  site : https://%s
  api  : https://%s
' "$DOM" "$D_API"
cat <<FIN

À FAIRE MAINTENANT, dans les deux portails Discord — c'est la seule
chose qui reste, et rien ne fonctionnera sans elle.

  PokéPension → OAuth2 > Redirects, AJOUTER sans rien supprimer :
    https://$D_API/auth/discord/retour

  Garde les redirections existantes : celle de l'application de bureau
  doit rester, sinon la version Tauri ne se connectera plus.

L'APPLICATION DE BUREAU se recompile avec la nouvelle adresse :
    POKEPENSION_API=https://$D_API cargo tauri build
Elle parle alors à la même API que le site, donc au même compte et aux
mêmes données.

Les ports 8130 et 8787 ne servent plus : Caddy route par nom d'hôte.
Tu peux retirer leurs lignes de compose.yml et fermer le pare-feu.
FIN
