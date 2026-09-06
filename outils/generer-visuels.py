# -*- coding: utf-8 -*-
"""
Fabrique les visuels fixes du site a partir du sceau de la Marine dessine
dans l'en-tete d'index.html : favicon, icones PWA, icone iOS et l'image de
partage Open Graph.

    python outils/generer-visuels.py

Tout est regenere a chaque passage ; rien a retoucher a la main. Les
polices viennent de Windows, avec des solutions de repli si elles
manquent. L'image de partage pose tout le dossier assets/img/photos/ en
mur d'avis de recherche, sous un voile, et garde sept portraits nets en
bande ; si le dossier est vide, le fond reste uni.
"""
import io
import random
import json
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow est requis :  pip install pillow")

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(RACINE, "assets", "img")
# Une image de partage par registre : meme mise en page, son propre mur
# de portraits, son propre decompte.
REGISTRES = [
    {"cle": "one-piece", "titre": ("Bureau des ", "Primes"),
     "label": "MARINE · SERVICE DES AVIS DE RECHERCHE",
     "l1": "Un pirate recherché chaque jour.",
     "l2": "Recoupez les fiches jusqu'à l'identifier.",
     "modes": 4, "fichier": "og.jpg"},
    {"cle": "naruto", "titre": ("Bingo ", "Book"),
     "label": "REGISTRE DES CINQ NATIONS · FICHES DE CIBLAGE",
     "l1": "Un ninja recherché chaque jour.",
     "l2": "Recoupez les fiches jusqu'à l'identifier.",
     "modes": 5, "fichier": "og-naruto.jpg"},
    {"cle": "bleach", "titre": ("Registre des ", "Âmes"),
     "label": "GOTEI 13 · RAPPORTS DE TERRAIN",
     "l1": "Une âme est recherchée chaque jour.",
     "l2": "Recoupez les fiches jusqu'à l'identifier.",
     "modes": 4, "fichier": "og-bleach.jpg"},
    {"cle": "inazuma", "titre": ("Feuille de ", "Match"),
     "label": "FOOTBALL FRONTIER · FICHES DE JOUEURS",
     "l1": "Un joueur est recherché chaque jour.",
     "l2": "Recoupez les fiches jusqu'à l'identifier.",
     "modes": 4, "fichier": "og-inazuma.jpg"},
    {"cle": "pokemon", "titre": ("Fiche ", "Pokédex"),
     "label": "POKÉDEX · RELEVÉS DE TERRAIN",
     "l1": "Un Pokémon est recherché chaque jour.",
     "l2": "Recoupez les fiches jusqu'à l'identifier.",
     "modes": 4, "fichier": "og-pokemon.jpg"},
    {"cle": "minecraft", "titre": ("Journal de ", "Bord"),
     "label": "CARNET DU BÛCHERON · CRÉATURES, BLOCS ET OBJETS",
     "l1": "Une créature, un bloc ou un objet chaque jour.",
     "l2": "Recoupez les fiches jusqu'à l'identifier.",
     "modes": 4, "fichier": "og-minecraft.jpg"},
]

# Jetons du theme sombre, repris de assets/css/style.css
FOND = (13, 20, 26)
ENCRE = (234, 227, 211)
ENCRE2 = (159, 173, 181)
ENCRE3 = (118, 131, 139)
TAMPON = (228, 97, 76)
TRAIT = (43, 58, 69)
SCEAU_FOND = (18, 32, 42)   # fond des icones, un cran au-dessus du noir

SS = 4                      # sur-echantillonnage avant reduction


# ---------------------------------------------------------------- polices
def police(*noms, **kw):
    """Premiere police trouvee parmi *noms*, sinon la police par defaut."""
    taille = kw.get("taille", 32)
    variation = kw.get("variation")
    dossier = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    for nom in noms:
        chemin = os.path.join(dossier, nom)
        if os.path.exists(chemin):
            f = ImageFont.truetype(chemin, taille)
            if variation:
                try:
                    f.set_variation_by_name(variation)
                except Exception:
                    pass
            return f
    return ImageFont.load_default()


def largeur(draw, texte, font, chasse=0):
    if not texte:
        return 0
    n = sum(draw.textlength(c, font=font) for c in texte)
    return n + chasse * (len(texte) - 1)


