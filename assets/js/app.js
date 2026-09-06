/* ==================================================================
   Bureau des Primes — moteur de jeu

   Module ES, portée isolée : rien ne fuit dans window. Le moteur ne
   connaît aucun univers en particulier — il lit celui que la page
   déclare (<body data-univers="…">), applique la description trouvée
   dans univers.js, et charge le registre correspondant.
   ================================================================== */

import { UNIVERS } from './univers.js';
import { habillerSelects } from './menu.js';
import { hash, slug, initials, echapper, teinteDe, plaque, brancherPhotos }
  from './commun.js';

const CLE_UNIVERS = document.body.dataset.univers || 'one-piece';
const U = UNIVERS[CLE_UNIVERS];
if (!U) {
  throw new Error('Univers inconnu : ' + CLE_UNIVERS +
    '. Vérifiez data-univers sur <body> et assets/js/univers.js.');
}
const DATA_URL = U.registre;

/* Panne de chargement : on remplace le plateau par un message lisible
   et on retire ce qui ne mènerait plus nulle part. */
function panne(titre, texte){
  const zone = document.getElementById('play');
  if (zone){
    zone.innerHTML = '<div class="empty"><h3>' + titre + '</h3><p>' + texte +
      '</p><p><button class="bouton" onclick="location.reload()">Recharger</button></p></div>';
  }
  // Sans registre : plus d'onglets de mode, plus de barre de proposition,
  // et plus de decompte de personnages a annoncer en pied de page.
  ['form', 'brief', 'modebar', 'foot-src'].forEach(function(id){
    const n = document.getElementById(id);
    if (n) n.hidden = true;
  });
}

let DATA;
try {
  const rep = await fetch(DATA_URL);
  if (!rep.ok) throw new Error('HTTP ' + rep.status + ' sur ' + DATA_URL);
  DATA = await rep.json();
} catch (err) {
  console.error('[Bureau des Primes] registre illisible.', err,
    '\nEn local, la page doit être servie en HTTP (voir README.md) : ' +
    'ouverte en file:// le navigateur bloque la lecture du registre.');
  panne('Dossier inaccessible',
    "Le registre des personnages n'a pas pu être ouvert. " +
    'Vérifiez votre connexion, puis rechargez la page.');
  throw err;
}

const PERSOS = DATA.persos;
/* Les echelles ordonnees (sagas, arcs, rangs…) viennent du registre ;
   un attribut ordinal dit laquelle il utilise. On memorise la position
   de chaque valeur pour comparer et orienter la flèche. */
const RANGS = {};
for (const [nom, valeurs] of Object.entries(DATA)) {
  if (Array.isArray(valeurs) && nom !== 'persos') {
    RANGS[nom] = Object.fromEntries(valeurs.map((v, i) => [v, i]));
  }
}
const EPOCH = Date.UTC(2026, 0, 1);

/* ------------------------------------------------------------------
   PORTRAITS
   Chaque personnage recoit une plaque generee — initiales sur un fond
   teinte par faction — que recouvre le portrait
   assets/img/photos/<univers>/<slug>.jpg quand il existe. Une image
   absente ou en erreur retombe sur la plaque, sans bruit.

   Les briques vivent dans commun.js : le lexique les emploie telles
   quelles, et les deux pages teintent donc le meme personnage de la
   meme facon.
   ------------------------------------------------------------------ */
const hueOf = f => teinteDe(U, f);
const mug = (p, taille) => plaque(U, p, taille);
const wirePhotos = () => brancherPhotos();


/* Le seul format que le moteur applique lui-meme ; les autres
   (berry, centimetres) sont declares par l'univers. */
const fmt = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');

const MODES = U.modes;
const MODE = Object.fromEntries(MODES.map(m => [m.id, m]));
/* Les intitulés des attributs comparés, dans l'ordre de compare(). */
const ATTRS = U.attrs.map(a => a.label);
/* Le plateau annonce combien d'attributs il compare. Les deux registres
   actuels en déclarent huit, mais rien ne l'impose : le chiffre se lit
   dans l'univers plutôt que d'être écrit en toutes lettres. */
const CHIFFRES = ['zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six',
                  'sept', 'huit', 'neuf', 'dix', 'onze', 'douze'];
const enLettres = n => CHIFFRES[n] || String(n);

