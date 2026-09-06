/* ==================================================================
   Bureau des Primes — comptes, classements, historique.

   Module séparé du moteur de jeu, et facultatif : si l'API ne répond
   pas (site déposé sur un hébergeur statique, PHP en panne), tout ce
   qui suit s'efface et le jeu continue en local comme avant. Rien ici
   ne doit jamais empêcher de jouer.

   Le lien avec assets/js/app.js tient en trois points, décrits dans le
   README : les événements « bdp:mode » et « bdp:victoire », et l'objet
   window.BDP.
   ================================================================== */

import { UNIVERS } from './univers.js';

const API = 'api/';
/* Chaque registre a ses propres séries et classements : toutes les
   requêtes portent l'univers de la page. */
const UNIVERS_PAGE = document.body.dataset.univers || 'one-piece';
const q = (chemin, params = '') => chemin + '?univers=' +
  encodeURIComponent(UNIVERS_PAGE) + (params ? '&' + params : '');
/* Les intitulés de mode viennent de l'univers : figés ici, ils
   afficheraient « Fruit du Démon » sur le registre Naruto. */
const MODES_LABEL = Object.fromEntries(
  (UNIVERS[UNIVERS_PAGE]?.modes || []).map(m => [m.id, m.label]));
const PORTEES = [
  ['jour', 'Avis du jour'],
  ['serie', 'Séries en cours'],
  ['parties', 'Assiduité'],
];
/* Le lobby n'a pas d'univers déclaré : c'est ce qui distingue l'accueil
   d'une page de jeu, et non une variable de plus à tenir d'accord. */
const SUR_LOBBY = !document.body.dataset.univers;
/* Deux axes : le PÉRIMÈTRE dit sur quoi on se compare, la PORTÉE ce
   qu'on compare. Sur une page de jeu on part du mode affiché, qui est
   le duel le plus serré ; au lobby il n'y a pas de mode, donc on part
   du classement global et chaque registre est accessible d'un onglet. */
const PERIMETRES = SUR_LOBBY
  ? [['global', 'Tous registres']].concat(
      Object.entries(UNIVERS).map(([cle, u]) => ['jeu:' + cle, u.titre]))
  : [['mode', 'Ce mode'], ['jeu', 'Tout le registre'], ['global', 'Tous registres']];

let etat = null;          // dernière réponse de moi.php
let mode = 'classique';   // mode affiché par le jeu
let portee = 'jour';
let perimetre = PERIMETRES[0][0];
let apiDispo = true;

const MOTS = ['zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six',
              'sept', 'huit', 'neuf', 'dix'];
const enLettres = n => MOTS[n] || String(n);

const el = id => document.getElementById(id);
const dire = m => (window.BDP && window.BDP.toast ? window.BDP.toast(m) : null);

/* ---------- appels ---------- */
async function api(chemin, options) {
  const rep = await fetch(API + chemin, Object.assign({
    headers: { 'Accept': 'application/json' },
    credentials: 'same-origin',
  }, options));
  const type = rep.headers.get('content-type') || '';
  if (!type.includes('application/json')) {
    // Un hébergeur statique renvoie la page 404 en HTML : ce n'est pas
    // une panne, c'est un site sans backend.
    throw Object.assign(new Error('api_absente'), { absente: true });
  }
  const corps = await rep.json();
  if (!rep.ok) {
    throw Object.assign(new Error(corps.erreur || 'erreur'), { corps, http: rep.status });
  }
  return corps;
}

function poster(chemin, corps) {
  return api(chemin, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(Object.assign({ univers: UNIVERS_PAGE }, corps)),
  });
}

