# -*- coding: utf-8 -*-
"""
Verifie les registres : champs manquants, echelles inconnues, bassins
vides, portraits absents, doublons.

    python outils/verifier-registres.py            tous les univers
    python outils/verifier-registres.py one-piece  un seul

Sort en code 1 si une anomalie bloquante est trouvee, pour pouvoir
etre branche sur un hook ou une CI.
"""
import io
import json
import os
import re
import sys
import unicodedata

# La console Windows repond en cp1252 : sans cette ligne, le premier nom
# a macron — « Chojiro », « Jushiro » — faisait tomber l'outil en pleine
# liste d'erreurs, et on ne voyait jamais la fin du rapport.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Les champs que chaque univers doit porter : attributs compares, champs
# lus par les modes a indice, champs affiches sur l'affiche finale.
ATTENDUS = {
    'one-piece': {
        'attrs': ['genre', 'equipage', 'origine', 'fruitDetail', 'haki',
                  'prime', 'taille', 'saga'],
        'autres': ['nom', 'fruit', 'fruitNom', 'fruitNomEn', 'epithete',
                   'espece', 'chapitre', 'statut'],
        'echelles': {'saga': 'sagas'},
        'listes': ['haki'],
        'nombres': ['taille'],
        'nombres_nullables': ['prime'],
        'hors_echelle': [],
    },
    'naruto': {
        'attrs': ['genre', 'village', 'clan', 'kekkei', 'chakra', 'rang',
                  'taille', 'arc'],
        'autres': ['nom', 'technique', 'epithete', 'serie', 'chapitre', 'statut'],
        'echelles': {'rang': 'rangs', 'arc': 'arcs'},
        'listes': ['chakra'],
        'nombres': ['taille'],
        'nombres_nullables': ['taille'],
        # Valeurs admises hors echelle : compare() retombe alors sur une
        # egalite stricte, sans fleche. C'est voulu, pas une anomalie.
        'hors_echelle': ['Inconnu'],
    },
    'bleach': {
        'attrs': ['genre', 'race', 'affiliation', 'rang', 'zanpakuto',
                  'liberation', 'taille', 'arc'],
        # zanpakutoSeul ne sert qu'au bassin du mode Zanpakuto : il porte
        # le nom quand celui-ci designe une seule personne, rien sinon.
        'autres': ['nom', 'chapitre', 'zanpakutoSeul'],
        'echelles': {'arc': 'arcs'},
        'listes': [],
        'nombres': ['taille'],
        'nombres_nullables': ['taille'],
        'hors_echelle': [],
    },
    'inazuma': {
        'attrs': ['genre', 'element', 'poste', 'pays', 'technique', 'equipes',
                  'apparence', 'saison'],
        # techniqueSeul ne sert qu'au bassin du mode Technique : il porte la
        # technique quand elle designe une seule personne, et rien sinon.
        'autres': ['nom', 'surnom', 'numero', 'techniqueSeul', 'statut'],
        'echelles': {'saison': 'saisons'},
        'listes': ['equipes', 'apparence'],
        'nombres': ['numero'],
        'nombres_nullables': ['numero'],
        'hors_echelle': [],
    },
    'minecraft': {
        'attrs': ['type', 'categorie', 'famille', 'dimension', 'pv',
                  'empilement', 'butin', 'version'],
        # Trois marqueurs de bassin, un par mode restreint, plus ce que la
        # fusion des deux anciennes tables a conserve sans l'afficher.
        'autres': ['nom', 'deplacement', 'apparition', 'outil', 'renouvelable',
                   'estCreature', 'estObjet', 'estButin', 'lachePar'],
        'echelles': {'version': 'versions'},
        'listes': ['butin', 'lachePar'],
        'nombres': ['pv', 'empilement'],
        'nombres_nullables': ['pv', 'empilement'],
        'hors_echelle': [],
    },
    'pokemon': {
        'attrs': ['types', 'categorie', 'couleur', 'stade', 'taille', 'poids',
                  'stats', 'generation'],
        'autres': ['nom', 'numero', 'sprite', 'type1', 'talent', 'talents',
                   'description', 'statut'],
        'echelles': {'stade': 'stades', 'generation': 'generations'},
        'listes': ['types', 'talents'],
        'nombres': ['taille', 'poids', 'stats', 'numero'],
        'nombres_nullables': [],
        'hors_echelle': [],
    },
}


