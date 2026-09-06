/* ==================================================================
   Bureau des Primes — les briques partagées

   Ce que le moteur de jeu (app.js) et le lexique (lexique.js) doivent
   fabriquer de la même façon : l'empreinte, le slug d'un portrait, la
   plaque d'identité. Recopier ces quatre fonctions dans le lexique
   aurait suffi à ce que les deux pages finissent par diverger — une
   teinte ici, un accent là — sur les mêmes personnages.

   Rien ici ne connaît d'univers en particulier : l'univers est toujours
   passé en argument.
   ================================================================== */

/* FNV-1a 32 bits. Sert à deux choses sans rapport : la teinte stable
   d'une plaque, et le tirage du jour dans app.js. Cette seconde
   utilisation a un jumeau en PHP (api/_jeu.php) : les deux doivent
   rendre le même nombre pour la même chaîne, sinon le serveur et le
   navigateur ne cherchent pas le même personnage. Ne pas y toucher
   sans corriger l'autre. */
export function hash(str){
  let h = 2166136261;
  for (let i = 0; i < str.length; i++){ h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

/* Le nom de fichier d'un portrait. Les signes de genre sont transcrits
   avant l'écrasement du reste : sinon « Nidoran♀ » et « Nidoran♂ »
   donnent le même slug, et les deux fiches partagent un seul portrait.
   La même règle est écrite dans outils/telecharger-portraits.py — les
   deux doivent rester d'accord. */
export const slug = n => n.toLowerCase().normalize('NFD')
  .replace(/[̀-ͯ]/g, '')
  .replace(/♀/g, '-f').replace(/♂/g, '-m')
  .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

export function initials(n){
  const w = n.replace(/\(.*?\)/g, '').split(/[\s.'-]+/).filter(x => x.length > 1);
  return ((w[0] || n)[0] + (w.length > 1 ? w[w.length - 1][0] : '')).toUpperCase();
}

export function echapper(s){
  return String(s).replace(/[&<>"']/g, c =>
    ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}

const HUES = [8, 32, 50, 96, 150, 186, 210, 250, 288, 330];

/* Teinte de la plaque : l'univers dit sur quel attribut elle se cale
   (équipage, village…) et fixe les couleurs des grandes maisons ; le
   reste est teinté par empreinte, pour rester stable d'un jour à
   l'autre. */
export const teinteDe = (U, faction) => U.teintes[faction] !== undefined
  ? U.teintes[faction] : HUES[hash(faction || '') % HUES.length];

export const photoSrc = (U, p) =>
  U.photos ? U.photos + slug(p.nom) + '.jpg' : null;

const SIL = '<svg class="sil" viewBox="0 0 40 40" aria-hidden="true">' +
  '<circle cx="20" cy="14.5" r="7.6"></circle>' +
  '<path d="M5.5 40c0-8.6 6.5-13.8 14.5-13.8S34.5 31.4 34.5 40Z"></path></svg>';

/* La plaque d'identité : initiales sur fond teinté, recouvertes par le
   portrait quand il existe. `differe` demande au navigateur de ne
   charger l'image qu'à l'approche de l'écran — sans quoi le lexique
   Pokémon lancerait mille requêtes d'un coup. */
export function plaque(U, p, taille, differe){
  const src = photoSrc(U, p);
  return '<span class="mug ' + (taille || '') + '" style="--mugc:hsl(' +
    teinteDe(U, p[U.teinteSur]) + ' 46% 36%)" aria-hidden="true">' + SIL +
    '<span class="ini">' + initials(p.nom) + '</span>' +
    (src ? '<img alt="" ' + (differe ? 'loading="lazy" ' : '') +
           'src="' + src + '">' : '') + '</span>';
}

/* Une image absente ne doit rien afficher du tout : on retire la balise
   et la plaque aux initiales reste visible dessous. */
export function brancherPhotos(racine){
  (racine || document).querySelectorAll('.mug img, .ico img').forEach(img => {
    img.addEventListener('error', () => img.remove(), { once:true });
  });
}
