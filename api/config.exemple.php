<?php
/**
 * Bureau des Primes — configuration.
 *
 * Copier ce fichier en  api/config.php  et le remplir. config.php n'est
 * jamais versionné ni mis en ligne depuis un dépôt public : il contient
 * le mot de passe de la base et le secret Discord.
 *
 * Les valeurs peuvent aussi venir de variables d'environnement, ce qui
 * évite d'écrire des secrets dans un fichier : si la variable existe,
 * elle gagne.
 */

return [

    // --- Base de données -------------------------------------------
    // Chez un hébergeur mutualisé, ces quatre valeurs sont fournies
    // dans le panneau d'administration au moment où la base est créée.
    'bd' => [
        'hote'      => getenv('BDP_BD_HOTE') ?: 'localhost',
        'port'      => (int) (getenv('BDP_BD_PORT') ?: 3306),
        'base'      => getenv('BDP_BD_BASE') ?: 'bureau_des_primes',
        'utilisateur' => getenv('BDP_BD_USER') ?: 'root',
        'motdepasse'  => getenv('BDP_BD_PASS') ?: '',
    ],

    // --- Application Discord ---------------------------------------
    // https://discord.com/developers/applications
    //   1. New Application, puis onglet OAuth2
    //   2. copier Client ID et Client Secret ci-dessous
    //   3. dans Redirects, ajouter EXACTEMENT l'URL de 'redirection'
    //      ci-dessous — au caractère près, https compris
    'discord' => [
        'client_id'     => getenv('BDP_DISCORD_ID') ?: '',
        'client_secret' => getenv('BDP_DISCORD_SECRET') ?: '',
        'redirection'   => getenv('BDP_DISCORD_REDIRECT')
                           ?: 'https://bureau-des-primes.example/api/retour.php',
    ],

    // --- Site -------------------------------------------------------
    // Adresse de la page de jeu, vers laquelle on renvoie après une
    // connexion ou une déconnexion.
    'accueil' => getenv('BDP_ACCUEIL') ?: 'https://bureau-des-primes.example/',

    // Mettre à false en production : les erreurs partent alors dans le
    // journal du serveur au lieu d'être renvoyées au navigateur.
    'debogage' => (bool) (getenv('BDP_DEBOGAGE') ?: false),

    // --- Mode bêta ---------------------------------------------------
    // Pendant les essais : le classement et l'historique sont mis en
    // sommeil, et l'avis du jour se rejoue sans attendre le lendemain.
    // Les deux vont ensemble — rejouer à volonté viderait le classement
    // de son sens. Repasser à false rend le jeu à sa forme normale.
    'beta' => (bool) (getenv('BDP_BETA') ?: false),
];