/* ---------- utils ---------- */
const norm = s => s.toLowerCase().normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]/g, '');
/* ------------------------------------------------------------------
   LE JOUR DE JEU

   L'avis bascule à minuit, heure de Paris. On raisonne toujours sur la
   date calendaire du fuseau, jamais sur un décompte d'heures : les deux
   changements d'heure annuels ajoutent ou retirent soixante minutes, et
   un « toutes les 24 h » dériverait deux fois par an.

   api/_jeu.php fait le même calcul dans le même fuseau. Les deux doivent
   rester d'accord, sinon le serveur refuse les parties pendant l'heure
   de décalage.
   ------------------------------------------------------------------ */
const FUSEAU = 'Europe/Paris';
const decoupeJour = new Intl.DateTimeFormat('fr-CA', {
  timeZone: FUSEAU, year:'numeric', month:'2-digit', day:'2-digit',
});
/** La date du jour à Paris, au format AAAA-MM-JJ. */
function jourJeu(){
  const p = {};
  for (const m of decoupeJour.formatToParts(new Date())) p[m.type] = m.value;
  return p.year + '-' + p.month + '-' + p.day;
}
/* Une date calendaire ramenée au minuit UTC correspondant. Sert
   uniquement à compter des jours — numéro d'avis, veille — jamais à
   désigner un instant réel, ce qui la met à l'abri des changements
   d'heure. */
function minuit(jour){
  const [a, m, j] = jour.split('-').map(Number);
  return Date.UTC(a, m - 1, j);
}
const dayKey = () => jourJeu();
const dayNum = () => Math.floor((minuit(dayKey()) - EPOCH) / 86400000) + 1;
const longDate = () => new Date(minuit(dayKey()))
  .toLocaleDateString('fr-FR', { weekday:'long', day:'numeric', month:'long', year:'numeric', timeZone:'UTC' });
/* Le bassin d'un mode est declare dans le registre, pas dans univers.js :
   api/_jeu.php lit exactement la meme regle. Deux sources auraient derive,
   et le serveur aurait refuse des parties valides. */
const BASSINS = Object.fromEntries(DATA.modes.map(m => [m.id, m]));
function dansBassin(p, m){
  if (!m.champ) return true;
  const v = p[m.champ];
  /* Une liste vide est un tableau, donc « truthy » : sans ce test elle
     entrerait dans le bassin cote navigateur alors que le PHP l'en
     ecarte, et le serveur refuserait la partie. */
  if (Array.isArray(v)) return v.length > 0;
  return !!v && v !== m.sauf;
}
const poolOf = id => PERSOS.filter(p => dansBassin(p, BASSINS[id]));
function targetOf(m){
  const pool = poolOf(m);
  return pool[hash(dayKey() + '::' + m) % pool.length];
}
const store = {
  get(k, d){ try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch(e){ return d; } },
  set(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch(e){} }
};
/* Chaque univers a sa propre progression : sans la cle, les deux jeux
   partageraient sessions et statistiques dans le localStorage. */
const SK = 'bdp.v1.' + CLE_UNIVERS + '.';
const el = id => document.getElementById(id);

let toastTimer;
function toast(msg){
  const t = el('toast');
  t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 2200);
}

/* ---------- state ---------- */
let mode = 'classique';
let practice = false;
const sessions = {};

function session(){
  const key = mode + (practice ? '|entrainement' : '|' + dayKey());
  if (!sessions[key]){
    const saved = practice ? null : store.get(SK + key, null);
    const pool = poolOf(mode);
    /* La cible reprise doit encore appartenir au bassin du mode, et pas
       seulement au registre : un personnage qui perd son épithète sort du
       bassin « Épithète », et resolve() ne le retrouverait plus — la
       session reprise serait ingagnable à vie. On repart de zéro. */
    if (saved && saved.target && pool.some(p => p.nom === saved.target)){
      sessions[key] = { key, target:saved.target, guesses:saved.guesses || [], done:!!saved.done };
    } else {
      const t = practice ? pool[Math.floor(Math.random() * pool.length)].nom : targetOf(mode).nom;
      sessions[key] = { key, target:t, guesses:[], done:false };
    }
  }
  return sessions[key];
}
function save(s){
  if (practice) return;
  store.set(SK + s.key, { target:s.target, guesses:s.guesses, done:s.done });
}
const byName = n => PERSOS.find(p => p.nom === n);