/* ---------- barre de compte ---------- */
function rendreCompte() {
  const zone = el('compte');
  if (!zone) return;

  if (!etat || (!etat.connecte && !etat.discord)) {
    // Pas d'application Discord déclarée : inutile de montrer un bouton
    // qui ne mènerait qu'à une erreur.
    zone.hidden = true;
    return;
  }
  zone.hidden = false;

  if (!etat.connecte) {
    zone.innerHTML =
      // On dit au serveur d'où l'on part : sans cela, le retour de Discord
      // déposait le joueur sur le lobby, même s'il jouait déjà.
      '<a class="discord" href="' + API + 'connexion.php?retour=' +
        encodeURIComponent(location.pathname) + '">' + logoDiscord() +
      '<span>Se connecter avec Discord</span></a>' +
      '<span class="compte-note">Pour garder vos séries et entrer au classement.</span>';
    return;
  }

  const j = etat.joueur;
  const faits = Object.keys(etat.aujourdhui || {});
  zone.innerHTML =
    '<div class="moi">' +
      '<img class="tete" src="' + j.avatar + '" alt="" width="28" height="28">' +
      '<span class="nom">' + echapper(j.pseudo) + '</span>' +
      (faits.length
        ? '<span class="compte-note">' + faits.length + ' avis résolu' +
          (faits.length > 1 ? 's' : '') + " aujourd'hui</span>"
        : '<span class="compte-note">Aucun avis résolu aujourd\'hui</span>') +
    '</div>' +
    '<form method="post" action="' + API + 'deconnexion.php" class="sortir">' +
      '<button type="submit" class="lien">Déconnexion</button></form>';

  // Le formulaire part en POST pour ne pas être déclenché par un
  // préchargement de lien ; deconnexion.php renvoie ensuite sur le site.
  zone.querySelector('.sortir').addEventListener('submit', async e => {
    e.preventDefault();
    try { await poster('deconnexion.php', {}); } catch (err) { /* sans effet */ }
    etat = await api(q('moi.php'));
    rendreTout();
    dire('Déconnecté');
  });
}

function logoDiscord() {
  return '<svg viewBox="0 0 24 18" width="20" height="15" aria-hidden="true">' +
    '<path fill="currentColor" d="M20.3 1.6A19.8 19.8 0 0 0 15.4.1a14 14 0 0 0-.6 1.3 18.3 18.3 0 0 0-5.5 0A13.9 13.9 0 0 0 8.6.1a19.7 19.7 0 0 0-4.9 1.5C.6 6.3-.3 10.8.2 15.3a19.9 19.9 0 0 0 6 3 14.6 14.6 0 0 0 1.3-2.1 13 13 0 0 1-2-1c.2-.1.3-.3.5-.4a14.2 14.2 0 0 0 12.1 0l.4.4a13 13 0 0 1-2 1 14.4 14.4 0 0 0 1.3 2.1 19.8 19.8 0 0 0 6-3c.6-5.2-.8-9.7-3.5-13.7ZM8.0 12.6c-1.2 0-2.1-1.1-2.1-2.4S6.8 7.8 8 7.8s2.2 1.1 2.1 2.4-.9 2.4-2.1 2.4Zm8 0c-1.2 0-2.1-1.1-2.1-2.4s.9-2.4 2.1-2.4 2.2 1.1 2.1 2.4-.9 2.4-2.1 2.4Z"/></svg>';
}

/* ---------- classement ---------- */
/* « jeu:naruto » porte l'univers dans l'identifiant : le lobby propose un
   onglet par registre sans avoir à tenir une seconde variable. */
function requeteClassement() {
  const [p, u] = perimetre.split(':');
  let params = 'perimetre=' + p + '&portee=' + encodeURIComponent(portee);
  if (p !== 'global') {
    params += '&univers=' + encodeURIComponent(u || UNIVERS_PAGE);
  }
  if (p === 'mode') params += '&mode=' + encodeURIComponent(mode);
  return 'classement.php?' + params;
}

function intitulePerimetre() {
  const [p, u] = perimetre.split(':');
  // Compte les registres plutot que de l'ecrire : le titre disait encore
  // « quatre » quand le cinquieme est arrive.
  if (p === 'global') return 'Les ' + enLettres(Object.keys(UNIVERS).length) + ' registres';
  const cle = u || UNIVERS_PAGE;
  const titre = UNIVERS[cle] ? UNIVERS[cle].titre : cle;
  return p === 'mode' ? 'Mode ' + (MODES_LABEL[mode] || mode) : titre;
}

