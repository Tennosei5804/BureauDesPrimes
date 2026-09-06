<?php
/**
 * Bureau des Primes — les règles du jeu, côté serveur.
 *
 * Ce fichier reproduit exactement le tirage d'assets/js/app.js : même
 * empreinte FNV-1a, même clé « jour::mode », même ordre de registre.
 * C'est ce qui permet au serveur de recalculer la cible de n'importe
 * quel jour et donc de vérifier une partie avant de l'écrire en base,
 * au lieu de croire le navigateur sur parole.
 */

declare(strict_types=1);

/** Origine de la numérotation des avis, identique à EPOCH dans app.js. */
const BDP_EPOCH = '2026-01-01';

/** Fuseau qui decide du changement d'avis. */
const BDP_FUSEAU = 'Europe/Paris';

/** Les univers ouverts. Ajouter une entree suffit, avec son registre. */
const BDP_UNIVERS = ['one-piece', 'naruto', 'bleach', 'pokemon', 'inazuma', 'minecraft'];

/**
 * Le registre d'un univers, lu une fois par requête.
 *
 * Il porte aussi la definition des bassins de modes, que le navigateur
 * lit au meme endroit : c'est ce qui garantit que le serveur valide les
 * memes parties que celles que le jeu propose.
 */
function registre(string $univers): array
{
    static $cache = [];
    if (isset($cache[$univers])) {
        return $cache[$univers];
    }
    if (!in_array($univers, BDP_UNIVERS, true)) {
        refuser('univers_inconnu', 'Univers inconnu : ' . $univers);
    }
    $chemin = __DIR__ . '/../assets/data/' . $univers . '.json';
    $brut = @file_get_contents($chemin);
    if ($brut === false) {
        throw new RuntimeException('Registre introuvable : ' . $chemin);
    }
    return $cache[$univers] = json_decode($brut, true, 512, JSON_THROW_ON_ERROR);
}

/** Les identifiants de mode d'un univers. */
function modes(string $univers): array
{
    return array_column(registre($univers)['modes'], 'id');
}

/**
 * FNV-1a 32 bits, le portage de hash() dans assets/js/commun.js (le
 * moteur l'y importe). Math.imul y multiplie
 * modulo 2^32 ; ici le masque fait le même travail. Les clés hachées sont
 * toujours de l'ASCII, donc parcourir des octets revient au même que
 * parcourir des unités UTF-16 en JavaScript.
 */
function empreinte(string $s): int
{
    $h = 2166136261;
    $n = strlen($s);
    for ($i = 0; $i < $n; $i++) {
        $h ^= ord($s[$i]);
        $h = ($h * 16777619) & 0xFFFFFFFF;
    }
    return $h;
}

/** Les personnages éligibles à un mode, dans l'ordre du registre. */
function bassin(string $univers, string $mode): array
{
    $reg = registre($univers);
    $def = null;
    foreach ($reg['modes'] as $m) {
        if ($m['id'] === $mode) { $def = $m; break; }
    }
    if ($def === null) {
        refuser('mode_inconnu', 'Mode de jeu inconnu : ' . $mode);
    }
    return array_values(array_filter($reg['persos'], static function (array $p) use ($def): bool {
        if (empty($def['champ'])) {
            return true;
        }
        $v = $p[$def['champ']] ?? null;
        // Une liste : vide ou non, « sauf » n'a pas de sens dessus.
        // Le pendant de ce test est dans dansBassin(), app.js — les deux
        // doivent trier le registre dans le même ordre, sinon les cibles
        // divergent et le serveur refuse toutes les parties du mode.
        if (is_array($v)) {
            return count($v) > 0;
        }
        return !empty($v) && $v !== ($def['sauf'] ?? null);
    }));
}
/**
 * Le jour de jeu courant, au format AAAA-MM-JJ.
 *
 * L'avis bascule a minuit, heure de Paris. On prend la date calendaire du
 * fuseau, jamais un decompte d'heures : les changements d'heure decalent
 * l'horloge de soixante minutes deux fois par an, et un « toutes les
 * 24 h » deriverait d'autant. assets/js/app.js fait le meme calcul dans le
 * meme fuseau — les deux doivent rester d'accord, sinon le serveur refuse
 * les parties pendant l'heure de decalage.
 */
