# -*- coding: utf-8 -*-
"""Reconstruit la partie « blocs et objets » de assets/data/minecraft.json.

    py outils/construire-minecraft.py --etat   # ce que ca donnerait
    py outils/construire-minecraft.py          # ecrit le registre

La source est fr.minecraft.wiki. Trois choses en sont tirees, et rien
n'est devine quand le wiki le dit :

  - la liste elle-meme : Categorie:Bloc et Categorie:Objets, moins les
    pages qui ne sont pas du jeu (poisson d'avril, Education, Dungeons,
    homonymies, blocs supprimes) ;
  - la nature de chaque page : ses categories portent deja « Nourriture »,
    « Redstone », « Minerai », « Plante », « Ressources superposables »…
    Les deduire du nom francais aurait rate tout ce qui ne se nomme pas
    comme il se comporte ;
  - la premiere version, lue dans le tableau d'historique.

Restent deduits du nom : la famille (bois, pierre, fer…) et la dimension,
que le wiki ne range pas en categories.

Les creatures ne sont pas touchees : elles sont dans le meme registre,
verifiees a la main, et le wiki ne les liste pas dans ces categories.
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata

import requests

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, "assets", "data", "minecraft.json")
CACHE = os.environ.get("BDP_CACHE_MC") or os.path.join(
    os.environ.get("TEMP", "/tmp"), "bdp-mcwiki")

API = "https://fr.minecraft.wiki/api.php"
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "BureauDesPrimes/1.0 (projet de fan)"


# --- ce qu'on ne garde pas -------------------------------------------

CATEGORIES_EXCLUES = {
    "Poisson d'avril", "Blocs de poisson d'avril", "Objets de poisson d'avril",
    "Minecraft Education", "Blocs de Minecraft Education",
    "Objets de Minecraft Education", "Objets Minecraft Dungeons",
    "Objets Minecraft Earth", "Blocs supprimes", "Blocs supprimés",
    "Objets supprimés", "Objets de Minecraft, Le Film",
    "Blocs de Minecraft, Le Film", "Blocs Créatif ou commandes uniquement",
    "Fonctionnalités prévues", "Blocs prévus", "Objets prévus",
}

TITRES_EXCLUS = re.compile(
    r"\(homonymie\)|poisson d'avril|\(supprim|Minecraft Dungeons|"
    r"Minecraft Earth|Minecraft Education|Le Film|\bA Very Fine Item\b",
    re.I)

# Des familles ou le wiki tient une page par variante : vingt-deux
# disques de musique, vingt-cinq potions, vingt ornements d'armure,
# seize teintures. Toutes partagent les huit memes attributs — dans un
# jeu de deduction, ce sont des fiches qu'aucun indice ne separe, et le
# joueur qui repond « Disque cat » quand c'est « Disque stal » voit huit
# cases vertes et perd quand meme. On garde le concept, pas la couleur.
VARIANTES = re.compile(
    r"^(Disque [^(]|Potion d|Potion [ébp]|Ornement d|Teinture [a-zé]|"
    r"Wagonnet [àa]|Wagonnet avec|Wagonnet de|Wagonnet g|Wagonnet m|"
    r"Rails d|Dalle d|Dalle e|Escalier e|Muret )")

# Meme chose pour les finitions : « pierre noire », « pierre noire
# polie », « pierre noire taillee », « pierre noire taillee craquelee »
# sont quatre fiches et une seule matiere. La matiere reste, la finition
# part — c'est aussi le nom que le joueur donne au bloc.
FINITIONS = re.compile(
    r"\b(poli|polie|polies|taill[ée]e?s?|sculpt[ée]e?s?|craquel[ée]e?s?|"
    r"carrel[ée]e?s?|lisse|lisses|cisel[ée]e?s?|ciment[ée]e?s?)\s*$", re.I)

# Des pages de mecanique, pas des choses qu'on tient dans la main.
NOMS_EXCLUS = {
    "Air", "Air compactée", "Air vide", "Bloc", "Blocs", "Objets", "Objet",
    "Armes (homonymie)", "Armure", "Autre portail (bloc)",
    "Bloc de commande", "Bloc de structure", "Bloc de test",
    "Bloc de débogage", "Bloc de jigsaw", "Barrière (bloc technique)",
    "Lumière", "Vide", "Portail (bloc)", "Bordure du monde",
}


# --- la nature, lue dans les categories du wiki ------------------------
# Premiere regle qui s'applique, dans cet ordre : une page « Nourriture »
# qui porte aussi « Blocs fabriques » est d'abord de la nourriture.

CATEGORIE_PAR_WIKI = [
    ("Nourriture",          "Nourriture"),
    ("Outils",              "Outil"),
    ("Combat",              "Arme"),          # affine plus bas par le nom
    ("Minerai",             "Ressource"),
    ("Minerais",            "Ressource"),
    ("Redstone",            "Mécanisme"),
    ("Mécanismes",          "Mécanisme"),
    ("Stockage",            "Mécanisme"),
    ("Blocs utilitaires",   "Mécanisme"),
    ("Utilitaires",         "Mécanisme"),
    ("Transport",           "Mécanisme"),
    ("Plante",              "Végétal"),
    ("Plantes",             "Végétal"),
    ("Disques de musique",  "Décoration"),
    ("Sources de lumière",  "Décoration"),
    ("Dalles",              "Construction"),
    ("Escaliers",           "Construction"),
    ("Murets",              "Construction"),
    ("Blocs fabriqués",     "Construction"),
    ("Environnement",       "Construction"),
]

ARMURE = re.compile(r"\barmure|casque|plastron|jambi[eè]re|botte|bouclier|"
                    r"cotte de maille", re.I)

# --- la famille, deduite du nom ---------------------------------------
# L'ordre compte : « bloc de fer » est du fer avant d'etre un bloc.

FAMILLES = [
    # Un livre n'est pas range par sa matiere. Papier plus cuir le
    # rendrait organique, mais personne ne le rangerait avec la laine et
    # les carottes : c'est un objet, pas un materiau. Cette ligne passe
    # en premier pour attraper aussi « Livre et plume », que le motif
    # organique prendrait sinon par le mot « plume ».
    ("Autre",       r"\blivres?\b"),
    ("Netherite",   r"netherite"),
    ("Diamant",     r"diamant"),
    ("Émeraude",    r"émeraude"),
    ("Or",          r"\bor\b|dor[ée]|en or|d'or"),
    ("Fer",         r"\bfer\b|en fer|de fer|enclume|seau|chaudron|rails?\b|"
                    r"wagonnet|entonnoir|cisailles|boussole|montre|piston|"
                    r"distributeur|dropper|fabricateur|meule|"
                    r"paratonnerre|cha[îi]ne|barreaux|magn[ée]tite"),
    ("Cuivre",      r"cuivre"),
    ("Améthyste",   r"améthyste"),
    ("Quartz",      r"quartz"),
    ("Redstone",    r"redstone"),
    ("Lapis-lazuli", r"lapis"),
    ("Charbon",     r"charbon"),
    ("Verre",       r"verre|vitre|fiole|longue-vue|balise|lentille"),
    ("Bois",        r"bois|planche|b[uû]che|rondin|ch[êe]ne|bouleau|sapin|"
                    r"acajou|acacia|ceris|mangrove|bambou|[ée]carlate|tordu|"
                    r"champign|tronc|pancarte|[ée]chelle|[ée]chafaudage|"
                    r"tonneau|[ée]tabli|m[ée]tier [àa] tisser|pupitre|"
                    r"[ée]tag[èe]re|bateau|portillon|\bbol\b|b[âa]ton|"
                    r"cadre|coffre|biblioth[èe]que|composteur|ruche|"
                    r"jukebox|bo[îi]te|lit\b|pousse|arc\b|arbal[èe]te"),
    # Les pierres se separent par matiere plutot que de tomber toutes
    # dans « Pierre » : neuf basaltes, huit ardoises et six roches ignees
    # y partageaient les huit memes attributs, donc la meme fiche aux
    # yeux du joueur.
    ("Ardoise",     r"ardoise|deepslate"),
    ("Pierre noire", r"basalte|pierre noire|blackstone"),
    ("Grès",        r"gr[èe]s"),
    ("Prismarine",  r"prismarine"),
    ("Purpur",      r"purpur"),
    ("Brique",      r"brique"),
    ("Béton",       r"b[ée]ton"),
    # Meme garde que pour le sol : une pomme de terre cuite est un
    # aliment, pas un bloc de terre cuite.
    ("Terre cuite", r"(?<!pomme de )terre cuite"),
    ("Netherrack",  r"nether\s*rack|verrues du nether|nylium"),
    ("Roche ignée", r"granite|diorite|and[ée]site|tuf|calcite"),
    ("Pierre",      r"pierre|roche|obsidienne|dalle|escalier|muret"),
    # Le sol et l'eau gelee tombaient dans « Organique », devenu un
    # fourre-tout ou du sable voisinait avec la laine et les carottes.
    # Deux familles les recuperent, posees juste avant lui pour que les
    # matieres nommees plus haut gardent la main : « Terre cuite » reste
    # de la terre cuite, « Briques de terre crue » une brique, « Seau de
    # neige poudreuse » du fer.
    #
    # La garde sur « terre » n'est pas un detail : sans elle, une pomme
    # de terre serait rangee avec le gravier.
    # Le sculk est une matiere a lui seul, arrivee avec les profondeurs :
    # six blocs qui ne ressemblent a rien d'autre du jeu.
    ("Sculk",       r"sculk"),
    ("Glace et neige", r"\bneiges?\b|\bglaces?\b"),
    ("Terre et sable", r"\bsables?\b|gravier|argile|podzol|"
                       r"(?<!pomme de )\bterres?\b"),
    # L'equipement passe avant les matieres vivantes, et apres les
    # metaux : une pioche en fer reste du fer, une pioche tout court n'a
    # pas de matiere et c'est de l'equipement. La selle et le harnais y
    # vont malgre leur cuir — le joueur les range avec le barda, pas avec
    # la viande. L'arc et l'arbalete, eux, restent du bois : « Bois »
    # passe bien plus haut dans cette liste.
    ("Équipement",  r"pioche|hache|pelle|houe|\bépées?\b|masse|trident|"
                    r"fl[èe]che|bottes|casque|jambi[èe]res|plastron|"
                    r"bouclier|canne [àa] p[êe]che|pinceau|carquois|"
                    r"selle|harnais|laisse|\blances?\b|armure|[ée]lytres"),
    # Ce qui vient d'une bete. La ficelle y est : dans ce jeu, elle tombe
    # des araignees. Les limites de mot ne sont pas decoratives — sans
    # elles, « tortue » se lit dans « lianes tortueuses » et « oeuf »
    # dans « soufre ».
    ("Animal",      r"laine|cuir|\bos\b|plume|viande|poisson|morue|saumon|"
                    r"miel|cire|slime|\btoile|corde|ficelle|chair|steak|"
                    r"boeufs?\b|porc|poulet|mouton|lapin|\boeufs?\b|"
                    r"carapace|coquille|[ée]caille|membrane|larme|encre|"
                    r"corne|\btortues?\b|araign|shulker|ghast|phantom|"
                    r"blaze|nautile|tatou|\bt[êe]tes?\b|totem|nid|"
                    r"g[âa]teau"),
    # Ce qui pousse. Le papier vient de la canne a sucre, le livre non :
    # lui est parti dans « Autre » plus haut.
    ("Plante",      r"graine|fleur|feuille|herbe|papier|citrouille|melon|"
                    r"carotte|pomme|bl[ée]|betterave|sucre|cacao|algue|"
                    r"varech|mousse|racine|liane|vigne|champignon|"
                    r"myc[ée]lium|allium|az[ae]l|buisson|cactus|coquelicot|"
                    r"foug[èe]re|lilas|marguerite|muguet|n[ée]nuphar|"
                    r"past[èe]que|pivoine|rosier|\broses?\b|tournesol|"
                    r"tulipe|chorus|planturne|foliogoutte|p[ée]tales|"
                    r"\bplantes?\b|verrue|pousse|bambou|lichen|"
                    r"champilampe|paille|baies|soupe|cookie|pain|"
                    r"tige|liseron|s[èe]ve|gousse"),
]


# --- la dimension ------------------------------------------------------

MOTS_NETHER = re.compile(
    r"nether|blaze|ghast|magma|piglin|hoglin|wither|quartz|"
    r"[ée]carlate|tordu|basalte|pierre noire|blackstone|soul|[âa]me|"
    r"crimson|warped|glowstone|lumineuse|strider|ancient|antique", re.I)
MOTS_END = re.compile(
    r"\bend\b|\bl'end\b|ender|shulker|chorus|purpur|dragon|"
    r"obsidienne pleureuse", re.I)


# --- les versions ------------------------------------------------------
# Le tableau d'historique donne l'ere puis la version. L'echelle du jeu
# garde le niveau « majeure.mineure » : « Classique » disparait au profit
# des numeros reels, et les eres d'avant la 1.0 gardent leur prefixe,
# a1.2 et b1.8 etant les versions telles que le jeu les nommait.

# Le marqueur d'ere n'est pas un mot mais une etiquette libre : « java
# beta », « java alpha », « indev », « release », et cote Bedrock
# « pocket alpha », « bedrock ». On y cherche donc le mot, dans cet
# ordre — « pre-classique » contient « classique ». Une etiquette qu'on
# ne reconnait pas signale un autre tableau, donc une autre edition.
ERES = (
    ("pre-classique", 0), ("preclassique", 0), ("pre classique", 0),
    ("pre-classic", 0), ("preclassic", 0),
    ("infdev", 3), ("indev", 2),
    ("classique", 1), ("classic", 1),
    ("alpha", 4), ("beta", 5),
)

API_EN = "https://minecraft.wiki/api.php"
PREFIXE_ERE = {0: "0.0", 1: "0.0", 2: "0.0", 3: "0.0", 4: "a", 5: "b", 6: ""}


# Les concepts que le wiki traite en page de survol, sans infobox, mais
# que tout joueur nomme : une dalle est une dalle, quel que soit le bois.
def _concept(cat, fam, v, outil=""):
    return {"type": "Bloc", "categorie": cat, "famille": fam,
            "dimension": "Surface", "pv": None, "empilement": 64,
            "butin": [], "version": v, "deplacement": "", "apparition": "",
            "outil": outil, "renouvelable": "Oui", "estCreature": "",
            "estObjet": "Bloc", "lachePar": [], "estButin": "", "_en": ""}


CONCEPTS_A_LA_MAIN = {
    "Dalle":              _concept("Construction", "Pierre", "b1.3", "Pioche"),
    "Escalier":           _concept("Construction", "Pierre", "a1.0", "Pioche"),
    "Muret":              _concept("Construction", "Pierre", "b1.8", "Pioche"),
    "Bouton":             _concept("Mécanisme", "Pierre", "a1.0", "Pioche"),
    "Plaque de pression": _concept("Mécanisme", "Pierre", "a1.0", "Pioche"),
    "Porte":              _concept("Mécanisme", "Bois", "0.0", "Hache"),
    "Trappe":             _concept("Mécanisme", "Bois", "b1.6", "Hache"),
}


def sans_accent(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def fichier_cache(nom):
    return os.path.join(CACHE, sans_accent(nom).replace("/", "_")[:120] + ".json")


def api(**kw):
    kw.setdefault("format", "json")
    kw.setdefault("formatversion", "2")
    for essai in range(4):
        try:
            r = SESSION.get(API, params=kw, timeout=40)
            r.raise_for_status()
            return r.json()
        except Exception:
            if essai == 3:
                raise
            time.sleep(1.5 * (essai + 1))


def page_francaise(titre):
    """Le wikitexte d'une page de fr.minecraft.wiki hors des categories
    recoltees — les creatures, par exemple."""
    cible = os.path.join(CACHE, "fr_" + sans_accent(titre).replace("/", "_")[:110] + ".json")
    if os.path.exists(cible):
        with open(cible, "r", encoding="utf-8") as f:
            return json.load(f)
    texte = ""
    try:
        r = SESSION.get(API, params={
            "action": "query", "prop": "revisions", "rvprop": "content",
            "rvslots": "main", "titles": titre, "redirects": "1",
            "format": "json", "formatversion": "2"}, timeout=40)
        r.raise_for_status()
        pg = r.json()["query"]["pages"][0]
        texte = pg.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("content", "")
    except Exception as e:
        print("   page francaise illisible :", titre, e, file=sys.stderr)
    os.makedirs(CACHE, exist_ok=True)
    with open(cible, "w", encoding="utf-8") as f:
        json.dump(texte, f)
    time.sleep(0.15)
    return texte


def page_anglaise(titre):
    """Le wikitexte d'une page de minecraft.wiki, mis en cache."""
    cible = os.path.join(CACHE, "en_" + sans_accent(titre).replace("/", "_")[:110] + ".json")
    if os.path.exists(cible):
        with open(cible, "r", encoding="utf-8") as f:
            return json.load(f)
    texte = ""
    try:
        r = SESSION.get(API_EN, params={
            "action": "query", "prop": "revisions", "rvprop": "content",
            "rvslots": "main", "titles": titre, "redirects": "1",
            "format": "json", "formatversion": "2"}, timeout=40)
        r.raise_for_status()
        pg = r.json()["query"]["pages"][0]
        texte = pg.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("content", "")
    except Exception as e:
        print("   page anglaise illisible :", titre, e, file=sys.stderr)
    os.makedirs(CACHE, exist_ok=True)
    with open(cible, "w", encoding="utf-8") as f:
        json.dump(texte, f)
    time.sleep(0.15)
    return texte