"""Le slug vit dans outils/commun.py : il doit etre identique a celui du
telechargeur et a photoSrc() cote navigateur, et sa copie locale ici
signalait a tort les deux Nidoran comme depourvus de portrait."""
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import slug  # noqa: E402


def verifier(univers):
    chemin = os.path.join(RACINE, 'assets', 'data', univers + '.json')
    if not os.path.exists(chemin):
        return ['registre introuvable : ' + chemin], []
    d = json.load(io.open(chemin, encoding='utf-8'))
    regle = ATTENDUS.get(univers)
    if regle is None:
        return ['univers non decrit dans ce script : ' + univers], []

    dur, mou = [], []
    persos = d.get('persos', [])
    if not persos:
        dur.append('registre vide')
        return dur, mou

    # doublons de noms
    noms = [p.get('nom') for p in persos]
    vus = set()
    for n in noms:
        if n in vus:
            dur.append('nom en double : ' + str(n))
        vus.add(n)

    # champs manquants
    requis = regle['attrs'] + regle['autres']
    for p in persos:
        nom = p.get('nom', '(sans nom)')
        for c in requis:
            if c not in p:
                dur.append('%s : champ manquant « %s »' % (nom, c))
        for c in regle['listes']:
            if c in p and not isinstance(p[c], list):
                dur.append('%s : « %s » devrait etre une liste' % (nom, c))
        for c in regle['nombres']:
            if c in p and p[c] is not None and not isinstance(p[c], (int, float)):
                dur.append('%s : « %s » devrait etre un nombre' % (nom, c))
        for c in regle['nombres']:
            if c not in regle['nombres_nullables'] and p.get(c) is None:
                dur.append('%s : « %s » ne peut pas etre vide' % (nom, c))

    # valeurs ordinales presentes dans l'echelle du registre
    for champ, echelle in regle['echelles'].items():
        valeurs = d.get(echelle)
        if not isinstance(valeurs, list):
            dur.append('echelle « %s » absente du registre' % echelle)
            continue
        connues = set(valeurs) | set(regle.get('hors_echelle', []))
        for p in persos:
            v = p.get(champ)
            if v is not None and v not in connues:
                dur.append('%s : « %s » = %r hors de l\'echelle %s'
                           % (p.get('nom'), champ, v, echelle))

    # bassins de mode non vides
    for m in d.get('modes', []):
        champ = m.get('champ')
        if not champ:
            taille = len(persos)
        else:
            taille = sum(1 for p in persos
                         if p.get(champ) and p.get(champ) != m.get('sauf'))
        if taille == 0:
            dur.append('bassin vide pour le mode « %s »' % m.get('id'))
        elif taille < 10:
            mou.append('bassin etroit pour « %s » : %d personnages'
                       % (m.get('id'), taille))

    # portraits
    dossier = os.path.join(RACINE, 'assets', 'img', 'photos', univers)
    if os.path.isdir(dossier):
        presents = {f.rsplit('.', 1)[0] for f in os.listdir(dossier)}
        manquants = [p['nom'] for p in persos if slug(p['nom']) not in presents]
        if manquants:
            mou.append('%d portrait(s) manquant(s) : %s'
                       % (len(manquants), ', '.join(manquants[:6])
                          + ('…' if len(manquants) > 6 else '')))
        orphelins = presents - {slug(p['nom']) for p in persos}
        if orphelins:
            mou.append('%d portrait(s) sans personnage : %s'
                       % (len(orphelins), ', '.join(sorted(orphelins)[:6])))
    else:
        mou.append('dossier de portraits absent : ' + dossier)

    return dur, mou


def main():
    cibles = sys.argv[1:] or sorted(ATTENDUS)
    total = 0
    for u in cibles:
        dur, mou = verifier(u)
        print('=== %s ===' % u)
        if not dur and not mou:
            print('  rien a signaler')
        for m in dur:
            print('  ERREUR  ' + m)
        for m in mou:
            print('  note    ' + m)
        print()
        total += len(dur)
    if total:
        print('%d anomalie(s) bloquante(s).' % total)
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