def texte_chasse(draw, xy, texte, font, fill, chasse=0):
    """Texte pose lettre a lettre, pour un interlettrage large."""
    x, y = xy
    for c in texte:
        draw.text((x, y), c, font=font, fill=fill)
        x += draw.textlength(c, font=font) + chasse
    return x


# ------------------------------------------------------------------ sceau
def bezier(p0, pc, p1, pas=48):
    """Points d'une quadratique, pour retracer les courbes du SVG."""
    out = []
    for i in range(pas + 1):
        t = i / pas
        u = 1 - t
        out.append((u * u * p0[0] + 2 * u * t * pc[0] + t * t * p1[0],
                    u * u * p0[1] + 2 * u * t * pc[1] + t * t * p1[1]))
    return out


def trait_rond(draw, points, couleur, epaisseur):
    """Polyligne aux extremites arrondies : Pillow ne le fait pas seul."""
    draw.line(points, fill=couleur, width=int(round(epaisseur)), joint="curve")
    r = epaisseur / 2
    for x, y in (points[0], points[-1]):
        draw.ellipse([x - r, y - r, x + r, y + r], fill=couleur)


def sceau(taille, couleur, fond=None, marge=0.0, simplifie=False,
          motif="one-piece"):
    """
    Le sceau d'un registre sur un carre de *taille* px.

    *motif*     la cle du registre : la mouette de la Marine, la spirale
                de Konoha, le ballon du Football Frontier ou la Poke Ball
                du Pokedex. Meme anneau pour tous : les registres doivent
                se lire comme les tampons d'un meme bureau. Reprend le
                trace des SVG de assets/js/univers.js.

    *marge*     part du cote laissee vide autour (0.22 = 22 %), pour
                l'icone masquable.
    *simplifie* la mouette seule, agrandie, sans anneau, comme
                assets/img/favicon.svg : a 16 px les deux anneaux se
                bouchent et le sceau vire au pate.
    """
    T = taille * SS
    im = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if fond:
        d.rounded_rectangle([0, 0, T - 1, T - 1], radius=T * 0.22, fill=fond)

    # Le dessin d'origine tient dans un viewBox 100x100.
    ech = (T * (1 - 2 * marge)) / 100.0
    dep = T * marge

    def P(x, y):
        return (dep + x * ech, dep + y * ech)

    def E(w):
        return max(1.0, w * ech)

    if simplifie:
        mouette = (bezier(P(15.5, 49.5), P(32.75, 28.5), P(50, 45.75))
                   + bezier(P(50, 45.75), P(67.25, 28.5), P(84.5, 49.5))[1:])
        trait_rond(d, mouette, couleur, E(11.0))
        trait_rond(d, [P(26, 63.75), P(74, 63.75)], couleur, E(8.0))
        return im.resize((taille, taille), Image.LANCZOS)

    for rayon, ep in ((47, 2.4), (42.5, 1.0)):
        cx, cy = P(50, 50)
        r = rayon * ech
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=couleur, width=int(round(E(ep))))

    if motif == "naruto":
        # La spirale de Konoha : trois quarts de tour qui se resserrent,
        # plus la queue qui monte.
        import math
        pts = []
        for k in range(0, 141):
            t = k / 140.0
            ang = math.radians(-90 + 300 * t)
            r = (17 - 12 * t) * ech
            cx, cy = P(50, 50)
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        trait_rond(d, pts, couleur, E(4.2))
        trait_rond(d, [P(50, 33), P(50, 24)], couleur, E(4.2))
        return im.resize((taille, taille), Image.LANCZOS)

    if motif == "inazuma":
        # Le ballon : un cercle, le pentagone central plein, et les cinq
        # coutures qui en partent.
        cx, cy = P(50, 55)
        r = 14.5 * ech
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=couleur, width=int(round(E(2.8))))
        d.polygon([P(50, 47.5), P(57.1, 52.7), P(54.4, 61.1),
                   P(45.6, 61.1), P(42.9, 52.7)], fill=couleur)
        for a1, b1 in ((P(50, 47.5), P(50, 40)), (P(57.1, 52.7), P(64.2, 50.3)),
                       (P(54.4, 61.1), P(58.8, 67.2)), (P(45.6, 61.1), P(41.2, 67.2)),
                       (P(42.9, 52.7), P(35.8, 50.3))):
            trait_rond(d, [a1, b1], couleur, E(2.4))
        return im.resize((taille, taille), Image.LANCZOS)

    if motif == "pokemon":
        # La Poke Ball : le cercle, la ligne mediane, le bouton.
        cx, cy = P(50, 55)
        for rayon, ep in ((15, 2.8), (5.2, 2.8)):
            r = rayon * ech
            d.ellipse([cx - r, cy - r, cx + r, cy + r],
                      outline=couleur, width=int(round(E(ep))))
        trait_rond(d, [P(35, 55), P(42.5, 55)], couleur, E(3.4))
        trait_rond(d, [P(57.5, 55), P(65, 55)], couleur, E(3.4))
        return im.resize((taille, taille), Image.LANCZOS)

    if motif == "bleach":
        # Deux zanpakuto croises : deux lames et leurs gardes. A seize
        # pixels il ne reste qu'un X, ce qui se lit encore.
        for a1, b1, ep in ((P(36, 68), P(64, 42), 3.4), (P(64, 68), P(36, 42), 3.4),
                           (P(33, 58), P(45, 70), 2.6), (P(67, 58), P(55, 70), 2.6)):
            trait_rond(d, [a1, b1], couleur, E(ep))
        return im.resize((taille, taille), Image.LANCZOS)

    if motif == "minecraft":
        # Le visage du Creeper : deux yeux carres et la bouche a deux
        # crocs. Aucune courbe — c'est un jeu de cubes.
        # La grille du visage : huit cases de 3,5 px de cote. Les yeux
        # touchent la bouche, comme dans le jeu — un ecart d'une case les
        # faisait lire comme deux formes separees.
        for x0, y0, w, h in ((39.5, 44, 7, 7), (53.5, 44, 7, 7), (44.5, 53.5, 11, 7), (44.5, 60.5, 3.5, 6.5), (52, 60.5, 3.5, 6.5)):
            a1 = P(x0, y0)
            a2 = P(x0 + w, y0 + h)
            d.rectangle([a1, a2], fill=couleur)
        return im.resize((taille, taille), Image.LANCZOS)

    mouette = (bezier(P(27, 55), P(38.5, 41), P(50, 52.5))
               + bezier(P(50, 52.5), P(61.5, 41), P(73, 55))[1:])
    trait_rond(d, mouette, couleur, E(4.4))
    trait_rond(d, [P(34, 64.5), P(66, 64.5)], couleur, E(2.6))

    return im.resize((taille, taille), Image.LANCZOS)


