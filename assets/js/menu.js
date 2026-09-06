/* ==================================================================
   Bureau des Primes — les menus déroulants

   Un <select> ouvre une liste dessinée par le système : fond blanc,
   surlignage bleu, coins carrés. Sur un dossier sombre à la machine à
   écrire, ça tombe comme un cheveu sur la soupe, et aucune feuille de
   style ne peut la rattraper — cette liste-là n'appartient pas à la
   page.

   On garde donc le <select>, et on lui pose un menu par-dessus. Le
   <select> reste la source de vérité : c'est lui qui porte la valeur,
   c'est lui qui émet « change ». Le reste du site continue de lire
   `el('tri').value` et d'écouter `change` sans rien savoir d'ici, et si
   ce module ne se charge pas, il ne reste qu'un menu système laid mais
   parfaitement fonctionnel.
   ================================================================== */

const echapper = s => String(s).replace(/[&<>"']/g, c =>
  ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));

/** Le menu ouvert, s'il y en a un : un seul à la fois. */
let ouvert = null;

function fermerTout(sauf){
  if (ouvert && ouvert !== sauf) ouvert.fermer();
}

document.addEventListener('pointerdown', e => {
  if (ouvert && !ouvert.racine.contains(e.target)) ouvert.fermer();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && ouvert){ const m = ouvert; m.fermer(); m.bouton.focus(); }
});

