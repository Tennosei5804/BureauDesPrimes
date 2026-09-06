# -*- coding: utf-8 -*-
"""Construit assets/data/pokemon.json a partir de PokeAPI.

    py outils/construire-pokedex.py            # tout le Pokedex national
    py outils/construire-pokedex.py --jusqu 151
    py outils/construire-pokedex.py --sans-formes
    py outils/construire-pokedex.py --gigamax

Les 1025 entrees du Pokedex national, plus les formes alternatives qui
font vraiment un autre Pokemon : regionales, Mega-Evolutions et
Primo-Resurgences. Les formes Gigamax restent dehors par defaut — elles
ne changent que la taille — et « --gigamax » les fait entrer.

PokeAPI ne sert rien en gros : il faut deux appels par espece, plus les
chaines d'evolution et le nom francais de chaque talent. Environ 2 900
requetes au total. Tout est donc mis en cache sur disque : une seconde
execution ne redemande rien au reseau, et une coupure se reprend ou elle
s'est arretee.

L'API refuse la requete sans en-tete « User-Agent » : elle repond 403,
ce qui ressemble a s'y meprendre a un blocage reseau.
"""

import argparse
import colorsys
import json
import os
import sys
import time
import urllib.request

import requests

try:
    from PIL import Image
except ImportError:          # la couleur des formes sera simplement heritee
    Image = None

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, "assets", "data", "pokemon.json")
CACHE = os.environ.get("BDP_CACHE") or os.path.join(
    os.environ.get("TEMP", "/tmp"), "bdp-pokeapi")

API = "https://pokeapi.co/api/v2/"
DERNIER = 1025           # Pecharunt, dernier du Pokedex national a ce jour

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "BureauDesPrimes/1.0 (projet de fan)"

TYPES = {
    "normal": "Normal", "fire": "Feu", "water": "Eau", "grass": "Plante",
    "electric": "Électrik", "ice": "Glace", "fighting": "Combat",
    "poison": "Poison", "ground": "Sol", "flying": "Vol", "psychic": "Psy",
    "bug": "Insecte", "rock": "Roche", "ghost": "Spectre", "dragon": "Dragon",
    "dark": "Ténèbres", "steel": "Acier", "fairy": "Fée",
}

COULEURS = {
    "black": "Noir", "blue": "Bleu", "brown": "Brun", "gray": "Gris",
    "green": "Vert", "pink": "Rose", "purple": "Violet", "red": "Rouge",
    "white": "Blanc", "yellow": "Jaune",
}

GENERATIONS = {
    "generation-i": "Génération I", "generation-ii": "Génération II",
    "generation-iii": "Génération III", "generation-iv": "Génération IV",
    "generation-v": "Génération V", "generation-vi": "Génération VI",
    "generation-vii": "Génération VII", "generation-viii": "Génération VIII",
    "generation-ix": "Génération IX",
}

ECHELLE_GENERATIONS = [GENERATIONS["generation-%s" % r] for r in
                       ("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix")]

# Le stade se compte a partir de un : Bulbizarre est au stade 1,
# Herbizarre au stade 2, Florizarre au stade 3. « Base » n'etait pas un
# stade mais une etiquette de jeu de cartes.
ECHELLE_STADES = ["Stade 1", "Stade 2", "Stade 3"]


def fichier_cache(url):
    nom = url[len(API):].strip("/").replace("/", "_") or "racine"
    return os.path.join(CACHE, nom + ".json")


def get(url):
    """Une ressource de l'API, du cache si elle y est deja."""
    cible = fichier_cache(url)
    if os.path.exists(cible):
        with open(cible, "r", encoding="utf-8") as f:
            return json.load(f)
    for essai in range(5):
        try:
            r = SESSION.get(url, timeout=30)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            donnees = r.json()
            break
        except Exception as e:
            if essai == 4:
                raise
            # L'API accepte mal les rafales : on la laisse respirer.
            time.sleep(1.5 * (essai + 1))
            print("   reprise (%s) %s" % (type(e).__name__, url), file=sys.stderr)
    os.makedirs(CACHE, exist_ok=True)
    with open(cible, "w", encoding="utf-8") as f:
        json.dump(donnees, f)
    return donnees


def nom_fr(ressource, defaut=""):
    for n in ressource.get("names", []):
        if n["language"]["name"] == "fr":
            return n["name"]
    return defaut