# --------------------------------------------------------------- portraits
# Les visages mis en avant sur l'image de partage, par registre.
CHOIX = {
    "one-piece": ["monkey-d-luffy", "roronoa-zoro", "nami", "shanks-le-roux",
                  "barbe-blanche", "boa-hancock", "trafalgar-d-water-law"],
    "naruto":    ["naruto-uzumaki", "sasuke-uchiwa", "sakura-haruno",
                  "kakashi-hatake", "itachi-uchiwa", "gaara", "madara-uchiwa"],
    "inazuma":   ["mark-evans", "axel-blaze", "jude-sharp", "shawn-froste",
                  "nathan-jones", "xavier-foster", "jordan-greenway"],
    "pokemon":   ["pikachu", "dracaufeu", "mewtwo", "ronflex",
                  "rayquaza", "absol", "aeromite"],
    "minecraft": ["creeper", "enderman", "diamant", "pioche-en-diamant",
                  "etabli", "bloc-d-herbe", "ender-dragon"],
    "bleach":    ["ichigo-kurosaki", "rukia-kuchiki", "byakuya-kuchiki",
                  "kenpachi-zaraki", "gin-ichimaru", "grimmjow-jaggerjack",
                  "uryu-ishida"],
}


def rond(chemin, taille):
    """Portrait recadre en cercle, cercle d'un anneau discret."""
    T = taille * SS
    im = Image.open(chemin).convert("RGB")
    cote = min(im.size)
    gx = (im.width - cote) // 2
    gy = (im.height - cote) // 2
    im = im.crop((gx, gy, gx + cote, gy + cote)).resize((T, T), Image.LANCZOS)
    im = im.convert("RGBA")

    masque = Image.new("L", (T, T), 0)
    ImageDraw.Draw(masque).ellipse([0, 0, T - 1, T - 1], fill=255)
    im.putalpha(masque)

    ImageDraw.Draw(im).ellipse([0, 0, T - 1, T - 1], outline=TRAIT, width=3 * SS)
    return im.resize((taille, taille), Image.LANCZOS)


