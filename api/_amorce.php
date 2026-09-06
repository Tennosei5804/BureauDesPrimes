<?php
/**
 * Bureau des Primes — amorce commune à tous les points d'entrée de l'API.
 *
 * Chaque fichier public de api/ commence par  require __DIR__ . '/_amorce.php';
 * Les fichiers dont le nom commence par « _ » ne sont jamais appelés
 * directement : le .htaccess du dossier les refuse.
 */

declare(strict_types=1);

// Les horodatages stockés restent en UTC — c'est ce que MySQL écrit avec
// UTC_TIMESTAMP(), et un journal en UTC se relit sans ambiguïté. Le jour
// de jeu, lui, bascule à minuit heure de Paris : voir jour_jeu() dans
// _jeu.php, qui demande son fuseau explicitement.
date_default_timezone_set('UTC');

mb_internal_encoding('UTF-8');

// ---------------------------------------------------------------- config
$chemin = __DIR__ . '/config.php';
if (!is_file($chemin)) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode([
        'erreur' => 'config_absente',
        'message' => 'api/config.php est introuvable. Copier api/config.exemple.php et le remplir.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}
/** @var array $CONFIG */
$CONFIG = require $chemin;

if (!empty($CONFIG['debogage'])) {
    ini_set('display_errors', '1');
    error_reporting(E_ALL);
} else {
    ini_set('display_errors', '0');
    error_reporting(E_ALL);
}

/**
 * Une exception qui remonte jusqu'ici ne doit jamais afficher de trace :
 * elle contiendrait le mot de passe de la base ou le secret Discord.
 */
set_exception_handler(function (Throwable $e) use ($CONFIG): void {
    error_log('[Bureau des Primes] ' . $e->getMessage() . ' @ ' . $e->getFile() . ':' . $e->getLine());
    $details = !empty($CONFIG['debogage']) ? $e->getMessage() : null;
    repondre(['erreur' => 'panne_serveur', 'message' => $details], 500);
});

// ------------------------------------------------------------- réponses
/**
 * Renvoie du JSON et arrête le script. Aucune réponse de l'API n'est
 * mise en cache : elles dépendent toutes de la session.
 */
function repondre(array $corps, int $code = 200): never
{
    if (!headers_sent()) {
        http_response_code($code);
        header('Content-Type: application/json; charset=utf-8');
        header('Cache-Control: no-store');
        header('X-Content-Type-Options: nosniff');
    }
    echo json_encode($corps, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function refuser(string $code, string $message, int $http = 400): never
{
    repondre(['erreur' => $code, 'message' => $message], $http);
}

/** Impose la méthode HTTP attendue. */
function exiger_methode(string $methode): void
{
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== $methode) {
        header('Allow: ' . $methode);
        refuser('methode', 'Cette adresse attend une requête ' . $methode . '.', 405);
    }
}

/**
 * L'univers visé par la requête. Chaque registre a ses propres séries et
 * classements ; sans ce paramètre on mélangerait les deux jeux.
 * Par défaut « one-piece », ce qui laisse fonctionner les anciens appels.
 */
function univers_demande(?array $corps = null): string
{
    $u = $_GET['univers'] ?? ($corps['univers'] ?? 'one-piece');
    return is_string($u) ? $u : 'one-piece';
}

/** Corps JSON de la requête, en tableau. */
function corps_json(): array
{
    $brut = file_get_contents('php://input') ?: '';
    $data = json_decode($brut, true);
    return is_array($data) ? $data : [];
}

// -------------------------------------------------------------- session
function demarrer_session(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }
    $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
        || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');

    session_set_cookie_params([
        'lifetime' => 0,
        'path'     => '/',
        'secure'   => $https,
        'httponly' => true,
        // Lax et non Strict : au retour de Discord le navigateur arrive
        // par une navigation venue d'un autre site, et Strict effacerait
        // la session au moment précis où on en a besoin.
        'samesite' => 'Lax',
    ]);
    session_name('bdp_session');
    session_start();
}

// ------------------------------------------------------------------ PDO
function bd(): PDO
{
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }
    global $CONFIG;
    $c = $CONFIG['bd'];
    $dsn = sprintf('mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4',
        $c['hote'], $c['port'], $c['base']);

    $pdo = new PDO($dsn, $c['utilisateur'], $c['motdepasse'], [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        // Vraies requêtes préparées côté serveur : le pilote n'assemble
        // plus la requête lui-même, donc pas d'injection possible.
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);
    return $pdo;
}

/** Raccourci : prépare, exécute, rend le PDOStatement. */
function req(string $sql, array $args = []): PDOStatement
{
    $st = bd()->prepare($sql);
    $st->execute($args);
    return $st;
}

// ------------------------------------------------------------ le joueur
/** Le joueur connecté, ou null. */
function joueur_courant(): ?array
{
    demarrer_session();
    $id = $_SESSION['joueur_id'] ?? null;
    if (!$id) {
        return null;
    }
    $j = req('SELECT id, discord_id, pseudo, nom_affiche, avatar, cree_le
                FROM joueurs WHERE id = ?', [$id])->fetch();
    if (!$j) {
        // Compte supprimé entre-temps : la session ne vaut plus rien.
        unset($_SESSION['joueur_id']);
        return null;
    }
    return $j;
}

function exiger_joueur(): array
{
    $j = joueur_courant();
    if (!$j) {
        refuser('non_connecte', 'Cette action demande une connexion Discord.', 401);
    }
    return $j;
}

/** Le joueur tel que le front l'affiche : pseudo, avatar, rien de sensible. */
function joueur_public(array $j): array
{
    $avatar = null;
    if (!empty($j['avatar'])) {
        $ext = str_starts_with($j['avatar'], 'a_') ? 'gif' : 'png';
        $avatar = sprintf('https://cdn.discordapp.com/avatars/%s/%s.%s?size=64',
            $j['discord_id'], $j['avatar'], $ext);
    } else {
        // Avatar par défaut de Discord, choisi par le serveur pour ne pas
        // laisser un trou dans les classements.
        $n = (int) ((int) $j['discord_id'] >> 22) % 6;
        $avatar = 'https://cdn.discordapp.com/embed/avatars/' . $n . '.png';
    }
    return [
        'id'     => (int) $j['id'],
        'pseudo' => $j['nom_affiche'] ?: $j['pseudo'],
        'avatar' => $avatar,
    ];
}
