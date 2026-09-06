# -*- coding: utf-8 -*-
"""
Telecharge les icones officielles des valeurs de liste.

    python outils/telecharger-icones.py pokemon
    python outils/telecharger-icones.py naruto

Pokemon : les miniatures de type de Pokepedia, jeu de reference GO. Les
variantes HOME, EV ou EB sont des bandeaux portant le nom du type ecrit
dessus — inutilisables dans une pastille qui l ecrit deja en dessous.

Naruto : le wiki francophone ne publie pas les natures une par une, mais
un tableau unique. On y decoupe chaque octogone, aux coordonnees relevees
dessus, puis on rogne sur la partie opaque.

Les fichiers vont dans  assets/img/icones/<univers>/<slug>.png .
Une icone absente n'est pas une erreur : le jeu retombe sur le glyphe
declare dans univers.js (kanji ou trace SVG).

Images (c) leurs ayants droit respectifs, reprises a titre d'illustration.
"""
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow requis : pip install pillow")

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (bureau-des-primes; usage personnel)"}
TAILLE = 48                      # affichees a 14 px : de la marge pour les ecrans denses

POKEPEDIA = "https://www.pokepedia.fr/api.php"
TYPES = ["Normal", "Feu", "Eau", "Plante", "Électrik", "Glace", "Combat",
         "Poison", "Sol", "Vol", "Psy", "Insecte", "Roche", "Spectre",
         "Dragon", "Ténèbres", "Acier", "Fée"]

# Tableau des natures de chakra du wiki Naruto, et le centre de chaque
# octogone releve dessus (image de 1000 x 1286).
CHAKRA_SRC = ("https://static.wikia.nocookie.net/naruto/images/a/a9/"
              "Nature_de_Chakra_2.png/revision/latest/scale-to-width-down/1000"
              "?cb=20190126103836&path-prefix=fr")
CHAKRA_POS = {
    "Hyôton": (500, 70), "Futton": (250, 155), "Katon": (502, 307),
    "Suiton": (320, 437), "Jinton": (502, 502), "Fûton": (686, 437),
    "Mokuton": (95, 630), "Doton": (390, 653), "Raiton": (614, 653),
    "Jiton": (754, 848), "Ranton": (250, 845), "Bakuton": (502, 930),
    "Yôton": (120, 1113), "Inyôton": (502, 1113), "Inton": (890, 1113),
}
CHAKRA_COTE = 108                # boite de decoupe avant rognage

NARUTO_API = "https://naruto.fandom.com/fr/api.php"

# Les kekkei genkai, eux, ont chacun leur fichier. Les noms ne sont pas
# devines : ils sont releves dans les infobox du wiki, qui ecrivent
# « [[Fichier:Sharingan Triple.svg|link=Sharingan]] ». Quand une valeur a
# plusieurs symboles — un Mangekyo different par personnage — on prend le
# generique. Ce sont des SVG, que Pillow ne lit pas : on demande a l API
# sa vignette matricielle.
KEKKEI = {
    "Sharingan":     "Sharingan Triple.svg",
    "Byakugan":      "Byakugan.svg",
    "Rinnegan":      "Rinnegan.svg",
    "Jôgan":         "Jôgan.svg",
    "Kokugan":       "Dôjutsu Isshiki.svg",
    "Shikotsumyaku": "Shikotsumyaku Symbole.svg",
    "Enton":         "Enton Symbole.svg",
    "Clan de Jûgo":  "Kekkei Genkai du Clan de Jûgo Symbole.svg",
    "Sakon et Ukon": "Kekkei Genkai de Sakon et Ukon Symbole.svg",
}


