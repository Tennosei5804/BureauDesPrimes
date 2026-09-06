# -*- coding: utf-8 -*-
"""
Remplace le domaine du site partout ou il est ecrit.

    python outils/domaine.py bureau-des-primes.fr
    python outils/domaine.py --etat

Le domaine apparait dans les balises canoniques, l'Open Graph, le JSON-LD
de chaque page, dans robots.txt, sitemap.xml, l'exemple de configuration
et le diagnostic Discord. Le laisser sur « bureau-des-primes.example »
fait pointer les apercus de partage et le referencement dans le vide.

L'outil ne touche pas api/config.php : ce fichier n'est pas versionne et
porte l'URL de redirection Discord reelle, que le portail Discord doit
connaitre a l'identique. Il le signale a la fin.
"""
import io, os, re, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTUEL_PAR_DEFAUT = "bureau-des-primes.example"

# Les fichiers ou le domaine a un sens. On ne balaie pas tout le dossier :
# les registres et les portraits n'en contiennent pas, et un remplacement
# aveugle sur assets/ serait une mauvaise idee.
CIBLES = ["index.html", "robots.txt", "sitemap.xml", "README.md",
          "api/config.exemple.php", "outils/verifier-discord.php"]


def pages():
    """Les pages de jeu, deduites des fichiers presents."""
    return sorted(f for f in os.listdir(RACINE)
                  if f.endswith(".html") and f not in ("index.html", "404.html"))


def fichiers():
    vus = []
    for f in CIBLES + pages():
        chemin = os.path.join(RACINE, f)
        if os.path.exists(chemin) and chemin not in vus:
            vus.append(chemin)
    return vus


def domaine_actuel():
    """Le domaine ecrit dans index.html fait foi."""
    t = io.open(os.path.join(RACINE, "index.html"), encoding="utf-8").read()
    m = re.search(r"https?://([a-z0-9.-]+\.[a-z]{2,})/", t, re.I)
    return m.group(1) if m else ACTUEL_PAR_DEFAUT


def etat():
    actuel = domaine_actuel()
    print("domaine en place :", actuel)
    total = 0
    for chemin in fichiers():
        t = io.open(chemin, encoding="utf-8").read()
        n = t.count(actuel)
        if n:
            total += n
            print("  %-34s %d" % (os.path.relpath(chemin, RACINE), n))
    print("%d occurrence(s)" % total)
    if actuel.endswith(".example"):
        print("\nDomaine de demonstration : les apercus de partage et le "
              "referencement pointent dans le vide.")


def remplacer(nouveau):
    nouveau = nouveau.strip().rstrip("/")
    nouveau = re.sub(r"^https?://", "", nouveau)
    if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9-]+)+$", nouveau, re.I):
        sys.exit("Domaine invalide : " + nouveau)
    actuel = domaine_actuel()
    if actuel == nouveau:
        print("Le domaine est deja", nouveau)
        return

    total, touches = 0, 0
    for chemin in fichiers():
        t = io.open(chemin, encoding="utf-8").read()
        n = t.count(actuel)
        if not n:
            continue
        io.open(chemin, "w", encoding="utf-8", newline="\n").write(
            t.replace(actuel, nouveau))
        total += n
        touches += 1
        print("  %-34s %d" % (os.path.relpath(chemin, RACINE), n))
    print("\n%s -> %s : %d occurrence(s) dans %d fichier(s)"
          % (actuel, nouveau, total, touches))
    print("\nA faire a la main, l'outil n'y touche pas :")
    print("  - api/config.php : 'redirection' doit devenir")
    print("      https://%s/api/retour.php" % nouveau)
    print("  - le portail Discord : OAuth2 > Redirects, la meme ligne")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--etat"
    if arg == "--etat":
        etat()
    else:
        remplacer(arg)
