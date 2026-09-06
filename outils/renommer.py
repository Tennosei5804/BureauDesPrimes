# -*- coding: utf-8 -*-
"""Renomme des fiches et des valeurs dans les registres, portraits compris.

    py outils/renommer.py --etat      # ce qui changerait, sans rien ecrire
    py outils/renommer.py             # applique

Le nom d'une fiche n'est pas qu'un libelle : c'est la cle du registre, ce
que le joueur tape, et le nom du fichier de portrait (via le meme slug que
photoSrc() dans app.js). Le renommer a la main, c'est oublier l'un des
trois. D'ou cette table, seul endroit ou la correspondance est ecrite.

Regle appliquee ici, tiree de ce que demande le projet : le nom porte
l'ecriture de l'oeuvre, pas celle d'un editeur francais.

  1. pas d'alias entre parentheses   Akainu (Sakazuki) -> Akainu Sakazuki
  2. pas de nom propre francise      Uchiwa -> Uchiha, Baggy -> Buggy
  3. pas de trema d'adaptation       Kurenai, Sai, Mei  (les accents
     circonflexes restent : ils notent les voyelles longues, et tout le
     registre les emploie deja)
  4. le nom seul dans « nom »        Shanks le Roux -> Shanks
     (l'epithete a son propre champ, l'y laisser evite le doublon)
  5. les lieux ecrits en alphabet latin dans l'oeuvre gardent cette
     forme                          Societe des Ames -> Soul Society

Ce qui n'est PAS touche : les epithetes descriptives traduites de bonne
foi (« Le Chirurgien de la Mort »), et les surnoms-noms d'usage que toute
edition rend de la meme facon (Barbe Blanche, Barbe Noire, Big Mom).
"""

import argparse
import json
import os
import re
import sys
import unicodedata

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DONNEES = os.path.join(RACINE, "assets", "data")
PHOTOS = os.path.join(RACINE, "assets", "img", "photos")


# --- Les tables ------------------------------------------------------
# NOMS : la fiche elle-meme. VALEURS : les champs qui citent un nom ou un
# lieu. LISTES : les echelles du registre (arcs, versions...).

NOMS = {
    "one-piece": {
        # 1. alias entre parentheses
        "Akainu (Sakazuki)": "Akainu Sakazuki",
        "Aokiji (Kuzan)": "Aokiji Kuzan",
        "Kizaru (Borsalino)": "Kizaru Borsalino",
        "Fujitora (Issho)": "Fujitora Issho",
        "Ryokugyu (Aramaki)": "Ryokugyu Aramaki",
        "Bon Clay (Bentham)": "Bon Clay Bentham",
        # 2. noms propres francises — la fiche disait « Octo » quand sa
        #    propre epithete disait deja « Hachi ».
        "Baggy le Clown": "Buggy",
        "Octo": "Hachi",
        "Bell-mère": "Bellemère",
        # 4. l'epithete recopiee dans le nom
        "Shanks le Roux": "Shanks",
        "Marco le Phénix": "Marco",
    },
    "naruto": {
        # 2. Uchiwa est une invention de l'edition francaise
        "Fugaku Uchiwa": "Fugaku Uchiha",
        "Itachi Uchiwa": "Itachi Uchiha",
        "Madara Uchiwa": "Madara Uchiha",
        "Obito Uchiwa": "Obito Uchiha",
        "Sarada Uchiwa": "Sarada Uchiha",
        "Sasuke Uchiwa": "Sasuke Uchiha",
        "Shisui Uchiwa": "Shisui Uchiha",
        # 3. tremas d'adaptation
        "Kurenaï Yûhi": "Kurenai Yûhi",
        "Meï Terumî": "Mei Terumî",
        "Saï": "Sai",
        # 1. alias entre parentheses
        "Tobi (Zetsu Noir)": "Zetsu Noir",
    },
    "bleach": {
        # Le manga l'appelle Chad — チャド, Chado — et c'est ainsi que tout
        # le monde le nomme dans l'oeuvre. « Yasutora Sado » est son etat
        # civil, que le recit n'emploie presque jamais. Meme principe que
        # « Shanks » plus haut : la fiche porte le nom qu'on lui donne.
        "Yasutora Sado": "Chad",
    },
    "minecraft": {
        # Le registre disait « Pierraille », qui n'existe pas : le wiki
        # francophone n'a meme pas de page a ce nom. Il titre « Pierres »
        # et fait de « Pierre » une redirection — c'est le nom que le
        # joueur emploie pour le cobblestone. La roche, elle, s'appelle
        # « Roche », et c'est une autre fiche.
        "Pierres": "Pierre",
    },
}

