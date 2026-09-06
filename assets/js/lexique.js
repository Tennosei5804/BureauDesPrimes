/* ==================================================================
   Bureau des Primes — le lexique

   La liste complète d'un registre : tout ce que le jeu peut tirer, avec
   son portrait et sa fiche. Une seule page pour les six univers, choisi
   par ?jeu= dans l'adresse — le moteur ne connaît aucun registre en
   particulier, le lexique non plus.

   Les plaques, le slug et l'empreinte viennent de commun.js, les mêmes
   que le jeu : un personnage a donc ici exactement la tête et la teinte
   qu'il a sur le plateau.
   ================================================================== */

import { UNIVERS } from './univers.js';
import { plaque, brancherPhotos, echapper } from './commun.js';
import { habillerSelects, rafraichirMenus } from './menu.js';

const el = id => document.getElementById(id);

/* ---------- quel registre ---------- */
const demande = new URLSearchParams(location.search).get('jeu');
const CLE = UNIVERS[demande] ? demande : Object.keys(UNIVERS)[0];
const U = UNIVERS[CLE];
document.body.dataset.univers = CLE;

/* ---------- l'habillage, comme sur les pages de jeu ---------- */
function habiller(){
  const mets = (id, html) => { const n = el(id); if (n) n.innerHTML = html; };
  mets('mh-top', U.sousTitre);
  mets('wordmark', U.titre.replace(/\s(\S+)$/, ' <em>$1</em>'));
  mets('sceau', U.sceau);
  mets('tagline', 'La liste des ' + U.mots.pluriel +
       ' que ce registre contient. Le jeu tire chaque jour dedans.');
  mets('foot-fan', 'Projet de fan, sans lien avec les ayants droit de ' + U.oeuvre + '.');
  const w = el('foot-wiki');
  if (w){ w.textContent = U.wiki.nom; w.href = U.wiki.url; }
  document.title = 'Lexique ' + U.oeuvre + ' — ' + U.titre;
  const jouer = el('vers-jeu');
  if (jouer) jouer.href = CLE + '.html';
}

/* Les autres registres, pour passer de l'un à l'autre sans repasser par
   l'accueil. Même barre que les modes de jeu : c'est le même geste. */
function barreRegistres(){
  const registres = Object.values(UNIVERS);
  /* Deux commandes pour un meme choix, comme la barre de modes du jeu :
     les onglets au large, le menu en etroit. Six registres tiennent sur
     une ligne sur un ecran d'ordinateur et en prennent trois sur un
     telephone. La feuille de style montre l'un ou l'autre — les regles
     visent .modebar, que les deux barres portent. */
  el('registres').innerHTML =
    '<div class="onglets">' +
    registres.map(u =>
      '<a class="tab" href="?jeu=' + u.cle + '"' +
      (u.cle === CLE ? ' aria-current="page"' : '') + '>' +
      echapper(u.oeuvre) + '</a>').join('') +
    '</div>' +
    '<select class="barre-menu" id="registre-menu" aria-label="Registre">' +
    registres.map(u => '<option value="' + u.cle + '"' +
      (u.cle === CLE ? ' selected' : '') + '>' +
      echapper(u.oeuvre) + '</option>').join('') +
    '</select>';
  /* Changer de registre change de page : c'est exactement ce que font
     les onglets, qui sont des liens. */
  el('registre-menu').onchange = e => {
    location.href = '?jeu=' + e.target.value;
  };
}

/* ---------- le registre ---------- */
let FICHES = [];

async function charger(){
  const rep = await fetch(U.registre);
  if (!rep.ok) throw new Error('HTTP ' + rep.status + ' sur ' + U.registre);
  const d = await rep.json();
  FICHES = d.persos;
  /* Les échelles ordonnées servent à trier : « Génération II » se range
     après « Génération I », pas par ordre alphabétique. */
  for (const [nom, valeurs] of Object.entries(d)){
    if (Array.isArray(valeurs) && nom !== 'persos'){
      ECHELLES[nom] = Object.fromEntries(valeurs.map((v, i) => [v, i]));
    }
  }
}
const ECHELLES = {};

/* ---------- outils de recherche ---------- */
const sansAccent = s => String(s).toLowerCase().normalize('NFD')
  .replace(/[̀-ͯ]/g, '');

/** Tout le texte d'une fiche, pour la recherche libre. */
function paille(p){
  if (p.__paille) return p.__paille;
  const bouts = [p.nom];
  for (const [, v] of U.affiche.dossier(p)) bouts.push(v);
  if (p.epithete) bouts.push(p.epithete);
  return (p.__paille = sansAccent(bouts.join(' ')));
}

/* Les attributs sur lesquels on peut filtrer : ceux qui ont un nombre
   fini de valeurs. Un nombre (taille, prime) n'en fait pas partie — on
   trie dessus, on ne filtre pas. */
const FILTRABLES = U.attrs.filter(a => a.type !== 'nombre');
const TRIABLES = U.attrs.filter(a => a.type === 'nombre' || a.type === 'ordinal');

function valeursDe(attr){
  const vues = new Set();
  for (const p of FICHES){
    const v = p[attr.cle];
    if (Array.isArray(v)) v.forEach(x => x && vues.add(x));
    else if (v !== null && v !== undefined && v !== '') vues.add(v);
  }
  const liste = [...vues];
  const rang = ECHELLES[attr.echelle];
  if (rang) liste.sort((a, b) => (rang[a] ?? 99) - (rang[b] ?? 99));
  else liste.sort((a, b) => String(a).localeCompare(String(b), 'fr'));
  return liste;
}

