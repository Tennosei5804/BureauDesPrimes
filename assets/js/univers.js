/* ==================================================================
   Bureau des Primes — définition des univers

   Tout ce qui distingue un univers d'un autre vit ici : les attributs
   comparés, les modes, le vocabulaire, l'affiche finale. Le moteur
   (app.js) n'en connaît aucun en particulier, il applique ce qu'il lit.

   Ajouter un univers, c'est ajouter une entrée ici, un registre dans
   assets/data/ et une page qui porte data-univers. Aucune ligne du
   moteur, du style ou de la couche compte n'est à toucher.

   Les attributs se déclarent par type :
     exact     égalité stricte ; « famille » autorise un demi-point
               quand deux valeurs différentes partagent une catégorie
     ensemble  liste ; tout en commun donne vert, une partie jaune
     nombre    comparaison chiffrée, avec tolérance et flèche
     ordinal   position sur une échelle nommée du registre, avec flèche
   ================================================================== */

const fmt = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
const berry = n => '฿ ' + fmt(n);
/* Une taille en centimetres, ou « Inconnue ». Sept fiches du Bingo Book
   n'en declarent pas : fmt(null) affichait « null cm » sur l'affiche
   finale comme dans les indices. Le format d'attribut n'etait pas
   touche — cellNombre() ne l'appelle jamais avec une valeur vide — mais
   pistes et dossier lisent le personnage brut. */
const cm = n => n == null ? 'Inconnue' : fmt(n) + ' cm';
const numero = n => n == null ? 'Aucun' : 'n° ' + n;
const kg = n => n == null ? 'Inconnu' : String(n).replace('.', ',') + ' kg';
const pts = n => n == null ? 'Inconnu' : fmt(n) + ' pts';
/* Minecraft compte en demi-coeurs : 20 PV font dix coeurs, et c'est
   ainsi que le joueur les lit. */
const coeurs = n => n == null ? 'Inconnus' : fmt(n) + ' PV';
/* Un objet s'empile par 64, par 16, ou pas du tout. */
const pile = n => n == null ? 'Inconnu' : (n === 1 ? 'Aucun' : 'par ' + n);

