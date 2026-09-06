<?php
/**
 * Bureau des Primes — OAuth2 Discord, écrit à la main.
 *
 * Le flux est le « authorization code » standard : on envoie le joueur
 * chez Discord, Discord le renvoie avec un code à usage unique, on
 * échange ce code contre un jeton, et on lit son profil.
 *
 * Portée demandée : `identify` seulement. Ni adresse e-mail, ni liste de
 * serveurs — le jeu n'a besoin que d'un identifiant stable, d'un pseudo
 * et d'un avatar.
 */

declare(strict_types=1);

const DISCORD_AUTORISATION = 'https://discord.com/oauth2/authorize';
const DISCORD_JETON        = 'https://discord.com/api/oauth2/token';
const DISCORD_MOI          = 'https://discord.com/api/v10/users/@me';

function discord_config(): array
{
    global $CONFIG;
    $d = $CONFIG['discord'];
    if ($d['client_id'] === '' || $d['client_secret'] === '') {
        refuser('discord_non_configure',
            'L\'application Discord n\'est pas renseignée dans api/config.php.', 503);
    }
    return $d;
}

/** L'adresse chez Discord vers laquelle envoyer le joueur. */
function discord_url_autorisation(string $etat): string
{
    $d = discord_config();
    return DISCORD_AUTORISATION . '?' . http_build_query([
        'client_id'     => $d['client_id'],
        'redirect_uri'  => $d['redirection'],
        'response_type' => 'code',
        'scope'         => 'identify',
        'state'         => $etat,
        'prompt'        => 'none',   // pas de ré-autorisation à chaque connexion
    ], '', '&', PHP_QUERY_RFC3986);
}

/**
 * Appel HTTP vers Discord. Rend [code_http, corps_décodé].
 * Toute erreur réseau lève : l'appelant la transforme en redirection.
 */
function discord_appel(string $url, ?array $post = null, array $entetes = []): array
{
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 15,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
        CURLOPT_USERAGENT      => 'BureauDesPrimes (+https://github.com/, 1.0)',
        CURLOPT_HTTPHEADER     => array_merge(['Accept: application/json'], $entetes),
    ]);
    if ($post !== null) {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($post));
    }
    $corps = curl_exec($ch);
    if ($corps === false) {
        $err = curl_error($ch);
        curl_close($ch);
        throw new RuntimeException('Discord injoignable : ' . $err);
    }
    $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    return [$code, json_decode((string) $corps, true) ?: []];
}

/** Échange le code à usage unique contre un jeton d'accès. */
function discord_echanger_code(string $code): string
{
    $d = discord_config();
    [$http, $rep] = discord_appel(DISCORD_JETON, [
        'client_id'     => $d['client_id'],
        'client_secret' => $d['client_secret'],
        'grant_type'    => 'authorization_code',
        'code'          => $code,
        'redirect_uri'  => $d['redirection'],
    ], ['Content-Type: application/x-www-form-urlencoded']);

    if ($http !== 200 || empty($rep['access_token'])) {
        // La cause la plus fréquente : l'URL de redirection déclarée sur
        // le portail Discord ne correspond pas à celle de config.php.
        throw new RuntimeException('Échange du code refusé par Discord ('
            . $http . ' ' . ($rep['error_description'] ?? $rep['error'] ?? '?') . ')');
    }
    return (string) $rep['access_token'];
}

/** Le profil public du joueur : id, pseudo, avatar. */
function discord_utilisateur(string $jeton): array
{
    [$http, $rep] = discord_appel(DISCORD_MOI, null, ['Authorization: Bearer ' . $jeton]);
    if ($http !== 200 || empty($rep['id'])) {
        throw new RuntimeException('Profil Discord illisible (' . $http . ')');
    }
    return $rep;
}

/** Crée ou met à jour le joueur, et rend son identifiant local. */
function joueur_depuis_discord(array $u): int
{
    req('INSERT INTO joueurs (discord_id, pseudo, nom_affiche, avatar, cree_le, vu_le)
         VALUES (?, ?, ?, ?, UTC_TIMESTAMP(), UTC_TIMESTAMP())
         ON DUPLICATE KEY UPDATE
            pseudo = VALUES(pseudo), nom_affiche = VALUES(nom_affiche),
            avatar = VALUES(avatar), vu_le = UTC_TIMESTAMP()',
        [
            (string) $u['id'],
            mb_substr((string) ($u['username'] ?? 'pirate'), 0, 64),
            isset($u['global_name']) ? mb_substr((string) $u['global_name'], 0, 64) : null,
            $u['avatar'] ?? null,
        ]);

    $id = req('SELECT id FROM joueurs WHERE discord_id = ?', [(string) $u['id']])
        ->fetchColumn();
    return (int) $id;
}

/**
 * Le chemin d'où part la connexion, pour y ramener le joueur ensuite.
 *
 * On n'accepte qu'un chemin absolu de ce site. « https://ailleurs.test »
 * ou « //ailleurs.test » — protocole implicite — feraient de connexion.php
 * une redirection ouverte : un lien portant notre domaine, qui dépose le
 * visiteur n'importe où.
 */
function retour_demande(): ?string
{
    $v = (string) ($_GET['retour'] ?? '');
    if ($v === '' || strlen($v) > 300) {
        return null;
    }
    if ($v[0] !== '/' || str_starts_with($v, '//') || str_starts_with($v, '/\\')) {
        return null;
    }
    if (preg_match('/[\x00-\x1F\x7F]/', $v)) {   // retours ligne, injection d'en-tête
        return null;
    }
    return $v;
}

/** Le schéma, l'hôte et le port du site, déduits de « accueil ». */
function origine_site(): string
{
    global $CONFIG;
    $u = parse_url($CONFIG['accueil']);
    if (!$u || empty($u['host'])) {
        return rtrim($CONFIG['accueil'], '/');
    }
    return ($u['scheme'] ?? 'https') . '://' . $u['host']
         . (isset($u['port']) ? ':' . $u['port'] : '');
}

/**
 * Renvoie le joueur là d'où il vient, avec un mot sur ce qui s'est passé.
 *
 * Sans le chemin mémorisé au départ, on le déposait toujours sur le lobby :
 * se connecter depuis le Bingo Book faisait perdre la page en cours.
 */
function retour_accueil(string $etat, ?string $raison = null): never
{
    global $CONFIG;
    $base = $CONFIG['accueil'];
    if (isset($_SESSION['oauth_retour'])) {
        $chemin = (string) $_SESSION['oauth_retour'];
        unset($_SESSION['oauth_retour']);
        if ($chemin !== '') {
            $base = origine_site() . $chemin;
        }
    }
    $url = $base . (str_contains($base, '?') ? '&' : '?')
        . http_build_query(array_filter([
            'connexion' => $etat,
            'raison'    => $raison,
        ]));
    header('Location: ' . $url, true, 302);
    exit;
}