function habiller(select){
  if (select.dataset.habille) return;
  select.dataset.habille = '1';

  const racine = document.createElement('div');
  racine.className = 'menu';
  select.parentNode.insertBefore(racine, select);
  racine.appendChild(select);

  /* Le <select> ne sert plus qu'à porter l'état : on le retire du
     parcours au clavier et de la lecture d'écran, sinon le champ est
     annoncé deux fois. L'intitulé passe sur le bouton. */
  const intitule = select.getAttribute('aria-label') || '';
  select.setAttribute('aria-hidden', 'true');
  select.tabIndex = -1;

  const bouton = document.createElement('button');
  bouton.type = 'button';
  bouton.className = 'menu-bouton';
  bouton.setAttribute('aria-haspopup', 'listbox');
  bouton.setAttribute('aria-expanded', 'false');
  if (intitule) bouton.setAttribute('aria-label', intitule);

  const liste = document.createElement('ul');
  liste.className = 'menu-liste';
  liste.setAttribute('role', 'listbox');
  if (intitule) liste.setAttribute('aria-label', intitule);
  liste.hidden = true;

  racine.append(bouton, liste);

  const menu = { racine, bouton, liste, select, fermer, ouvrir, rafraichir };
  let survole = -1;                       // l'option sous le curseur clavier

  /* ---------- dessin ---------- */
  function rafraichir(){
    const options = [...select.options];
    liste.innerHTML = options.map((o, i) =>
      '<li role="option" id="' + identifiant(i) + '" data-i="' + i + '"' +
      (o.selected ? ' aria-selected="true"' : ' aria-selected="false"') +
      '>' + echapper(o.textContent) + '</li>').join('');
    const choisie = select.options[select.selectedIndex];
    bouton.textContent = choisie ? choisie.textContent : '';
    /* Le wrapper suit le hidden du <select> : le filtre de valeurs
       disparaît tant qu'aucun attribut n'est choisi. */
    racine.hidden = select.hidden;
  }

  const identifiant = i => (select.id || 'menu') + '-opt-' + i;

  /* ---------- ouverture ---------- */
  function ouvrir(){
    if (!liste.hidden) return;
    fermerTout(menu);
    rafraichir();
    liste.hidden = false;
    bouton.setAttribute('aria-expanded', 'true');
    ouvert = menu;
    placer();
    survoler(select.selectedIndex >= 0 ? select.selectedIndex : 0);
  }

  function fermer(){
    if (liste.hidden) return;
    liste.hidden = true;
    bouton.setAttribute('aria-expanded', 'false');
    liste.classList.remove('vers-haut');
    bouton.removeAttribute('aria-activedescendant');
    if (ouvert === menu) ouvert = null;
  }

  /* La liste s'ouvre vers le bas, sauf s'il n'y a pas la place : au bas
     d'un écran court, elle sortait de la fenêtre et devenait inatteignable. */
  function placer(){
    const b = bouton.getBoundingClientRect();
    const h = liste.offsetHeight;
    liste.classList.toggle('vers-haut',
      b.bottom + h + 8 > window.innerHeight && b.top - h - 8 > 0);
  }

  /* ---------- déplacement au clavier ---------- */
  function survoler(i){
    const items = [...liste.children];
    if (!items.length) return;
    survole = Math.max(0, Math.min(i, items.length - 1));
    items.forEach((n, k) => n.classList.toggle('survol', k === survole));
    bouton.setAttribute('aria-activedescendant', identifiant(survole));
    items[survole].scrollIntoView({ block: 'nearest' });
  }

  function choisir(i){
    if (i < 0 || i >= select.options.length) return;
    if (select.selectedIndex !== i){
      select.selectedIndex = i;
      /* C'est le <select> qui parle : le reste du site écoute « change »
         sur lui, exactement comme avant ce module. */
      select.dispatchEvent(new Event('change', { bubbles: true }));
    }
    rafraichir();
    fermer();
    bouton.focus();
  }

  /* ---------- branchements ---------- */
  bouton.addEventListener('click', () => (liste.hidden ? ouvrir() : fermer()));

  bouton.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' ||
        e.key === ' '){
      e.preventDefault();
      if (liste.hidden) ouvrir();
      else survoler(survole + (e.key === 'ArrowUp' ? -1 : 1));
      return;
    }
    if (!liste.hidden){
      if (e.key === 'Home'){ e.preventDefault(); survoler(0); }
      else if (e.key === 'End'){ e.preventDefault(); survoler(select.options.length - 1); }
      else if (e.key === 'Tab') fermer();
    }
  });

  /* Enter et Espace valident ; on les traite au relâchement pour ne pas
     rouvrir le menu que la touche vient de fermer. */
  bouton.addEventListener('keyup', e => {
    if (!liste.hidden && (e.key === 'Enter' || e.key === ' ')){
      e.preventDefault();
      choisir(survole);
    }
  });

  /* Frappe au vol : taper « gé » va à « Génération », comme un vrai
     menu système. La saisie s'oublie après une seconde de silence. */
  let frappe = '', minuteur = 0;
  bouton.addEventListener('keydown', e => {
    if (e.key.length !== 1 || e.ctrlKey || e.metaKey || e.altKey) return;
    e.preventDefault();
    if (liste.hidden) ouvrir();
    frappe += e.key.toLowerCase();
    clearTimeout(minuteur);
    minuteur = setTimeout(() => { frappe = ''; }, 1000);
    const sans = s => s.toLowerCase().normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
    const cible = sans(frappe);
    const i = [...select.options].findIndex(o => sans(o.textContent).startsWith(cible));
    if (i >= 0) survoler(i);
  });

  liste.addEventListener('click', e => {
    const li = e.target.closest('li[data-i]');
    if (li) choisir(Number(li.dataset.i));
  });
  liste.addEventListener('pointermove', e => {
    const li = e.target.closest('li[data-i]');
    if (li) survoler(Number(li.dataset.i));
  });

  /* Le lexique reconstruit les options du filtre de valeurs à chaque
     changement d'attribut, et masque le champ quand il n'y a rien à
     filtrer. On suit les deux sans qu'il ait à nous prévenir. */
  new MutationObserver(rafraichir).observe(select, {
    childList: true, attributes: true, attributeFilter: ['hidden'],
  });

  rafraichir();
}

/** Habille tous les <select> d'une zone. Idempotent. */
export function habillerSelects(racine = document){
  racine.querySelectorAll('select').forEach(habiller);
}

/** À appeler après avoir changé une valeur par programme : une
    affectation de `.value` n'émet aucun événement, et l'intitulé du
    bouton resterait sur l'ancien choix. */
export function rafraichirMenus(racine = document){
  racine.querySelectorAll('select[data-habille]').forEach(s => {
    const m = s.closest('.menu');
    const choisie = s.options[s.selectedIndex];
    if (m){
      m.querySelector('.menu-bouton').textContent = choisie ? choisie.textContent : '';
      m.hidden = s.hidden;
      [...m.querySelectorAll('li[data-i]')].forEach(li =>
        li.setAttribute('aria-selected',
          Number(li.dataset.i) === s.selectedIndex ? 'true' : 'false'));
    }
  });
}
