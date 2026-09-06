# Bureau des Primes

Quatre jeux de déduction quotidiens, en français. Chaque jour, un personnage
est recherché : on propose des noms, chaque proposition compare huit
attributs avec la cible, et on recoupe jusqu'à l'identifier.

| registre | œuvre | modes | personnages |
|---|---|---|---|
| **Bureau des Primes** (`one-piece.html`) | One Piece | Classique, Fruit du Démon, Prime, Épithète | 167 |
| **Bingo Book** (`naruto.html`) | Naruto & Boruto | Classique, Kekkei Genkai, Technique, Clan, Surnom | 104 |
| **Registre des Âmes** (`bleach.html`) | Bleach | Classique, Zanpakutô, Race, Affiliation | 124 |
| **Feuille de Match** (`inazuma.html`) | Inazuma Eleven | Classique, Supertechnique, Équipe, Numéro | 103 |
| **Fiche Pokédex** (`pokemon.html`) | Pokémon | Classique, Description, Catégorie, Talent | 386 |
| **Journal de Bord** (`minecraft.html`) | Minecraft — créatures, blocs et objets | Blocs et objets, Butin, Créatures, Version | 219 |

`index.html` est le lobby : il présente les registres, rappelle où en est le
joueur dans chacun, et porte le classement général. Chaque registre a sa
propre série et son propre avis du jour.

Chaque jeu a aussi un mode **Entraînement** qui tire au hasard sans toucher
à la série quotidienne. Le jeu se joue **sans compte** ; une connexion
Discord facultative ajoute les séries synchronisées entre appareils, les
classements et l'historique.

---

## Un seul moteur, plusieurs univers

Le moteur (`assets/js/app.js`) ne connaît aucun univers en particulier. La
page déclare le sien — `<body data-univers="naruto">` — et le moteur
applique la description trouvée dans `assets/js/univers.js` : attributs
comparés, modes, vocabulaire, sceau, affiche finale.

**Ajouter un cinquième registre**, c'est une entrée dans `univers.js`, un
registre dans `assets/data/`, un dossier de portraits, une page qui porte
`data-univers`, et l'ajout de la clé dans `BDP_UNIVERS` (`api/_jeu.php`).
Ni le moteur, ni le style, ni le lobby, ni la couche compte ne bougent.

Les attributs se déclarent par type :

| type | comparaison |
|---|---|
| `exact` | égalité stricte ; `famille` donne un demi-point à deux valeurs d'une même catégorie |
| `ensemble` | liste ; tout en commun donne vert, une partie jaune |
| `nombre` | comparaison chiffrée, avec tolérance et flèche |
| `ordinal` | position sur une échelle nommée du registre, avec flèche |

**Le bassin de chaque mode est déclaré dans le registre**, pas dans
`univers.js` : `api/_jeu.php` lit exactement la même règle. Deux sources
auraient dérivé, et le serveur aurait fini par refuser des parties valides.

## Deux façons de déployer

| | Sans backend | Avec backend |
|---|---|---|
| Hébergement | n'importe quel hôte statique | mutualisé PHP 8.1+ / MySQL, ou un VPS avec Docker |
| Le jeu | complet | complet |
| Progression | `localStorage`, par navigateur | suit le compte Discord |
| Classements, historique | absents | présents |
| À déployer | tout **sauf** `api/` et `outils/` | tout |

> **Sans backend, ne mettez pas `api/` en ligne.** Un hébergeur statique sert
> les `.php` en texte brut : `api/config.php` livrerait le mot de passe de la
> base et le secret Discord à qui demande l'URL. Le site détecte l'absence
> d'API tout seul et masque proprement la couche compte.

### Sur un VPS, avec Docker

`deploiement/` contient tout ce qu'il faut : trois conteneurs — Caddy qui
sert le site et obtient son certificat tout seul, PHP-FPM pour l'API,
MariaDB pour les comptes. Rien d'autre n'est installé sur la machine, et
le dépôt est monté en lecture seule : une mise à jour se fait en
remplaçant les fichiers, sans rien reconstruire.

