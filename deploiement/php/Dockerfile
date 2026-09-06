# Bureau des Primes — PHP-FPM.
#
# L'image officielle apporte déjà curl, openssl et mbstring, dont l'API a
# besoin pour parler à Discord et découper les pseudos. Seul pdo_mysql
# manque.

FROM php:8.3-fpm-alpine

RUN docker-php-ext-install pdo_mysql

# Réglages de production : les erreurs partent au journal, pas au
# navigateur. Le site a son propre drapeau « debogage », mais si PHP
# échoue avant de lire sa configuration, c'est ce fichier qui décide.
RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"

# Les sessions dans un volume, pas dans le conteneur : sinon chaque
# « docker compose up » après une mise à jour déconnecte tous les
# joueurs, et il faudrait se reconnecter à Discord à chaque déploiement.
RUN mkdir -p /sessions && chown www-data:www-data /sessions
RUN printf 'session.save_path = "/sessions"\n' \
    > /usr/local/etc/php/conf.d/bdp-sessions.ini
