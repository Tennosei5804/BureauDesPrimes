<?php
/**
 * Reprise d'une progression jouée sans compte.
 *
 * POST { parties: [ { mode, jour, propositions: [...] }, ... ] }
 *
 * À la première connexion, le navigateur envoie ce que contient son
 * localStorage. Chaque partie est vérifiée comme une partie du jour :
 * le serveur sait recalculer la cible de n'importe quelle date passée,
 * donc rien n'est admis sur parole. Une partie refusée n'interrompt pas
 * les autres — le détail revient dans `refusees`.
 */
declare(strict_types=1);
require __DIR__ . '/_amorce.php';
require __DIR__ . '/_jeu.php';
require __DIR__ . '/_stats.php';

exiger_methode('POST');
$joueur = exiger_joueur();

$corps   = corps_json();
$univers = univers_demande($corps);
$parties = $corps['parties'] ?? null;
if (!is_array($parties) || !array_is_list($parties)) {
    refuser('parties_invalides', 'Il manque la liste des parties à reprendre.');
}
if (count($parties) > 500) {
    refuser('trop_de_parties', 'Reprise limitée à 500 parties par envoi.');
}

$reprises = 0;
$deja = 0;
$refusees = [];

foreach ($parties as $i => $p) {
    $mode  = is_array($p) ? (string) ($p['mode'] ?? '') : '';
    $jour  = is_array($p) ? (string) ($p['jour'] ?? '') : '';
    $props = is_array($p) ? ($p['propositions'] ?? null) : null;

    // Contrôles à la main plutôt que valider_partie() : ici un refus
    // doit écarter une ligne, pas couper la requête entière.
    if (!in_array($mode, modes($univers), true) || !jour_valide($jour)
        || !is_array($props) || !array_is_list($props) || !$props
        || count($props) > 200) {
        $refusees[] = ['rang' => $i, 'raison' => 'partie_malformee'];
        continue;
    }
    $noms = array_map(static fn ($n) => is_string($n) ? $n : '', $props);
    // Le registre entier, comme valider_partie() : une fiche versée peut
    // porter un personnage qui ne pourrait jamais être la réponse du jour.
    $connus = array_column(registre($univers)['persos'], 'nom');
    if (array_diff($noms, $connus) || count(array_unique($noms)) !== count($noms)) {
        $refusees[] = ['rang' => $i, 'raison' => 'fiches_invalides'];
        continue;
    }
    if (end($noms) !== cible($univers, $mode, $jour)) {
        $refusees[] = ['rang' => $i, 'raison' => 'partie_non_resolue'];
        continue;
    }

    $r = enregistrer_partie((int) $joueur['id'], $univers, $mode, $jour, $noms, [
        'cible'  => end($noms),
        'fiches' => count($noms),
        'numero' => numero_avis($jour),
    ]);
    $r['nouveau'] ? $reprises++ : $deja++;
}

repondre([
    'reprises' => $reprises,
    'deja'     => $deja,
    'refusees' => $refusees,
    'stats'    => stats_joueur((int) $joueur['id'], $univers),
]);