def propre(texte):
    """Les textes du Pokedex arrivent avec les retours a la ligne de la
    boite de dialogue du jeu, et un tiret conditionnel invisible."""
    # Ecrits en echappement a dessein : colles tels quels, le tiret
    # conditionnel et le saut de page sont invisibles dans le fichier
    # et impossibles a relire.
    texte = texte.replace("\u00ad", "").replace("\f", " ")
    return " ".join(texte.split())


def description(espece):
    """La premiere entree francaise. L'ordre de l'API va du plus ancien
    au plus recent : la premiere est donc celle des jeux d'origine, la
    plus sobre, et c'est celle que le registre utilisait deja."""
    for e in espece.get("flavor_text_entries", []):
        if e["language"]["name"] == "fr":
            t = propre(e["flavor_text"])
            if t:
                return t
    return ""


def profondeur(chaine, nom_espece, niveau=1):
    """Le rang du Pokemon dans sa chaine d'evolution, a partir de 1."""
    if chaine["species"]["name"] == nom_espece:
        return niveau
    for suite in chaine.get("evolves_to", []):
        trouve = profondeur(suite, nom_espece, niveau + 1)
        if trouve:
            return trouve
    return 0


TALENTS_ABSENTS = set()
COULEURS_RELUES = []


def talents(fiche, cache_talents):
    """Les talents ordinaires, dans l'ordre des emplacements. Les talents
    caches restent dehors : ils ne sont pas annonces par le jeu, et le
    registre les excluait deja."""
    sortie = []
    for a in sorted(fiche["abilities"], key=lambda a: a["slot"]):
        if a["is_hidden"]:
            continue
        url = a["ability"]["url"]
        if url not in cache_talents:
            res = get(url)
            if res is None:
                # Un talent trop recent n'a pas toujours sa fiche : l'API
                # le nomme dans la variete mais rend 404 sur la ressource.
                # On garde alors sa cle, faute de traduction, plutot que
                # de faire tomber toute la construction pour un mot.
                TALENTS_ABSENTS.add(a["ability"]["name"])
                res = {}
            cache_talents[url] = nom_fr(
                res, a["ability"]["name"].replace("-", " ").title())
        sortie.append(cache_talents[url])
    return sortie


def statut(espece):
    if espece["is_mythical"]:
        return "Mythique"
    if espece["is_legendary"]:
        return "Légendaire"
    return "Commun"


# ------------------------------------------------------------------
# Les formes alternatives
#
# Le Pokedex national ne compte qu'une entree par espece, mais Raichu
# d'Alola n'est pas Raichu : ni les memes types, ni les memes stats, ni
# le meme talent. PokeAPI les publie comme des « varietes » de l'espece.
# On ne garde que celles qu'un joueur nommerait comme un autre Pokemon,
# et seulement quand quelque chose que le jeu compare change vraiment :
# les formes decoratives — les casquettes de Pikachu — ont les memes
# types, la meme taille et le meme total de stats, elles ne feraient que
# dedoubler des reponses.
#
# L'API ne publie la couleur, la categorie et le stade que par espece,
# jamais par forme. Le stade et la categorie s'heritent sans dommage.
# La couleur, elle, se voit : Goupix d'Alola annonce « Brun » comme
# Goupix alors qu'il est blanc. On la relit donc dans le rendu officiel,
# sous trois conditions strictes (voir couleur_de_forme).
# ------------------------------------------------------------------

SUFFIXES_REGIONAUX = ("-alola", "-galar", "-hisui", "-paldea")

# Les trois taureaux de Paldea nomment leur race apres la region : ce
# sont les seules formes regionales dont le nom ne finit pas par elle.
RACES_PALDEA = ("-paldea-combat-breed", "-paldea-blaze-breed",
                "-paldea-aqua-breed")

FAMILLES_PAR_DEFAUT = ("regionale", "mega", "primal")

# ------------------------------------------------------------------
# La couleur d'une forme, relue dans son rendu
#
# La couleur du Pokedex est un classement editorial, pas une mesure : sur
# deux cents entrees de couleur connue, relire le rendu n'en retrouve que
# 58 %. Elle ne peut donc pas servir de source. Elle sert d'ecart, sous
# trois conditions, et c'est ce qui la rend sure :
#
#   1. seulement les formes regionales. C'est la que le corps change
#      vraiment de couleur ; une Mega garde la sienne et ajoute des
#      ornements, sur lesquels la lecture se trompe (elle voyait
#      Mega-Flagadoss vert alors qu'il est rose).
#   2. seulement si la methode retrouve deja la couleur connue de
#      l'entree de base. Si elle ne sait pas dire que Goupix est brun,
#      elle n'a rien de fiable a dire sur Goupix d'Alola.
#   3. seulement si la couleur lue occupe une large part du corps. En
#      dessous, c'est un detail qui l'emporte de justesse, pas la robe.
#
# Ce qui ne passe pas ces trois portes garde la couleur de l'espece.
# ------------------------------------------------------------------

