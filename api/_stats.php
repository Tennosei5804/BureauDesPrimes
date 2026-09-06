<?php
/**
 * Bureau des Primes — écriture des parties et tenue des compteurs.
 *
 * `series` est un cache de ce que contient déjà `parties`. Il est
 * recalculé intégralement à chaque écriture plutôt qu'incrémenté : les
 * parties peuvent arriver dans le désordre (reprise d'une progression
 * locale à la première connexion), et une série calculée par
 * incréments successifs finirait fausse.
 */

declare(strict_types=1);

/**
 * Écrit une partie validée. Rend [nouveau, partie] ; nouveau vaut false
 * si ce joueur avait déjà résolu cet avis — le premier résultat reste.
 *
 * @param string[] $noms
 * @param array{cible:string, fiches:int, numero:int} $valide
 */
function enregistrer_partie(int $joueur_id, string $univers, string $mode,
                            string $jour, array $noms, array $valide): array
{
    $pdo = bd();
    $pdo->beginTransaction();
    try {
        // INSERT IGNORE plutôt qu'un SELECT préalable : la contrainte
        // unique (joueur, mode, jour) tranche même si deux onglets
        // envoient la même partie au même instant.
        $st = $pdo->prepare(
            'INSERT IGNORE INTO parties
                (joueur_id, univers, mode, jour, numero_avis, cible, fiches, resolu_le)
             VALUES (?, ?, ?, ?, ?, ?, ?, UTC_TIMESTAMP())');
        $st->execute([$joueur_id, $univers, $mode, $jour, $valide['numero'],
                      $valide['cible'], $valide['fiches']]);

        $nouveau = $st->rowCount() > 0;
        if ($nouveau) {
            $partie_id = (int) $pdo->lastInsertId();
            $ins = $pdo->prepare(
                'INSERT INTO propositions (partie_id, rang, personnage) VALUES (?, ?, ?)');
            foreach ($noms as $rang => $nom) {
                $ins->execute([$partie_id, $rang + 1, $nom]);
            }
            recalculer_serie($joueur_id, $univers, $mode);
        }

        $partie = req(
            'SELECT mode, jour, numero_avis, cible, fiches, resolu_le
               FROM parties WHERE joueur_id = ? AND univers = ? AND mode = ? AND jour = ?',
            [$joueur_id, $univers, $mode, $jour])->fetch();

        $pdo->commit();
    } catch (Throwable $e) {
        $pdo->rollBack();
        throw $e;
    }

    return ['nouveau' => $nouveau, 'partie' => $partie ?: null];
}

/**
 * Reconstruit la ligne `series` d'un joueur pour un mode, à partir de
 * ses parties. La série en cours est la suite de jours consécutifs qui
 * se termine à sa dernière partie ; la meilleure est la plus longue
 * jamais réalisée.
 */
function recalculer_serie(int $joueur_id, string $univers, string $mode): void
{
    $lignes = req('SELECT jour, fiches FROM parties
                    WHERE joueur_id = ? AND univers = ? AND mode = ?
                    ORDER BY jour ASC', [$joueur_id, $univers, $mode])->fetchAll();

    $parties = count($lignes);
    $fiches_total = array_sum(array_column($lignes, 'fiches'));
    $serie = 0;
    $meilleure = 0;
    $precedent = null;

    foreach ($lignes as $l) {
        $jour = $l['jour'];
        $serie = ($precedent !== null && $jour === lendemain($precedent)) ? $serie + 1 : 1;
        $meilleure = max($meilleure, $serie);
        $precedent = $jour;
    }

    req('INSERT INTO series
            (joueur_id, univers, mode, parties, fiches_total, serie,
             meilleure_serie, dernier_jour)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
         ON DUPLICATE KEY UPDATE
            parties = VALUES(parties), fiches_total = VALUES(fiches_total),
            serie = VALUES(serie), meilleure_serie = VALUES(meilleure_serie),
            dernier_jour = VALUES(dernier_jour)',
        [$joueur_id, $univers, $mode, $parties, $fiches_total, $serie,
         $meilleure, $precedent]);
}

function lendemain(string $jour): string
{
    return (new DateTimeImmutable($jour, new DateTimeZone('UTC')))
        ->modify('+1 day')->format('Y-m-d');
}

function veille(string $jour): string
{
    return (new DateTimeImmutable($jour, new DateTimeZone('UTC')))
        ->modify('-1 day')->format('Y-m-d');
}

/**
 * Une série n'est « en cours » que si le joueur a résolu un avis hier ou
 * aujourd'hui. Passé ce délai elle est rompue, même si la colonne garde
 * sa dernière valeur — ce qui évite de recalculer toute la table au
 * changement de jour.
 */
function serie_en_cours(?string $dernier_jour, int $serie): int
{
    if ($dernier_jour === null) {
        return 0;
    }
    $aujourdhui = jour_jeu();
    return ($dernier_jour === $aujourdhui || $dernier_jour === veille($aujourdhui))
        ? $serie : 0;
}

/** Les compteurs d'un joueur, un bloc par mode, plus un total. */
function stats_joueur(int $joueur_id, string $univers): array
{
    $lignes = req('SELECT mode, parties, fiches_total, serie, meilleure_serie, dernier_jour
                     FROM series WHERE joueur_id = ? AND univers = ?',
                  [$joueur_id, $univers])->fetchAll();
    $par_mode = [];
    foreach ($lignes as $l) {
        $par_mode[$l['mode']] = [
            'parties'         => (int) $l['parties'],
            'serie'           => serie_en_cours($l['dernier_jour'], (int) $l['serie']),
            'meilleure_serie' => (int) $l['meilleure_serie'],
            'fiches_moyenne'  => $l['parties']
                ? round($l['fiches_total'] / $l['parties'], 1) : null,
            'dernier_jour'    => $l['dernier_jour'],
        ];
    }
    foreach (modes($univers) as $m) {
        $par_mode[$m] ??= ['parties' => 0, 'serie' => 0, 'meilleure_serie' => 0,
                           'fiches_moyenne' => null, 'dernier_jour' => null];
    }

    $total_parties = array_sum(array_column($lignes, 'parties'));
    $total_fiches  = array_sum(array_column($lignes, 'fiches_total'));

    return [
        'modes' => $par_mode,
        'total' => [
            'parties'        => (int) $total_parties,
            'fiches_moyenne' => $total_parties ? round($total_fiches / $total_parties, 1) : null,
        ],
    ];
}

/**
 * Les avis déjà résolus aujourd'hui, pour que le front n'insiste pas.
 * Rendu en objet et non en tableau : vide, un tableau PHP se sérialise
 * en [] et le front recevrait un type différent selon le jour.
 */
function parties_du_jour(int $joueur_id, string $univers): stdClass
{
    $lignes = req('SELECT mode, fiches FROM parties
                    WHERE joueur_id = ? AND univers = ? AND jour = ?',
                  [$joueur_id, $univers, jour_jeu()])->fetchAll();
    $out = [];
    foreach ($lignes as $l) {
        $out[$l['mode']] = (int) $l['fiches'];
    }
    return (object) $out;
}
