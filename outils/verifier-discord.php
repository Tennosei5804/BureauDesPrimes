<?php
/**
 * Bureau des Primes — diagnostic de la connexion Discord.
 *
 *     php outils/verifier-discord.php
 *     php outils/verifier-discord.php http://localhost:8080
 *
 * Contrôle tout ce qui doit être vrai pour qu'une connexion aboutisse :
 * configuration lisible, identifiants plausibles, URL de redirection
 * cohérente avec l'adresse du site, base joignable, tables présentes,
 * extensions PHP disponibles, sessions inscriptibles.
 *
 * L'URL de redirection est la cause n° 1 des échecs : Discord compare
 * celle que le site envoie avec celle déclarée sur le portail, au
 * caractère près. Ce script affiche la valeur exacte à coller.
 *
 * Sort en code 1 s'il reste un point bloquant.
 */

declare(strict_types=1);

$RACINE = dirname(__DIR__);
$dur = 0;

function ok(string $m): void    { echo "  ok      $m\n"; }
function note(string $m): void  { echo "  note    $m\n"; }
function ko(string $m): void    { global $dur; $dur++; echo "  MANQUE  $m\n"; }

echo "=== Configuration ===\n";

$chemin = $RACINE . '/api/config.php';
if (!is_file($chemin)) {
    ko("api/config.php absent — copier api/config.exemple.php et le remplir.");
    exit(1);
}
$C = require $chemin;
ok('api/config.php lu');

$d = $C['discord'] ?? [];
$id = (string) ($d['client_id'] ?? '');
$secret = (string) ($d['client_secret'] ?? '');

if ($id === '') {
    ko("client_id vide — https://discord.com/developers/applications, onglet OAuth2.");
} elseif (!preg_match('/^\d{17,20}$/', $id)) {
    ko("client_id douteux : un Client ID Discord est un nombre de 17 à 20 chiffres.");
} else {
    ok('client_id renseigné (' . strlen($id) . ' chiffres)');
}

if ($secret === '') {
    ko("client_secret vide — même page, bouton « Reset Secret » pour l'obtenir.");
} elseif (strlen($secret) < 20) {
    ko('client_secret douteux : trop court (' . strlen($secret) . ' caractères).');
} else {
    ok('client_secret renseigné (' . strlen($secret) . ' caractères)');
}

echo "\n=== Adresses ===\n";

$redirection = (string) ($d['redirection'] ?? '');
$accueil     = (string) ($C['accueil'] ?? '');

$ur = parse_url($redirection);
$ua = parse_url($accueil);

if (!$ur || empty($ur['host'])) {
    ko("redirection illisible : « $redirection »");
} else {
    if (!str_ends_with((string) ($ur['path'] ?? ''), '/api/retour.php')) {
        ko("redirection doit se terminer par /api/retour.php — actuellement « "
           . ($ur['path'] ?? '') . " »");
    } else {
        ok('redirection pointe bien sur api/retour.php');
    }
    if (str_contains($redirection, 'bureau-des-primes.example')) {
        ko("redirection pointe encore sur le domaine de démonstration.");
    }
}

if (!$ua || empty($ua['host'])) {
    ko("accueil illisible : « $accueil »");
} elseif (str_contains($accueil, 'bureau-des-primes.example')) {
    ko("accueil pointe encore sur le domaine de démonstration.");
} else {
    ok('accueil : ' . $accueil);
}

// Un retour vers un autre hote que celui du site perd la session : le
// cookie n'y est pas envoye, et le joueur revient deconnecte.
if ($ur && $ua && !empty($ur['host']) && !empty($ua['host'])) {
    $hr = $ur['host'] . ':' . ($ur['port'] ?? ($ur['scheme'] === 'https' ? 443 : 80));
    $ha = $ua['host'] . ':' . ($ua['port'] ?? ($ua['scheme'] === 'https' ? 443 : 80));
    if ($hr !== $ha) {
        ko("redirection ($hr) et accueil ($ha) ne sont pas sur le même hôte : "
           . "le cookie de session ne suivra pas et le joueur reviendra déconnecté.");
    } else {
        ok('redirection et accueil sur le même hôte');
    }
    if (($ur['scheme'] ?? '') === 'http' && !in_array($ur['host'], ['localhost', '127.0.0.1'], true)) {
        note("redirection en http hors localhost : Discord l'accepte, mais le "
             . "jeton transite en clair. Passez en https en production.");
    }
}