function jour_jeu(): string
{
    return (new DateTimeImmutable('now', new DateTimeZone(BDP_FUSEAU)))
        ->format('Y-m-d');
}

/** Le personnage recherché pour un mode et un jour donnés. */
function cible(string $univers, string $mode, string $jour): string
{
    $b = bassin($univers, $mode);
    if (!$b) {
        throw new RuntimeException('Bassin vide : ' . $univers . '/' . $mode);
    }
    return $b[empreinte($jour . '::' . $mode) % count($b)]['nom'];
}

/** Le numéro d'avis affiché dans le bandeau, 1 le jour de l'EPOCH. */
function numero_avis(string $jour): int
{
    $debut = new DateTimeImmutable(BDP_EPOCH, new DateTimeZone('UTC'));
    $ce_jour = new DateTimeImmutable($jour, new DateTimeZone('UTC'));
    return (int) $debut->diff($ce_jour)->days + 1;
}

/** Un jour est jouable s'il n'est ni avant l'EPOCH ni dans le futur. */
function jour_valide(string $jour): bool
{
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $jour)) {
        return false;
    }
    $d = DateTimeImmutable::createFromFormat('!Y-m-d', $jour, new DateTimeZone('UTC'));
    if (!$d || $d->format('Y-m-d') !== $jour) {
        return false;
    }
    return $jour >= BDP_EPOCH && $jour <= jour_jeu();
}

/**
 * Vérifie une partie annoncée par le navigateur et rend ce qu'il faut
 * écrire en base. Contrôle le mode, le jour, l'existence de chaque
 * personnage, l'absence de doublon, et surtout que la dernière fiche
 * versée est bien la cible du jour.
 *
 * Limite assumée : le navigateur connaît la réponse, puisqu'il calcule
 * le tirage lui-même. Ces contrôles écartent les envois malformés,
 * rejouées et hors délai, pas un joueur qui forgerait sciemment une
 * partie parfaite. Rendre le classement infalsifiable demanderait de
 * déplacer tout le moteur ici — voir README.md.
 *
 * @param string[] $propositions
 * @return array{cible:string, fiches:int, numero:int}
 */
function valider_partie(string $univers, string $mode, string $jour, array $propositions): array
{
    if (!in_array($mode, modes($univers), true)) {
        refuser('mode_inconnu', 'Mode de jeu inconnu : ' . $mode);
    }
    if (!jour_valide($jour)) {
        refuser('jour_invalide', 'Date d\'avis hors des dates jouables.');
    }
    if (!$propositions) {
        refuser('partie_vide', 'Une partie sans fiche versée ne veut rien dire.');
    }
    if (count($propositions) > 200) {
        refuser('partie_trop_longue', 'Trop de fiches versées pour une seule partie.');
    }

    $noms = [];
    foreach ($propositions as $p) {
        if (!is_string($p)) {
            refuser('proposition_invalide', 'Fiche illisible dans la partie.');
        }
        $noms[] = $p;
    }
    if (count(array_unique($noms)) !== count($noms)) {
        refuser('doublon', 'La même fiche a été versée deux fois.');
    }

    // Chaque nom doit exister dans le REGISTRE, pas dans le bassin du
    // mode : on peut proposer n'importe quel personnage, y compris un qui
    // ne pourrait jamais être la réponse du jour — c'est une fiche versée
    // comme une autre. Seule la dernière doit tomber juste, et le contrôle
    // ci-dessous s'en charge. Le pendant de cette règle est resolve()
    // dans app.js : les deux doivent accepter les mêmes noms.
    $connus = array_column(registre($univers)['persos'], 'nom');
    $inconnus = array_diff($noms, $connus);
    if ($inconnus) {
        refuser('personnage_inconnu',
            'Personnage absent du registre : ' . reset($inconnus));
    }

    $attendu = cible($univers, $mode, $jour);
    if (end($noms) !== $attendu) {
        refuser('partie_non_resolue',
            'La dernière fiche versée n\'identifie pas le personnage recherché ce jour-là.');
    }

    return [
        'cible'  => $attendu,
        'fiches' => count($noms),
        'numero' => numero_avis($jour),
    ];
}