/* ---------- comparaison ---------- */
/* Une valeur chiffrée : égale, proche à la tolérance près, ou éloignée.
   La flèche dit de quel côté chercher. */
/* `num` marque les valeurs à aligner en chiffres tabulaires. C'est le
   type de l'attribut qui le dit, pas la forme du texte : deviner d'après
   « ฿ » ou « cm » revenait à câbler One Piece dans le moteur, et tout
   univers à une autre unité perdait l'alignement. */
function cellNombre(g, t, a){
  const tol = a.tolerance < 1 ? (t || 0) * a.tolerance : a.tolerance;
  if (g == null && t == null) return { s:'ok', txt:a.vide || '—' };
  /* Une absence ne dit pas la meme chose partout. « Aucune prime » est
     une prime — la plus basse de toutes — et se compare donc au reste :
     73 des 167 pirates n'en ont pas, et sans fleche l'attribut ne disait
     rien pres d'une fois sur deux. « Taille inconnue », elle, ne se
     compare a rien : l'oeuvre ne l'a jamais donnee. C'est l'univers qui
     tranche, avec videVautZero, et non le moteur en devinant. */
  if (a.videVautZero && (g == null) !== (t == null)){
    return { s:'no', num:g != null,
             txt:g == null ? (a.vide || '—') : a.format(g),
             dir:(g == null ? 0 : g) < (t == null ? 0 : t) ? '▲' : '▼' };
  }
  if (g == null) return { s:'no', txt:a.vide || '—' };
  const txt = a.format(g);
  if (t == null) return { s:'no', txt, num:true };
  if (g === t) return { s:'ok', txt, num:true };
  return { s:Math.abs(g - t) <= tol ? 'part' : 'no', txt, num:true,
           dir:g < t ? '▲' : '▼' };
}

/* Confronte une proposition à la cible, attribut par attribut, selon ce
   que l'univers déclare. Le moteur ne sait pas ce qu'est un Fruit du
   Démon ni un kekkei genkai : il applique un type de comparaison. */
function compare(g, t){
  return U.attrs.map(a => {
    const vg = g[a.cle], vt = t[a.cle];

    if (a.type === 'ensemble'){
      const commun = (vg || []).filter(x => (vt || []).includes(x));
      const identique = (vg || []).length === (vt || []).length
        && commun.length === (vg || []).length;
      return { s:identique ? 'ok' : (commun.length ? 'part' : 'no'),
               liste:vg || [], vide:a.vide || 'Aucun' };
    }

    if (a.type === 'nombre') return cellNombre(vg, vt, a);

    if (a.type === 'ordinal'){
      const echelle = RANGS[a.echelle] || {};
      const ig = echelle[vg], it = echelle[vt];
      if (ig === undefined || it === undefined){
        return { s:vg === vt ? 'ok' : 'no', txt:vg };
      }
      return { s:ig === it ? 'ok' : (Math.abs(ig - it) === 1 ? 'part' : 'no'),
               txt:vg, dir:ig === it ? null : (ig < it ? '▲' : '▼') };
    }

    // exact, avec un demi-point quand deux valeurs partagent une famille
    // (deux Paramécia différentes, par exemple).
    let etat = vg === vt ? 'ok' : 'no';
    if (etat === 'no' && a.famille
        && g[a.famille] === t[a.famille] && g[a.famille] !== a.familleNeutre){
      etat = 'part';
    }
    return { s:etat, txt:vg };
  });
}