FAMILLES_COULEUR = ("regionale",)
PART_MINIMALE = 0.55

# Les formes hors regionales dont la couleur du Pokedex differe vraiment
# de celle de l'espece. Ecrites a la main, et il le faut : aucune API ne
# les publie, et la relecture du rendu se trompe justement sur celles-la.
# Elle voit Mega-Dracaufeu X bleu — elle compte ses flammes — alors qu'il
# est noir. Une ligne ici vaut mieux qu'un seuil desserre qui ferait
# entrer vingt erreurs pour rattraper une omission.
COULEURS_A_LA_MAIN = {
    "charizard-mega-x": "Noir",
}

RENDUS = os.environ.get("BDP_RENDUS") or os.path.join(
    os.environ.get("TEMP", "/tmp"), "bdp-rendus")

GABARIT_RENDU = ("https://raw.githubusercontent.com/PokeAPI/sprites/master/"
                 "sprites/pokemon/other/%s/%d.png")


def rendu(ident):
    """Le rendu officiel d'une variete, sur fond transparent. Mis en
    cache comme les reponses de l'API ; un fichier vide note l'absence
    pour ne pas redemander a chaque construction."""
    os.makedirs(RENDUS, exist_ok=True)
    cible = os.path.join(RENDUS, "%d.png" % ident)
    if os.path.exists(cible):
        return cible if os.path.getsize(cible) else None
    for dossier in ("home", "official-artwork"):
        try:
            req = urllib.request.Request(
                GABARIT_RENDU % (dossier, ident),
                headers={"User-Agent": SESSION.headers["User-Agent"]})
            with urllib.request.urlopen(req, timeout=45) as r:
                brut = r.read()
            with open(cible, "wb") as f:
                f.write(brut)
            return cible
        except Exception:
            continue
    open(cible, "wb").close()
    return None


def categorie_couleur(r, g, b):
    """Le pixel rendu dans l'une des dix couleurs du Pokedex."""
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    t = h * 360
    # Le brun passe avant les gris : c'est un orange sombre ou terne, et
    # peu sature il tomberait sinon dans « Gris ».
    if 12 <= t < 50 and s >= 0.12 and v < 0.62:
        return "Brun"
    if s < 0.16:
        return "Blanc" if v > 0.74 else ("Noir" if v < 0.34 else "Gris")
    if v < 0.26:
        return "Noir"
    if t < 12 or t >= 340:
        return "Rose" if (v > 0.84 and s < 0.42) else "Rouge"
    if t < 50:
        # L'orange n'existe pas au Pokedex : sombre ou tres sature il va
        # au brun, clair et doux au rouge.
        return "Brun" if (v < 0.78 or s > 0.78) else "Rouge"
    if t < 72:
        return "Jaune"
    if t < 175:
        return "Vert"
    if t < 248:
        return "Bleu"
    if t < 302:
        return "Violet"
    return "Rose"


def profil_couleur(chemin):
    """La couleur majoritaire du corps et la part qu'elle occupe. Les
    pixels transparents ne comptent pas : le fond n'est pas le Pokemon."""
    im = Image.open(chemin).convert("RGBA")
    im.thumbnail((160, 160))
    compte, total = {}, 0
    for r, g, b, a in im.getdata():
        if a < 200:
            continue
        c = categorie_couleur(r, g, b)
        compte[c] = compte.get(c, 0) + 1
        total += 1
    if not total:
        return None, 0.0
    gagnant = max(compte, key=compte.get)
    return gagnant, compte[gagnant] / float(total)


def couleur_de_forme(base, ident, fam, cle=None):
    """La couleur retenue, ou None pour garder celle de l'espece."""
    if cle in COULEURS_A_LA_MAIN:
        return COULEURS_A_LA_MAIN[cle]
    if Image is None or fam not in FAMILLES_COULEUR:
        return None
    chemin_base = rendu(base["sprite"])
    chemin_forme = rendu(ident)
    if not chemin_base or not chemin_forme:
        return None
    vue_base, _ = profil_couleur(chemin_base)
    if vue_base != base["couleur"]:
        return None                      # porte 2 : methode non validee ici
    vue_forme, part = profil_couleur(chemin_forme)
    if vue_forme == vue_base or part < PART_MINIMALE:
        return None                      # porte 3 : rien de net a signaler
    return vue_forme