def tous_les_portraits(univers):
    """
    Tous les portraits du dossier, dans un ordre melange mais stable :
    trier par nom de fichier regrouperait les personnages d'un meme
    equipage, donc des aplats de couleur identiques cote a cote.
    """
    dossier = os.path.join(IMG, "photos", univers)
    fichiers = sorted(f for f in os.listdir(dossier) if f.endswith(".jpg")) \
        if os.path.isdir(dossier) else []
    melange = random.Random(20260101)
    melange.shuffle(fichiers)
    return [os.path.join(dossier, f) for f in fichiers]


def halo(taille, alpha=190):
    """
    Un disque sombre qui s'efface vers le bord, pose sous un element
    fin. Pillow ne connait pas les degrades radiaux : on empile des
    cercles concentriques, du plus large au plus etroit.
    """
    T = taille * 2
    im = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pas = 64
    for i in range(pas):
        r = T / 2 * (1 - i / pas)
        a = int(alpha * (i / pas) ** 1.5)
        d.ellipse([T / 2 - r, T / 2 - r, T / 2 + r, T / 2 + r], fill=FOND + (a,))
    return im.resize((taille, taille), Image.LANCZOS)


def mosaique(univers, L, H, cote):
    """
    Un mur d'avis de recherche : tous les portraits en tuiles carrees,
    repetes si la grille est plus grande que le dossier.
    """
    chemins = tous_les_portraits(univers)
    if not chemins:
        return None
    cols = -(-L // cote)
    lignes = -(-H // cote)
    mur = Image.new("RGB", (cols * cote, lignes * cote), FOND)
    for i in range(cols * lignes):
        im = Image.open(chemins[i % len(chemins)]).convert("RGB")
        c = min(im.size)
        gx, gy = (im.width - c) // 2, (im.height - c) // 2
        im = im.crop((gx, gy, gx + c, gy + c)).resize((cote, cote), Image.LANCZOS)
        mur.paste(im, ((i % cols) * cote, (i // cols) * cote))
    return mur.crop((0, 0, L, H))


# ------------------------------------------------------------------ rendus
def icones():
    os.makedirs(IMG, exist_ok=True)
    faits = []

    for cote, nom in ((192, "icon-192.png"), (512, "icon-512.png"),
                      (180, "apple-touch-icon.png")):
        sceau(cote, TAMPON, fond=SCEAU_FOND).save(os.path.join(IMG, nom))
        faits.append("assets/img/" + nom)

    # Masquable : le systeme peut rogner jusqu'a 20 % de chaque bord.
    im = Image.new("RGBA", (512, 512), SCEAU_FOND)
    im.alpha_composite(sceau(512, TAMPON, marge=0.22))
    im.save(os.path.join(IMG, "icon-512-maskable.png"))
    faits.append("assets/img/icon-512-maskable.png")

    # Le .ico n'est lu que par les navigateurs qui ignorent le SVG : il
    # doit tenir a 16 px, d'ou le dessin simplifie.
    sceau(256, TAMPON, fond=SCEAU_FOND, simplifie=True).save(
        os.path.join(RACINE, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    faits.append("favicon.ico")
    return faits


def og(reg):
    L, H, M = 1200, 630, 72
    im = Image.new("RGB", (L, H), FOND)

    # Le mur d'avis en fond : tout le registre y passe. Fortement
    # assombri, il donne une matiere sans disputer la lisibilite au
    # titre — une carte de partage se lit d'abord en vignette.
    mur = mosaique(reg["cle"], L, H, 63)
    if mur:
        # L'opacite du voile se calcule pour chaque colonne d'un coup :
        # dessiner un aplat puis un degrade par-dessus ne cumulerait
        # rien, ImageDraw remplace les pixels au lieu de les melanger.
        voile = Image.new("RGBA", (L, H), (0, 0, 0, 0))
        vd = ImageDraw.Draw(voile)
        for x in range(L):
            gauche = max(0.0, 1 - x / (L * 0.60))   # 1 au bord, 0 au centre
            vd.line([(x, 0), (x, H)], fill=FOND + (int(205 + 44 * gauche),))
        # Un voile de pied, pour que la ligne du bas ne tombe jamais sur
        # un portrait clair.
        bas = Image.new("RGBA", (L, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bas)
        for y in range(H - 96, H):
            bd.line([(0, y), (L, y)], fill=FOND + (int(180 * (y - H + 96) / 96),))
        voile = Image.alpha_composite(voile, bas)
        im = Image.alpha_composite(mur.convert("RGBA"), voile).convert("RGB")

    d = ImageDraw.Draw(im, "RGBA")

    # Le grain du site : une trame horizontale tres pale.
    for y in range(0, H, 4):
        d.line([(0, y), (L, y)], fill=(234, 227, 211, 9))

    f_label = police("bahnschrift.ttf", "segoeuib.ttf",
                     taille=22, variation="SemiBold Condensed")
    f_titre = police("georgiab.ttf", "cambriab.ttf", taille=86)
    f_texte = police("segoeui.ttf", "arial.ttf", taille=27)
    f_pied = police("bahnschrift.ttf", "segoeui.ttf",
                    taille=21, variation="SemiBold Condensed")

    texte_chasse(d, (M, 62), reg["label"], f_label, TAMPON, chasse=3.2)
    d.line([(M, 112), (L - M, 112)], fill=TRAIT, width=1)

    x = texte_chasse(d, (M, 158), reg["titre"][0], f_titre, ENCRE)
    texte_chasse(d, (x, 158), reg["titre"][1], f_titre, TAMPON)

    d.text((M, 288), reg["l1"], font=f_texte, fill=ENCRE2)
    d.text((M, 326), reg["l2"], font=f_texte, fill=ENCRE2)

    # Sceau a droite, aligne sur le bloc de titre. Ses anneaux sont fins :
    # sans halo ils se perdent dans les portraits du fond.
    h = halo(300)
    im.paste(h, (L - M - 242, 108), h)
    s = sceau(184, TAMPON, motif=reg["cle"])
    im.paste(s, (L - M - 184, 166), s)

    # Bande de portraits, centree.
    vedettes = CHOIX.get(reg["cle"], [])
    dispo = [os.path.join(IMG, "photos", reg["cle"], n + ".jpg") for n in vedettes]
    dispo = [p for p in dispo if os.path.exists(p)]
    if dispo:
        cote, ecart = 118, 26
        total = len(dispo) * cote + (len(dispo) - 1) * ecart
        x, y = (L - total) // 2, 420
        for p in dispo:
            v = rond(p, cote)
            im.paste(v, (x, y), v)
            x += cote + ecart

    d.line([(M, 566), (L - M, 566)], fill=TRAIT, width=1)
    # Le nombre de personnages se lit dans le registre : fige ici, il
    # deviendrait faux au premier ajout.
    combien = len(json.load(io.open(
        os.path.join(RACINE, "assets", "data", reg["cle"] + ".json"),
        encoding="utf-8"))["persos"])
    gauche = ("%d MODES \u00b7 %d PERSONNAGES \u00b7 NOUVELLE CIBLE CHAQUE NUIT"
              % (reg["modes"], combien))
    droite = "BUREAU-DES-PRIMES"
    texte_chasse(d, (M, 584), gauche, f_pied, ENCRE3, chasse=2.4)
    texte_chasse(d, (L - M - largeur(d, droite, f_pied, 2.4), 584),
                 droite, f_pied, ENCRE3, chasse=2.4)

    # JPEG et non PNG : le mur de portraits est photographique, et le
    # PNG le rendait quatre fois plus lourd pour un resultat identique
    # a l'oeil. Une carte de partage doit rester legere, les robots la
    # telechargent a chaque partage.
    chemin = os.path.join(IMG, reg["fichier"])
    im.save(chemin, "JPEG", quality=86, optimize=True, progressive=True)
    return "assets/img/%s (%d Ko, mur de %d portraits)" % (
        reg["fichier"], os.path.getsize(chemin) // 1024,
        len(tous_les_portraits(reg["cle"])))


if __name__ == "__main__":
    for nom in icones():
        print("  " + nom)
    for reg in REGISTRES:
        print("  " + og(reg))
