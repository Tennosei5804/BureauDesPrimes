# -*- coding: utf-8 -*-
"""Ce que plusieurs outils doivent calculer de la meme facon.

Pour l'instant une seule regle, mais c'est la plus piegeuse : le nom de
fichier d'un portrait. Elle existait en trois exemplaires — le
telechargeur, le verificateur, et photoSrc() cote navigateur — et les
trois ont diverge le jour ou les signes de genre sont apparus : le
verificateur annoncait Nidoran(f) et Nidoran(m) sans portrait alors que
les deux fichiers etaient la, sous des noms qu'il ne savait pas former.

Le jumeau JavaScript est dans assets/js/commun.js. Les deux doivent
rendre exactement la meme chaine.
"""

import re
import unicodedata


def slug(nom):
    """Le nom de fichier d'un portrait, sans accent ni majuscule.

    « Monkey D. Luffy » -> monkey-d-luffy
    « Nidoran(f) »      -> nidoran-f     (le signe est transcrit avant
                                          l'ecrasement du reste, sinon
                                          les deux Nidoran se partagent
                                          un seul fichier)
    """
    n = unicodedata.normalize("NFD", nom.lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = n.replace("♀", "-f").replace("♂", "-m")
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", n))
