<?php
/**
 * Classements.
 *
 * GET ?perimetre=mode|jeu|global&univers=naruto&mode=classique
 *     &portee=jour|serie|parties&limite=25
 *
 * Deux axes indépendants.
 *
 *   Le PÉRIMÈTRE dit sur quoi on compare :
 *     mode    un mode d'un registre — le duel le plus serré
 *     jeu     tous les modes d'un registre
 *     global  les quatre registres réunis
 *
 *   La PORTÉE dit ce qu'on compare :
 *     jour     l'avis du jour : le plus d'avis résolus devant, à égalité
 *              le moins de fiches versées, puis le plus rapide
 *     serie    les séries en cours les plus longues
 *     parties  le plus d'avis résolus depuis le début
 *
 * Au périmètre « mode » il n'y a qu'un avis par jour : « le plus d'avis
 * résolus » vaut 1 pour tout le monde et le classement retombe de
 * lui-même sur le nombre de fiches. Une seule requête sert donc les
 * trois périmètres, ce qui évite trois tris qui divergeraient.
 */
declare(strict_types=1);
require __DIR__ . '/_amorce.php';
require __DIR__ . '/_jeu.php';
require __DIR__ . '/_stats.php';

exiger_methode('GET');

$perimetre = (string) ($_GET['perimetre'] ?? 'mode');
if (!in_array($perimetre, ['mode', 'jeu', 'global'], true)) {
    refuser('perimetre_inconnu', 'Périmètre inconnu : ' . $perimetre);
}
$portee = (string) ($_GET['portee'] ?? 'jour');
if (!in_array($portee, ['jour', 'serie', 'parties'], true)) {
    refuser('portee_inconnue', 'Classement inconnu : ' . $portee);
}

// L'univers et le mode ne sont exigés que là où ils veulent dire quelque
// chose : demander un mode pour un classement global n'aurait pas de sens.
$univers = $perimetre === 'global' ? null : univers_demande();
$mode = null;
if ($univers !== null) {
    // modes() lit le registre, donc valide l'univers au passage : sans ce
    // contrôle un univers inventé rendrait un classement vide au lieu
    // d'une erreur.
    $connus = modes($univers);
    if ($perimetre === 'mode') {
        $mode = (string) ($_GET['mode'] ?? 'classique');
        if (!in_array($mode, $connus, true)) {
            refuser('mode_inconnu', 'Mode de jeu inconnu : ' . $mode);
        }
    }
}

// Borné puis injecté en dur : MySQL refuse un paramètre lié dans LIMIT
// quand les requêtes préparées ne sont pas émulées.
$limite = max(1, min(100, (int) ($_GET['limite'] ?? 25)));

$jour = jour_jeu();
$moi = joueur_courant();
$moi_id = $moi ? (int) $moi['id'] : 0;

/**
 * La restriction de périmètre, en SQL et en paramètres.
 *
 * Renvoie une chaîne à coller derrière un WHERE déjà ouvert, donc
 * toujours préfixée de « AND », vide au périmètre global.
 */
function perimetre_sql(?string $univers, ?string $mode, string $prefixe = ''): array
{
    $p = $prefixe === '' ? '' : $prefixe . '.';
    if ($univers === null) {
        return ['', []];
    }
    if ($mode === null) {
        return [" AND {$p}univers = ?", [$univers]];
    }
    return [" AND {$p}univers = ? AND {$p}mode = ?", [$univers, $mode]];
}

$colonnes = 'j.id, j.discord_id, j.pseudo, j.nom_affiche, j.avatar';
// GROUP BY sur toutes les colonnes lues : MariaDB ne déduit pas toujours
// qu'elles dépendent de j.id, et ONLY_FULL_GROUP_BY refuserait la requête.
$groupe = 'GROUP BY j.id, j.discord_id, j.pseudo, j.nom_affiche, j.avatar';