```bash
cd deploiement && cp .env.exemple .env && nano .env && docker compose up -d
```

Les étapes détaillées sont dans `deploiement/LISEZMOI.md`.

Un point à connaître : **les trois `.htaccess` du projet ne servent à
rien hors d'Apache.** Le `Caddyfile` reporte leurs règles — refus de
`api/config.php`, de `api/_*.php` et de `outils/`, en-têtes de sécurité,
page 404, durées de cache. Si vous montez une autre pile, reportez-les
aussi : sans elles, `api/config.php` livre le mot de passe de la base le
jour où PHP tombe.

## Voir le site en local

```bash
demarrer.cmd
```

Le script cherche PHP (celui du système, sinon la pile portable dans
`%LOCALAPPDATA%\bureau-des-primes-dev`), démarre la base locale si elle est
installée, sert le site sur le port 8080 et ouvre le navigateur. Sans PHP il
retombe sur Python en mode statique — le jeu marche, la couche compte reste
masquée.

**Un double-clic sur `index.html` ne suffit pas** : ouvert en `file://`, le
navigateur refuse de lire `assets/data/<univers>.json` et la page affiche
« Dossier inaccessible ».

## Mise en ligne

### 1. Les fichiers

Tout déposer à la racine du domaine. Aucune étape de build. Le site est prévu
pour vivre **à la racine** : dans un sous-dossier, `index.html` fonctionne tel
quel (chemins relatifs) mais `404.html` non — ses chemins sont absolus, parce
qu'elle doit répondre sous n'importe quelle URL ratée.

`.htaccess` (fourni) branche la page 404, coupe le listing de répertoire et
interdit l'accès à `api/config.php`, aux fichiers internes `api/_*.php` et à
`outils/`. **Sous nginx il est ignoré** : il faut transposer ces règles dans la
configuration du serveur, sans quoi la configuration est lisible publiquement.

### 2. Le domaine de démonstration

`bureau-des-primes.example` apparaît dans `index.html` (canonical, Open Graph,
JSON-LD), `robots.txt`, `sitemap.xml` et `api/config.exemple.php`. Tant qu'il
n'est pas remplacé, les aperçus de partage et le référencement pointent dans
le vide.

```bash
grep -rn "bureau-des-primes.example" .
```

### 3. La base MySQL

Créer une base en **utf8mb4** dans le panneau de l'hébergeur, puis :

```bash
cp api/config.exemple.php api/config.php   # et remplir la section « bd »
php outils/migrer.php
```

Sans accès SSH, coller `api/schema.sql` dans phpMyAdmin : c'est le même SQL,
ré-exécutable sans risque.

`php outils/migrer.php --etat` affiche le contenu des tables et les cibles du
jour ; `--recalculer` refait les compteurs de `series` à partir de `parties`.

### 4. L'application Discord

Sur <https://discord.com/developers/applications> :

1. **New Application**, lui donner un nom — c'est celui que verront les
   joueurs sur l'écran d'autorisation.
2. Onglet **OAuth2** : copier *Client ID* et *Client Secret* dans
   `api/config.php`.
3. Toujours dans **OAuth2**, section *Redirects*, ajouter **exactement**
   l'URL de `redirection` de `config.php` — au caractère près, `https`
   compris. Une différence ici est la cause n° 1 des échecs de connexion.
4. Renseigner `accueil` avec l'adresse de la page de jeu.

`connexion.php` accepte un paramètre `retour` : le chemin d'où part la
connexion, pour y ramener le joueur au lieu du lobby. Il ne voyage pas dans
l'URL de retour — Discord ne relaie que `state` — mais reste en session le
temps du tour. Seul un chemin absolu de ce site est accepté : `//ailleurs`,
`https://ailleurs` ou un chemin relatif sont ignorés et ramènent au lobby,
sans quoi `connexion.php` deviendrait une redirection ouverte portant notre
domaine.

Portée demandée : `identify` seulement. Ni adresse e-mail, ni liste de
serveurs. Tant que `client_id` est vide, le bouton de connexion ne s'affiche
pas du tout.