function remplirOutils(){
  el('f-attr').innerHTML = '<option value="">Filtrer par…</option>' +
    FILTRABLES.map(a => '<option value="' + a.cle + '">' +
      echapper(a.label) + '</option>').join('');
  el('tri').innerHTML = '<option value="nom">Ordre alphabétique</option>' +
    TRIABLES.map(a => '<option value="' + a.cle + '">' +
      echapper(a.label) + '</option>').join('');
}

function remplirValeurs(){
  const attr = FILTRABLES.find(a => a.cle === el('f-attr').value);
  const zone = el('f-valeur');
  if (!attr){ zone.hidden = true; zone.innerHTML = ''; return; }
  zone.hidden = false;
  zone.innerHTML = '<option value="">Toutes les valeurs</option>' +
    valeursDe(attr).map(v => '<option value="' + echapper(v) + '">' +
      echapper(v) + '</option>').join('');
}

/* ---------- la sélection courante ---------- */
function selection(){
  const q = sansAccent(el('q').value.trim());
  const cle = el('f-attr').value;
  const val = el('f-valeur').hidden ? '' : el('f-valeur').value;
  let liste = FICHES;

  if (q) liste = liste.filter(p => paille(p).includes(q));
  if (cle && val){
    liste = liste.filter(p => {
      const v = p[cle];
      return Array.isArray(v) ? v.includes(val) : v === val;
    });
  }

  const tri = el('tri').value;
  liste = liste.slice();
  if (tri === 'nom'){
    liste.sort((a, b) => a.nom.localeCompare(b.nom, 'fr'));
  } else {
    const attr = U.attrs.find(a => a.cle === tri);
    const rang = ECHELLES[attr.echelle];
    const poids = p => {
      const v = p[tri];
      if (rang) return rang[v] ?? -1;
      return v === null || v === undefined ? -Infinity : v;
    };
    liste.sort((a, b) => poids(a) - poids(b) || a.nom.localeCompare(b.nom, 'fr'));
  }
  return liste;
}

/* ---------- rendu ---------- */
/* Le rendu se fait par tranches : mille fiches Pokémon d'un coup, ce
   sont dix mille nœuds et autant d'images demandées avant que la page
   ne réponde. On en pose cent, puis cent de plus quand la sentinelle
   arrive à l'écran. */
const TRANCHE = 100;
let courante = [];
let posees = 0;

function carte(p){
  const lignes = U.affiche.dossier(p)
    .map(([k, v]) => '<div class="lx-l"><span class="k">' + echapper(k) +
      '</span><span class="v">' + echapper(v) + '</span></div>').join('');
  return '<article class="lx-fiche">' +
    '<header>' + plaque(U, p, 'md', true) + '<span class="lx-id">' +
      '<span class="lx-nom">' + echapper(p.nom) + '</span>' +
      (p.epithete ? '<span class="lx-ep">« ' + echapper(p.epithete) + ' »</span>' : '') +
    '</span></header><div class="lx-corps">' + lignes + '</div></article>';
}

function poserTranche(){
  if (posees >= courante.length) return;
  const bout = courante.slice(posees, posees + TRANCHE);
  el('grille').insertAdjacentHTML('beforeend', bout.map(carte).join(''));
  posees += bout.length;
  brancherPhotos(el('grille'));
  el('sentinelle').hidden = posees >= courante.length;
}

function rendre(){
  courante = selection();
  posees = 0;
  el('grille').innerHTML = '';
  const n = courante.length;
  /* Le decompte dit « personnages » et non « pirates » ou « ninjas » :
     c'est un chiffre de dossier, pas une phrase de l'univers — et la
     meme barre sert aux six registres. Minecraft garde son mot : ses
     fiches sont des blocs et des objets, « personnages » y serait faux. */
  const mot = U.mots.fiche
    ? (n === 1 ? U.mots.fiche : U.mots.fiches)
    : (n === 1 ? 'personnage' : 'personnages');
  el('compte-lex').textContent = n
    ? n + ' ' + mot + (n < FICHES.length ? ' sur ' + FICHES.length : '')
    : 'Aucune fiche ne correspond';
  poserTranche();
}

/* ---------- branchements ---------- */
function brancher(){
  el('q').addEventListener('input', rendre);
  el('tri').addEventListener('change', rendre);
  el('f-attr').addEventListener('change', () => { remplirValeurs(); rendre(); });
  el('f-valeur').addEventListener('change', rendre);
  el('vider').addEventListener('click', () => {
    el('q').value = ''; el('f-attr').value = ''; el('tri').value = 'nom';
    remplirValeurs(); rendre();
    /* Poser une valeur par programme n'emet aucun evenement : sans ce
       rappel, les menus garderaient l'intitule de l'ancien choix. */
    rafraichirMenus();
  });
  new IntersectionObserver(entrees => {
    if (entrees.some(e => e.isIntersecting)) poserTranche();
  }, { rootMargin: '600px' }).observe(el('sentinelle'));
}

/* ---------- démarrage ---------- */
habiller();
barreRegistres();
try {
  await charger();
} catch (err){
  console.error('[Bureau des Primes] registre illisible.', err);
  el('grille').innerHTML = '<div class="empty"><h3>Dossier inaccessible</h3>' +
    "<p>Le registre n'a pas pu être ouvert. Rechargez la page.</p></div>";
  throw err;
}
remplirOutils();
remplirValeurs();
habillerSelects();
brancher();
rendre();
el('foot-count').textContent = FICHES.length;
