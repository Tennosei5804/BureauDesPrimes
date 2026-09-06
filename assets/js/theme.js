/* ==================================================================
   Bureau des Primes — thème clair / sombre

   Trois états, pas deux : « Système » suit le réglage du navigateur,
   « Clair » et « Sombre » le forcent. Sans troisième état, un visiteur
   qui a touché au réglage ne pourrait plus revenir au comportement par
   défaut, et son choix survivrait à un changement de préférence système.

   La feuille de style connaît déjà les trois cas (voir style.css) :
     :root                                    la palette claire
     @media (prefers-color-scheme: dark)      redéfinie, sauf si on force clair
     :root[data-theme="dark"]                 redéfinie, forçage sombre
   Ce module ne fait que poser l'attribut sur <html> et le retenir.

   Le choix est relu par un petit script en tête de page, avant le
   premier rendu : le poser d'ici seulement ferait clignoter la page en
   clair avant de passer au sombre, ce module étant différé.
   ================================================================== */

const CLE = 'bdp.theme';

/* Valeurs stockées telles quelles, sans JSON : le script anti-clignotement
   des pages les lit avec un simple getItem, il doit rester minuscule. */
const CHOIX = [
  { id: 'auto',  label: 'Système', titre: 'Suivre le réglage du système' },
  { id: 'light', label: 'Clair',   titre: 'Forcer le thème clair' },
  { id: 'dark',  label: 'Sombre',  titre: 'Forcer le thème sombre' },
];

/* Les mêmes fonds que --bg dans style.css : la barre du navigateur doit
   s'accorder à la page, y compris quand le thème est forcé. */
const FOND = { light: '#DFD9CA', dark: '#0D141A' };

const sombreSysteme = window.matchMedia
  ? window.matchMedia('(prefers-color-scheme: dark)')
  : null;

function lire(){
  try {
    const v = localStorage.getItem(CLE);
    return v === 'light' || v === 'dark' ? v : 'auto';
  } catch (e) { return 'auto'; }
}

function ecrire(v){
  try {
    if (v === 'auto') localStorage.removeItem(CLE);
    else localStorage.setItem(CLE, v);
  } catch (e) { /* navigation privée : le choix ne survit pas, tant pis */ }
}

/** Le thème effectivement affiché, une fois le système pris en compte. */
function effectif(choix){
  if (choix !== 'auto') return choix;
  return sombreSysteme && sombreSysteme.matches ? 'dark' : 'light';
}

/* Les deux <meta name="theme-color"> des pages portent une media query :
   dès qu'on force un camp, elles ne décrivent plus la réalité. On en
   ajoute une troisième, sans media, que l'on garde à jour — la dernière
   déclaration applicable l'emporte. */
function colorerBarre(theme){
  let m = document.querySelector('meta[name="theme-color"][data-force]');
  if (!m){
    m = document.createElement('meta');
    m.name = 'theme-color';
    m.setAttribute('data-force', '');
    document.head.appendChild(m);
  }
  m.content = FOND[theme];
}

function appliquer(choix){
  const racine = document.documentElement;
  if (choix === 'auto') racine.removeAttribute('data-theme');
  else racine.setAttribute('data-theme', choix);
  colorerBarre(effectif(choix));
  document.dispatchEvent(new CustomEvent('bdp:theme',
    { detail: { choix, theme: effectif(choix) } }));
}

function dessiner(zone, choix){
  zone.innerHTML =
    '<span class="theme-lbl">Thème</span>' +
    CHOIX.map(c =>
      '<button type="button" class="theme-btn" data-v="' + c.id + '"' +
      ' title="' + c.titre + '" aria-pressed="' + (c.id === choix) + '">' +
      c.label + '</button>').join('');
  zone.querySelectorAll('.theme-btn').forEach(b => {
    b.onclick = () => {
      const v = b.dataset.v;
      ecrire(v);
      appliquer(v);
      dessiner(zone, v);
    };
  });
}

const zone = document.getElementById('theme');
const choix = lire();
appliquer(choix);
if (zone){
  zone.hidden = false;
  dessiner(zone, choix);
}

/* En mode « Système », un changement de réglage pendant la visite doit
   suivre : la feuille de style le fait seule, la barre du navigateur non. */
if (sombreSysteme){
  const suivre = () => { if (lire() === 'auto') appliquer('auto'); };
  if (sombreSysteme.addEventListener) sombreSysteme.addEventListener('change', suivre);
  else if (sombreSysteme.addListener) sombreSysteme.addListener(suivre);
}