```bash
php outils/verifier-discord.php
```

Le diagnostic contrôle les identifiants, la cohérence entre l'URL de
redirection et l'adresse du site, la base, les extensions PHP, et affiche
la ligne exacte à coller dans *Redirects*. Il sort en code 1 tant qu'un
point bloque.

> **Pile portable : le magasin de certificats.** Un PHP portable arrive sans
> `curl.cainfo`. cURL refuse alors de vérifier le certificat de `discord.com`,
> l'échange du code échoue, et le joueur revient déconnecté sans message — la
> connexion semble « se remettre à zéro » à chaque essai. Le remède est de
> nommer un magasin dans `php.ini` :
>
> ```ini
> curl.cainfo    = "…/php/cacert.pem"
> openssl.cafile = "…/php/cacert.pem"
> ```
>
> Git for Windows en fournit un dans `mingw64/etc/ssl/certs/ca-bundle.crt`.
> `verifier-discord.php` teste désormais la joignabilité TLS et nomme ce cas.

**`api/config.php` n'est jamais versionné** (`.gitignore`). Les valeurs
peuvent aussi venir de variables d'environnement (`BDP_BD_PASS`,
`BDP_DISCORD_SECRET`…), qui l'emportent sur le fichier.

## Arborescence

```
index.html              le lobby
one-piece.html          Bureau des Primes
naruto.html             Bingo Book
bleach.html             Registre des Âmes
inazuma.html            Feuille de Match
minecraft.html          Journal de Bord
pokemon.html            Fiche Pokédex
404.html                avis introuvable
.htaccess               404, en-têtes, protection des fichiers sensibles
favicon.ico  site.webmanifest  robots.txt  sitemap.xml
demarrer.cmd            aperçu local

assets/
  css/style.css         toute la mise en forme, thème clair et sombre
  js/app.js             le moteur de jeu (module ES)
  js/compte.js          comptes, classements, historique — facultatif
  js/univers.js         la description des quatre registres
  js/lobby.js           la page d'accueil
  js/theme.js           le choix clair / sombre
  data/one-piece.json   167 personnages, 11 sagas
  data/naruto.json      104 personnages, 14 arcs, 7 rangs
  data/bleach.json      124 personnages, 7 arcs
  data/inazuma.json     103 joueurs, 3 saisons
  data/minecraft.json   219 entrées (64 créatures, 155 blocs et objets)
  data/pokemon.json     386 Pokémon, 3 générations
  img/photos/one-piece/ les portraits, <slug>.jpg
  img/photos/naruto/
  img/photos/inazuma/
  img/photos/pokemon/
  img/                  favicon SVG, icônes PWA, image de partage

api/                    ne pas déployer sur un hôte statique
  config.exemple.php    modèle à copier en config.php
  schema.sql            les quatre tables
  _amorce.php           config, PDO, sessions, réponses JSON
  _jeu.php              règles du jeu côté serveur, validation
  _stats.php            écriture des parties, calcul des séries
  _discord.php          OAuth2
  connexion.php  retour.php  deconnexion.php
  moi.php  partie.php  importer.php  classement.php  historique.php

outils/                 lancés en ligne de commande, jamais servis
  commun.py                 le slug d'un portrait, partagé par les outils
  migrer.php                schéma et entretien de la base
  telecharger-portraits.py  portraits manquants  [one-piece|naruto|bleach|pokemon|inazuma|minecraft]
  construire-pokedex.py     le Pokédex national complet, depuis PokéAPI
  construire-minecraft.py   blocs et objets, depuis fr.minecraft.wiki
  minecraft-noms-en.json    nom anglais de chaque bloc, pour ses visuels
  renommer.py               renomme fiches et valeurs, portraits compris
  verifier-registres.py     controle des registres avant mise en ligne
  verifier-discord.php      diagnostic de la connexion Discord
  generer-visuels.py        favicon, icônes, image de partage
  domaine.py                remplace le domaine dans toutes les pages
```

## Comment ça tient ensemble