async function rendreClassement() {
  const zone = el('classement');
  if (!zone || !apiDispo) return;
  if (enBeta()) return void dormir('classement');
  // Le classement se consulte sans compte : il s'affiche dès que l'API
  // répond, connecté ou non.
  zone.hidden = false;

  const rang = (cls, liste, actif, attr) => '<div class="cl-onglets ' + cls + '">' +
    liste.map(([id, label]) =>
      '<button class="tab" data-' + attr + '="' + id + '" aria-selected="' +
      (id === actif) + '">' + echapper(label) + '</button>').join('') + '</div>';

  zone.innerHTML =
    '<div class="cl-tete"><h3>Registre du bureau</h3>' +
    '<span class="cl-mode">' + echapper(intitulePerimetre()) + '</span></div>' +
    rang('cl-perim', PERIMETRES, perimetre, 'perim') +
    rang('', PORTEES, portee, 'p') +
    '<div class="cl-corps"><p class="cl-vide">Consultation du registre&hellip;</p></div>';

  zone.querySelectorAll('.cl-perim .tab').forEach(b => {
    b.onclick = () => { perimetre = b.dataset.perim; rendreClassement(); };
  });
  zone.querySelectorAll('.cl-onglets:not(.cl-perim) .tab').forEach(b => {
    b.onclick = () => { portee = b.dataset.p; rendreClassement(); };
  });

  let data;
  try {
    data = await api(requeteClassement());
  } catch (err) {
    zone.querySelector('.cl-corps').innerHTML =
      '<p class="cl-vide">Registre momentanément inaccessible.</p>';
    return;
  }

  const corps = zone.querySelector('.cl-corps');
  if (!data.lignes.length) {
    corps.innerHTML = '<p class="cl-vide">' + (portee === 'jour'
      ? "Personne n'a encore résolu d'avis aujourd'hui ici."
      : 'Aucun joueur classé pour le moment.') + '</p>';
    return;
  }

  // Les unités viennent du serveur : lui seul sait ce qu'il a trié, et
  // les recalculer ici les ferait diverger au premier périmètre ajouté.
  // « avis » est invariable : un nom déjà terminé par s, x ou z ne prend
  // pas la marque du pluriel.
  const compte = (n, u) => n + ' ' + u + (n > 1 && !/[sxz]$/.test(u) ? 's' : '');
  corps.innerHTML =
    '<ol class="cl-liste">' + data.lignes.map(l =>
      '<li' + (l.moi ? ' class="moi"' : '') + '>' +
        '<span class="rang">' + String(l.rang).padStart(2, '0') + '</span>' +
        '<img class="tete" src="' + l.avatar + '" alt="" width="24" height="24">' +
        '<span class="nom">' + echapper(l.pseudo) + '</span>' +
        '<span class="score">' + compte(l.score, data.unite) +
          (l.appoint ? '<i>' + compte(l.appoint, data.unite_appoint) + '</i>' : '') +
        '</span>' +
      '</li>').join('') + '</ol>' +
    '<p class="cl-pied">' + data.total + ' joueur' + (data.total > 1 ? 's' : '') +
      (data.mon_rang ? ' &middot; vous êtes ' + data.mon_rang + '<sup>e</sup>' : '') + '</p>';
}

/* ---------- historique ---------- */
async function rendreHistorique() {
  const zone = el('historique');
  if (!zone) return;
  if (enBeta()) return void dormir('historique');
  if (!etat || !etat.connecte) { zone.hidden = true; return; }
  zone.hidden = false;

  if (zone.dataset.charge === '1') return;

  let data;
  try {
    data = await api(q('historique.php', 'limite=25'));
  } catch (err) {
    return;
  }
  zone.dataset.charge = '1';

  const corps = zone.querySelector('.hi-corps');
  if (!data.parties.length) {
    corps.innerHTML = '<p class="cl-vide">Aucun avis classé pour l\'instant.</p>';
    return;
  }
  corps.innerHTML = data.parties.map(p =>
    '<div class="hi-ligne">' +
      '<span class="hi-avis">n<sup>o</sup>&nbsp;' + p.numero + '</span>' +
      '<span class="hi-mode">' + (MODES_LABEL[p.mode] || p.mode) + '</span>' +
      '<span class="hi-cible">' + echapper(p.cible) + '</span>' +
      '<span class="hi-fiches">' + p.fiches + ' fiche' + (p.fiches > 1 ? 's' : '') + '</span>' +
      '<span class="hi-suite">' + p.propositions.map(echapper).join(' &rsaquo; ') + '</span>' +
    '</div>').join('');
}