def famille(cle, forme):
    """La famille d'une variete, ou None si ce n'en est pas une."""
    # « is_mega » vient de l'API : il couvre aussi les Mega-Evolutions
    # ajoutees apres coup — celles de Mega Dimension, par exemple —
    # sans liste a tenir a jour ici.
    if forme.get("is_mega"):
        return "mega"
    if cle.endswith("-primal"):
        return "primal"
    if cle.endswith("-gmax"):
        return "gigamax"
    if cle.endswith(SUFFIXES_REGIONAUX) or cle.endswith(RACES_PALDEA):
        return "regionale"
    return None


def apostrophe(texte):
    """L'API ecrit « Raichu d’Alola » avec l'apostrophe typographique. Les
    six registres n'emploient que l'apostrophe droite — quarante-huit
    noms l'utilisent deja — et la recherche du lexique, qui ne retire
    que les accents, ne ferait pas le rapprochement entre les deux."""
    return texte.replace("\u2019", "'")


def nom_de_forme(forme, nom_base):
    """Le nom francais complet. L'API le porte dans « names »
    (« Raichu d'Alola », « Mega-Dracaufeu X ») ; « form_names » n'a que
    l'etiquette (« Forme d'Alola ») et ne sert que de repli."""
    plein = nom_fr(forme)
    if plein:
        return apostrophe(plein)
    for n in forme.get("form_names", []):
        if n["language"]["name"] == "fr":
            return apostrophe("%s (%s)" % (nom_base, n["name"]))
    return nom_base


def generation_de(forme, cache):
    """La generation qui a introduit la forme, pas celle de l'espece :
    Raichu est de premiere generation, Raichu d'Alola de septieme."""
    groupe = forme["version_group"]["name"]
    if groupe not in cache:
        vg = get(API + "version-group/%s/" % groupe)
        cache[groupe] = GENERATIONS.get(
            ((vg or {}).get("generation") or {}).get("name"), "")
    return cache[groupe]


def change(forme, base):
    """Vrai si la forme se joue autrement que l'entree de base. On ne
    regarde que ce que le jeu compare et que la forme peut porter : la
    couleur, la categorie et le stade appartiennent a l'espece et sont
    les memes pour toutes ses varietes."""
    return any(forme[c] != base[c]
               for c in ("types", "taille", "poids", "stats"))


def ajouter_formes(persos, espece, base, familles, cache_talents, cache_gen):
    """Pose derriere l'entree de base les formes retenues, dans l'ordre
    de l'API. Rend le nombre ajoute."""
    ajoutes = 0
    retenues = []
    for v in espece.get("varieties", []):
        if v["is_default"]:
            continue
        cle = v["pokemon"]["name"]
        forme = get(API + "pokemon-form/%s/" % cle)
        fam = famille(cle, forme) if forme else None
        if fam not in familles:
            continue
        variete = get(API + "pokemon/%s/" % cle)
        if not variete:
            continue
        types = [TYPES[t["type"]["name"]] for t in
                 sorted(variete["types"], key=lambda t: t["slot"])]
        liste_talents = talents(variete, cache_talents)
        fiche = dict(base)
        fiche.update({
            "nom": nom_de_forme(forme, base["nom"]),
            # Le numero reste celui de l'espece — c'est ainsi que le
            # Pokedex les compte — mais le rendu a son propre
            # identifiant, et c'est lui qui va chercher le portrait.
            "sprite": variete["id"],
            "types": types,
            "type1": types[0],
            "taille": variete["height"] * 10,
            "poids": round(variete["weight"] / 10.0, 1),
            "stats": sum(s["base_stat"] for s in variete["stats"]),
            "talent": liste_talents[0] if liste_talents else "",
            "talents": liste_talents,
            "generation": generation_de(forme, cache_gen) or base["generation"],
            # L'entree du Pokedex decrit l'espece, pas la forme. La
            # recopier donnerait deux reponses pour un meme indice, et
            # le mode Description est le seul ou aucun indice n'est
            # aujourd'hui partage : mieux vaut l'en sortir.
            "description": "",
        })
        relue = couleur_de_forme(base, variete["id"], fam, cle)
        if relue:
            fiche["couleur"] = relue
            COULEURS_RELUES.append((fiche["nom"], base["couleur"], relue))
        if not change(fiche, base):
            continue
        # Deux varietes peuvent ne differer que par ce que le jeu ne
        # compare pas : Mistigrix male et Mistigrix femelle ont la meme
        # Mega-Evolution, les trois formes de Nigirigon aussi. Le
        # registre ne retient qu'une entree de base par espece ; il ne
        # retient de meme qu'une de ces jumelles, la premiere.
        if any(not change(fiche, deja) for deja in retenues):
            continue
        retenues.append(fiche)
        persos.append(fiche)
        ajoutes += 1
    return ajoutes