def membres(cat):
    out, cont = [], {}
    while True:
        p = dict(action="query", list="categorymembers", cmtitle=cat,
                 cmlimit="max", cmtype="page")
        p.update(cont)
        r = api(**p)
        out += [x["title"] for x in r["query"]["categorymembers"]]
        if "continue" not in r:
            return out
        cont = r["continue"]


def recolter():
    """Titres, categories et wikitexte de toutes les pages, mis en cache."""
    cible = os.path.join(CACHE, "pages.json")
    if os.path.exists(cible):
        with open(cible, "r", encoding="utf-8") as f:
            return json.load(f)

    blocs = set(membres("Catégorie:Bloc"))
    objets = set(membres("Catégorie:Objets"))
    titres = sorted(blocs | objets)
    print("%d blocs, %d objets, %d pages" % (len(blocs), len(objets), len(titres)))

    pages = {}
    for i in range(0, len(titres), 20):
        lot = titres[i:i + 20]
        r = api(action="query", prop="revisions|categories", rvprop="content",
                rvslots="main", cllimit="max", titles="|".join(lot))
        for pg in r["query"]["pages"]:
            t = pg["title"]
            rev = pg.get("revisions", [{}])[0]
            pages.setdefault(t, {"cats": [], "texte": ""})
            pages[t]["texte"] = rev.get("slots", {}).get("main", {}).get("content", "")
            pages[t]["cats"] += [c["title"].replace("Catégorie:", "")
                                 for c in pg.get("categories", [])]
        cont = r.get("continue")
        while cont:
            p = dict(action="query", prop="revisions|categories", rvprop="content",
                     rvslots="main", cllimit="max", titles="|".join(lot))
            p.update(cont)
            r = api(**p)
            for pg in r["query"]["pages"]:
                pages.setdefault(pg["title"], {"cats": [], "texte": ""})
                pages[pg["title"]]["cats"] += [
                    c["title"].replace("Catégorie:", "")
                    for c in pg.get("categories", [])]
            cont = r.get("continue")
        if (i // 20) % 10 == 0:
            print("   %d / %d" % (i, len(titres)))

    donnees = {"blocs": sorted(blocs), "objets": sorted(objets), "pages": pages}
    os.makedirs(CACHE, exist_ok=True)
    with open(cible, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False)
    return donnees


# --- lecture d'une page ------------------------------------------------

def champ_infobox(texte, nom):
    m = re.search(r"^\|\s*%s\s*=\s*(.*)$" % re.escape(nom), texte,
                  re.M | re.I)
    return m.group(1).strip() if m else ""


def empilement(texte, cats):
    """« superposable = Oui (64) » quand la page le dit, sinon la
    categorie d'entretien, qui ne donne que oui ou non."""
    v = champ_infobox(texte, "superposable")
    if v:
        m = re.search(r"\((\d+)\)", v)
        if m:
            return int(m.group(1))
        if re.match(r"\s*non", v, re.I):
            return 1
        return 64
    if "Ressources non superposables" in cats:
        return 1
    if "Ressources superposables" in cats:
        return 64
    return None


def empilement_ou_defaut(texte, cats, est_bloc):
    """Cent une pages portent « Superposabilite manquante » : le wiki ne
    sait pas. Un bloc s'empile par 64 sauf exception, et laisser le champ
    vide affichait « Inconnu » sur des blocs aussi communs que la roche."""
    n = empilement(texte, cats)
    if n is None and est_bloc:
        return 64
    return n


def renouvelable(texte, cats):
    v = champ_infobox(texte, "renouvelable")
    if v:
        return "Non" if re.match(r"\s*non", v, re.I) else "Oui"
    if "Ressources non renouvelables" in cats:
        return "Non"
    if "Ressources renouvelables" in cats:
        return "Oui"
    return ""


def titre_anglais(texte):
    """Le lien interlangue « [[en:...]] », present sur presque toutes les
    pages. Plus sur que la phrase d'introduction : c'est le titre exact de
    la page anglaise, donc de quoi aller y lire ce qui manque ici."""
    m = re.search(r"\[\[en:([^\]]+)\]\]", texte)
    return m.group(1).strip() if m else ""


def nom_anglais(texte):
    en = titre_anglais(texte)
    if en:
        return en
    m = re.search(r"nom anglais\s*:\s*'''''([^']+)'''''", texte)
    if not m:
        return ""
    # La phrase d'introduction ecrit le nom en minuscules ; le titre de
    # page, lui, porte des capitales initiales.
    return " ".join(w[:1].upper() + w[1:] for w in m.group(1).strip().split())


VERSION = re.compile(r"^(?:v)?(\d+(?:\.\d+)*[a-z]?(?:_\d+)?|rd-\d+)$", re.I)


def ere_de(etiquette):
    """Le rang de l'ere annoncee par une ligne du tableau, ou None quand
    l'etiquette n'est pas une ere de l'edition Java."""
    v = sans_accent(etiquette).strip()
    # Les autres editions d'abord : « pocket alpha » contient « alpha »
    # et « legacy console » a ses propres numeros. Les laisser passer
    # ramenait des « a0.14 » (Pocket) et des « 26.2 » (console) dans une
    # echelle qui ne parle que de l'edition Java.
    if re.search(r"pocket|bedrock|console|education|nintendo|"
                 r"playstation|xbox|switch|vita|china|earth|dungeons", v):
        return None
    # « java upcoming » : annonce, pas encore jouable. Une chose qui n'est
    # pas dans le jeu ne peut pas etre la reponse du jour.
    if "upcoming" in v or "a venir" in v:
        return None
    for mot, rang in ERES:
        if mot in v:
            return rang
    if not v or "java" in v or "release" in v:
        return 6
    return None


def premiere_version(texte):
    """L'ere et la version ou la chose apparait, lues dans l'historique.

    Seul le premier tableau compte, celui de l'edition Java. Les suivants
    — Bedrock, Pocket, console — renumerotent tout : sans cette coupure
    le registre recoltait des « 26.2 » et des « 20100629 », qui ne sont
    des versions de rien pour le joueur. On s'arrete donc des qu'une ere
    inconnue apparait : c'est la marque qu'on a change de tableau.
    """
    debut = re.search(r"==+\s*(?:Historique|History)\s*==+", texte)
    if not debut:
        return None
    seg = texte[debut.end():debut.end() + 30000]
    ere = None
    premiere = None
    premiere_ligne = None
    # « LigneHistorique » sur le wiki francophone, « HistoryLine » sur
    # l'anglophone, ou l'on va chercher ce que le premier ne dit pas.
    for m in re.finditer(r"\{\{(?:LigneHistorique|HistoryLine)\|(\|)?([^|}]*)(\|)?", seg):
        marque, valeur = m.group(1), m.group(2).strip()
        if not marque:
            # une ligne d'ere : « java beta », « indev », « release »…
            rang = ere_de(valeur)
            if rang is None:
                break                    # on a quitte le tableau Java
            ere = rang
            continue
        if ere is None:
            ere = 6
        est_version = bool(VERSION.match(valeur))
        suite = seg[m.end():m.end() + 260]
        # La ligne qui dit « Ajout » fait foi, meme quand elle est datee
        # plutot que numerotee : le coffre est « ajoute » un 24 janvier
        # 2010, sous l'ere Indev. Ne regarder que les lignes numerotees
        # faisait remonter la premiere retouche venue — le coffre datait
        # de la beta 1.8, sept mois apres son arrivee dans le jeu.
        if re.search(r"\bajout", suite, re.I):
            return (ere, valeur if est_version else "")
        if premiere is None and est_version:
            premiere = (ere, valeur)
        if premiere_ligne is None:
            premiere_ligne = (ere, valeur if est_version else "")
    if premiere:
        return premiere
    if premiere_ligne:
        return premiere_ligne
    # Une ere sans numero : « ajout un Seecret Friday », une date d'Indev.
    # L'ere seule situe deja la chose dans le temps.
    return (ere, "") if ere is not None else None


def etiquette_version(ere, brut):
    """« b1.8 », « a1.2 », « 1.16 », « 0.0 » : le niveau majeure.mineure,
    prefixe par l'ere quand elle precede la 1.0."""
    if ere <= 3 or brut.startswith("rd-"):
        return "0.0"
    if not brut:
        # L'ere sans numero : on la place a son premier palier.
        return {4: "a1.0", 5: "b1.0"}.get(ere, "")
    # Le wiki ecrit parfois « v1.0.1 » : le v est une convention d'ecriture,
    # pas un morceau du numero, et le garder donnait des « av1.0 ».
    bouts = re.split(r"[._]", brut.lstrip("vV"))
    court = ".".join(bouts[:2]) if len(bouts) > 1 else bouts[0]
    court = re.sub(r"[a-z]+$", "", court)
    return PREFIXE_ERE[ere] + court


def rang_version(etiq):
    """De quoi ranger l'echelle : alpha avant beta avant les versions."""
    if etiq == "0.0":
        return (0, 0, 0)
    if etiq.startswith("a"):
        groupe, reste = 1, etiq[1:]
    elif etiq.startswith("b"):
        groupe, reste = 2, etiq[1:]
    else:
        groupe, reste = 3, etiq
    bouts = (reste.split(".") + ["0"])[:2]
    try:
        return (groupe, int(bouts[0]), int(bouts[1]))
    except ValueError:
        return (groupe, 0, 0)


def categorie_de(nom, cats, est_bloc):
    for cat_wiki, valeur in CATEGORIE_PAR_WIKI:
        if cat_wiki in cats:
            if valeur == "Arme" and ARMURE.search(nom):
                return "Armure"
            return valeur
    return "Construction" if est_bloc else "Ressource"


# Les categories qui disent deja « equipement » en d'autres mots.
CATEGORIES_EQUIPEMENT = {"Outil", "Arme", "Armure"}


def famille_de(nom, categorie=None):
    """La famille d'une fiche. La categorie n'entre en jeu que pour un
    cas : une fiche rangee en Outil, Arme ou Armure n'a pas besoin d'une
    famille « Equipement » qui redit la meme chose. Le joueur y perdait
    un des huit attributs — deux cases pour un seul renseignement.
    Une pioche sans matiere n'a pas de matiere : elle va donc dans
    « Autre », et c'est la reponse honnete.

    Restent en « Equipement » les pieces de barda que la categorie ne
    trahit pas : la selle et le harnais sont des « Ressource », la laisse
    un « Mecanisme »."""
    n = sans_accent(nom)
    for famille, motif in FAMILLES:
        if re.search(sans_accent(motif), n):
            if famille == "Équipement" and categorie in CATEGORIES_EQUIPEMENT:
                continue          # on laisse la suite de la liste decider
            return famille
    return "Autre"


def dimension_de(nom, texte):
    tete = texte[:2500]
    if MOTS_END.search(nom) or re.search(r"\[\[End\]\]|dans l'\[\[End", tete):
        return "End"
    if MOTS_NETHER.search(nom) or re.search(r"\[\[Nether\]\]|dans le \[\[Nether", tete):
        return "Nether"
    return "Surface"


def outil_de(texte):
    v = champ_infobox(texte, "outil")
    if not v:
        return ""
    v = re.sub(r"\[\[|\]\]|\{\{|\}\}", "", v).split("|")[0].strip()
    for mot in ("Pioche", "Hache", "Pelle", "Houe", "Cisailles", "Épée"):
        if sans_accent(mot) in sans_accent(v):
            return mot
    if re.match(r"\s*aucun", v, re.I):
        return "Aucun"
    return ""


def construire():
    donnees = recolter()
    pages, blocs = donnees["pages"], set(donnees["blocs"])
    fiches, ignorees = [], []

    for titre in sorted(pages):
        p = pages[titre]
        cats = set(p["cats"])
        if (titre in NOMS_EXCLUS or TITRES_EXCLUS.search(titre)
                or cats & CATEGORIES_EXCLUES):
            ignorees.append(titre)
            continue
        texte = p["texte"]
        if not texte or texte.lstrip().upper().startswith("#REDIR"):
            ignorees.append(titre)
            continue
        # Une page sans infobox est une page de survol — « Dalle »,
        # « Minerai », « Plante », « Bloc solide » — pas une chose du jeu.
        # Les sept qui comptent quand meme sont reprises a la main.
        if "{{Infobox" not in texte and "{{infobox" not in texte:
            ignorees.append(titre)
            continue
        # Cinquante-deux dalles, quarante-six escaliers, trente-deux
        # murets : tous identiques a un materiau pres. Dans un jeu de
        # deduction ce sont cent trente fiches qu'aucun indice ne separe.
        # Le concept suffit, et il est ajoute a la main.
        if (cats & {"Dalles", "Escaliers", "Murets"}
                or VARIANTES.match(titre) or FINITIONS.search(titre)):
            ignorees.append(titre)
            continue

        est_bloc = titre in blocs
        v = premiere_version(texte)
        etiq = etiquette_version(*v) if v else ""
        cat = categorie_de(titre, cats, est_bloc)

        fiches.append({
            "nom": titre,
            "type": "Bloc" if est_bloc else "Objet",
            "categorie": cat,
            "famille": famille_de(titre, cat),
            "dimension": dimension_de(titre, texte),
            "pv": None,
            "empilement": empilement_ou_defaut(texte, cats, est_bloc),
            "butin": [],
            "version": etiq,
            "deplacement": "",
            "apparition": "",
            "outil": outil_de(texte),
            "renouvelable": renouvelable(texte, cats),
            "estCreature": "",
            "estObjet": "Bloc" if est_bloc else "Objet",
            "lachePar": [],
            "estButin": "",
            "_en": nom_anglais(texte),
        })

    for nom, gabarit in CONCEPTS_A_LA_MAIN.items():
        fiches.append(dict(gabarit, nom=nom))

    # Le wiki francophone laisse des sections d'historique vides — un
    # « {{...}} » en guise de tableau, ou rien du tout. La page anglaise,
    # elle, est tenue a jour ; le lien interlangue y mene directement.
    manquants = [f for f in fiches if not f["version"] and f["_en"]]
    if manquants:
        print("historique absent cote francais : %d pages relues en anglais"
              % len(manquants))
        for f in manquants:
            texte = page_anglaise(f["_en"])
            v = premiere_version(texte) if texte else None
            if v:
                f["version"] = etiquette_version(*v)

    # Ce qui n'a de version dans aucun des deux wikis n'est pas dans le
    # jeu : blocs techniques, objets d'Education, choses annoncees mais
    # pas encore sorties. Une chose absente du jeu ne peut pas etre la
    # reponse du jour.
    for f in [x for x in fiches if not x["version"]]:
        ignorees.append(f["nom"] + " (aucune version)")
        fiches.remove(f)

    return fiches, ignorees


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--etat", action="store_true")
    args = ap.parse_args()

    fiches, ignorees = construire()
    print("\n%d fiches retenues, %d pages ecartees" % (len(fiches), len(ignorees)))

    with open(SORTIE, "r", encoding="utf-8") as f:
        registre = json.load(f)
    creatures = [p for p in registre["persos"] if p["type"] == "Créature"]
    anciens = {p["nom"] for p in registre["persos"] if p["type"] != "Créature"}
    nouveaux = {f["nom"] for f in fiches}

    print("disparus de l'ancien registre (%d) :" % len(anciens - nouveaux))
    for n in sorted(anciens - nouveaux):
        print("   ", n)

    sans_version = [f["nom"] for f in fiches if not f["version"]]
    print("sans version : %d" % len(sans_version), sans_version[:10])
    sans_en = [f["nom"] for f in fiches if not f["_en"]]
    print("sans nom anglais : %d" % len(sans_en), sans_en[:10])

    import collections
    print("categories :", dict(collections.Counter(f["categorie"] for f in fiches)))
    print("familles   :", dict(collections.Counter(f["famille"] for f in fiches)))
    print("dimensions :", dict(collections.Counter(f["dimension"] for f in fiches)))
    print("versions   :", dict(collections.Counter(f["version"] for f in fiches)))

    if args.etat:
        print("\n(rien n'a ete ecrit)")
        return

    # Les creatures gardent leurs donnees, mais pas leur version : elles
    # etaient notees « Classique », « Alpha », « Bêta », qui ne sont plus
    # des paliers de l'echelle. On relit la leur au meme endroit que
    # celle des blocs, pour que les deux se comparent.
    # Leur version tenait deja en toutes lettres et avait ete verifiee a
    # la main : « 1.14 » pour le renard, « Bêta » pour le loup. On garde
    # ce qui est deja numerote — le wiki, sur les pages de creatures,
    # rendait « 1.9 » pour le chat et « b1.0 » pour le dragon de l'End —
    # et on ne relit que les trois eres a convertir.
    ERE_EN_PALIER = {"Classique": "0.0", "Alpha": "a1.0", "Bêta": "b1.0"}
    pages = recolter()["pages"]
    for c in creatures:
        ancienne = c["version"]
        if ancienne not in ERE_EN_PALIER:
            continue                     # deja un numero : on n'y touche pas
        palier = ERE_EN_PALIER[ancienne]
        texte = pages.get(c["nom"], {}).get("texte", "") or page_francaise(c["nom"])
        v = premiere_version(texte) if texte else None
        etiq = etiquette_version(*v) if v else ""
        # On n'accepte le wiki que s'il confirme l'ere : sinon il ferait
        # remonter une retouche posterieure au lieu de l'arrivee.
        c["version"] = etiq if etiq[:1] == palier[:1] else palier

    # Le lien butin : quelle creature lache quoi. Il etait etabli a la
    # main dans l'ancien registre et le wiki ne le donne pas sous cette
    # forme ; on le reporte sur les fiches dont le nom n'a pas bouge.
    ancien_butin = {p["nom"]: p for p in registre["persos"]}
    reportes = 0
    for f in fiches:
        vieux = ancien_butin.get(f["nom"])
        if vieux and (vieux.get("lachePar") or vieux.get("estButin")):
            f["lachePar"] = vieux.get("lachePar", [])
            f["estButin"] = vieux.get("estButin", "")
            reportes += 1
    print("liens de butin reportes : %d" % reportes)

    # Le nom anglais sert au telechargement des visuels : le wiki
    # anglophone publie « File:<Nom anglais>.png », et le francophone
    # porte le lien interlangue qui le donne. On le range a cote plutot
    # que dans le registre, qui n'a pas a le transporter jusqu'au
    # navigateur.
    table_en = {f["nom"]: f["_en"] for f in fiches if f.get("_en")}
    for f in fiches:
        f.pop("_en", None)
    chemin_en = os.path.join(RACINE, "outils", "minecraft-noms-en.json")
    with open(chemin_en, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(table_en.items())), f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("noms anglais ecrits : %d" % len(table_en))

    # L'echelle : les versions rencontrees, creatures comprises, rangees.
    toutes = {f["version"] for f in fiches if f["version"]}
    toutes |= {c["version"] for c in creatures if c["version"]}
    echelle = sorted(toutes, key=rang_version)

    registre["versions"] = echelle
    registre["persos"] = sorted(fiches + creatures, key=lambda p: p["nom"])
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(registre, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\n%d fiches ecrites (%d creatures gardees)"
          % (len(registre["persos"]), len(creatures)))


if __name__ == "__main__":
    main()