if ($portee === 'jour') {
    [$ou, $args] = perimetre_sql($univers, $mode, 'p');

    $lignes = req(
        "SELECT $colonnes,
                COUNT(*) AS resolus, SUM(p.fiches) AS fiches, MAX(p.resolu_le) AS dernier
           FROM parties p JOIN joueurs j ON j.id = p.joueur_id
          WHERE p.jour = ?$ou
          $groupe
          ORDER BY resolus DESC, fiches ASC, dernier ASC
          LIMIT $limite", array_merge([$jour], $args))->fetchAll();

    $total = (int) req(
        "SELECT COUNT(DISTINCT p.joueur_id) FROM parties p WHERE p.jour = ?$ou",
        array_merge([$jour], $args))->fetchColumn();

    $rang_moi = null;
    if ($moi_id) {
        $ma = req(
            "SELECT COUNT(*) AS resolus, SUM(p.fiches) AS fiches, MAX(p.resolu_le) AS dernier
               FROM parties p WHERE p.joueur_id = ? AND p.jour = ?$ou",
            array_merge([$moi_id, $jour], $args))->fetch();
        if ($ma && (int) $ma['resolus'] > 0) {
            $rang_moi = 1 + (int) req(
                "SELECT COUNT(*) FROM (
                    SELECT p.joueur_id,
                           COUNT(*) AS r, SUM(p.fiches) AS f, MAX(p.resolu_le) AS d
                      FROM parties p WHERE p.jour = ?$ou GROUP BY p.joueur_id
                 ) t
                  WHERE t.r > ?
                     OR (t.r = ? AND (t.f < ? OR (t.f = ? AND t.d < ?)))",
                array_merge([$jour], $args,
                    [$ma['resolus'], $ma['resolus'], $ma['fiches'], $ma['fiches'], $ma['dernier']])
            )->fetchColumn();
        }
    }
    // Un seul avis par jour dans un mode : c'est le nombre de fiches qui
    // départage. Dès qu'on élargit, c'est le nombre d'avis résolus.
    $cle_score = $perimetre === 'mode' ? 'fiches' : 'resolus';
    $unite = $perimetre === 'mode' ? 'fiche' : 'avis';
    // Hors d'un mode unique, tout le monde affiche « 1 avis » ou presque :
    // c'est le total de fiches qui départage, autant le montrer.
    $cle_appoint = $perimetre === 'mode' ? null : 'fiches';
    $unite_appoint = 'fiche';
} elseif ($portee === 'serie') {
    // Une série n'est en cours que si le joueur a résolu un avis hier ou
    // aujourd'hui ; au-delà elle est rompue et n'a plus à figurer ici.
    // Sur plusieurs modes on retient la plus longue, pas leur somme :
    // additionner des séries parallèles ne décrirait aucune assiduité.
    $depuis = veille($jour);
    [$ou, $args] = perimetre_sql($univers, $mode, 's');

    $lignes = req(
        "SELECT $colonnes,
                MAX(s.serie) AS serie, SUM(s.parties) AS parties,
                MAX(s.meilleure_serie) AS meilleure_serie
           FROM series s JOIN joueurs j ON j.id = s.joueur_id
          WHERE s.dernier_jour >= ? AND s.serie > 0$ou
          $groupe
          ORDER BY serie DESC, parties DESC
          LIMIT $limite", array_merge([$depuis], $args))->fetchAll();

    $total = (int) req(
        "SELECT COUNT(DISTINCT s.joueur_id) FROM series s
          WHERE s.dernier_jour >= ? AND s.serie > 0$ou",
        array_merge([$depuis], $args))->fetchColumn();

    $rang_moi = null;
    if ($moi_id) {
        $ma = req(
            "SELECT MAX(s.serie) AS serie, SUM(s.parties) AS parties FROM series s
              WHERE s.joueur_id = ? AND s.dernier_jour >= ? AND s.serie > 0$ou",
            array_merge([$moi_id, $depuis], $args))->fetch();
        if ($ma && (int) $ma['serie'] > 0) {
            $rang_moi = 1 + (int) req(
                "SELECT COUNT(*) FROM (
                    SELECT s.joueur_id, MAX(s.serie) AS se, SUM(s.parties) AS pa
                      FROM series s
                     WHERE s.dernier_jour >= ? AND s.serie > 0$ou
                     GROUP BY s.joueur_id
                 ) t
                  WHERE t.se > ? OR (t.se = ? AND t.pa > ?)",
                array_merge([$depuis], $args, [$ma['serie'], $ma['serie'], $ma['parties']])
            )->fetchColumn();
        }
    }
    $cle_score = 'serie';
    $unite = 'jour';
    $cle_appoint = 'parties';
    $unite_appoint = 'avis';
} else {
    [$ou, $args] = perimetre_sql($univers, $mode, 's');

    $lignes = req(
        "SELECT $colonnes,
                SUM(s.parties) AS parties, SUM(s.fiches_total) AS fiches_total,
                MAX(s.meilleure_serie) AS meilleure_serie
           FROM series s JOIN joueurs j ON j.id = s.joueur_id
          WHERE s.parties > 0$ou
          $groupe
          ORDER BY parties DESC, fiches_total ASC
          LIMIT $limite", $args)->fetchAll();

    $total = (int) req(
        "SELECT COUNT(DISTINCT s.joueur_id) FROM series s WHERE s.parties > 0$ou",
        $args)->fetchColumn();

    $rang_moi = null;
    if ($moi_id) {
        $ma = req(
            "SELECT SUM(s.parties) AS parties, SUM(s.fiches_total) AS fiches_total
               FROM series s WHERE s.joueur_id = ? AND s.parties > 0$ou",
            array_merge([$moi_id], $args))->fetch();
        if ($ma && (int) $ma['parties'] > 0) {
            $rang_moi = 1 + (int) req(
                "SELECT COUNT(*) FROM (
                    SELECT s.joueur_id, SUM(s.parties) AS pa, SUM(s.fiches_total) AS fi
                      FROM series s WHERE s.parties > 0$ou GROUP BY s.joueur_id
                 ) t
                  WHERE t.pa > ? OR (t.pa = ? AND t.fi < ?)",
                array_merge($args, [$ma['parties'], $ma['parties'], $ma['fiches_total']])
            )->fetchColumn();
        }
    }
    $cle_score = 'parties';
    $unite = 'avis';
    $cle_appoint = 'meilleure_serie';
    $unite_appoint = 'jour';
}

$classement = [];
foreach ($lignes as $rang => $l) {
    $classement[] = joueur_public($l) + [
        'rang'    => $rang + 1,
        'score'   => (int) $l[$cle_score],
        'appoint' => $cle_appoint === null ? null : (int) $l[$cle_appoint],
        'moi'     => (int) $l['id'] === $moi_id,
    ];
}

repondre([
    'perimetre' => $perimetre,
    'univers'   => $univers,
    'mode'      => $mode,
    'portee'    => $portee,
    'unite'     => $unite,
    'unite_appoint' => $cle_appoint === null ? null : $unite_appoint,
    'jour'      => $jour,
    'total'     => $total,
    'lignes'    => $classement,
    'mon_rang'  => $rang_moi,
]);