echo "\n=== Base de données ===\n";

$bd = $C['bd'] ?? [];
try {
    $pdo = new PDO(
        sprintf('mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4',
                $bd['hote'] ?? 'localhost', $bd['port'] ?? 3306, $bd['base'] ?? ''),
        $bd['utilisateur'] ?? '', $bd['motdepasse'] ?? '',
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    ok('base joignable : ' . ($bd['base'] ?? '?') . ' sur '
       . ($bd['hote'] ?? '?') . ':' . ($bd['port'] ?? '?'));

    $presentes = $pdo->query('SHOW TABLES')->fetchAll(PDO::FETCH_COLUMN);
    foreach (['joueurs', 'parties', 'propositions', 'series'] as $t) {
        if (in_array($t, $presentes, true)) {
            $n = $pdo->query('SELECT COUNT(*) FROM ' . $t)->fetchColumn();
            ok(sprintf('table %-12s %s ligne(s)', $t, $n));
        } else {
            ko("table $t absente — lancer : php outils/migrer.php");
        }
    }
} catch (Throwable $e) {
    ko('base injoignable : ' . $e->getMessage());
    note('sans base, la connexion Discord aboutit puis échoue à enregistrer le joueur.');
}

echo "\n=== Environnement PHP ===\n";

foreach (['curl' => 'appels vers Discord', 'openssl' => 'TLS', 'pdo_mysql' => 'base',
          'mbstring' => 'découpe des pseudos'] as $ext => $usage) {
    if (extension_loaded($ext)) {
        ok("extension $ext ($usage)");
    } else {
        ko("extension $ext absente — nécessaire pour : $usage");
    }
}

$dossier_sessions = session_save_path() ?: sys_get_temp_dir();
if (is_writable($dossier_sessions)) {
    ok('sessions inscriptibles : ' . $dossier_sessions);
} else {
    ko('dossier de sessions non inscriptible : ' . $dossier_sessions);
}

echo "\n=== Joignabilité de Discord ===\n";

// Le piège que ce contrôle existe pour attraper : une pile PHP sans magasin
// de certificats. cURL refuse alors de vérifier discord.com, l'échange du
// code échoue, et le joueur revient déconnecté sans explication — la
// connexion « se remet à zéro » à chaque essai.
if (extension_loaded('curl')) {
    $ch = curl_init('https://discord.com/api/v10/gateway');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 15,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
    ]);
    $rep  = curl_exec($ch);
    $err  = curl_error($ch);
    $http = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    $pem = ini_get('curl.cainfo') ?: ini_get('openssl.cafile');
    if ($rep === false) {
        ko('discord.com injoignable en TLS : ' . $err);
        if (stripos($err, 'certificate') !== false) {
            note($pem
                ? "curl.cainfo pointe sur « $pem » : fichier absent ou illisible ?"
                : "aucun magasin de certificats déclaré — renseigner curl.cainfo et "
                  . "openssl.cafile dans php.ini (php --ini indique lequel est lu).");
        }
    } else {
        ok('discord.com joignable en TLS (HTTP ' . $http . ')');
        if ($pem) {
            ok('magasin de certificats : ' . $pem);
        } else {
            note('aucun curl.cainfo déclaré : la vérification passe par le magasin '
                 . 'du système. Sur une pile portable, mieux vaut le nommer.');
        }
    }
}

echo "\n=== À coller sur le portail Discord ===\n";
echo "  OAuth2 > Redirects, exactement cette ligne :\n\n";
echo "      " . $redirection . "\n\n";
echo "  Portée demandée par le site : identify (rien d'autre).\n";

echo "\n";
if ($dur) {
    echo "$dur point(s) bloquant(s). La connexion Discord ne peut pas aboutir en l'état.\n";
    exit(1);
}
echo "Tout est en place : la connexion Discord devrait fonctionner.\n";
exit(0);
