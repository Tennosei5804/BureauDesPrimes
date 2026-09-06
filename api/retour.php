<?php
/**
 * Retour de Discord : on vérifie l'état, on échange le code contre un
 * jeton, on lit le profil, on ouvre la session, et on renvoie le joueur
 * sur la page de jeu.
 */
declare(strict_types=1);
require __DIR__ . '/_amorce.php';
require __DIR__ . '/_discord.php';

exiger_methode('GET');
demarrer_session();

// Le joueur a refusé l'autorisation sur l'écran Discord.
if (isset($_GET['error'])) {
    retour_accueil('refusee', (string) $_GET['error']);
}

$etat_recu   = (string) ($_GET['state'] ?? '');
$etat_attendu = (string) ($_SESSION['oauth_etat'] ?? '');
$ne_le       = (int) ($_SESSION['oauth_ne_le'] ?? 0);
unset($_SESSION['oauth_etat'], $_SESSION['oauth_ne_le']);

if ($etat_attendu === '' || !hash_equals($etat_attendu, $etat_recu)) {
    retour_accueil('erreur', 'etat');
}
// Une demande vieille de plus de dix minutes n'a plus de raison d'aboutir.
if ($ne_le && time() - $ne_le > 600) {
    retour_accueil('erreur', 'expiree');
}

$code = (string) ($_GET['code'] ?? '');
if ($code === '') {
    retour_accueil('erreur', 'code_absent');
}

try {
    $jeton = discord_echanger_code($code);
    $profil = discord_utilisateur($jeton);
    $joueur_id = joueur_depuis_discord($profil);
} catch (Throwable $e) {
    error_log('[Bureau des Primes] connexion Discord : ' . $e->getMessage());
    retour_accueil('erreur', 'discord');
}

// Nouvel identifiant de session une fois l'identité établie : sans cela,
// un identifiant obtenu avant la connexion resterait valable après.
session_regenerate_id(true);
$_SESSION['joueur_id'] = $joueur_id;

retour_accueil('ok');
