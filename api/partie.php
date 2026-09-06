<?php
/**
 * Enregistrement d'un avis résolu.
 *
 * POST { mode, jour, propositions: ["Nami", "Kaido", ...] }
 *
 * Le serveur recalcule la cible du jour et rejoue la partie avant
 * d'écrire quoi que ce soit : voir valider_partie() dans _jeu.php.
 */
declare(strict_types=1);
require __DIR__ . '/_amorce.php';
require __DIR__ . '/_jeu.php';
require __DIR__ . '/_stats.php';

exiger_methode('POST');
$joueur = exiger_joueur();

$corps   = corps_json();
$univers = univers_demande($corps);
$mode  = (string) ($corps['mode'] ?? '');
$jour  = (string) ($corps['jour'] ?? '');
$props = $corps['propositions'] ?? null;

if (!is_array($props) || !array_is_list($props)) {
    refuser('propositions_invalides', 'Il manque la liste des fiches versées.');
}

$valide = valider_partie($univers, $mode, $jour, $props);
$resultat = enregistrer_partie((int) $joueur['id'], $univers, $mode, $jour,
                               $props, $valide);

repondre([
    'enregistre' => true,
    // false : cet avis avait déjà été résolu, le premier résultat prime.
    'nouveau'    => $resultat['nouveau'],
    'partie'     => $resultat['partie'],
    'stats'      => stats_joueur((int) $joueur['id'], $univers),
]);