Le moteur de jeu ne connaît ni Discord ni la base. Il annonce ce qu'il fait,
et `compte.js` écoute — ou pas. Le raccord tient en trois points :

| | |
|---|---|
| `bdp:mode` | événement, le joueur a changé de mode |
| `bdp:victoire` | événement, un avis vient d'être résolu |
| `window.BDP` | `toast()` et `partiesLocales()`, en lecture |

Si `api/moi.php` ne répond pas du JSON, `compte.js` masque ses trois
conteneurs et se tait. C'est la même page qui sert dans les deux déploiements.

### Le plateau

Chaque proposition est une **carte** : un bandeau avec le portrait, le nom et
le numéro d'avis, puis les huit attributs comparés, chacun portant son
intitulé et sa couleur. Trois paliers :

**Une fiche par ligne**, la plus récente en haut. Les attributs se
répartissent sur quatre colonnes, deux sous 640 px.

| largeur | fiches de front | attributs de front |
|---|---|---|
| ≥ 640 px | 1 | 4 |
| < 640 px | 1 | 2 |

Deux fiches de front tenaient sur moitié moins de hauteur, et c'est ainsi
que le plateau a d'abord été fait. Deux défauts l'ont emporté : la lecture
sautait de droite à gauche — on lisait la fiche 02 puis la 01 sur la même
ligne — et deux cartes voisines n'avaient pas la même hauteur dès qu'une
liste était vide d'un côté et pleine de l'autre, si bien que leurs
attributs ne se faisaient plus face. En colonne, l'ordre est celui du
dépouillement et chaque attribut tombe exactement sous le même.

Il y avait un tableau à huit colonnes avant les cartes. Il imposait un
défilement horizontal permanent sur téléphone, et sur grand écran il
éloignait la ligne d'en-tête des valeurs qu'elle nommait.

Contrepartie assumée : une carte occupe plus de place qu'une ligne de
tableau, et la colonne unique ne la rattrape pas.

Un attribut de type `ensemble` — haki, natures de chakra, types — prend
toute la rangée et écrit ses valeurs en toutes lettres, chacune dans sa
teinte. Il l'occupe entière parce qu'un ninja peut porter dix natures de
chakra : sur deux colonnes, la liste débordait de la fiche. Les abrégés de
trois lettres qui la précédaient — « ARM », « FÛT » — demandaient de
deviner ce qu'on lisait.

Chaque valeur peut porter une icône, posée **au-dessus** du nom. Empilée,
la pastille est bien plus étroite qu'en ligne — les dix natures de chakra
de Naruto tiennent alors sur une seule ligne.

Deux sources, dans cet ordre :

1. `assets/img/icones/<univers>/<slug>.png` si le fichier existe — les
   icônes officielles, récupérées par `outils/telecharger-icones.py` ;
2. sinon le glyphe déclaré dans `icones` (`univers.js`) : le kanji de la
   nature, ou un SVG dessiné.

Le repli n'est pas décoratif : une image absente est retirée à l'erreur et
le glyphe reparaît, exactement comme pour un portrait manquant. C'est ce
qui fait tenir Enton, absent du tableau du wiki, et le haki, qui n'a aucun
symbole dans l'œuvre — plaque, œil et couronne y sont dessinés ici.

**La largeur de la cellule se mesure, fiche par fiche.** Après rendu, le
moteur additionne la largeur réelle des pastilles et prend le plus petit
nombre de colonnes qui les tient sur une ligne. Les pastilles ne se
compriment pas — elles passent à la ligne — donc leur largeur mesurée est
leur largeur vraie.

Deux approches ont été écartées avant. Sur toute la rangée, trois
pastilles de haki laissaient un bandeau vide de 900 px. Calculée sur le
maximum du registre, la largeur donnait deux colonnes à toutes les fiches
Naruto, alors qu'Itachi et ses cinq natures tiennent dans une. La mesure
est refaite au redimensionnement de la fenêtre.

`teintesValeurs` accepte `[teinte, saturation]` en plus d'une teinte seule :
les types ternes — Normal, Acier, Ténèbres — comme le Yin et le Yang, noir
et blanc sur le tableau du wiki, seraient criards à la saturation par
défaut.