/* ---------- render ---------- */
function renderModes(){
  el('modebar').innerHTML =
    /* Deux commandes pour un meme choix. Au large, les onglets : quatre
       ou cinq modes tiennent sur une ligne et se lisent d'un coup d'oeil.
       Sur un telephone ils passent a la ligne et mangent un tiers de
       l'ecran avant que le jeu ne commence — le menu prend alors le
       relais. La feuille de style montre l'un ou l'autre ; rien ici ne
       mesure la largeur, ce qui serait faux des la rotation. */
    '<div class="onglets" role="tablist" aria-label="Modes de jeu">' +
    MODES.map(m => '<button class="tab" role="tab" data-m="' + m.id + '" aria-selected="' +
      (m.id === mode) + '">' + m.label + '</button>').join('') +
    '</div>' +
    '<select class="barre-menu" id="mode-menu" aria-label="Mode de jeu">' +
    MODES.map(m => '<option value="' + m.id + '"' +
      (m.id === mode ? ' selected' : '') + '>' + echapper(m.label) +
      '</option>').join('') +
    '</select>' +
    '<label class="practice"' + (practice ? ' data-actif="1"' : '') + '>' +
      '<input type="checkbox" id="practice"' + (practice ? ' checked' : '') + '>' +
      '<span class="case" aria-hidden="true"></span>' +
      '<span>Entraînement</span></label>' +
    /* La sortie vers le lexique : tout ce que ce registre contient, sans
       avoir à le deviner une fiche à la fois. L'intitulé vient de
       l'univers — « les pirates », « les entrées » — plutôt que d'un mot
       générique qui ne dirait rien de ce qu'on va y trouver. */
    '<a class="vers-lexique" href="lexique.html?jeu=' + CLE_UNIVERS + '">Liste des ' +
      U.mots.pluriel + '</a>';
  el('modebar').querySelectorAll('.tab').forEach(b => {
    b.onclick = () => { mode = b.dataset.m; render(); };
  });
  el('mode-menu').onchange = e => { mode = e.target.value; render(); };
  el('practice').onchange = e => { practice = e.target.checked; render(); };
  /* renderModes() refait la barre a chaque tour : le menu habille est
     detruit avec elle, il faut donc le reposer sur le <select> neuf. */
  habillerSelects(el('modebar'));
}

function renderBrief(){
  const m = MODE[mode], s = session(), t = byName(s.target);
  const clue = m.indice && !s.done ? m.indice(t) : null;
  el('brief').innerHTML =
    '<div class="brief-body">' +
      '<span class="k">Mode ' + m.label +
        (practice ? ' · tirage aléatoire' : ' · avis du jour') + '</span>' +
      '<h2>' + m.titre + '</h2><p>' + m.sous + '</p></div>' +
    (clue ? '<div class="clue"><span class="k">' + clue.k + '</span><div class="val' +
            (clue.mono ? ' mono' : '') + '">' + clue.v + '</div></div>' : '');
}

/* Un attribut de fiche : son intitule, sa valeur, et la fleche qui dit
   de quel cote chercher. L'intitule est un vrai element du document et
   non un ::before de feuille de style : sans ligne d'en-tete, c'est lui
   qui porte le sens, y compris pour un lecteur d'ecran. */
/* Chaque valeur d'une liste porte sa teinte : l'univers la fixe pour les
   valeurs qui en ont une d'usage — les types Pokémon, les natures de
   chakra — et le reste est teinté par empreinte, donc stable. La feuille
   de style n'en reçoit que la teinte : c'est elle qui choisit la clarté,
   pour rester lisible dans les deux thèmes. */
function styleValeur(v){
  const t = U.teintesValeurs && U.teintesValeurs[v];
  // [teinte, saturation] quand l'univers en declare une : les types ternes
  // de Pokemon — Normal, Acier, Tenebres — seraient criards autrement.
  const h = Array.isArray(t) ? t[0]
          : (t !== undefined ? t : HUES[hash(String(v)) % HUES.length]);
  return '--h:' + h + (Array.isArray(t) ? ';--s:' + t[1] + '%' : '');
}

/* Une valeur peut porter une icône : un dessin pour le haki, le kanji de
   la nature pour le chakra. L'univers la déclare, le moteur la pose telle
   quelle — SVG ou caractère, il ne fait pas la différence. */
const iconeValeur = v => (U.icones && U.icones[v]) || '';

/* L'icone officielle si le dossier de l'univers en contient une, le
   glyphe declare sinon — kanji ou trace. Une image absente est retiree a
   l'erreur, exactement comme un portrait manquant. */
function iconeHTML(v){
  const glyphe = iconeValeur(v);
  const fichier = U.iconesDossier ? U.iconesDossier + slug(v) + '.png' : null;
  if (!glyphe && !fichier) return '';
  return '<span class="ico">' + glyphe +
    (fichier ? '<img alt="" src="' + fichier + '">' : '') + '</span>';
}