VALEURS = {
    "one-piece": {
        "epithete": {
            "Baggy le Clown": "Buggy le Clown",
            "Shanks le Roux": "Le Roux",
            "Marco le Phénix": "Le Phénix",
            "Violette": "Violet",
        },
    },
    "naruto": {
        "clan": {"Uchiwa": "Uchiha"},
        "epithete": {
            "Le Fantôme des Uchiwa": "Le Fantôme des Uchiha",
            "Le Dernier des Uchiwa": "Le Dernier des Uchiha",
        },
    },
    "bleach": {
        # 5. « Soul Society » est ecrit ainsi dans le manga. Le nom sert
        #    a deux endroits — l'affiliation d'un personnage et l'arc du
        #    recit — et l'echelle « arcs » plus bas. Les trois doivent
        #    bouger ensemble : n'en changer que deux laissait l'arc de
        #    cinquante-trois fiches hors de son echelle.
        "affiliation": {"Société des Âmes": "Soul Society"},
        "arc": {"Société des Âmes": "Soul Society"},
    },
    "minecraft": {},
}

LISTES = {
    "bleach": {"arcs": {"Société des Âmes": "Soul Society"}},
}

# Les seuls champs qui citent une AUTRE fiche par son nom. Passer la table
# des noms sur tous les champs sans distinction ecrasait l'epithete :
# « Baggy le Clown » y devenait « Buggy », et la correction d'epithete
# prevue plus bas ne trouvait plus rien a corriger.
REFERENCES = {
    "minecraft": ("butin", "lachePar"),
}


# --- Mecanique -------------------------------------------------------

def slug(nom):
    """Le meme slug que photoSrc() dans app.js et que telecharger-portraits."""
    n = unicodedata.normalize("NFD", nom.lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", n))


def remplacer_partout(valeur, table):
    """Une valeur de champ : texte, ou liste de textes (butin, lachePar)."""
    if isinstance(valeur, str):
        return table.get(valeur, valeur)
    if isinstance(valeur, list):
        return [table.get(v, v) if isinstance(v, str) else v for v in valeur]
    return valeur


def traiter(univers, ecrire):
    chemin = os.path.join(DONNEES, univers + ".json")
    with open(chemin, "r", encoding="utf-8") as f:
        d = json.load(f)

    noms = NOMS.get(univers, {})
    journal = []

    connus = {p["nom"] for p in d["persos"]}
    for ancien, nouveau in noms.items():
        if ancien not in connus:
            journal.append("  ABSENT   %s" % ancien)
        elif nouveau in connus and nouveau != ancien:
            journal.append("  COLLISION %s -> %s (existe deja)" % (ancien, nouveau))

    # 1. le nom de la fiche
    for p in d["persos"]:
        if p["nom"] in noms:
            avant = p["nom"]
            p["nom"] = noms[avant]
            journal.append("  nom       %-26s -> %s" % (avant, p["nom"]))

    # 2. les champs qui citent une autre fiche par son nom
    for cle in REFERENCES.get(univers, ()):
        for p in d["persos"]:
            if cle not in p:
                continue
            neuf = remplacer_partout(p[cle], noms)
            if neuf != p[cle]:
                p[cle] = neuf
                journal.append("  ref       %-26s %s : %s" % (p["nom"], cle, neuf))

    # 3. les valeurs de champ (clan, affiliation, epithete...)
    for cle, table in VALEURS.get(univers, {}).items():
        n = 0
        for p in d["persos"]:
            if cle in p:
                neuf = remplacer_partout(p[cle], table)
                if neuf != p[cle]:
                    p[cle] = neuf
                    n += 1
        if n:
            journal.append("  valeur    %-12s %d fiche(s) %s" % (cle, n, table))

    # 4. les echelles du registre
    for cle, table in LISTES.get(univers, {}).items():
        if cle in d:
            avant = list(d[cle])
            d[cle] = [table.get(v, v) for v in d[cle]]
            if d[cle] != avant:
                journal.append("  echelle   %s : %s" % (cle, table))

    # 5. les portraits, qui portent le slug du nom
    dossier = os.path.join(PHOTOS, univers)
    for ancien, nouveau in noms.items():
        a = os.path.join(dossier, slug(ancien) + ".jpg")
        b = os.path.join(dossier, slug(nouveau) + ".jpg")
        if not os.path.exists(a) or a == b:
            continue          # le slug n'a pas bouge : rien a renommer
        if os.path.exists(b) and a != b:
            journal.append("  PORTRAIT  %s existe deja, %s non renomme"
                           % (os.path.basename(b), os.path.basename(a)))
            continue
        journal.append("  portrait  %s -> %s"
                       % (os.path.basename(a), os.path.basename(b)))
        if ecrire:
            os.rename(a, b)

    if ecrire and journal:
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
            f.write("\n")

    return journal


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--etat", action="store_true",
                    help="montre ce qui changerait sans rien ecrire")
    args = ap.parse_args()
    ecrire = not args.etat

    total = 0
    for univers in ("one-piece", "naruto", "bleach", "minecraft"):
        journal = traiter(univers, ecrire)
        if journal:
            print("=== %s" % univers)
            for l in journal:
                print(l)
            total += len(journal)
    print()
    print("%s : %d changement(s)" % ("applique" if ecrire else "etat", total))
    if not ecrire:
        print("(rien n'a ete ecrit)")


if __name__ == "__main__":
    main()
