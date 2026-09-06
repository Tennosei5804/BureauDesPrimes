<?php
/**
 * L'état du joueur courant. Appelé au chargement de la page : c'est ce
 * qui décide si le site affiche « Se connecter » ou un profil, et si la
 * couche compte existe seulement (déploiement statique sans API).
 */
declare(strict_types=1);
require __DIR__ . '/_amorce.php';
require __DIR__ . '/_jeu.php';
require __DIR__ . '/_stats.php';

exiger_methode('GET');

$univers = univers_demande();
registre($univers);   // valide l'univers, refuse s'il est inconnu
$jour = jour_jeu();
$base = [
    'univers' => $univers,
    'jour'    => $jour,
    'numero'  => numero_avis($jour),
    // Dit au front s'il doit proposer le bouton Discord : sans
    // application déclarée, mieux vaut ne rien afficher du tout.
    'discord' => ($CONFIG['discord']['client_id'] ?? '') !== '',
    // Mode bêta : le front met le classement en sommeil et laisse
    // rejouer l'avis du jour. Voir 'beta' dans config.php.
    'beta'    => (bool) ($CONFIG['beta'] ?? false),
];

$j = joueur_courant();
if (!$j) {
    repondre($base + ['connecte' => false]);
}

req('UPDATE joueurs SET vu_le = UTC_TIMESTAMP() WHERE id = ?', [$j['id']]);

repondre($base + [
    'connecte'   => true,
    'joueur'     => joueur_public($j) + ['depuis' => $j['cree_le']],
    'stats'      => stats_joueur((int) $j['id'], $univers),
    'aujourdhui' => parties_du_jour((int) $j['id'], $univers),
]);
