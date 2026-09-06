<?php
/**
 * Départ de la connexion : on fabrique un jeton anti-CSRF, on le range en
 * session, puis on envoie le joueur chez Discord.
 */
declare(strict_types=1);
require __DIR__ . '/_amorce.php';
require __DIR__ . '/_discord.php';

exiger_methode('GET');
demarrer_session();

// L'état est comparé au retour : il garantit que le code reçu répond
// bien à une demande partie d'ici, et pas d'un lien piégé.
$etat = bin2hex(random_bytes(16));
$_SESSION['oauth_etat'] = $etat;
$_SESSION['oauth_ne_le'] = time();

// La page d'où part la connexion, pour y revenir plutôt que sur le lobby.
// Elle voyage en session et non dans l'URL de retour : Discord ne renvoie
// que « state », et un paramètre aller-retour serait modifiable en chemin.
$retour = retour_demande();
if ($retour !== null) {
    $_SESSION['oauth_retour'] = $retour;
} else {
    unset($_SESSION['oauth_retour']);
}

header('Location: ' . discord_url_autorisation($etat), true, 302);