function attrHTML(c, i){
  const cls = c.s === 'ok' ? 'ok' : c.s === 'part' ? 'part' : '';
  const val = c.liste
    ? (c.liste.length
        ? '<span class="hakichips">' +
          c.liste.map(h => {
            return '<i style="' + styleValeur(h) + '">' + iconeHTML(h) + h + '</i>';
          }).join('') + '</span>'
        : '<span>' + c.vide + '</span>')
    : (c.num
        ? '<span class="num">' + c.txt + '</span>'
        : '<span>' + c.txt + '</span>');
  return '<div class="att ' + cls + '" style="--i:' + i + '">' +
         '<dt>' + ATTRS[i] + '</dt><dd>' + val +
         (c.dir ? '<span class="arrow">' + c.dir + '</span>' : '') + '</dd></div>';
}
function renderPlay(){
  const s = session(), t = byName(s.target), n = s.guesses.length;
  if (!n){
    el('play').innerHTML =
      '<div class="empty"><h3>Dossier vide</h3>' +
      '<p>Proposez un nom pour verser une première fiche. ' +
      (mode === 'classique'
        ? 'Chacune sera comparée au recherché sur ces ' +
          enLettres(ATTRS.length) + ' points :'
        : 'Chaque erreur déverrouillera un indice.') + '</p>' +
      (mode === 'classique'
        ? '<div class="attrs">' + ATTRS.map(c => '<span>' + c + '</span>').join('') + '</div>'
        : '') +
      '</div>';
    return;
  }
  if (mode === 'classique'){
    // La plus recente en haut : c'est celle qu'on vient de verser.
    const cartes = s.guesses.map((nm, i) => ({ nm, i })).reverse().map(({ nm, i }) => {
      const g = byName(nm);
      const atts = compare(g, t).map(attrHTML).join('');
      return '<article class="fiche">' +
        '<header class="fiche-tete">' + mug(g) +
          '<span class="nm">' + g.nom + '</span>' +
          '<span class="no">' + String(i + 1).padStart(2, '0') + '</span>' +
        '</header>' +
        '<dl class="fiche-attrs">' + atts + '</dl></article>';
    }).join('');
    el('play').innerHTML = '<div class="fiches">' + cartes + '</div>';
  } else {
    const m = MODE[mode];
    // Ce que chaque proposition a ouvert, dans l'ordre où on l'a appris.
    const ouverts = s.guesses.map((nm, i) =>
      (nm !== s.target && m.pistes[i]) ? { n: i + 1, piste: m.pistes[i](t) } : null);

    // La plus récente en haut, comme les fiches du mode Classique : c'est
    // la ligne qu'on vient d'obtenir qu'on relit en premier.
    const rows = s.guesses.map((nm, i) => ({ nm, i })).reverse().map(({ nm, i }) => {
      const g = byName(nm);
      const good = nm === s.target;
      const ouvert = ouverts[i];
      return '<div class="hintrow ' + (good ? 'reveal' : 'wrong') + '">' +
        '<span class="idx">' + String(i + 1).padStart(2, '0') + '</span>' +
        mug(g, 'md') + '<span class="who">' + g.nom + '</span>' +
        '<span class="hint">' + (ouvert
          // Sans ce mot, la valeur se lit comme un attribut du personnage
          // proposé alors qu'elle décrit le recherché.
          ? '<span class="tag">Indice ' + ouvert.n + '</span>' +
            '<span class="lbl">' + ouvert.piste[0] + '</span>' +
            '<span class="v">' + ouvert.piste[1] + '</span>'
          : '<span class="lbl">' + (good ? 'Identifié' : "Plus d'indice") + '</span>') + '</span>' +
        '</div>';
    }).join('');

    // Les indices se lisent aussi d'affilée : empilés entre les portraits
    // et dans l'ordre inverse, on ne voit plus ce qu'ils disent ensemble.
    const acquis = ouverts.filter(Boolean);
    const recap = acquis.length
      ? '<details class="recap"><summary>Tous les indices (' + acquis.length + ')</summary>' +
        '<ul class="recap-liste">' + acquis.map(o =>
          '<li><span class="n">Indice ' + o.n + '</span>' +
            '<span class="lbl">' + o.piste[0] + '</span>' +
            '<span class="v">' + o.piste[1] + '</span></li>').join('') +
        '</ul></details>'
      : '';
    el('play').innerHTML = '<div class="hints">' + rows + '</div>' + recap;
  }
}

