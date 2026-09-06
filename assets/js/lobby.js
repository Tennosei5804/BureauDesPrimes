/* ==================================================================
   Bureau des Primes — le lobby

   Construit une carte par univers déclaré dans univers.js : rien n'est
   écrit en dur ici, ajouter un registre suffit à le faire apparaître.

   Chaque carte annonce aussi où en est le joueur — série en cours et
   avis du jour déjà résolus — en relisant le localStorage du jeu
   correspondant. Le moteur n'a pas besoin d'être chargé pour ça : la
   clé de stockage porte l'univers.
   ================================================================== */

import { UNIVERS } from './univers.js';

const FUSEAU = 'Europe/Paris';
const decoupeJour = new Intl.DateTimeFormat('fr-CA', {
  timeZone: FUSEAU, year: 'numeric', month: '2-digit', day: '2-digit',
});
function jourJeu(){
  const p = {};
  for (const m of decoupeJour.formatToParts(new Date())) p[m.type] = m.value;
  return p.year + '-' + p.month + '-' + p.day;
}
function minuit(jour){
  const [a, m, j] = jour.split('-').map(Number);
  return Date.UTC(a, m - 1, j);
}
const EPOCH = Date.UTC(2026, 0, 1);

function lire(cle, defaut){
  try { const v = localStorage.getItem(cle); return v ? JSON.parse(v) : defaut; }
  catch (e) { return defaut; }
}

/** Ce que ce navigateur sait de la progression dans un univers. */
function etat(u){
  const SK = 'bdp.v1.' + u.cle + '.';
  const st = lire(SK + 'stats', { played: 0, streak: 0, best: 0 });
  const jour = jourJeu();
  let faits = 0;
  for (const m of u.modes){
    const s = lire(SK + m.id + '|' + jour, null);
    if (s && s.done) faits++;
  }
  return { serie: st.streak || 0, resolus: st.played || 0,
           faits, total: u.modes.length };
}

function echapper(s){
  return String(s).replace(/[&<>"']/g, c =>
    ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}

function carte(u){
  const e = etat(u);
  const avancement = e.faits
    ? e.faits + ' / ' + e.total + " avis résolus aujourd'hui"
    : e.total + ' modes · aucun avis résolu aujourd\'hui';
  return '<a class="registre" href="' + u.cle + '.html">' +
    '<span class="registre-sceau" aria-hidden="true">' + u.sceau + '</span>' +
    '<span class="registre-corps">' +
      '<span class="k">' + echapper(u.oeuvre) + '</span>' +
      '<span class="registre-nom">' + echapper(u.titre) + '</span>' +
      '<span class="registre-texte">' + echapper(u.accroche) + '</span>' +
      '<span class="registre-etat">' +
        '<span>' + avancement + '</span>' +
        (e.serie ? '<span class="registre-serie">Série ' + e.serie + '</span>' : '') +
      '</span>' +
    '</span></a>';
}

/* Une œuvre peut tenir plusieurs registres : Minecraft en a deux, les
   créatures et les blocs. Ils se rangent ensemble, sinon la grille les
   sépare au gré de la largeur — le Journal de Bord finissait une rangée
   et la Table de Craft en ouvrait une autre, alors que c'est le même
   jeu. On groupe sur `oeuvre`, qui existait déjà. */
function familles(univers){
  const groupes = [];
  for (const u of Object.values(univers)){
    const dernier = groupes[groupes.length - 1];
    if (dernier && dernier.oeuvre === u.oeuvre) dernier.registres.push(u);
    else groupes.push({ oeuvre: u.oeuvre, registres: [u] });
  }
  return groupes;
}

function bloc(g){
  if (g.registres.length === 1) return carte(g.registres[0]);
  // L'intitule passe par data-oeuvre : le CSS le pose en ::before, sur
  // l'ecart de la grille, sans ajouter d'element ni de hauteur.
  return '<div class="famille" data-oeuvre="' + echapper(g.oeuvre) + ' · ' +
    enLettres(g.registres.length) + ' registres">' +
    g.registres.map(carte).join('') + '</div>';
}

const MOTS = ['zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six'];
const enLettres = n => MOTS[n] || String(n);

const zone = document.getElementById('lobby');
if (zone) zone.innerHTML = familles(UNIVERS).map(bloc).join('');

/* Les lexiques : la liste complete de chaque registre, pour qui veut
   consulter plutot que jouer. */
const liens = document.getElementById('lex-liens');
if (liens){
  liens.innerHTML = '<span class="lex-liens-titre">Consulter un registre</span>' +
    Object.values(UNIVERS).map(u =>
      '<a href="lexique.html?jeu=' + u.cle + '">' + echapper(u.oeuvre) + '</a>').join('');
}

/* La ligne de date reprend celle des jeux, pour que le lobby annonce le
   même avis du jour. */
const jour = jourJeu();
const dl = document.getElementById('dl-date');
if (dl){
  dl.textContent = new Date(minuit(jour)).toLocaleDateString('fr-FR',
    { weekday:'long', day:'numeric', month:'long', year:'numeric', timeZone:'UTC' });
}
const dk = document.getElementById('dk-num');
if (dk) dk.textContent = Math.floor((minuit(jour) - EPOCH) / 86400000) + 1;