/* ---------- synchronisation ---------- */
/** Une victoire vient d'être obtenue : on la verse au dossier du joueur. */
async function verser(detail) {
  if (!etat || !etat.connecte || detail.entrainement) return;
  try {
    const rep = await poster('partie.php', {
      mode: detail.mode, jour: detail.jour, propositions: detail.propositions,
    });
    etat.stats = rep.stats;
    etat.aujourdhui[detail.mode] = detail.propositions.length;
    if (rep.nouveau) dire('Avis versé à votre dossier');
    rendreCompte();
    rendreClassement();
    // L'historique est mis en cache après son premier chargement :
    // il faut le rouvrir pour que la partie du jour y apparaisse.
    const hi = el('historique');
    if (hi) hi.dataset.charge = '';
    rendreHistorique();
  } catch (err) {
    // Le jeu vient d'être gagné : ce n'est pas le moment d'afficher une
    // erreur technique. La partie reste dans le localStorage et sera
    // reprise à la prochaine connexion.
    console.warn('[Bureau des Primes] partie non versée :', err.message);
  }
}

/** Première connexion : on propose au serveur ce qui traînait en local. */
async function reprendreLocal() {
  if (!etat || !etat.connecte || !window.BDP) return;
  const marque = 'bdp.v1.' + UNIVERS_PAGE + '.reprise.' + etat.joueur.id;
  try { if (localStorage.getItem(marque)) return; } catch (e) { return; }

  const parties = window.BDP.partiesLocales();
  if (!parties.length) {
    try { localStorage.setItem(marque, '1'); } catch (e) {}
    return;
  }
  try {
    const rep = await poster('importer.php', { parties });
    etat.stats = rep.stats;
    localStorage.setItem(marque, '1');
    if (rep.reprises) {
      const n = rep.reprises;
      dire(n + (n > 1 ? ' parties reprises' : ' partie reprise') + ' de cet appareil');
    }
    rendreCompte();
    rendreClassement();
  } catch (err) {
    console.warn('[Bureau des Primes] reprise locale impossible :', err.message);
  }
}

/* ---------- retour de Discord ---------- */
function messageConnexion() {
  const p = new URLSearchParams(location.search);
  const c = p.get('connexion');
  if (!c) return;
  const raisons = {
    etat: 'la demande ne correspondait pas',
    expiree: 'la demande a expiré',
    code_absent: 'Discord n\'a pas renvoyé de code',
    discord: 'Discord n\'a pas répondu',
  };
  if (c === 'ok') dire('Connecté');
  else if (c === 'deconnecte') dire('Déconnecté');
  else if (c === 'refusee') dire('Connexion refusée');
  else if (c === 'erreur') dire('Connexion impossible : ' + (raisons[p.get('raison')] || 'erreur'));

  // On nettoie l'adresse : ces paramètres n'ont plus de sens une fois lus.
  p.delete('connexion'); p.delete('raison');
  const q = p.toString();
  history.replaceState(null, '', location.pathname + (q ? '?' + q : '') + location.hash);
}

/* ---------- divers ---------- */
function echapper(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function rendreTout() {
  rendreCompte();
  rendreClassement();
  rendreHistorique();
  if (enBeta()) document.dispatchEvent(new CustomEvent('bdp:beta'));
}

/* En bêta le classement et l'historique dorment : on peut rejouer l'avis
   du jour autant qu'on veut, un classement n'y voudrait plus rien dire.
   Le drapeau vient du serveur, jamais du navigateur.

   La garde vit dans chaque fonction et non dans rendreTout() : l'écouteur
   « bdp:mode » appelle rendreClassement() directement, et le classement
   reparaissait au premier changement de mode. */
function enBeta() {
  return !!(etat && etat.beta);
}

function dormir(id) {
  const n = el(id);
  if (n) n.hidden = true;
  return true;
}

/* ---------- branchement ---------- */
document.addEventListener('bdp:mode', e => {
  if (e.detail.mode === mode) return;
  mode = e.detail.mode;
  rendreClassement();
});
document.addEventListener('bdp:victoire', e => verser(e.detail));

try {
  etat = await api(q('moi.php'));
} catch (err) {
  // Site sans backend : on retire proprement toute la couche compte.
  apiDispo = false;
  ['compte', 'classement', 'historique'].forEach(id => {
    const n = el(id);
    if (n) n.hidden = true;
  });
  if (!err.absente) {
    console.warn('[Bureau des Primes] API injoignable :', err.message);
  }
}

if (apiDispo) {
  messageConnexion();
  rendreTout();
  // Le lobby n'appartient à aucun registre : y reprendre les parties
  // locales n'en remonterait qu'un seul, choisi au hasard du repli.
  if (!SUR_LOBBY) reprendreLocal();
}
