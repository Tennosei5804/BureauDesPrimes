<?php
/**
 * Les parties passées du joueur connecté, de la plus récente à la plus
 * ancienne, avec le détail des fiches versées.
 *
 * GET ?limite=20&avant=2026-08-30   (avant : pagination par date)
 */
declare(strict_types=1);
require __DIR__ . '/_amorce.php';
require __DIR__ . '/_jeu.php';
require __DIR__ . '/_stats.php';

exiger_methode('GET');
$joueur = exiger_joueur();

$univers = univers_demande();
$limite = max(1, min(100, (int) ($_GET['limite'] ?? 20)));
$mode = (string) ($_GET['mode'] ?? '');
$avant = (string) ($_GET['avant'] ?? '');

$where = ['p.joueur_id = ?', 'p.univers = ?'];
$args = [(int) $joueur['id'], $univers];
if ($mode !== '') {
    if (!in_array($mode, modes($univers), true)) {
        refuser('mode_inconnu', 'Mode de jeu inconnu : ' . $mode);
    }
    $where[] = 'p.mode = ?';
    $args[] = $mode;
}
if ($avant !== '') {
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $avant)) {
        refuser('avant_invalide', 'Le paramètre « avant » attend une date AAAA-MM-JJ.');
    }
    $where[] = 'p.jour < ?';
    $args[] = $avant;
}
$filtre = implode(' AND ', $where);

$parties = req(
    "SELECT p.id, p.mode, p.jour, p.numero_avis, p.cible, p.fiches, p.resolu_le
       FROM parties p
      WHERE $filtre
      ORDER BY p.jour DESC, p.mode ASC
      LIMIT $limite", $args)->fetchAll();

// Les fiches de toutes les parties de la page en une seule requête,
// plutôt qu'une requête par ligne affichée.
$fiches = [];
if ($parties) {
    $ids = array_column($parties, 'id');
    $trous = implode(',', array_fill(0, count($ids), '?'));
    $lignes = req("SELECT partie_id, rang, personnage
                     FROM propositions
                    WHERE partie_id IN ($trous)
                    ORDER BY partie_id, rang", $ids)->fetchAll();
    foreach ($lignes as $l) {
        $fiches[(int) $l['partie_id']][] = $l['personnage'];
    }
}

$sortie = [];
foreach ($parties as $p) {
    $sortie[] = [
        'mode'         => $p['mode'],
        'jour'         => $p['jour'],
        'numero'       => (int) $p['numero_avis'],
        'cible'        => $p['cible'],
        'fiches'       => (int) $p['fiches'],
        'resolu_le'    => $p['resolu_le'],
        'propositions' => $fiches[(int) $p['id']] ?? [],
    ];
}

repondre([
    'parties' => $sortie,
    // À renvoyer en « avant » pour la page suivante ; null quand tout a
    // été servi.
    'suite'   => count($sortie) === $limite ? end($sortie)['jour'] : null,
]);