def construire(jusqu, familles=FAMILLES_PAR_DEFAUT):
    cache_talents = {}
    cache_chaines = {}
    cache_gen = {}
    persos = []
    manques = []
    formes = 0

    for numero in range(1, jusqu + 1):
        espece = get(API + "pokemon-species/%d/" % numero)
        fiche = get(API + "pokemon/%d/" % numero)
        if not espece or not fiche:
            manques.append(numero)
            continue

        nom = nom_fr(espece, espece["name"].title())

        url_chaine = (espece.get("evolution_chain") or {}).get("url")
        rang = 1
        if url_chaine:
            if url_chaine not in cache_chaines:
                cache_chaines[url_chaine] = get(url_chaine)
            chaine = cache_chaines[url_chaine]
            rang = profondeur(chaine["chain"], espece["name"]) or 1
        rang = min(rang, len(ECHELLE_STADES))

        types = [TYPES[t["type"]["name"]] for t in
                 sorted(fiche["types"], key=lambda t: t["slot"])]
        liste_talents = talents(fiche, cache_talents)
        genre = ""
        for g in espece.get("genera", []):
            if g["language"]["name"] == "fr":
                genre = g["genus"]
                break

        base = {
            "nom": nom,
            "numero": numero,
            # Le rendu HOME s'adresse par l'identifiant de la variete,
            # pas par le numero du Pokedex : les deux coincident pour
            # une entree de base, jamais pour une forme.
            "sprite": fiche["id"],
            "types": types,
            "categorie": genre,
            "couleur": COULEURS.get(espece["color"]["name"], "Gris"),
            "stade": ECHELLE_STADES[rang - 1],
            "generation": GENERATIONS[espece["generation"]["name"]],
            "taille": fiche["height"] * 10,              # decimetres -> cm
            "poids": round(fiche["weight"] / 10.0, 1),   # hectogrammes -> kg
            "stats": sum(s["base_stat"] for s in fiche["stats"]),
            "talent": liste_talents[0] if liste_talents else "",
            "talents": liste_talents,
            "description": description(espece),
            "type1": types[0],
            "statut": statut(espece),
        }
        persos.append(base)
        formes += ajouter_formes(persos, espece, base, familles,
                                 cache_talents, cache_gen)

        if numero % 50 == 0 or numero == jusqu:
            print("  %4d / %d  %s" % (numero, jusqu, nom))

    if manques:
        print("absents de l'API :", manques, file=sys.stderr)
    if TALENTS_ABSENTS:
        print("talents sans fiche (nom anglais conserve) : %s"
              % ", ".join(sorted(TALENTS_ABSENTS)), file=sys.stderr)
    if COULEURS_RELUES:
        print("couleurs relues dans le rendu (%d) :" % len(COULEURS_RELUES))
        for nom, avant_c, apres in COULEURS_RELUES:
            print("   %-38s %-7s -> %s" % (nom, avant_c, apres))
    elif Image is None:
        print("Pillow absent : les formes gardent la couleur de l'espece.",
              file=sys.stderr)
    return persos, formes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jusqu", type=int, default=DERNIER,
                    help="dernier numero du Pokedex a construire")
    ap.add_argument("--sans-formes", action="store_true",
                    help="n'ecrire que les entrees de base du Pokedex")
    ap.add_argument("--gigamax", action="store_true",
                    help="ajouter aussi les formes Gigamax")
    args = ap.parse_args()

    familles = () if args.sans_formes else FAMILLES_PAR_DEFAUT
    if args.gigamax:
        familles += ("gigamax",)

    print("cache :", CACHE)
    persos, formes = construire(args.jusqu, familles)

    with open(SORTIE, "r", encoding="utf-8") as f:
        registre = json.load(f)

    registre["generations"] = ECHELLE_GENERATIONS[:]
    registre["stades"] = ECHELLE_STADES[:]
    registre["persos"] = persos

    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(registre, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print("%d fiches ecrites dans %s (dont %d formes alternatives)"
          % (len(persos), SORTIE, formes))


if __name__ == "__main__":
    main()