def slug(n):
    n = unicodedata.normalize("NFD", n.lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", n))


def dossier(univers):
    d = os.path.join(RACINE, "assets", "img", "icones", univers)
    os.makedirs(d, exist_ok=True)
    return d


def masquer_octogone(im, rayon):
    """Efface tout hors d un octogone centre : sur le tableau des natures,
    les traits qui relient les cases debordent dans la boite de decoupe et
    fausseraient le rognage."""
    from PIL import ImageDraw
    masque = Image.new("L", im.size, 0)
    cx, cy = im.width / 2, im.height / 2
    import math
    pts = [(cx + rayon * math.cos(math.pi / 8 + i * math.pi / 4),
            cy + rayon * math.sin(math.pi / 8 + i * math.pi / 4)) for i in range(8)]
    ImageDraw.Draw(masque).polygon(pts, fill=255)
    vide = Image.new("RGBA", im.size, (0, 0, 0, 0))
    return Image.composite(im, vide, masque)


def enregistrer(im, cible):
    """Rogne sur la partie opaque, met au carre, reduit."""
    im = im.convert("RGBA")
    boite = im.getbbox()
    if boite:
        im = im.crop(boite)
    cote = max(im.size)
    carre = Image.new("RGBA", (cote, cote), (0, 0, 0, 0))
    carre.paste(im, ((cote - im.width) // 2, (cote - im.height) // 2))
    carre.resize((TAILLE, TAILLE), Image.LANCZOS).save(cible)


def url_fichier(api, nom, vignette=0):
    u = (api + "?action=query&titles=" + urllib.parse.quote("Fichier:" + nom)
         + "&prop=imageinfo&iiprop=url&format=json&formatversion=2")
    # Un SVG ne s ouvre pas avec Pillow ; le wiki sait en rendre un PNG a
    # la largeur demandee, et le renvoie dans thumburl.
    if vignette:
        u += "&iiurlwidth=" + str(vignette)
    d = json.loads(urllib.request.urlopen(
        urllib.request.Request(u, headers=UA), timeout=45).read().decode("utf-8"))
    for p in d.get("query", {}).get("pages", []):
        for i in p.get("imageinfo", []):
            return i.get("thumburl") if vignette else i.get("url")
    return None


def telecharger(url):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=45).read()


def faire_pokemon():
    d = dossier("pokemon")
    faits, sautes, echecs = 0, 0, []
    for i, t in enumerate(TYPES, 1):
        cible = os.path.join(d, slug(t) + ".png")
        if os.path.exists(cible):
            sautes += 1
            continue
        try:
            url = url_fichier(POKEPEDIA, "Miniature Type %s GO.png" % t)
            if not url:
                raise LookupError("miniature introuvable")
            enregistrer(Image.open(io.BytesIO(telecharger(url))), cible)
            faits += 1
            print("[%2d/%d] %s" % (i, len(TYPES), slug(t)))
            time.sleep(0.2)
        except Exception as e:
            echecs.append(t)
            print("[%2d/%d] ECHEC %-12s %s" % (i, len(TYPES), t, e))
    print("\n%d telechargees, %d deja presentes, %d echecs." % (faits, sautes, len(echecs)))
    if echecs:
        print("Manquantes :", ", ".join(echecs))


def faire_naruto():
    d = dossier("naruto")
    print("Tableau des natures :", CHAKRA_SRC[:70], "...")
    planche = Image.open(io.BytesIO(telecharger(CHAKRA_SRC))).convert("RGBA")
    print("  image", planche.size)
    demi = CHAKRA_COTE // 2
    for nom, (x, y) in CHAKRA_POS.items():
        boite = (x - demi, y - demi, x + demi, y + demi)
        case = masquer_octogone(planche.crop(boite), 47)
        enregistrer(case, os.path.join(d, slug(nom) + ".png"))
        print("  %-10s decoupe en %s" % (nom, boite))
    print("\n%d natures decoupees.\n" % len(CHAKRA_POS))

    faits, sautes, echecs = 0, 0, []
    for i, (nom, fichier) in enumerate(sorted(KEKKEI.items()), 1):
        cible = os.path.join(d, slug(nom) + ".png")
        if os.path.exists(cible):
            sautes += 1
            continue
        try:
            url = url_fichier(NARUTO_API, fichier)
            if not url:
                raise LookupError("fichier introuvable : " + fichier)
            # thumburl de l API renvoie le SVG tel quel pour la moitie des
            # fichiers ; c est la forme « scale-to-width-down » de l URL
            # qui declenche vraiment le rendu matriciel cote wiki.
            url = re.sub(r"/revision/latest",
                         "/revision/latest/scale-to-width-down/%d" % (TAILLE * 4),
                         url, count=1)
            enregistrer(Image.open(io.BytesIO(telecharger(url))), cible)
            faits += 1
            print("[%d/%d] %-16s %s" % (i, len(KEKKEI), slug(nom), fichier))
            time.sleep(0.2)
        except Exception as e:
            echecs.append(nom)
            print("[%d/%d] ECHEC %-14s %s" % (i, len(KEKKEI), nom, e))
    print("\n%d kekkei genkai telecharges, %d deja presents, %d echecs."
          % (faits, sautes, len(echecs)))
    if echecs:
        print("Manquants :", ", ".join(echecs))


if __name__ == "__main__":
    quoi = sys.argv[1] if len(sys.argv) > 1 else ""
    if quoi == "pokemon":
        faire_pokemon()
    elif quoi == "naruto":
        faire_naruto()
    else:
        sys.exit("Usage : python outils/telecharger-icones.py [pokemon|naruto]")