function renderVerdict(){
  const s = session();
  if (!s.done){ el('verdict').innerHTML = ''; return; }
  const t = byName(s.target);
  const line = (k, v) => '<div><span class="k">' + k + '</span><span class="v">' + v + '</span></div>';
  const A = U.affiche;
  el('verdict').innerHTML =
    '<div class="poster"><div class="poster-in">' +
    '<div class="captured">' + A.tampon + '</div>' +
    '<h3>' + A.titre + '</h3><div class="doa">' + A.sous + '</div>' +
    mug(t, 'lg') +
    '<div class="who">' + t.nom + '</div>' +
    (t.epithete ? '<div class="ep">« ' + t.epithete + ' »</div>' : '') +
    '<div class="bounty' + (A.valeurVide(t) ? ' none' : '') + '">' +
      A.valeur(t) + '</div>' +
    '<div class="fine">' + A.mention(t) + '</div>' +
    '<div class="dossier">' +
      A.dossier(t).map(([k, v]) => line(k, v)).join('') +
    '</div>' +
    '<div class="verdict-actions">' +
      '<button class="act primary" id="share">' +
        (navigator.share ? 'Partager' : 'Copier le résultat') + '</button>' +
      '<button class="act" id="again">' +
        (practice ? 'Nouveau tirage' : 'Rejouer') +
      '</button>' +
    '</div>' +
    '<div class="partage" id="partage" hidden></div>' +
    '</div></div>';
  el('share').onclick = share;
  el('again').onclick = () => {
    /* Aucune attente jusqu'à minuit, dans aucun registre : un nouveau
       tirage tout de suite, dans le même mode. L'avis du jour reste
       résolu et la série est acquise — ces tirages-là ne comptent ni au
       classement ni dans la série, c'est ce qui permet d'en enchaîner
       autant qu'on veut sans fausser le jeu quotidien. */
    practice = true;
    delete sessions[mode + '|entrainement'];
    render();
  };
}

function renderStrip(){
  const st = store.get(SK + 'stats', { played:0, streak:0, best:0, total:0 });
  const s = session();
  el('dl-date').textContent = longDate();
  el('dk-num').textContent = practice ? '—' : dayNum();
  el('dk-streak').textContent = st.streak;
  el('dk-count').textContent = s.guesses.length;
  const box = (v, k) => '<div class="stat"><b>' + v + '</b><span class="k">' + k + '</span></div>';
  el('strip').innerHTML =
    box(st.played, 'Avis résolus') + box(st.streak, 'Série en cours') +
    box(st.best, 'Record de série') +
    box(st.played ? (st.total / st.played).toFixed(1) : '—', 'Fiches par avis');
}

/* Le bandeau et le pied de page appartiennent à l'univers : le gabarit
   HTML est le même pour les deux jeux, seul son remplissage change. */
function habillerPage(){
  const mets = (id, html) => { const n = el(id); if (n) n.innerHTML = html; };
  mets('mh-top', U.sousTitre);
  mets('wordmark', U.titre.replace(/\s(\S+)$/, ' <em>$1</em>'));
  mets('sceau', U.sceau);
  mets('tagline', U.accroche);
  mets('foot-fan', 'Projet de fan, sans lien avec les ayants droit de ' + U.oeuvre + '.');
  const w = el('foot-wiki');
  if (w){ w.textContent = U.wiki.nom; w.href = U.wiki.url; }
}

function render(){
  habillerPage();
  renderModes(); renderBrief(); renderPlay(); renderVerdict(); renderStrip(); wirePhotos();
  const s = session();
  acItems = []; acIx = -1;
  el('ac').hidden = true;
  el('input').value = '';
  el('input').disabled = s.done;
  el('submit').disabled = s.done;
  el('input').placeholder = s.done ? 'Avis classé.' : "Nom d'un personnage…";
  el('foot-count').textContent = PERSOS.length;
  annoncerMode();
}

/* ------------------------------------------------------------------
   RACCORD AVEC LA COUCHE COMPTE  (assets/js/compte.js)

   Le jeu ne connaît ni Discord ni la base : il se contente d'annoncer
   ce qu'il fait. Si compte.js est absent ou si l'API ne répond pas,
   ces annonces ne sont écoutées par personne et rien ne change.

     bdp:mode      le joueur a changé de mode      { mode, jour }
     bdp:victoire  un avis vient d'être résolu     { mode, jour,
                                                     propositions[],
                                                     entrainement }
     window.BDP    lecture seule, pour la reprise de progression
   ------------------------------------------------------------------ */
