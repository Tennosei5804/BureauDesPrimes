<?php
/**
 * Bureau des Primes — mise en place et entretien de la base.
 *
 *   php outils/migrer.php              applique api/schema.sql
 *   php outils/migrer.php --recalculer refait tous les compteurs `series`
 *   php outils/migrer.php --etat       montre l'état des tables
 *
 * Volontairement réservé à la ligne de commande : exposé sur le web, il
 * laisserait n'importe qui toucher au schéma. Sans accès SSH chez votre
 * hébergeur, collez api/schema.sql dans phpMyAdmin — c'est le même SQL.
 */

declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit("Cet outil ne se lance qu'en ligne de commande.\n");
}

require __DIR__ . '/../api/_amorce.php';
require __DIR__ . '/../api/_jeu.php';
require __DIR__ . '/../api/_stats.php';

$action = $argv[1] ?? '--installer';

function ligne(string $s = ''): void
{
    echo $s . "\n";
}

try {
    bd();
} catch (PDOException $e) {
    ligne('Connexion à la base impossible : ' . $e->getMessage());
    ligne('Vérifiez la section « bd » de api/config.php.');
    exit(1);
}

switch ($action) {
    case '--installer':
        $sql = file_get_contents(__DIR__ . '/../api/schema.sql');
        if ($sql === false) {
            ligne('api/schema.sql introuvable.');
            exit(1);
        }
        // Les commentaires partent d'abord : chaque ordre du schéma est
        // précédé des siens, et les garder ferait passer le bloc entier
        // pour un commentaire. Découpage ensuite sur « ; » — le schéma
        // ne contient ni procédure stockée ni point-virgule en chaîne.
        $sql = preg_replace('/^\s*--.*$/m', '', $sql);
        $ordres = array_filter(array_map('trim', explode(';', $sql)));
        $faits = 0;
        foreach ($ordres as $ordre) {
            bd()->exec($ordre);
            $faits++;
        }
        ligne('Schéma appliqué : ' . $faits . ' ordre(s) exécuté(s).');
        // fallthrough volontaire vers l'état
    case '--etat':
        ligne();
        foreach (['joueurs', 'parties', 'propositions', 'series'] as $t) {
            try {
                $n = req("SELECT COUNT(*) FROM `$t`")->fetchColumn();
                ligne(sprintf('  %-14s %6d ligne(s)', $t, $n));
            } catch (PDOException $e) {
                ligne(sprintf('  %-14s absente', $t));
            }
        }
        ligne();
        ligne('  avis du jour  n° ' . numero_avis(jour_jeu()) . '  (' . jour_jeu() . ' Paris)');
        foreach (BDP_UNIVERS as $u) {
            ligne('    ' . $u);
            foreach (modes($u) as $m) {
                ligne(sprintf('      %-12s %s', $m, cible($u, $m, jour_jeu())));
            }
        }
        break;

    case '--recalculer':
        $paires = req('SELECT DISTINCT joueur_id, univers, mode FROM parties')->fetchAll();
        foreach ($paires as $p) {
            recalculer_serie((int) $p['joueur_id'], $p['univers'], $p['mode']);
        }
        ligne('Compteurs refaits pour ' . count($paires) . ' couple(s) joueur/mode.');
        break;

    default:
        ligne('Action inconnue : ' . $action);
        ligne('Attendu : --installer, --recalculer ou --etat');
        exit(1);
}
