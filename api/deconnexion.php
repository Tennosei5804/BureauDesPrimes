<?php
/** Fin de session. Le compte et les parties restent en base. */
declare(strict_types=1);
require __DIR__ . '/_amorce.php';
require __DIR__ . '/_discord.php';

demarrer_session();
$_SESSION = [];
if (ini_get('session.use_cookies')) {
    $p = session_get_cookie_params();
    setcookie(session_name(), '', time() - 42000,
        $p['path'], $p['domain'], $p['secure'], $p['httponly']);
}
session_destroy();

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
    repondre(['connecte' => false]);
}
retour_accueil('deconnecte');