let modeAnnonce = null;
function annoncerMode(){
  if (mode === modeAnnonce) return;
  modeAnnonce = mode;
  document.dispatchEvent(new CustomEvent('bdp:mode',
    { detail:{ mode, jour: dayKey() } }));
}

window.BDP = {
  toast,
  /** Les avis résolus conservés par ce navigateur, prêts à être versés. */
  partiesLocales(){
    const out = [];
    let n;
    try { n = localStorage.length; } catch(e){ return out; }
    for (let i = 0; i < n; i++){
      const cle = localStorage.key(i);
      if (!cle || !cle.startsWith(SK)) continue;
      const reste = cle.slice(SK.length);
      const coupe = reste.indexOf('|');
      if (coupe < 0) continue;                       // SK+'stats', SK+'reprise.*'
      const m = reste.slice(0, coupe), jour = reste.slice(coupe + 1);
      if (!MODE[m] || !/^\d{4}-\d{2}-\d{2}$/.test(jour)) continue;  // entraînement
      const v = store.get(cle, null);
      if (!v || !v.done || !Array.isArray(v.guesses) || !v.guesses.length) continue;
      out.push({ mode:m, jour, propositions:v.guesses });
    }
    return out;
  },
};

/* ---------- stats ---------- */
function recordWin(n){
  if (practice) return;
  const st = store.get(SK + 'stats', { played:0, streak:0, best:0, total:0, last:null });
  const y = new Date(minuit(dayKey()) - 86400000).toISOString().slice(0, 10);
  if (st.last !== dayKey()) st.streak = st.last === y ? st.streak + 1 : 1;
  st.last = dayKey();
  st.played++; st.total += n;
  st.best = Math.max(st.best, st.streak);
  store.set(SK + 'stats', st);
}

/* ---------- partage ------------------------------------------------
   Quatre voies, de la meilleure a la dernière. Aucune n'est disponible
   partout : la feuille de partage du système n'existe que sur mobile,
   et navigator.clipboard exige un contexte sécurisé — en HTTP le bouton
   ne faisait rien du tout. On descend l'escalier jusqu'à ce qu'une
   marche tienne. */

function texteResultat(){
  const s = session(), t = byName(s.target);
  const body = mode === 'classique'
    ? s.guesses.map(n => compare(byName(n), t)
        .map(c => c.s === 'ok' ? '🟩' : c.s === 'part' ? '🟨' : '🟥').join('')).join('\n')
    : s.guesses.map(n => n === s.target ? '🟩' : '🟥').join('');
  const n = s.guesses.length;
  // Le titre vient de l'univers : figé ici, un résultat partagé depuis le
  // Bingo Book s'annoncerait sous le nom de l'autre registre.
  const head = U.titre + ' — ' + MODE[mode].label +
    (practice ? '' : ' n°' + dayNum()) + ' · ' + n + ' fiche' + (n > 1 ? 's' : '');
  /* Le lien fait la différence entre un résultat qu'on montre et un jeu
     qu'on fait essayer : sans lui, celui qui reçoit la grille ne sait
     pas où jouer. */
  return head + '\n' + body + '\n\n' + location.origin + location.pathname;
}

/* La copie d'avant navigator.clipboard. Obsolète, mais c'est la seule
   qui marche hors HTTPS — et le site tourne en clair tant qu'il n'a pas
   de nom de domaine. */
function copierAncienneManiere(txt){
  const zone = document.createElement('textarea');
  zone.value = txt;
  zone.setAttribute('readonly', '');
  zone.style.cssText = 'position:fixed;top:-1000px;opacity:0';
  document.body.appendChild(zone);
  zone.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
  zone.remove();
  return ok;
}

/* Dernier recours : on montre le texte, déjà sélectionné. Ça marche
   partout, y compris là où le navigateur refuse toute copie automatique. */
function montrerTexte(txt){
  const zone = el('partage');
  if (!zone) return;
  zone.hidden = false;
  zone.innerHTML = '<span class="k">Copiez ce texte</span>' +
    '<textarea readonly rows="' + Math.min(12, txt.split('\n').length + 1) + '"></textarea>';
  const champ = zone.querySelector('textarea');
  champ.value = txt;
  champ.focus();
  champ.select();
}