export const UNIVERS = {

  /* ---------------------------------------------------------------- */
  'one-piece': {
    cle: 'one-piece',
    titre: 'Bureau des Primes',
    sousTitre: 'Marine · Service des avis de recherche',
    oeuvre: 'One Piece',
    registre: 'assets/data/one-piece.json',
    photos: 'assets/img/photos/one-piece/',
    accroche: "Un pirate est recherché chaque jour. Versez des fiches au " +
              "dossier et recoupez-les jusqu'à l'identifier.",
    mots: { entite: 'pirate', pluriel: 'pirates' },
    wiki: { nom: 'One Piece Wiki', url: 'https://onepiece.fandom.com/fr/wiki/Wiki_One_Piece' },

    /* La couleur de la plaque d'initiales suit cet attribut. */
    teinteSur: 'equipage',
    /* Teinte des pastilles de haki. L'Armement noircit le corps, d'ou
       l'ardoise ; l'Observation est le « Kenbunshoku », toujours rendu en
       bleu ; le Haki des Rois eclate en violet dans l'anime. */
    teintesValeurs: {
      'Armement': 218, 'Observation': 190, 'Rois': 285,
    },
    icones: {
      'Armement':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path fill-rule="evenodd" fill="currentColor" ' +
        'd="M8 1.5 13.6 4.6v6.8L8 14.5 2.4 11.4V4.6Z M8 5.1 10.9 6.7v3.4L8 11.7 5.1 10.1V6.7Z">' +
        '</path></svg>',
      'Observation':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M1.4 8S4 3.7 8 3.7 14.6 8 14.6 8 12 12.3 8 12.3 1.4 8 1.4 8Z" ' +
        'fill="none" stroke="currentColor" stroke-width="1.5"></path>' +
        '<circle cx="8" cy="8" r="2" fill="currentColor"></circle></svg>',
      'Rois':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M2.3 12.4h11.4l1.1-7.4-3.9 2.9L8 3l-2.9 4.9L1.2 5Z" ' +
        'fill="currentColor"></path></svg>',
    },
    teintes: {
      'Équipage du Chapeau de Paille': 6, 'Marine': 212,
      'Équipage de Barbe Blanche': 44, 'Équipage aux Cent Bêtes': 284,
      'Équipage de Big Mom': 330, 'Équipage de Barbe Noire': 256,
      'Armée Révolutionnaire': 150, 'Équipage de Roger': 38,
      'Cross Guild': 190, 'Équipage du Roux': 14, 'Cipher Pol': 206,
      'Clan Kozuki': 96,
    },

    /* Le sceau de la Marine : deux anneaux, la mouette, la barre. */
    sceau: `<svg viewBox="0 0 100 100" role="presentation">
      <defs><path id="anneau" d="M50,50 m-35,0 a35,35 0 1,1 70,0 a35,35 0 1,1 -70,0"></path></defs>
      <circle cx="50" cy="50" r="47" fill="none" stroke="currentColor" stroke-width="2.4"></circle>
      <circle cx="50" cy="50" r="42.5" fill="none" stroke="currentColor" stroke-width="1"></circle>
      <text font-family="Oswald, sans-serif" font-size="10.4" letter-spacing="2.3" fill="currentColor">
        <textPath href="#anneau" startOffset="25%" text-anchor="middle">MARINE &#183; JUSTICE</textPath></text>
      <path d="M27 55 q11.5 -14 23 -2.5 q11.5 -11.5 23 2.5" fill="none"
            stroke="currentColor" stroke-width="4.4" stroke-linecap="round"></path>
      <path d="M34 64.5 h32" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"></path>
    </svg>`,

    attrs: [
      { cle: 'genre',       label: 'Genre',          type: 'exact' },
      { cle: 'equipage',    label: 'Équipage',       type: 'exact' },
      { cle: 'origine',     label: 'Origine',        type: 'exact' },
      { cle: 'fruitDetail', label: 'Fruit du Démon', type: 'exact',
        famille: 'fruit', familleNeutre: 'Aucun' },
      { cle: 'haki',        label: 'Haki',           type: 'ensemble', vide: 'Aucun' },
      { cle: 'prime',       label: 'Prime',          type: 'nombre',
        format: berry, vide: 'Aucune', tolerance: 0.25,
        /* Ne pas etre recherche, c'est une prime de zero : la fleche a
           donc un sens. Une taille inconnue n'en a pas. */
        videVautZero: true },
      { cle: 'taille',      label: 'Taille',         type: 'nombre',
        format: cm, tolerance: 15 },
      { cle: 'saga',        label: '1re saga',       type: 'ordinal', echelle: 'sagas' },
    ],

    modes: [
      { id: 'classique', label: 'Classique',
        titre: "Qui est le pirate recherché aujourd'hui ?",
        sous: 'Aucun indice de départ. Chaque fiche versée dévoile huit attributs à recouper.' },
      { id: 'fruit', label: 'Fruit du Démon',
        titre: 'À qui appartient ce Fruit du Démon ?',
        sous: "Le nom japonais du fruit, rien d'autre. Chaque erreur ouvre un indice.",
        indice: p => ({ k: 'Fruit du Démon', v: p.fruitNom }),
        pistes: [
          p => ['Type', p.fruitDetail],
          p => ['Traduction', p.fruitNomEn || '—'],
          p => ['Équipage', p.equipage],
          p => ['Saga', p.saga],
          p => ['Origine', p.origine],
          p => ['Taille', cm(p.taille)],
        ] },
      { id: 'prime', label: 'Prime',
        titre: 'Quelle tête vaut cette somme ?',
        sous: "Le montant exact d'un avis de recherche en vigueur.",
        indice: p => ({ k: 'Prime en vigueur', v: berry(p.prime), mono: true }),
        pistes: [
          p => ['Genre', p.genre],
          p => ['Origine', p.origine],
          p => ['Fruit du Démon', p.fruitDetail],
          p => ['Équipage', p.equipage],
          p => ['Saga', p.saga],
          p => ['Épithète', p.epithete || '—'],
        ] },
      { id: 'epithete', label: 'Épithète',
        titre: 'Qui porte ce surnom ?',
        sous: "L'épithète telle qu'on la crie sur les quais.",
        indice: p => ({ k: 'Épithète', v: '« ' + p.epithete + ' »' }),
        pistes: [
          p => ['Équipage', p.equipage],
          p => ['Fruit du Démon', p.fruitDetail],
          p => ['Prime', p.prime ? berry(p.prime) : 'Aucune'],
          p => ['Saga', p.saga],
          p => ['Origine', p.origine],
          p => ['Taille', cm(p.taille)],
        ] },
    ],

    affiche: {
      titre: 'WANTED',
      sous: 'Dead or Alive',
      tampon: 'Capturé',
      valeur: p => p.prime ? berry(p.prime) : 'Aucune prime connue',
      valeurVide: p => !p.prime,
      /* Cross Guild place des primes sur des officiers de la Marine :
         créditer le Gouvernement Mondial serait un contresens. */
      mention: p => p.primeEmetteur === 'Cross Guild'
        ? 'Cross Guild · Prime sur la Marine'
        : 'Marine · Gouvernement Mondial',
      dossier: p => [
        ['Équipage', p.equipage],
        ['Origine', p.origine],
        ['Fruit du Démon', p.fruitNom ? p.fruitNom + ' · ' + p.fruitDetail : 'Aucun'],
        ['Haki', p.haki.length ? p.haki.join(' · ') : 'Aucun'],
        ['Taille', cm(p.taille)],
        ['Espèce', p.espece],
        ['1re apparition', p.saga + ' · ch. ' + p.chapitre],
        ['Statut', p.statut],
      ],
    },
  },

  /* ---------------------------------------------------------------- */
  naruto: {
    cle: 'naruto',
    titre: 'Bingo Book',
    sousTitre: 'Registre des Cinq Nations · Fiches de ciblage',
    oeuvre: 'Naruto',
    registre: 'assets/data/naruto.json',
    photos: 'assets/img/photos/naruto/',
    iconesDossier: 'assets/img/icones/naruto/',
    accroche: 'Un ninja est recherché chaque jour. Versez des fiches au ' +
              "dossier et recoupez-les jusqu'à l'identifier.",
    mots: { entite: 'ninja', pluriel: 'ninjas' },
    wiki: { nom: 'Naruto Wiki', url: 'https://naruto.fandom.com/fr/wiki/Wiki_Naruto' },

    teinteSur: 'village',
    /* Teinte des natures de chakra, celles des symboles de l'anime :
       Katon le feu, Suiton l'eau, Doton la terre, Futon le vent, Raiton
       la foudre, puis les kekkei genkai qui les combinent. */
    /* Teintes relevees sur le tableau des natures du wiki : le rouge du
       Katon, le bleu du Suiton, le brun du Doton, le vert du Futon, le
       jaune du Raiton. Yin et Yang y sont noir et blanc — d'ou leur
       saturation quasi nulle, que la paire [teinte, saturation] permet. */
    teintesValeurs: {
      'Katon': [0, 78], 'Suiton': [210, 88], 'Doton': [28, 52],
      'Fûton': [160, 70], 'Raiton': [55, 92], 'Hyôton': [172, 50],
      'Mokuton': [100, 58], 'Ranton': [240, 40], 'Futton': [350, 60],
      'Jinton': [32, 38], 'Bakuton': [22, 92], 'Enton': [10, 35],
      'Jiton': [282, 70], 'Inton': [220, 12], 'Yôton': [45, 15],
      'Inyôton': [280, 18],
    },
    icones: {
      'Katon': '火', 'Suiton': '水', 'Doton': '土', 'Fûton': '風', 'Raiton': '雷',
      'Mokuton': '木', 'Hyôton': '氷', 'Ranton': '嵐', 'Futton': '沸',
      'Jinton': '塵', 'Bakuton': '爆', 'Enton': '炎', 'Jiton': '磁',
      'Inton': '陰', 'Yôton': '陽', 'Inyôton': '陰陽',
    },
    teintes: {
      'Konoha': 96, 'Suna': 38, 'Kiri': 200, 'Kumo': 268, 'Iwa': 24,
      'Oto': 284, 'Ame': 210, 'Akatsuki': 356, 'Kara': 190,
      'Taki': 160, 'Uzushio': 6,
    },

    /* Le sceau des Cinq Nations : la spirale de Konoha, dessinée d'un
       seul trait, sous le même anneau que celui de la Marine — les deux
       jeux doivent se lire comme deux registres du même bureau. */
    sceau: `<svg viewBox="0 0 100 100" role="presentation">
      <defs><path id="anneau" d="M50,50 m-35,0 a35,35 0 1,1 70,0 a35,35 0 1,1 -70,0"></path></defs>
      <circle cx="50" cy="50" r="47" fill="none" stroke="currentColor" stroke-width="2.4"></circle>
      <circle cx="50" cy="50" r="42.5" fill="none" stroke="currentColor" stroke-width="1"></circle>
      <text font-family="Oswald, sans-serif" font-size="10.4" letter-spacing="2.3" fill="currentColor">
        <textPath href="#anneau" startOffset="25%" text-anchor="middle">CINQ NATIONS &#183; SHINOBI</textPath></text>
      <path d="M50 33 a17 17 0 1 1 -12 29 a12 12 0 1 1 8.5 -20.5 a7 7 0 1 0 -4.5 12"
            fill="none" stroke="currentColor" stroke-width="4.2"
            stroke-linecap="round" stroke-linejoin="round"></path>
      <path d="M50 33 v-9" stroke="currentColor" stroke-width="4.2" stroke-linecap="round"></path>
    </svg>`,

    attrs: [
      { cle: 'genre',   label: 'Genre',            type: 'exact' },
      { cle: 'village', label: 'Village',          type: 'exact' },
      { cle: 'clan',    label: 'Clan',             type: 'exact' },
      { cle: 'kekkei',  label: 'Kekkei Genkai',    type: 'ensemble', vide: 'Aucun' },
      { cle: 'chakra',  label: 'Nature élémentaire', type: 'ensemble', vide: 'Aucune' },
      { cle: 'rang',    label: 'Rang ninja',       type: 'ordinal', echelle: 'rangs' },
      { cle: 'taille',  label: 'Taille',           type: 'nombre',
        format: cm, vide: 'Inconnue', tolerance: 15 },
      { cle: 'arc',     label: '1re apparition',   type: 'ordinal', echelle: 'arcs' },
    ],

    modes: [
      { id: 'classique', label: 'Classique',
        titre: "Quel ninja est recherché aujourd'hui ?",
        sous: 'Aucun indice de départ. Chaque fiche versée dévoile huit attributs à recouper.' },
      { id: 'kekkei', label: 'Kekkei Genkai',
        titre: 'À qui appartient ce pouvoir héréditaire ?',
        sous: 'Un kekkei genkai, rien de plus. Chaque erreur ouvre un indice.',
        indice: p => ({ k: 'Kekkei Genkai', v: p.kekkei.join(' · ') }),
        pistes: [
          p => ['Village', p.village],
          p => ['Clan', p.clan],
          p => ['Rang ninja', p.rang],
          p => ['1re apparition', p.arc],
          p => ['Genre', p.genre],
          p => ['Taille', cm(p.taille)],
        ] },
      { id: 'technique', label: 'Technique',
        titre: 'Qui maîtrise cette technique ?',
        sous: 'La technique signature, celle à laquelle on le reconnaît.',
        indice: p => ({ k: 'Technique signature', v: p.technique }),
        pistes: [
          p => ['Village', p.village],
          p => ['Nature de chakra', p.chakra.length ? p.chakra.join(' · ') : 'Aucune'],
          p => ['Rang ninja', p.rang],
          p => ['Clan', p.clan],
          p => ['1re apparition', p.arc],
          p => ['Taille', cm(p.taille)],
        ] },
      { id: 'clan', label: 'Clan',
        titre: 'De quel clan vient ce ninja ?',
        sous: 'Un clan compte souvent plusieurs membres : les indices tranchent.',
        indice: p => ({ k: 'Clan', v: p.clan }),
        pistes: [
          p => ['Rang ninja', p.rang],
          p => ['Kekkei Genkai', p.kekkei],
          p => ['1re apparition', p.arc],
          p => ['Genre', p.genre],
          p => ['Taille', cm(p.taille)],
          p => ['Statut', p.statut],
        ] },
      { id: 'surnom', label: 'Surnom',
        titre: 'Qui porte ce surnom ?',
        sous: "Le nom qu'on lui donne sur le champ de bataille.",
        indice: p => ({ k: 'Surnom', v: '« ' + p.epithete + ' »' }),
        pistes: [
          p => ['Village', p.village],
          p => ['Clan', p.clan],
          p => ['Rang ninja', p.rang],
          p => ['1re apparition', p.arc],
          p => ['Nature de chakra', p.chakra.length ? p.chakra.join(' · ') : 'Aucune'],
          p => ['Taille', cm(p.taille)],
        ] },
    ],

    affiche: {
      titre: 'BINGO BOOK',
      sous: 'Cible répertoriée',
      tampon: 'Identifié',
      valeur: p => p.rang,
      valeurVide: p => p.rang === 'Inconnu',
      mention: () => 'Registre des Cinq Nations',
      dossier: p => [
        ['Village', p.village],
        ['Clan', p.clan],
        ['Kekkei Genkai', p.kekkei],
        ['Nature de chakra', p.chakra.length ? p.chakra.join(' · ') : 'Aucune'],
        ['Technique', p.technique || 'Aucune répertoriée'],
        ['Taille', cm(p.taille)],
        ['1re apparition', p.arc + ' · ' + p.serie + ' ch. ' + p.chapitre],
        ['Statut', p.statut],
      ],
    },
  },

  /* ---------------------------------------------------------------- */
  bleach: {
    cle: 'bleach',
    titre: 'Registre des Âmes',
    sousTitre: 'Gotei 13 · Rapports de terrain',
    oeuvre: 'Bleach',
    registre: 'assets/data/bleach.json',
    photos: 'assets/img/photos/bleach/',
    accroche: 'Une âme est recherchée chaque jour. Versez des fiches au ' +
              "dossier et recoupez-les jusqu'à l'identifier.",
    mots: { entite: 'personnage', pluriel: 'personnages' },
    wiki: { nom: 'Bleach Wiki', url: 'https://bleach.fandom.com/fr/wiki/' },

    /* La plaque se cale sur la race : c'est la ligne de partage du
       recit, et le code couleur que le lecteur a en tete. */
    teinteSur: 'race',
    teintes: {
      'Shinigami': 214, 'Quincy': 196, 'Arrancar': 6, 'Vizard': 274,
      'Hollow': 320, 'Fullbringer': 38, 'Humain': 96, 'Bount': 150,
      'Autre': 46,
    },

    /* Deux zanpakuto croises. Le sceau doit se lire a seize pixels :
       une lame et sa garde, deux fois, et rien d'autre. */
    sceau: `<svg viewBox="0 0 100 100" role="presentation">
      <defs><path id="anneau" d="M50,50 m-35,0 a35,35 0 1,1 70,0 a35,35 0 1,1 -70,0"></path></defs>
      <circle cx="50" cy="50" r="47" fill="none" stroke="currentColor" stroke-width="2.4"></circle>
      <circle cx="50" cy="50" r="42.5" fill="none" stroke="currentColor" stroke-width="1"></circle>
      <text font-family="Oswald, sans-serif" font-size="10.4" letter-spacing="2.3" fill="currentColor">
        <textPath href="#anneau" startOffset="25%" text-anchor="middle">GOTEI 13 &#183; RAPPORTS</textPath></text>
      <path d="M36 68 L64 42" stroke="currentColor" stroke-width="3.4" stroke-linecap="round"></path>
      <path d="M64 68 L36 42" stroke="currentColor" stroke-width="3.4" stroke-linecap="round"></path>
      <path d="M33 58 L45 70" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"></path>
      <path d="M67 58 L55 70" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"></path>
    </svg>`,

    attrs: [
      { cle: 'genre',       label: 'Genre',        type: 'exact' },
      { cle: 'race',        label: 'Race',         type: 'exact' },
      { cle: 'affiliation', label: 'Affiliation',  type: 'exact' },
      { cle: 'rang',        label: 'Grade',        type: 'exact' },
      { cle: 'zanpakuto',   label: 'Zanpakutô',    type: 'exact' },
      { cle: 'liberation',  label: 'Libération',   type: 'exact' },
      { cle: 'taille',      label: 'Taille',       type: 'nombre',
        format: n => fmt(n) + ' cm', vide: 'Inconnue', tolerance: 15 },
      { cle: 'arc',         label: '1re apparition', type: 'ordinal', echelle: 'arcs' },
    ],

    modes: [
      { id: 'classique', label: 'Classique',
        titre: "Quelle âme est recherchée aujourd'hui ?",
        sous: 'Aucun indice de départ. Chaque fiche versée dévoile huit attributs à recouper.' },
      { id: 'zanpakuto', label: 'Zanpakutô',
        titre: 'À qui appartient cette lame ?',
        sous: "Le nom du zanpakutô, celui qu'on crie pour le libérer.",
        indice: p => ({ k: 'Zanpakutô', v: p.zanpakuto }),
        pistes: [
          p => ['Race', p.race],
          p => ['Affiliation', p.affiliation],
          p => ['Grade', p.rang],
          p => ['Libération', p.liberation],
          p => ['1re apparition', p.arc],
          p => ['Taille', cm(p.taille)],
        ] },
      { id: 'race', label: 'Race',
        titre: 'Quel personnage de cette race ?',
        sous: 'La race seule. Chaque erreur ouvre un indice.',
        indice: p => ({ k: 'Race', v: p.race }),
        pistes: [
          p => ['Affiliation', p.affiliation],
          p => ['Grade', p.rang],
          p => ['Genre', p.genre],
          p => ['Libération', p.liberation],
          p => ['1re apparition', p.arc],
          p => ['Taille', cm(p.taille)],
        ] },
      { id: 'affiliation', label: 'Affiliation',
        titre: 'Qui sert sous cette bannière ?',
        sous: 'Le camp, rien de plus. Chaque erreur ouvre un indice.',
        indice: p => ({ k: 'Affiliation', v: p.affiliation }),
        pistes: [
          p => ['Grade', p.rang],
          p => ['Race', p.race],
          p => ['Libération', p.liberation],
          p => ['Genre', p.genre],
          p => ['1re apparition', p.arc],
          p => ['Taille', cm(p.taille)],
        ] },
    ],

    affiche: {
      titre: 'RAPPORT',
      sous: 'Âme identifiée',
      tampon: 'Classée',
      valeur: p => cm(p.taille),
      valeurVide: p => p.taille == null,
      mention: p => p.rang === 'Capitaine'
        ? 'Gotei 13 · Rapport de capitaine'
        : 'Gotei 13 · Rapport de terrain',
      dossier: p => [
        ['Race', p.race],
        ['Affiliation', p.affiliation],
        ['Grade', p.rang],
        ['Zanpakutô', p.zanpakuto],
        ['Libération', p.liberation],
        ['Genre', p.genre],
        ['Taille', cm(p.taille)],
        ['1re apparition', p.arc],
      ],
    },
  },

  /* ---------------------------------------------------------------- */
  pokemon: {
    cle: 'pokemon',
    titre: 'Fiche Pokédex',
    sousTitre: 'Laboratoire du Professeur · Relevés de terrain',
    oeuvre: 'Pokémon',
    registre: 'assets/data/pokemon.json',
    photos: 'assets/img/photos/pokemon/',
    iconesDossier: 'assets/img/icones/pokemon/',
    accroche: 'Un Pokémon est recherché chaque jour. Versez des fiches au ' +
              "dossier et recoupez-les jusqu'à l'identifier.",
    mots: { entite: 'Pokémon', pluriel: 'Pokémon',
            fiche: 'Pokémon', fiches: 'Pokémons' },
    wiki: { nom: 'PokéAPI', url: 'https://pokeapi.co/' },

    /* La plaque se cale sur le type principal : c'est le code couleur que
       tout le monde a en tête. */
    teinteSur: 'type1',
    /* Les pastilles de type reprennent exactement les teintes de la
       plaque : c'est le meme code couleur, celui que tout joueur a en
       tete depuis les jeux. */
    /* Les 18 types, teinte et saturation d'apres la palette des jeux.
       Les types ternes — Normal, Acier, Tenebres — perdaient tout a la
       saturation par defaut, d'ou la paire [teinte, saturation]. */
    teintesValeurs: {
      'Normal': [59, 22],
      'Feu': [25, 84],
      'Eau': [220, 82],
      'Plante': [99, 54],
      'Électrik': [48, 92],
      'Glace': [178, 48],
      'Combat': [2, 66],
      'Poison': [301, 46],
      'Sol': [44, 68],
      'Vol': [254, 82],
      'Psy': [342, 92],
      'Insecte': [68, 74],
      'Roche': [48, 40],
      'Spectre': [270, 28],
      'Dragon': [256, 96],
      'Ténèbres': [26, 24],
      'Acier': [240, 18],
      'Fée': [330, 54],
    },

    /* Icones dessinees ici, pas reprises : Pokepedia et Pokebip servent
       les visuels du jeu de cartes, qui ne m'appartiennent pas. Ce sont
       des silhouettes, lisibles a 11 px — c'est la seule taille ou elles
       servent. */
    icones: {
      'Normal':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<circle cx="8" cy="8" r="5.2" fill="none" stroke="currentColor" stroke-width="2.6"></circle></svg>',
      'Feu':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M8.6 1.3c.5 2.5-.5 3.6-1.6 4.7-1.3 1.3-2.7 2.6-2.7 4.9a3.9 3.9 0 0 0 7.8 0c0-1.5-.5-2.6-1.2-3.5-.2.9-.7 1.4-1.3 1.4-.9 0-1.4-.8-1.2-1.8.4-2 .6-3.8.2-5.7Z" fill="currentColor"></path></svg>',
      'Eau':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M8 1.5c2.9 3.5 4.7 6 4.7 8a4.7 4.7 0 0 1-9.4 0c0-2 1.8-4.5 4.7-8Z" fill="currentColor"></path></svg>',
      'Plante':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M13.9 2.1C7.3 1.9 2.4 4.6 2.4 9.5c0 1.4.5 2.7 1.4 3.6L9.7 6.8l-4.6 6.9c.9.5 1.9.8 3 .8 4.7 0 7.1-6.2 5.8-12.4Z" fill="currentColor"></path></svg>',
      'Électrik':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M9.9 1.1 3.3 9h3.5l-1 5.9 6.9-8.3H9.2Z" fill="currentColor"></path></svg>',
      'Glace':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M8 1.4v13.2M2.3 4.7l11.4 6.6M13.7 4.7 2.3 11.3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" fill="none"></path></svg>',
      'Combat':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M4 6h6.4a2.7 2.7 0 0 1 2.7 2.7v1.1a3.5 3.5 0 0 1-3.5 3.5H6.7A2.7 2.7 0 0 1 4 10.6Z" fill="currentColor"></path><path d="M6.2 6V4.3M8.5 6V3.9M10.8 6V4.5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"></path><path d="M4 8.7H2.2" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"></path></svg>',
      'Poison':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M7.2 3c2.3 2.9 3.8 4.9 3.8 6.6a3.9 3.9 0 0 1-7.8 0C3.2 7.9 4.9 5.9 7.2 3Z" fill="currentColor"></path><circle cx="12.4" cy="4.2" r="1.8" fill="currentColor"></circle></svg>',
      'Sol':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M1.4 13.7h13.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" fill="none"></path><path d="M1.8 12.6c0-3 2-5.4 4.4-5.4s4.4 2.4 4.4 5.4Z" fill="currentColor"></path><path d="M9.6 12.6c0-2 1.4-3.6 3-3.6 .9 0 1.7.4 2.2 1v2.6Z" fill="currentColor"></path></svg>',
      'Vol':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M1.5 8.6C5.2 4.6 9.7 3.1 14.6 3.1c-1.6 3.3-4.5 5-7.2 5.6 2.3.6 4.1.2 5.8-.8-1.2 3.3-4.3 5-7.4 5-2 0-3.5-.8-4.3-1.9Z" fill="currentColor"></path></svg>',
      'Psy':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M8 13.8A5.8 5.8 0 1 1 13.8 8c0 2.3-1.9 4.2-4.2 4.2S5.4 10.3 5.4 8A2.6 2.6 0 0 1 8 5.4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path></svg>',
      'Insecte':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<circle cx="8" cy="4.7" r="2" fill="currentColor"></circle><ellipse cx="8" cy="10.4" rx="3.3" ry="3.9" fill="currentColor"></ellipse><path d="M6.6 3.3 4.5 1.5M9.4 3.3l2.1-1.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"></path></svg>',
      'Roche':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M2.4 9.6 5.3 3.6h5.5l3 6-2.6 3.6H5Z" fill="currentColor"></path></svg>',
      'Spectre':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M8 1.6a5.1 5.1 0 0 0-5.1 5.1v7.7l1.7-1.6 1.7 1.6 1.7-1.6 1.7 1.6 1.7-1.6 1.7 1.6V6.7A5.1 5.1 0 0 0 8 1.6Z" fill="currentColor"></path></svg>',
      'Dragon':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M3.4 12.4c-.9-3.2-.5-6.2 1.1-9M8 12.6c-1-3.6-1-7 0-10.4M12.6 12.4c.9-3.2.5-6.2-1.1-9" stroke="currentColor" stroke-width="1.9" fill="none" stroke-linecap="round"></path><path d="M3 13.6h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path></svg>',
      'Ténèbres':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M10.6 1.7a6.4 6.4 0 1 0 3.4 9.7A6.4 6.4 0 0 1 10.6 1.7Z" fill="currentColor"></path></svg>',
      'Acier':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<circle cx="8" cy="8" r="3.3" fill="none" stroke="currentColor" stroke-width="2"></circle><path d="M8 1.3v2.2M8 12.5v2.2M1.3 8h2.2M12.5 8h2.2M3.3 3.3l1.5 1.5M11.2 11.2l1.5 1.5M12.7 3.3l-1.5 1.5M4.8 11.2l-1.5 1.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"></path></svg>',
      'Fée':
        '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<path d="M8 1.1c.8 4.3 2.2 5.7 6.5 6.5-4.3.8-5.7 2.2-6.5 6.5-.8-4.3-2.2-5.7-6.5-6.5C5.8 6.8 7.2 5.4 8 1.1Z" fill="currentColor"></path></svg>',
    },
    teintes: {
      'Normal': 45, 'Feu': 14, 'Eau': 210, 'Plante': 110, 'Électrik': 48,
      'Glace': 185, 'Combat': 6, 'Poison': 285, 'Sol': 35, 'Vol': 200,
      'Psy': 320, 'Insecte': 75, 'Roche': 40, 'Spectre': 265,
      'Dragon': 250, 'Ténèbres': 20, 'Acier': 205, 'Fée': 335,
    },

    /* Le sceau du laboratoire : le même anneau que les autres registres,
       une Poké Ball au centre. */
    sceau: `<svg viewBox="0 0 100 100" role="presentation">
      <defs><path id="anneau" d="M50,50 m-35,0 a35,35 0 1,1 70,0 a35,35 0 1,1 -70,0"></path></defs>
      <circle cx="50" cy="50" r="47" fill="none" stroke="currentColor" stroke-width="2.4"></circle>
      <circle cx="50" cy="50" r="42.5" fill="none" stroke="currentColor" stroke-width="1"></circle>
      <text font-family="Oswald, sans-serif" font-size="10.4" letter-spacing="2.3" fill="currentColor">
        <textPath href="#anneau" startOffset="25%" text-anchor="middle">POK&#201;DEX &#183; RELEV&#201;S</textPath></text>
      <circle cx="50" cy="55" r="15" fill="none" stroke="currentColor" stroke-width="2.8"></circle>
      <path d="M35 55 h30" stroke="currentColor" stroke-width="3.4"></path>
      <circle cx="50" cy="55" r="5.2" fill="none" stroke="currentColor" stroke-width="2.8"></circle>
    </svg>`,

    attrs: [
      { cle: 'types',      label: 'Types',       type: 'ensemble', vide: 'Aucun' },
      { cle: 'categorie',  label: 'Catégorie',   type: 'exact' },
      { cle: 'couleur',    label: 'Couleur',     type: 'exact' },
      { cle: 'stade',      label: 'Évolution',   type: 'ordinal', echelle: 'stades' },
      { cle: 'taille',     label: 'Taille',      type: 'nombre',
        format: cm, tolerance: 15 },
      { cle: 'poids',      label: 'Poids',       type: 'nombre',
        format: kg, tolerance: 0.25 },
      { cle: 'stats',      label: 'Total stats', type: 'nombre',
        format: pts, tolerance: 40 },
      { cle: 'generation', label: 'Génération',  type: 'ordinal', echelle: 'generations' },
    ],

    modes: [
      { id: 'classique', label: 'Classique',
        titre: "Quel Pokémon est recherché aujourd'hui ?",
        sous: 'Aucun indice de départ. Chaque fiche versée dévoile huit attributs à recouper.' },
      { id: 'description', label: 'Description',
        titre: 'De quel Pokémon parle cette entrée ?',
        sous: "L'entrée du Pokédex, son nom masqué. Chaque erreur ouvre un indice.",
        indice: p => ({ k: 'Entrée du Pokédex', v: p.description }),
        pistes: [
          p => ['Types', p.types.join(' · ')],
          p => ['Génération', p.generation],
          p => ['Couleur', p.couleur],
          p => ['Évolution', p.stade],
          p => ['Taille', cm(p.taille)],
          p => ['Talent', p.talent],
        ] },
      { id: 'categorie', label: 'Catégorie',
        titre: 'Quel Pokémon porte cette catégorie ?',
        sous: "L'espèce telle que le Pokédex la nomme.",
        indice: p => ({ k: 'Catégorie', v: p.categorie }),
        pistes: [
          p => ['Types', p.types.join(' · ')],
          p => ['Couleur', p.couleur],
          p => ['Génération', p.generation],
          p => ['Évolution', p.stade],
          p => ['Poids', kg(p.poids)],
          p => ['Talent', p.talent],
        ] },
      { id: 'talent', label: 'Talent',
        titre: 'Quel Pokémon a ce talent ?',
        sous: 'Un talent est souvent partagé : les indices tranchent.',
        indice: p => ({ k: 'Talent', v: p.talent }),
        pistes: [
          p => ['Types', p.types.join(' · ')],
          p => ['Génération', p.generation],
          p => ['Catégorie', p.categorie],
          p => ['Couleur', p.couleur],
          p => ['Taille', cm(p.taille)],
          p => ['Total stats', pts(p.stats)],
        ] },
    ],

    affiche: {
      titre: 'POKÉDEX',
      sous: 'Entrée complétée',
      tampon: 'Capturé',
      valeur: p => 'N° ' + String(p.numero).padStart(3, '0'),
      valeurVide: () => false,
      /* Trois statuts depuis le Pokédex national complet : les fabuleux
         ne sont pas des légendaires, et les confondre effaçait une
         distinction que le jeu lui-même fait. */
      mention: p => p.statut === 'Mythique'
        ? 'Pokédex régional · Signalement fabuleux'
        : p.statut === 'Légendaire'
          ? 'Pokédex régional · Signalement légendaire'
          : 'Pokédex régional · Laboratoire du Professeur',
      dossier: p => [
        ['Types', p.types.join(' · ')],
        ['Catégorie', p.categorie],
        ['Couleur', p.couleur],
        ['Évolution', p.stade],
        ['Taille', cm(p.taille)],
        ['Poids', kg(p.poids)],
        ['Total des stats', pts(p.stats)],
        ['Talents', p.talents.join(' · ')],
      ],
    },
  },
  /* ---------------------------------------------------------------- */
  inazuma: {
    cle: 'inazuma',
    titre: 'Feuille de Match',
    sousTitre: 'Football Frontier · Fiches de joueurs',
    oeuvre: 'Inazuma Eleven',
    registre: 'assets/data/inazuma.json',
    photos: 'assets/img/photos/inazuma/',
    accroche: 'Un joueur est recherché chaque jour. Versez des fiches au ' +
              "dossier et recoupez-les jusqu'à l'identifier.",
    mots: { entite: 'joueur', pluriel: 'joueurs' },
    wiki: { nom: 'Inazuma Eleven Wiki', url: 'https://inazuma-eleven.fandom.com/fr/wiki/Wiki_Inazuma_Eleven' },

    /* La teinte suit l'element : les equipes sont devenues une liste, et
       une liste ne designe pas une couleur. */
    teinteSur: 'element',
    /* Teinte des familles de Supertechniques : les quatre classifications
       du jeu, plus les talents. */
    teintesValeurs: {
      'Tir': 14, 'Attaque': 30, 'Défense': 210, 'Gardien': 145, 'Talent': 275,
    },
    /* Quatre elements, quatre teintes : celles du jeu. Les equipes ne
       peuvent plus servir, un joueur en a jusqu'a quatre. */
    teintes: {
      'Feu': 14, 'Terre': 36, 'Bois': 128, 'Vent': 196,
    },

    /* Le sceau de la fédération : le même anneau que les deux autres
       registres, un ballon à la place de la mouette et de la spirale. */
    sceau: `<svg viewBox="0 0 100 100" role="presentation">
      <defs><path id="anneau" d="M50,50 m-35,0 a35,35 0 1,1 70,0 a35,35 0 1,1 -70,0"></path></defs>
      <circle cx="50" cy="50" r="47" fill="none" stroke="currentColor" stroke-width="2.4"></circle>
      <circle cx="50" cy="50" r="42.5" fill="none" stroke="currentColor" stroke-width="1"></circle>
      <text font-family="Oswald, sans-serif" font-size="10.4" letter-spacing="2.3" fill="currentColor">
        <textPath href="#anneau" startOffset="25%" text-anchor="middle">FOOTBALL &#183; FRONTIER</textPath></text>
      <circle cx="50" cy="55" r="14.5" fill="none" stroke="currentColor" stroke-width="2.8"></circle>
      <path d="M50 47.5 l7.1 5.2 -2.7 8.4 h-8.8 l-2.7 -8.4 Z" fill="currentColor"></path>
      <path d="M50 47.5 v-7.5 M57.1 52.7 l7.1 -2.4 M54.4 61.1 l4.4 6.1 M45.6 61.1 l-4.4 6.1 M42.9 52.7 l-7.1 -2.4"
            stroke="currentColor" stroke-width="2.4" stroke-linecap="round"></path>
    </svg>`,

    attrs: [
      { cle: 'genre',      label: 'Genre',        type: 'exact' },
      { cle: 'element',    label: 'Élément',      type: 'exact' },
      { cle: 'poste',      label: 'Poste',        type: 'exact' },
      { cle: 'pays',       label: 'Pays',         type: 'exact' },
      { cle: 'technique',  label: 'Supertechnique', type: 'exact' },
      /* Un joueur passe par plusieurs equipes au fil des saisons : une
         seule valeur en rangeait le gardien du Chaos sous Diamond Dust,
         et on ne pouvait plus le trouver par son equipe. */
      { cle: 'equipes',    label: 'Équipes',      type: 'ensemble', vide: 'Aucune' },
      { cle: 'apparence',  label: 'Apparence',    type: 'ensemble', vide: 'Rien de notable' },
      { cle: 'saison',     label: '1re saison',   type: 'ordinal', echelle: 'saisons' },
    ],

    modes: [
      { id: 'classique', label: 'Classique',
        titre: "Quel joueur est recherché aujourd'hui ?",
        sous: 'Aucun indice de départ. Chaque fiche versée dévoile huit attributs à recouper.' },
      { id: 'technique', label: 'Supertechnique',
        titre: 'Qui lance cette Supertechnique ?',
        sous: "Le nom de la technique signature, celle à laquelle on le reconnaît.",
        indice: p => ({ k: 'Supertechnique', v: p.technique }),
        pistes: [
          p => ['Apparence', p.apparence.length ? p.apparence.join(' · ') : 'Rien de notable'],
          p => ['Poste', p.poste],
          p => ['Équipes', p.equipes.join(' · ')],
          p => ['Élément', p.element],
          p => ['1re saison', p.saison],
          p => ['Numéro', numero(p.numero)],
        ] },
      { id: 'equipe', label: 'Équipe',
        titre: 'Qui joue dans cette équipe ?',
        sous: 'Une équipe compte onze titulaires : les indices tranchent.',
        indice: p => ({ k: 'Équipe', v: p.equipes.join(' · ') }),
        pistes: [
          p => ['Poste', p.poste],
          p => ['Élément', p.element],
          p => ['Numéro', numero(p.numero)],
          p => ['1re saison', p.saison],
          p => ['Genre', p.genre],
          p => ['Supertechnique', p.technique || '—'],
        ] },
      { id: 'numero', label: 'Numéro',
        titre: 'Qui porte ce numéro ?',
        sous: 'Un numéro de maillot, et rien d\'autre pour commencer.',
        indice: p => ({ k: 'Numéro de maillot', v: numero(p.numero), mono: true }),
        pistes: [
          p => ['Équipes', p.equipes.join(' · ')],
          p => ['Poste', p.poste],
          p => ['Élément', p.element],
          p => ['1re saison', p.saison],
          p => ['Pays', p.pays],
          p => ['Supertechnique', p.technique || '—'],
        ] },
    ],

    affiche: {
      titre: 'FEUILLE DE MATCH',
      sous: 'Onze de départ',
      tampon: 'Sélectionné',
      valeur: p => numero(p.numero),
      valeurVide: p => p.numero == null,
      mention: () => 'Football Frontier · Fédération scolaire',
      dossier: p => [
        ['Équipes', p.equipes.length ? p.equipes.join(' · ') : 'Aucune'],
        ['Pays', p.pays],
        ['Poste', p.poste],
        ['Élément', p.element],
        ['Supertechnique', p.technique || 'Aucune'],
        ['Apparence', p.apparence.length ? p.apparence.join(' · ') : 'Rien de notable'],
        ['Numéro', numero(p.numero)],
        ['1re apparition', p.saison],
      ],
    },
  },

  /* ---------------------------------------------------------------- */
  minecraft: {
    cle: 'minecraft',
    titre: 'Journal de Bord',
    sousTitre: 'Carnet du bûcheron · Créatures, blocs et objets',
    oeuvre: 'Minecraft',
    registre: 'assets/data/minecraft.json',
    photos: 'assets/img/photos/minecraft/',
    accroche: 'Une créature, un bloc ou un objet est recherché chaque jour. ' +
              "Versez des fiches au dossier et recoupez-les jusqu'à l'identifier.",
    /* Le registre melange trois natures : le pluriel les nomme toutes
       les trois, sinon « les entrees » ne dit rien de ce qu'on y trouve. */
    mots: { entite: 'entrée', pluriel: 'blocs, objets et créatures',
            fiche: 'entrée', fiches: 'entrées' },
    wiki: { nom: 'Minecraft Wiki', url: 'https://minecraft.fandom.com/wiki/' },

    /* La famille sert pour les trois : elle porte l'espece d'une creature
       et la matiere d'un bloc. */
    teinteSur: 'famille',
    teintes: {
      'Animal': 96, 'Mort-vivant': 142, 'Arthropode': 28, 'Illageois': 268,
      'Créature du Nether': 8, 'Aquatique': 196, 'Golem': 36,
      'Villageois': 46, 'Autre': 320,
      'Bois': 28, 'Pierre': 210, 'Fer': 200, 'Or': 46, 'Diamant': 176,
      'Netherite': 320, 'Cuivre': 18, 'Organique': 96,
    },

    /* Le visage du Creeper, en carres pleins comme dans le jeu. */
    sceau: `<svg viewBox="0 0 100 100" role="presentation">
      <defs><path id="anneau" d="M50,50 m-35,0 a35,35 0 1,1 70,0 a35,35 0 1,1 -70,0"></path></defs>
      <circle cx="50" cy="50" r="47" fill="none" stroke="currentColor" stroke-width="2.4"></circle>
      <circle cx="50" cy="50" r="42.5" fill="none" stroke="currentColor" stroke-width="1"></circle>
      <text font-family="Oswald, sans-serif" font-size="10.4" letter-spacing="2.3" fill="currentColor">
        <textPath href="#anneau" startOffset="25%" text-anchor="middle">CARNET &#183; MINECRAFT</textPath></text>
      <rect x="39.5" y="44" width="7" height="7" fill="currentColor"></rect>
      <rect x="53.5" y="44" width="7" height="7" fill="currentColor"></rect>
      <rect x="44.5" y="53.5" width="11" height="7" fill="currentColor"></rect>
      <rect x="44.5" y="60.5" width="3.5" height="6.5" fill="currentColor"></rect>
      <rect x="52" y="60.5" width="3.5" height="6.5" fill="currentColor"></rect>
    </svg>`,

    /* Huit attributs pour trois natures. Les points de vie ne valent que
       pour une creature, l'empilement que pour un bloc ou un objet : le
       moteur affiche « — » de l'autre cote, comme la prime chez One Piece
       pour un personnage qui n'en a pas. */
    attrs: [
      { cle: 'type',       label: 'Type',           type: 'exact' },
      { cle: 'categorie',  label: 'Catégorie',      type: 'exact' },
      { cle: 'famille',    label: 'Famille',        type: 'exact' },
      { cle: 'dimension',  label: 'Dimension',      type: 'exact' },
      { cle: 'pv',         label: 'Points de vie',  type: 'nombre',
        format: coeurs, vide: '—', tolerance: 6 },
      { cle: 'empilement', label: 'Empilement',     type: 'nombre',
        format: pile, vide: '—', tolerance: 0 },
      { cle: 'butin',      label: 'Butin',          type: 'ensemble', vide: 'Aucun' },
      { cle: 'version',    label: '1re version',    type: 'ordinal', echelle: 'versions' },
    ],

    modes: [
      { id: 'classique', label: 'Blocs et objets',
        titre: "Quel bloc ou objet est recherché aujourd'hui ?",
        sous: 'Aucun indice de départ. Chaque fiche versée dévoile huit attributs à recouper.' },
      { id: 'butin', label: 'Butin',
        titre: 'Que laisse tomber cette créature ?',
        sous: "Le nom de la créature. À vous de dire ce qu'elle lâche.",
        indice: p => ({ k: 'Lâché par', v: p.lachePar.join(' · ') }),
        pistes: [
          p => ['Type', p.type],
          p => ['Catégorie', p.categorie],
          p => ['Famille', p.famille],
          p => ['Dimension', p.dimension],
          p => ['Empilement', pile(p.empilement)],
          p => ['1re version', p.version],
        ] },
      { id: 'mobs', label: 'Créatures',
        titre: "Quelle créature est recherchée aujourd'hui ?",
        sous: 'Aucun indice de départ. Chaque fiche versée dévoile huit attributs à recouper.' },
      { id: 'version', label: 'Version',
        titre: 'Quoi, arrivé dans cette version ?',
        sous: "La mise à jour qui l'a introduit dans le jeu.",
        indice: p => ({ k: '1re version', v: p.version, mono: true }),
        pistes: [
          p => ['Type', p.type],
          p => ['Catégorie', p.categorie],
          p => ['Famille', p.famille],
          p => ['Dimension', p.dimension],
          p => ['Points de vie', coeurs(p.pv)],
          p => ['Empilement', pile(p.empilement)],
        ] },
    ],

    affiche: {
      titre: 'JOURNAL',
      sous: 'Fiche complétée',
      tampon: 'Consignée',
      valeur: p => p.pv != null ? coeurs(p.pv) : pile(p.empilement),
      valeurVide: p => p.pv == null && p.empilement == null,
      mention: p => p.type === 'Créature'
        ? 'Journal de bord · Relevé de créature'
        : 'Journal de bord · Relevé d’inventaire',
      dossier: p => [
        ['Type', p.type],
        ['Catégorie', p.categorie],
        ['Famille', p.famille],
        ['Dimension', p.dimension],
        ['Points de vie', coeurs(p.pv)],
        ['Empilement', pile(p.empilement)],
        ['Butin', p.butin.length ? p.butin.join(' · ') : 'Aucun'],
        ['1re version', p.version],
      ],
    },
  },

};