Les teintes viennent de `teintesValeurs`, dans `univers.js` : celles des
types Pokémon et des natures de chakra sont celles d'usage. La feuille de
style n'en reçoit que la teinte et choisit elle-même la clarté, pour rester
lisible dans les deux thèmes.

Les intitulés sont de vrais `<dt>` dans le document, pas des `::before` de
feuille de style : sans ligne d'en-tête, ce sont eux qui portent le sens, y
compris pour un lecteur d'écran.

### Le classement

Deux axes indépendants, tous deux servis par `api/classement.php`.

Le **périmètre** dit sur quoi on se compare :

| | |
|---|---|
| `mode` | un mode d'un registre — le duel le plus serré |
| `jeu` | tous les modes d'un registre |
| `global` | les quatre registres réunis |

La **portée** dit ce qu'on compare : `jour` (l'avis du jour), `serie` (les
séries en cours) et `parties` (le total d'avis résolus).

Une page de jeu ouvre sur son mode et propose d'élargir ; le lobby ouvre sur
le global et propose un onglet par registre. Les deux affichent le même
composant, `rendreClassement()` dans `compte.js`.

Au périmètre `mode` il n'y a qu'un avis par jour : « le plus d'avis résolus »
vaut 1 pour tout le monde et le tri retombe de lui-même sur le nombre de
fiches versées. Une seule requête sert donc les trois périmètres — trois
requêtes séparées auraient fini par diverger. Dès qu'on élargit, le score
devient le nombre d'avis résolus et les fiches passent en valeur d'appoint,
affichée à côté : sans elle, quatre joueurs à « 1 avis » sembleraient
à égalité alors que le classement les a bien départagés.

Une série se compte par registre et par mode. Sur un périmètre large on
retient **la plus longue**, jamais leur somme : additionner des séries
parallèles ne décrirait aucune assiduité réelle.

L'unité affichée (`fiche`, `avis`, `jour`) vient de la réponse du serveur.
C'est lui qui a trié, lui seul sait ce qu'il a compté.

### Le thème

La feuille de style décrit trois états : la palette claire sur `:root`, la
sombre sous `prefers-color-scheme`, et la même sombre sous
`:root[data-theme="dark"]` pour le forçage. `assets/js/theme.js` ajoute le
choix manuel — **Système, Clair, Sombre** — dans le bandeau d'état, et le
retient dans `localStorage` sous la clé `bdp.theme`.

Trois états et non deux : sans « Système », un visiteur qui a touché au
réglage ne pourrait plus revenir au comportement par défaut, et son choix
survivrait à un changement de préférence du système.

Chaque page relit ce choix dans un script en clair placé **avant la feuille
de style** : posé depuis le module, différé, la page clignoterait dans
l'autre camp avant de basculer. C'est la seule ligne de JavaScript en clair
du site, et c'est pour ça.

Sans JavaScript, les trois boutons restent masqués et la page suit le
système, comme avant.

### Ce que compare chaque registre

Les huit attributs d'un registre vivent dans `assets/js/univers.js`, et le
moteur ne connaît qu'eux. Feuille de Match compare : genre, élément, poste,
pays, supertechnique, **équipes**, **apparence**, 1re saison.

Deux d'entre eux sont des listes, et c'est voulu.

**Les équipes.** Un joueur en traverse plusieurs au fil des saisons. Avec une
seule valeur, le gardien du Chaos se retrouvait rangé sous « Diamond Dust »
— l'équipe que son infobox cite en premier — et devenait introuvable quand
le jeu annonçait « Chaos ». Le registre garde donc toutes ses équipes, mais
seulement celles de l'anime : le wiki en liste soixante-douze, exclusivités
de jeux comprises, et une fiche qui en afficherait dix-sept ne dirait plus
rien. La liste retenue est écrite en clair dans le composeur.

**L'apparence.** Couleur de cheveux et signes distinctifs — lunettes,
casquette, bandeau, cicatrice. Elle est extraite de la section « Apparence »
du wiki avec un vocabulaire fermé : le wiki décrit les teintes en noms de
pigments (« lapis-lazuli », « sépia », « mordoré »), qui retombent tous sur
une famille de couleur. Une pastille « Cheveux bruns » se recoupe d'une fiche
à l'autre, « Cheveux cacao » non. Cinq joueurs n'ont aucun trait relevé et
affichent « Rien de notable » — mieux vaut un vide honnête qu'un trait
inventé.

Le mode Supertechnique, lui, ne tire que parmi les **68 joueurs dont la
technique ne désigne qu'eux**. Dix-sept techniques sont partagées par deux
joueurs ; elles restent affichées comme attribut, mais un indice à deux
réponses valables casserait le mode. C'est le champ `techniqueSeul` qui porte
cette restriction, et le bassin du mode le lit.

#### Minecraft, le registre qui ne se scrape pas

Les quatre premiers registres viennent d'un wiki. Le cinquième non : le wiki
Minecraft francophone donne des points de vie en « 15 – 30 », en
« Gros : 16 | Moyen : 14 », voire en « ;Version Java :10 », et son champ
`image` contient ce qui traîne — une capture de village pour l'abeille, un
inventaire pour l'âne, une vignette de Creeper pour le cube de magma.

La table des 64 créatures est donc écrite à la main dans le composeur, et le
wiki sert de **contrôle** : le composeur compare ses points de vie aux siens
et signale les écarts. Il en reste un, assumé — le wiki donne 80 PV au
Dragon de l'End, qui en a 200.

Les portraits, eux, viennent du wiki **anglophone** : il publie un rendu par
créature, sur fond transparent, et `File:<Nom>.png` y redirige vers la
dernière version. D'où la table des noms anglais dans le téléchargeur, et un
cadrage « entier » plutôt que le carré serré des portraits de personnages —
le dragon est large et plat, le Blaze haut et étroit, les rogner par le haut
leur coupait la tête.

### Le tirage du jour

`hash(date + "::" + mode) % taille du bassin`, avec une empreinte FNV-1a
32 bits. Tout le monde a le même pirate, et il change à **minuit, heure de
Paris** — la date calendaire du fuseau `Europe/Paris`, jamais un décompte
d'heures, sinon le basculement dériverait à chaque changement d'heure.
`api/_jeu.php` refait exactement le même calcul que `assets/js/app.js` : c'est
ce qui permet au serveur de recalculer la cible de n'importe quelle date et
donc de vérifier une partie avant de l'écrire. **Toucher au tirage d'un côté
sans l'autre casse silencieusement l'enregistrement des parties.**

### Ce que le serveur vérifie, et ce qu'il ne peut pas

Avant d'écrire une partie, le serveur contrôle le mode, la date, l'existence
de chaque personnage dans le bassin du mode, l'absence de doublon, et que la
dernière fiche versée est bien la cible du jour. Un avis déjà résolu ne peut
pas être rejoué : le premier résultat reste.

**Limite assumée :** le navigateur calcule le tirage lui-même, donc il connaît
la réponse. Ces contrôles écartent les envois malformés, rejoués ou hors
délai, pas un joueur qui forgerait sciemment une partie parfaite depuis la
console. Rendre le classement infalsifiable demanderait de déplacer le moteur
entièrement côté serveur — le client demanderait l'énoncé, enverrait chaque
proposition et recevrait la comparaison. C'est faisable, mais c'est une autre
architecture : le jeu ne fonctionnerait plus sans backend.

## Modifier le contenu

**Ajouter un personnage** : une entrée dans `assets/data/<univers>.json`.
Les champs `nom`, `genre`, `equipage`, `origine`, `fruit`, `fruitDetail`,
`haki`, `prime`, `taille`, `saga`, `chapitre`, `espece`, `statut` servent au
mode Classique ; `epithete`, `fruitNom` et `fruitNomEn` alimentent les trois
autres modes. `prime: null` signifie « aucune prime connue ». Le compteur du
pied de page se met à jour tout seul.

`primeEmetteur` dit qui a émis l'avis. `null` vaut Gouvernement Mondial, le
cas ordinaire. `"Cross Guild"` couvre les primes que Buggy, Crocodile et
Mihawk ont mises sur des officiers de la Marine — huit à ce jour, d'Akainu à
Helmeppo. L'affiche finale change alors sa mention de bas de page : créditer
le Gouvernement Mondial d'un avis lancé contre ses propres amiraux serait un
contresens. Le champ ne se voit nulle part ailleurs, pour ne pas donner
d'indice supplémentaire en mode Prime.

Modifier le registre change aussi les tirages passés. Les parties déjà en base
gardent la cible enregistrée ce jour-là, mais une reprise de progression
locale portant sur ces dates sera refusée : c'est voulu.

**Le portrait qui va avec** : `assets/img/photos/<univers>/<slug>.jpg`, où le slug est
le nom en minuscules, sans accents, mots séparés par des tirets — « Monkey D.
Luffy » donne `monkey-d-luffy.jpg`. Une image absente n'est pas une erreur :
le jeu retombe sur une plaque aux initiales, teintée par équipage.

```bash
python outils/telecharger-portraits.py one-piece
python outils/telecharger-portraits.py naruto
python outils/telecharger-portraits.py inazuma
python outils/telecharger-portraits.py pokemon
python outils/telecharger-portraits.py bleach
python outils/telecharger-portraits.py minecraft
```

L'option `--refaire` refait aussi les portraits déjà présents : c'est ce
qu'il faut quand le cadrage change, pas quand il manque une fiche.

Deux registres ne se tiennent pas à la main. `construire-pokedex.py` lit
les 1025 Pokémon sur PokéAPI ; `construire-minecraft.py` lit les blocs et
les objets sur `fr.minecraft.wiki`, en gardant les créatures telles
quelles. Les deux mettent leurs réponses en cache : une seconde exécution
ne redemande rien au réseau.

```bash
python outils/construire-pokedex.py
python outils/construire-minecraft.py --etat   # sans rien écrire
```

Les icônes de valeur se récupèrent à part :

```bash
python outils/telecharger-icones.py pokemon   # miniatures de type, jeu GO
python outils/telecharger-icones.py naruto    # natures découpées dans le tableau du wiki
```

Pour Pokémon, les variantes HOME, EV ou EB sont des bandeaux portant le
nom du type écrit dessus : inutilisables dans une pastille qui l'écrit
déjà en dessous. Celles de GO sont carrées. Pour Naruto, le wiki
francophone ne publie pas les natures une par une mais un tableau
unique : l'outil y découpe chaque octogone, en masquant les traits du
schéma qui débordent dans la boîte de découpe.

L'outil parcourt le registre et ne télécharge que ce qui manque. Pour un
personnage qu'il ne connaît pas, il cherche la page sur le wiki, garde les
images dont le nom contient « Infobox », et note les candidates : l'anime
avant le manga, le format portrait avant le panoramique, l'après-ellipse
avant l'avant-ellipse. Il retombe sur l'image principale de la page si
aucune infobox ne convient.

C'est une heuristique : **regardez les images obtenues** après un gros ajout.
Un portrait manifestement faux se règle en supprimant le fichier — la plaque
aux initiales reprend la place — ou en ajoutant l'URL à la main dans la carte
`URLS` du script, qui a toujours le dernier mot.

## Deux choses à savoir

- `EPOCH` (`assets/js/app.js` et `api/_jeu.php`) fixe l'origine de la
  numérotation des avis au 1ᵉʳ janvier 2026. C'est de la cosmétique : le
  tirage dépend de la date, pas du numéro.
- Les polices viennent de Google Fonts. Hors ligne, la page reste lisible :
  les piles de repli sont déclarées dans `style.css`.

## Crédits

Projet de fan, sans lien avec Eiichiro Oda, Shueisha ou Toei Animation.
Données vérifiées sur le [One Piece Wiki](https://onepiece.fandom.com/fr/wiki/Wiki_One_Piece).
Les portraits appartiennent à leurs ayants droit et sont repris ici à titre
d'illustration.