async function share(){
  const txt = texteResultat();

  // 1. La feuille de partage du système : Discord, WhatsApp, SMS.
  if (navigator.share){
    try {
      await navigator.share({ text: txt });
      return;
    } catch (e){
      // Annulé par le joueur : ce n'est pas un échec, on s'arrête là.
      if (e && e.name === 'AbortError') return;
    }
  }

  // 2. Le presse-papiers moderne, en contexte sécurisé.
  if (navigator.clipboard && navigator.clipboard.writeText){
    try {
      await navigator.clipboard.writeText(txt);
      toast('Résultat copié');
      return;
    } catch (e){ /* on descend d'une marche */ }
  }

  // 3. L'ancienne méthode, seule à fonctionner en HTTP.
  if (copierAncienneManiere(txt)){
    toast('Résultat copié');
    return;
  }

  // 4. À la main.
  montrerTexte(txt);
}

/* ---------- guessing ---------- */
/* Tout le registre est proposable, y compris hors du bassin du mode.
   Restreindre aux seuls candidats possibles reduisait le jeu : en mode
   Prime, 73 des 167 personnages ne pouvaient meme pas etre tapes, ce qui
   revenait a offrir un tri gratuit au joueur. Une proposition hors bassin
   est une fiche comme une autre : elle se compare et elle se trompe. */
function resolve(raw){
  const q = norm(raw);
  if (!q) return null;
  const pool = PERSOS;
  return pool.find(p => norm(p.nom) === q)
      || pool.find(p => norm(p.nom).startsWith(q))
      || pool.find(p => norm(p.nom).includes(q))
      || null;
}
function submitGuess(raw){
  const s = session();
  if (s.done) return;
  const p = resolve(raw);
  if (!p){ toast('Personnage introuvable'); return; }
  if (s.guesses.includes(p.nom)){ toast('Fiche déjà versée'); return; }
  s.guesses.push(p.nom);
  if (p.nom === s.target){
    s.done = true;
    recordWin(s.guesses.length);
    document.dispatchEvent(new CustomEvent('bdp:victoire', { detail:{
      mode, jour: dayKey(), propositions: s.guesses.slice(), entrainement: practice,
    }}));
  }
  save(s);
  render();
  if (s.done) el('verdict').scrollIntoView({ behavior:'smooth', block:'nearest' });
}
function doSubmit(){
  const typed = el('input').value.trim();
  if (!typed) return;
  submitGuess(acItems[acIx] ? acItems[acIx].nom : typed);
}

/* ---------- autocomplete ---------- */
let acItems = [], acIx = -1;
function updateAC(){
  const q = norm(el('input').value);
  const box = el('ac'), s = session();
  if (!q){ box.hidden = true; acItems = []; acIx = -1; return; }
  acItems = PERSOS
    .filter(p => !s.guesses.includes(p.nom) && norm(p.nom).includes(q))
    .sort((a, b) => norm(a.nom).indexOf(q) - norm(b.nom).indexOf(q))
    .slice(0, 8);
  if (!acItems.length){ box.hidden = true; acIx = -1; return; }
  acIx = 0;
  box.innerHTML = acItems.map((p, i) =>
    '<li role="option" data-i="' + i + '" aria-selected="' + (i === 0) + '">' + mug(p, 'sm') +
    '<span class="nm">' + p.nom + '</span><span class="sub">' + p[U.teinteSur] + '</span></li>').join('');
  box.hidden = false;
  wirePhotos();
  box.querySelectorAll('li').forEach(li => {
    li.onmousedown = e => { e.preventDefault(); submitGuess(acItems[+li.dataset.i].nom); };
  });
}
function moveAC(d){
  if (el('ac').hidden || !acItems.length) return;
  acIx = (acIx + d + acItems.length) % acItems.length;
  el('ac').querySelectorAll('li').forEach((li, i) => li.setAttribute('aria-selected', i === acIx));
  el('ac').children[acIx].scrollIntoView({ block:'nearest' });
}

el('input').addEventListener('input', updateAC);
el('input').addEventListener('keydown', e => {
  if (e.key === 'ArrowDown'){ e.preventDefault(); moveAC(1); }
  else if (e.key === 'ArrowUp'){ e.preventDefault(); moveAC(-1); }
  else if (e.key === 'Escape'){ el('ac').hidden = true; }
  else if (e.key === 'Enter'){ e.preventDefault(); doSubmit(); }
});
el('input').addEventListener('blur', () => setTimeout(() => { el('ac').hidden = true; }, 130));
el('form').addEventListener('submit', e => { e.preventDefault(); doSubmit(); });

render();
