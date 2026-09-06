# -*- coding: utf-8 -*-
"""
Telecharge les portraits des personnages depuis le One Piece Wiki et les
prepare pour le site.

    python outils/telecharger-portraits.py [one-piece|naruto|inazuma|pokemon]

Chaque image est recadree sur le buste, reduite en 200x200 et enregistree
dans  assets/img/photos/<slug>.jpg. Relancer le script ne retelecharge
que ce qui manque. Une image absente laisse simplement la plaque generee.

Images (c) Eiichiro Oda / Shueisha / Toei Animation, recuperees depuis le
One Piece Wiki pour un usage personnel.
"""
import io, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

try:
    from PIL import Image
except ImportError:
    Image = None
    print("Pillow absent : les images seront enregistrees telles quelles.")
    print("Pour des fichiers plus legers : pip install pillow\n")

PAPIER = (234, 222, 192)
TAILLE = 200
RACINE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Les deux wikis n'attendent pas la meme presentation. Fandom sert
# volontiers un agent de navigateur ; minecraft.wiki, lui, repond 403 et
# une page « Please wait » a tout ce qui ressemble a un navigateur, et
# accepte un agent nomme. Chaque univers dit lequel il lui faut.
UA_NAVIGATEUR = "Mozilla/5.0 (bureau-des-primes; usage personnel)"
UA_NOMME = "BureauDesPrimes/1.0 (projet de fan)"

# Un registre par univers, avec son wiki et son dossier de portraits.
# Les deux wikis ne nomment pas leurs images de la meme facon :
#  - One Piece met « Infobox » dans le nom du fichier, on peut donc les
#    reperer et les noter (anime avant manga, portrait avant panoramique) ;
#  - Naruto ne le fait pas du tout, mais son infobox declare le portrait
#    dans un champ « Images onglets ». C'est de la qu'il faut le lire,
#    sinon on recupere une image de technique au hasard.
UNIVERS = {
    "one-piece": {"api": "https://onepiece.fandom.com/fr/api.php",
                  "strategie": "infobox-nommee"},
    "naruto":    {"api": "https://naruto.fandom.com/fr/api.php",
                  "strategie": "champ-image",
                  "modele": "{{Infobox/Personnage",
                  "champs": ["Images onglets", "Image"]},
    # Inazuma Eleven declare ses visuels dans une <gallery> a l'interieur
    # du champ Image de l'infobox : la premiere vignette est le portrait
    # de la serie d'origine, c'est celle qu'on veut.
    "inazuma":   {"api": "https://inazuma-eleven.fandom.com/fr/api.php",
                  "strategie": "champ-image",
                  "modele": "{{Personnage",
                  "champs": ["Image"]},
    # Pokemon ne passe pas par un wiki : PokeAPI publie les rendus
    # Pokemon HOME a une adresse deduite du numero du Pokedex. Pas de
    # recherche, pas d'heuristique — le registre porte deja le numero.
    # Bleach nomme son visuel dans le champ « image » de l'infobox, sous
    # trois modeles differents selon l'anciennete de la page : « Infobox
    # perso », « Infobox Personnages », « Infobox/Arrancar ». On vise le
    # prefixe commun.
    "bleach":    {"api": "https://bleach.fandom.com/fr/api.php",
                  "strategie": "champ-image",
                  "modele": "{{Infobox",
                  "champs": ["Images onglets", "image", "Image"]},
    # Minecraft passe par le wiki ANGLOPHONE. Le champ « image » du wiki
    # francophone contient ce qui traine : une capture de village pour
    # l'abeille, un inventaire pour l'ane, une vignette de Creeper pour le
    # cube de magma. Le wiki anglophone publie un rendu par creature, et
    # « File:<Nom>.png » y redirige vers la derniere version. Il faut donc
    # le nom anglais, d'ou la table ci-dessous.
    # minecraft.wiki, pas minecraft.fandom.com : le second est l'ancien
    # wiki, fige depuis le depart de la communaute, et il ignore tout ce
    # qui est arrive depuis — le cuivre, la resine, le soufre, les
    # epreuves. Cinquante et un blocs y restaient sans visuel.
    "minecraft": {"api": "https://minecraft.wiki/api.php",
                  "strategie": "fichier-anglais",
                  "cadrage": "entier",
                  "ua": UA_NOMME},
    # Pokemon ne passe pas par un wiki : PokeAPI publie les rendus
    # Les rendus sont detoures sur fond transparent : les cadrer « au
    # buste » comme une capture d'anime coupait la moitie du Pokemon —
    # Dracaufeu perdait ses ailes, Roucarnage sa tete. C'est un corps
    # entier aux proportions libres, donc le meme cadrage que Minecraft.
    "pokemon":   {"api": None,
                  "strategie": "url-directe",
                  "cadrage": "entier",
                  # Le rendu HOME d'abord, l'illustration officielle en
                  # repli : HOME s'arrete avant les dernieres generations.
                  # L'adresse suit « sprite » et non le numero du
                  # Pokedex : Raichu et Raichu d'Alola partagent le
                  # numero 26 mais n'ont evidemment pas le meme rendu.
                  "gabarits": [
                      "https://raw.githubusercontent.com/PokeAPI/sprites/"
                      "master/sprites/pokemon/other/home/{sprite}.png",
                      "https://raw.githubusercontent.com/PokeAPI/sprites/"
                      "master/sprites/pokemon/other/official-artwork/{sprite}.png",
                  ]},
}

# Le nom anglais de chaque creature, pour retrouver son rendu.
NOMS_EN = {
    "Abeille": "Bee", "Allay": "Allay", "Araignée": "Spider",
    "Araignée venimeuse": "Cave Spider", "Blaze": "Blaze",
    "Champimeuh": "Mooshroom", "Chat": "Cat", "Chauve-souris": "Bat",
    "Cheval": "Horse", "Cheval-squelette": "Skeleton Horse", "Chèvre": "Goat",
    "Cochon": "Pig", "Creeper": "Creeper", "Cube de magma": "Magma Cube",
    "Dauphin": "Dolphin", "Dromadaire": "Camel", "Ender Dragon": "Ender Dragon",
    "Enderman": "Enderman", "Endermite": "Endermite", "Gardien": "Guardian",
    "Golem de fer": "Iron Golem", "Golem de neige": "Snow Golem",
    "Grenouille": "Frog", "Hoglin": "Hoglin", "Illusionniste": "Illusioner",
    "Lama": "Llama", "Lapin": "Rabbit", "Loup": "Wolf", "Mouton": "Sheep",
    "Noyé": "Drowned", "Ocelot": "Ocelot", "Ours blanc": "Polar Bear",
    "Panda": "Panda", "Perroquet": "Parrot", "Phantom": "Phantom",
    "Piglin": "Piglin", "Piglin barbare": "Piglin Brute",
    "Piglin zombifié": "Zombified Piglin", "Pillard": "Pillager",
    "Poisson d'argent": "Silverfish", "Poule": "Chicken", "Poulpe": "Squid",
    "Poulpe luisant": "Glow Squid", "Ravageur": "Ravager", "Renard": "Fox",
    "Shulker": "Shulker", "Slime": "Slime", "Sorcière": "Witch",
    "Squelette": "Skeleton", "Tortue": "Turtle", "Têtard": "Tadpole",
    "Vache": "Cow", "Vex": "Vex", "Villageois": "Villager",
    "Vindicateur": "Vindicator", "Warden": "Warden", "Wither": "Wither",
    "Wither squelette": "Wither Skeleton", "Zoglin": "Zoglin",
    "Zombie": "Zombie", "Zombie momifié": "Husk",
    "Zombie-villageois": "Zombie Villager", "Âne": "Donkey",
    "Évocateur": "Evoker",
}

# Cinq creatures n'ont pas de rendu « generique » : le wiki en publie un
# par variante. On nomme celui qui vient a l'esprit quand on entend le mot.
NOMS_EN.update({
    "Chat": "Tabby Cat", "Cheval": "White Horse", "Lapin": "Brown Rabbit JE1 BE1",
    "Perroquet": "Red Parrot", "Villageois": "Plains Farmer",
})

# Le nom anglais de chaque bloc et objet. Meme raison que pour les
# creatures : « File:<Nom>.png » du wiki anglophone donne la texture
# officielle, sur fond transparent et a jour.
# Les cinq cent quarante-huit noms anglais releves par
# construire-minecraft.py, via le lien interlangue de chaque page. La
# table ecrite a la main plus bas reste devant : elle corrige les cas ou
# le fichier d'image ne porte pas le nom de la page.
try:
    with io.open(os.path.join(RACINE, "outils", "minecraft-noms-en.json"),
                 encoding="utf-8") as _f:
        NOMS_EN_WIKI = json.load(_f)
except (IOError, ValueError):
    NOMS_EN_WIKI = {}

NOMS_EN_BLOCS = {
    # Les pages de concept — « Dalle », « Epee », « Porte » — n'ont pas
    # de fichier a leur nom : le wiki publie une image par materiau. On
    # nomme celle qui vient a l'esprit quand on entend le mot.
    "Dalle": "Oak Slab", "Escalier": "Oak Stairs", "Muret": "Cobblestone Wall",
    "Porte": "Oak Door", "Porte en bois": "Oak Door", "Trappe": "Oak Trapdoor",
    "Trappe en bois": "Oak Trapdoor", "Bouton": "Stone Button",
    "Bouton en bois": "Oak Button", "Plaque de pression": "Stone Pressure Plate",
    "Plaque de pression en bois": "Oak Pressure Plate",
    "Portillon": "Oak Fence Gate", "Barrière en bois": "Oak Fence",
    "Épée": "Diamond Sword", "Pioche": "Diamond Pickaxe", "Hache": "Diamond Axe",
    "Pelle": "Diamond Shovel", "Houe": "Diamond Hoe",
    "Planches": "Oak Planks", "Bûche": "Oak Log", "Bûche écorcée": "Stripped Oak Log",
    "Bois": "Oak Wood", "Bois écorcé": "Stripped Oak Wood", "Feuilles": "Oak Leaves",
    "Tas de feuilles": "Leaf Litter", "Bateau": "Oak Boat", "Pancarte": "Oak Sign",
    "Lit": "Red Bed", "Tapis": "White Carpet", "Bannière": "White Banner",
    "Teinture": "Red Dye", "Disque": "Music Disc 13", "Corail": "Tube Coral",
    "Corail mort": "Dead Tube Coral", "Bloc de corail": "Tube Coral Block",
    "Gorgone de corail": "Tube Coral Fan",
    "Verre coloré": "White Stained Glass", "Vitre colorée": "White Stained Glass Pane",
    "Terre cuite colorée": "White Terracotta",
    "Terre cuite émaillée": "White Glazed Terracotta",
    "Béton en poudre": "White Concrete Powder", "Chaîne en fer": "Chain",
    "Tulipe": "Red Tulip", "Buisson": "Bush", "Étagère": "Oak Shelf",
    "Modèle de forge": "Netherite Upgrade Smithing Template",
    "Amélioration en netherite": "Netherite Upgrade Smithing Template",
    "Tesson de poterie": "Angler Pottery Sherd",
    "Bloc infesté": "Infested Stone", "Nylium": "Crimson Nylium",
    "Coffre-fort": "Vault", "Poisson-globe (objet)": "Pufferfish",
    "Poisson tropical (objet)": "Tropical Fish",

    # Les butins de creatures qui n'etaient pas dans la table des blocs :
    # ils y sont entres quand les deux registres ont fusionne.
    "Boule de neige": "Snowball", "Bœuf cru": "Raw Beef",
    "Carapace de shulker": "Shulker Shell", "Coquelicot": "Poppy",
    "Corne de chèvre": "Goat Horn", "Cristal de prismarine": "Prismarine Crystals",
    "Crâne de wither squelette": "Wither Skeleton Skull",
    "Disque de musique": "Music Disc 13 JE1 BE1", "Lapin cru": "Raw Rabbit",
    "Membrane de phantom": "Phantom Membrane", "Morue crue": "Raw Cod",
    "Mouton cru": "Raw Mutton", "Patte de lapin": "Rabbit's Foot",
    "Peau de lapin": "Rabbit Hide", "Poche d'encre": "Ink Sac",
    "Poche d'encre luminescente": "Glow Ink Sac", "Porc cru": "Raw Porkchop",
    "Poulet cru": "Raw Chicken", "Pépite d'or": "Gold Nugget",
    "Saumon cru": "Raw Salmon", "Selle": "Saddle", "Sucre": "Sugar",
    "Totem d'immortalité": "Totem of Undying", "Écaille": "Scute",
    "Œuf de dragon": "Dragon Egg",

    "Alambic": "Brewing Stand",
    "Arbalète": "Crossbow",
    "Arc": "Bow",
    "Ardoise des abîmes": "Deepslate",
    "Argile": "Clay",
    "Balise": "Beacon",
    "Bambou": "Bamboo",
    "Bloc d'améthyste": "Block of Amethyst",
    "Bloc d'herbe": "Grass Block",
    "Bouclier": "Shield",
    "Boule de slime": "Slimeball",
    "Boussole": "Compass",
    "Bouton": "Stone Button",
    "Brique": "Bricks",
    "Briquet": "Flint and Steel",
    "Bâton": "Stick",
    "Bâton de Blaze": "Blaze Rod",
    "Béton": "White Concrete",
    "Bûche de cerisier": "Cherry Log",
    "Bûche de chêne": "Oak Log",
    "Bûche de mangrove": "Mangrove Log",
    "Calcite": "Calcite",
    "Canne à pêche": "Fishing Rod",
    "Carotte": "Carrot",
    "Casque en diamant": "Diamond Helmet",
    "Chair putréfiée": "Rotten Flesh",
    "Charbon": "Coal",
    "Chaudron": "Cauldron",
    "Cisailles": "Shears",
    "Citrouille": "Pumpkin",
    "Coffre": "Chest",
    "Comparateur": "Redstone Comparator",
    "Cookie": "Cookie",
    "Corde": "String",
    "Crème de magma": "Magma Cream",
    "Cuir": "Leather",
    "Diamant": "Diamond",
    "Distributeur": "Dispenser",
    "Débris antiques": "Ancient Debris",
    "Enclume": "Anvil",
    "Entonnoir": "Hopper",
    "Feuilles de chêne": "Oak Leaves",
    "Flèche": "Arrow",
    "Four": "Furnace",
    "Fruit du Chorus": "Chorus Fruit",
    "Glace": "Ice",
    "Gravier": "Gravel",
    "Grès": "Sandstone",
    "Gâteau": "Cake",
    "Hache en fer": "Iron Axe JE5 BE2",
    "Horloge": "Clock",
    "Houe en fer": "Iron Hoe",
    "Laine": "White Wool",
    "Lapis-lazuli": "Lapis Lazuli",
    "Larme de Ghast": "Ghast Tear",
    "Levier": "Lever",
    "Lingot d'or": "Gold Ingot",
    "Lingot de cuivre": "Copper Ingot",
    "Lingot de fer": "Iron Ingot",
    "Lingot de netherite": "Netherite Ingot",
    "Longue-vue": "Spyglass",
    "Melon": "Melon Slice",
    "Minerai d'or": "Gold Ore",
    "Minerai d'émeraude": "Emerald Ore",
    "Minerai de charbon": "Coal Ore",
    "Minerai de cuivre": "Copper Ore",
    "Minerai de diamant": "Diamond Ore",
    "Minerai de fer": "Iron Ore",
    "Minerai de lapis-lazuli": "Lapis Lazuli Ore",
    "Minerai de redstone": "Redstone Ore",
    "Mousse": "Moss Block",
    "Mycélium": "Mycelium",
    "Neige": "Snow Block",
    "Netherrack": "Netherrack",
    "Nid d'abeille": "Beehive",
    "Observateur": "Observer",
    "Obsidienne": "Obsidian",
    "Os": "Bone",
    "Pain": "Bread",
    "Pelle en fer": "Iron Shovel",
    "Perle de l'Ender": "Ender Pearl",
    "Pierraille": "Cobblestone",
    "Pierre": "Stone",
    "Pierre de l'End": "End Stone",
    "Pierre lumineuse": "Glowstone",
    "Pioche en bois": "Wooden Pickaxe",
    "Pioche en diamant": "Diamond Pickaxe",
    "Pioche en fer": "Iron Pickaxe",
    "Pioche en netherite": "Netherite Pickaxe",
    "Pioche en pierre": "Stone Pickaxe",
    "Piston": "Piston",
    "Planches de chêne": "Oak Planks",
    "Plaque de pression": "Stone Pressure Plate",
    "Plastron en diamant": "Diamond Chestplate",
    "Plume": "Feather",
    "Pomme": "Apple",
    "Pomme de terre": "Potato",
    "Pomme dorée": "Golden Apple",
    "Porc cuit": "Cooked Porkchop",
    "Poudre de redstone": "Redstone Dust",
    "Poudre à canon": "Gunpowder",
    "Prismarine": "Prismarine",
    "Purpur": "Purpur Block",
    "Quartz du Nether": "Block of Quartz",
    "Rail": "Rail",
    "Roche-mère": "Bedrock",
    "Répéteur": "Redstone Repeater",
    "Sable": "Sand",
    "Sculk": "Sculk",
    "Seau": "Bucket",
    "Silex": "Flint",
    "Soupe de champignons": "Mushroom Stew",
    "Steak": "Steak",
    "TNT": "TNT",
    "Table d'enchantement": "Enchanting Table",
    "Terre": "Dirt",
    "Terre cuite": "Terracotta",
    "Torche": "Torch",
    # « Redstone Torch.png » n existe pas : le wiki ne publie que les
    # versions numerotees de cette texture.
    "Torche de redstone": "Redstone Torch JE4",
    "Trident": "Trident",
    "Tuf": "Tuff",
    "Verre": "Glass",
    "Écho": "Echo Shard",
    "Élytres": "Elytra",
    "Émeraude": "Emerald",
    "Épée en diamant": "Diamond Sword",
    "Établi": "Crafting Table",
    "Étoile du Nether": "Nether Star",
    "Œil d'araignée": "Spider Eye",
    "Œil de l'Ender": "Eye of Ender",
}

# Personnages dont le nom d'usage ne mene pas a la bonne page.
ALIAS = {
    "a": "A (Quatrième Raikage)",
    "zetsu-noir": "Tobi",
    "torune-aburame": "Torune",
}
# --refaire : refait aussi les portraits deja presents. Sans lui le script
# ne comble que les trous, ce qui est le bon defaut mais empeche de
# reappliquer un cadrage corrige.
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
REFAIRE = "--refaire" in sys.argv
UNIV = ARGS[0] if ARGS else "one-piece"
if UNIV not in UNIVERS:
    sys.exit("Univers inconnu : %s. Attendu : %s"
             % (UNIV, ", ".join(UNIVERS)))
API = UNIVERS[UNIV]["api"]
UA = {"User-Agent": UNIVERS[UNIV].get("ua", UA_NAVIGATEUR)}
DOSSIER = os.path.join(RACINE, "assets", "img", "photos", UNIV)
REGISTRE = os.path.join(RACINE, "assets", "data", UNIV + ".json")

URLS = {
# Le Warden : son champ « image » pointe un GIF Tenor externe, pas un
# fichier du wiki. Le rendu officiel est sur le wiki anglophone.
"minecraft:warden": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/7/7f/Warden_JE1_BE1.png/revision/latest",
"monkey-d-luffy": "https://static.wikia.nocookie.net/onepiece/images/6/6d/Monkey_D._Luffy_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20260611004637",
"roronoa-zoro": "https://static.wikia.nocookie.net/onepiece/images/5/52/Roronoa_Zoro_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20241029161719",
"nami": "https://static.wikia.nocookie.net/onepiece/images/6/68/Nami_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20260315214841",
"usopp": "https://static.wikia.nocookie.net/onepiece/images/3/35/Usopp_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20221127233827",
"sanji": "https://static.wikia.nocookie.net/onepiece/images/b/b6/Sanji_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240122012744",
"tony-tony-chopper": "https://static.wikia.nocookie.net/onepiece/images/a/af/Tony_Tony_Chopper_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240720150824",
"nico-robin": "https://static.wikia.nocookie.net/onepiece/images/b/bc/Nico_Robin_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20260610121757",
"franky": "https://static.wikia.nocookie.net/onepiece/images/8/8c/Franky_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20241110020715",
"brook": "https://static.wikia.nocookie.net/onepiece/images/4/41/Brook_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20161016160925",
"jinbe": "https://static.wikia.nocookie.net/onepiece/images/8/81/Jinbe_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20170521201349",
"nefertari-vivi": "https://static.wikia.nocookie.net/onepiece/images/0/09/Nefertari_Vivi_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20190505023647",
"shanks-le-roux": "https://static.wikia.nocookie.net/onepiece/images/6/66/Shanks_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240829145447",
"kaido": "https://static.wikia.nocookie.net/onepiece/images/2/2d/Kaidou_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20231102015517",
"big-mom": "https://static.wikia.nocookie.net/onepiece/images/d/d8/Charlotte_Linlin_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20180423150804",
"barbe-noire": "https://static.wikia.nocookie.net/onepiece/images/f/ff/Marshall_D._Teach_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240128044952",
"barbe-blanche": "https://static.wikia.nocookie.net/onepiece/images/b/b7/Edward_Newgate_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20220926165737",
"gol-d-roger": "https://static.wikia.nocookie.net/onepiece/images/2/24/Gol_D._Roger_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230612100153",
"silvers-rayleigh": "https://static.wikia.nocookie.net/onepiece/images/b/b1/Silvers_Rayleigh_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230601221758",
"monkey-d-garp": "https://static.wikia.nocookie.net/onepiece/images/e/e1/Monkey_D._Garp_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230207160645",
"dracule-mihawk": "https://static.wikia.nocookie.net/onepiece/images/b/bf/Dracule_Mihawk_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20151222105910",
"trafalgar-d-water-law": "https://static.wikia.nocookie.net/onepiece/images/4/4d/Trafalgar_D._Water_Law_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230124163510",
"eustass-kid": "https://static.wikia.nocookie.net/onepiece/images/4/47/Eustass_Kid_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240505021859",
"killer": "https://static.wikia.nocookie.net/onepiece/images/7/70/Killer_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20210815025653",
"basil-hawkins": "https://static.wikia.nocookie.net/onepiece/images/f/f8/Basil_Hawkins_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230906163534",
"scratchmen-apoo": "https://static.wikia.nocookie.net/onepiece/images/d/d0/Scratchmen_Apoo_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20210426143015",
"x-drake": "https://static.wikia.nocookie.net/onepiece/images/0/04/X_Drake_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20200209080003",
"jewelry-bonney": "https://static.wikia.nocookie.net/onepiece/images/6/62/Jewelry_Bonney_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230123001318",
"capone-bege": "https://static.wikia.nocookie.net/onepiece/images/9/99/Capone_Bege_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20160911163015",
"urouge": "https://static.wikia.nocookie.net/onepiece/images/f/fb/Urouge_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230126223235",
"boa-hancock": "https://static.wikia.nocookie.net/onepiece/images/f/f0/Boa_Hancock_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230126022456",
"crocodile": "https://static.wikia.nocookie.net/onepiece/images/f/fd/Crocodile_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230125235528",
"donquixote-doflamingo": "https://static.wikia.nocookie.net/onepiece/images/7/7e/Donquixote_Doflamingo_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20231017082245",
"bartholomew-kuma": "https://static.wikia.nocookie.net/onepiece/images/8/8d/Bartholomew_Kuma_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20221012030835",
"gecko-moria": "https://static.wikia.nocookie.net/onepiece/images/b/be/Gecko_Moria_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20181127062446",
"baggy-le-clown": "https://static.wikia.nocookie.net/onepiece/images/f/f7/Buggy_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240813025900",
"edward-weevil": "https://static.wikia.nocookie.net/onepiece/images/b/be/Edward_Weevil_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20160807113654",
"akainu-sakazuki": "https://static.wikia.nocookie.net/onepiece/images/d/d7/Sakazuki_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20220829052511",
"kizaru-borsalino": "https://static.wikia.nocookie.net/onepiece/images/1/14/Borsalino_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20190603023753",
"aokiji-kuzan": "https://static.wikia.nocookie.net/onepiece/images/d/d6/Kuzan_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240811021341",
"fujitora-issho": "https://static.wikia.nocookie.net/onepiece/images/e/e8/Issho_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20220718140829",
"ryokugyu-aramaki": "https://static.wikia.nocookie.net/onepiece/images/0/05/Aramaki_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240930142146",
"smoker": "https://static.wikia.nocookie.net/onepiece/images/c/c4/Smoker_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20221101011905",
"tashigi": "https://static.wikia.nocookie.net/onepiece/images/1/1e/Tashigi_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20251127120726",
"coby": "https://static.wikia.nocookie.net/onepiece/images/b/b8/Koby_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20241114130518",
"sengoku": "https://static.wikia.nocookie.net/onepiece/images/2/24/Sengoku_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20210208064630",
"king": "https://static.wikia.nocookie.net/onepiece/images/8/8f/King_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230423142631",
"queen": "https://static.wikia.nocookie.net/onepiece/images/5/52/Queen_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20200920174728",
"jack": "https://static.wikia.nocookie.net/onepiece/images/3/3f/Jack_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20161009223938",
"ulti": "https://static.wikia.nocookie.net/onepiece/images/d/dc/Ulti_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240831170217",
"page-one": "https://static.wikia.nocookie.net/onepiece/images/4/46/Page_One_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20211128115519",
"who-s-who": "https://static.wikia.nocookie.net/onepiece/images/9/94/Who%27s-Who_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20211201215156",
"black-maria": "https://static.wikia.nocookie.net/onepiece/images/e/e2/Black_Maria_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20210808144206",
"yamato": "https://static.wikia.nocookie.net/onepiece/images/b/bd/Yamato_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20260126165014",
"charlotte-katakuri": "https://static.wikia.nocookie.net/onepiece/images/2/2e/Charlotte_Katakuri_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230204155539",
"charlotte-cracker": "https://static.wikia.nocookie.net/onepiece/images/6/64/Charlotte_Cracker_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20170730021804",
"charlotte-smoothie": "https://static.wikia.nocookie.net/onepiece/images/c/c5/Charlotte_Smoothie_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20180423150946",
"charlotte-perospero": "https://static.wikia.nocookie.net/onepiece/images/7/7e/Charlotte_Perospero_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20211101122146",
"charlotte-pudding": "https://static.wikia.nocookie.net/onepiece/images/6/60/Charlotte_Pudding_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20250106015531",
"charlotte-oven": "https://static.wikia.nocookie.net/onepiece/images/f/f0/Charlotte_Oven_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20181028111159",
"marco-le-phenix": "https://static.wikia.nocookie.net/onepiece/images/4/4a/Polo_Marco_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20221010015200",
"portgas-d-ace": "https://static.wikia.nocookie.net/onepiece/images/4/4f/Portgas_D._Ace_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240629132600",
"izo": "https://static.wikia.nocookie.net/onepiece/images/8/81/Izou_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20210919035558",
"jozu": "https://static.wikia.nocookie.net/onepiece/images/6/61/Jozu_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20220702104233",
"vista": "https://static.wikia.nocookie.net/onepiece/images/7/78/Vista_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20180131180522",
"sabo": "https://static.wikia.nocookie.net/onepiece/images/c/c2/Sabo_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230804035141",
"monkey-d-dragon": "https://static.wikia.nocookie.net/onepiece/images/f/f5/Monkey_D._Dragon_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20250621010227",
"emporio-ivankov": "https://static.wikia.nocookie.net/onepiece/images/d/de/Emporio_Ivankov_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20180624120810",
"karasu": "https://static.wikia.nocookie.net/onepiece/images/9/9a/Karasu_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20190414113619",
"rob-lucci": "https://static.wikia.nocookie.net/onepiece/images/d/d7/Rob_Lucci_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230102052113",
"kaku": "https://static.wikia.nocookie.net/onepiece/images/0/09/Kaku_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20221127204534",
"blueno": "https://static.wikia.nocookie.net/onepiece/images/2/2b/Blueno_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240915021752",
"kin-emon": "https://static.wikia.nocookie.net/onepiece/images/e/ec/Kin%27emon_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20191124100115",
"kozuki-oden": "https://static.wikia.nocookie.net/onepiece/images/7/7a/Kouzuki_Oden_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20210425071747",
"kozuki-momonosuke": "https://static.wikia.nocookie.net/onepiece/images/8/8b/Kouzuki_Momonosuke_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240904123638",
"caesar-clown": "https://static.wikia.nocookie.net/onepiece/images/a/a6/Caesar_Clown_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20221101011307",
"dr-vegapunk": "https://static.wikia.nocookie.net/onepiece/images/b/b9/Vegapunk_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240428020834",
"enel": "https://static.wikia.nocookie.net/onepiece/images/a/ad/Enel_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230520213625",
"bartolomeo": "https://static.wikia.nocookie.net/onepiece/images/e/eb/Bartolomeo_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20221027202808",
"cavendish": "https://static.wikia.nocookie.net/onepiece/images/a/a1/Cavendish_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20140224010824",
"hajrudin": "https://static.wikia.nocookie.net/onepiece/images/b/b8/Hajrudin_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240319195654",
"bellamy": "https://static.wikia.nocookie.net/onepiece/images/2/27/Bellamy_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230116235201",
"perona": "https://static.wikia.nocookie.net/onepiece/images/4/4a/Perona_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20221124200121",
"bepo": "https://static.wikia.nocookie.net/onepiece/images/5/5f/Bepo_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20231210123641",
"carrot": "https://static.wikia.nocookie.net/onepiece/images/e/e2/Carrot_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20180826142459",
"pedro": "https://static.wikia.nocookie.net/onepiece/images/c/c8/Pedro_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20170423080015",
"arlong": "https://static.wikia.nocookie.net/onepiece/images/0/01/Arlong_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230403145629",
"don-krieg": "https://static.wikia.nocookie.net/onepiece/images/b/bb/Krieg_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230123170612",
"kuro": "https://static.wikia.nocookie.net/onepiece/images/7/7e/Kuro_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20231006042805",
"bon-clay-bentham": "https://static.wikia.nocookie.net/onepiece/images/0/0e/Bentham_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20160929070742",
"daz-bones": "https://static.wikia.nocookie.net/onepiece/images/e/e9/Daz_Bonez_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20221102004113",
"dorry": "https://static.wikia.nocookie.net/onepiece/images/2/2d/Dorry_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20250927120409",
"brogy": "https://static.wikia.nocookie.net/onepiece/images/b/bf/Brogy_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20250824161255",
"nefertari-cobra": "https://static.wikia.nocookie.net/onepiece/images/7/7f/Nefertari_Cobra_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20170219154108",
"shirahoshi": "https://static.wikia.nocookie.net/onepiece/images/c/c1/Shirahoshi_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20240814220909",
"rebecca": "https://static.wikia.nocookie.net/onepiece/images/f/f6/Rebecca_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20190519094508",
"vinsmoke-judge": "https://static.wikia.nocookie.net/onepiece/images/6/6f/Vinsmoke_Judge_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20170626124958",
"vinsmoke-reiju": "https://static.wikia.nocookie.net/onepiece/images/a/a3/Vinsmoke_Reiju_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20231211104854",
"magellan": "https://static.wikia.nocookie.net/onepiece/images/9/9e/Magellan_Anime_Post_Timeskip_Infobox.png/revision/latest/scale-to-width-down/220?cb=20251102163212",
"crocus": "https://static.wikia.nocookie.net/onepiece/images/3/34/Crocus_Anime_Infobox.png/revision/latest/scale-to-width-down/220?cb=20230403010215"
}


def prepare(brut, cible):
    if Image is None:
        io.open(cible, "wb").write(brut)
        return
    im = Image.open(io.BytesIO(brut))
    transparent = im.mode in ("RGBA", "LA", "P")
    if transparent:
        im = im.convert("RGBA")

    # Deux cadrages. « buste » convient a un portrait de personnage : on
    # coupe un carre serre ancre en haut, la tete y tombe toujours bien.
    # « entier » sert aux rendus de creature, qui sont des corps complets
    # aux proportions libres — le dragon est large et plat, le Blaze
    # haut et etroit. Les rogner par le haut leur coupait la tete.
    if UNIVERS[UNIV].get("cadrage") == "entier" and transparent:
        boite = im.getbbox()
        if boite:
            im = im.crop(boite)
        # Une marge : colle aux bords, le sujet touchait le cadre et la
        # vignette paraissait rognee alors qu'elle est entiere.
        cote = int(max(im.size) * 1.08)
        carre = Image.new("RGBA", (cote, cote), (0, 0, 0, 0))
        carre.paste(im, ((cote - im.width) // 2, (cote - im.height) // 2))
        im = carre
        fond = Image.new("RGB", im.size, PAPIER)
        fond.paste(im, mask=im.split()[-1])
        im = fond.resize((TAILLE, TAILLE), Image.LANCZOS)
        im.save(cible, "JPEG", quality=84, optimize=True)
        return

    if transparent:
        fond = Image.new("RGB", im.size, PAPIER)
        fond.paste(im, mask=im.split()[-1])
        im = fond
    else:
        im = im.convert("RGB")
    w, h = im.size
    cote = min(int(w * 0.72), h)                  # carre serre, ancre en haut
    x = (w - cote) // 2
    im = im.crop((x, 0, x + cote, cote)).resize((TAILLE, TAILLE), Image.LANCZOS)
    im.save(cible, "JPEG", quality=84, optimize=True)


# Le slug vit dans outils/commun.py, avec le verificateur : c'est la
# meme regle que photoSrc() cote navigateur, et elle doit rester unique.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import slug  # noqa: E402


def cle_comparaison(s):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", s.lower()))


def api(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def url_fichier(fichier):
    """L'adresse d'un fichier du wiki, en vignette de 400 px."""
    d = api({"action": "query", "titles": fichier, "prop": "imageinfo",
             "iiprop": "url", "iiurlwidth": "400",
             "format": "json", "formatversion": "2"})
    pages = d.get("query", {}).get("pages", [])
    if not pages:
        return None
    info = (pages[0].get("imageinfo") or [{}])[0]
    return info.get("thumburl") or info.get("url")


def image_infobox(titre):
    """
    Le portrait d'infobox d'une page.

    Une page porte des dizaines d'images ; on ne garde que celles dont le
    nom contient « Infobox », puis on les note. L'anime passe avant le
    manga (le reste du dossier est en couleur) et l'apres-ellipse avant
    l'avant-ellipse, comme les 99 portraits choisis a la main. Le nom du
    personnage departage les infobox d'armes ou de navires qui trainent
    sur la meme page.
    """
    d = api({"action": "query", "titles": titre, "prop": "images",
             "imlimit": "200", "format": "json", "formatversion": "2",
             "redirects": "1"})
    pages = d.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None, None
    vrai = pages[0].get("title") or titre
    fichiers = [i["title"] for i in (pages[0].get("images") or [])
                if "Infobox" in i["title"]][:30]
    if not fichiers:
        return vrai, None
    base = cle_comparaison(vrai.split()[0])

    # Les dimensions de tous les candidats en un appel : le cadrage
    # suppose un portrait, et certaines infobox sont des captures
    # panoramiques avec le nom incruste, qui se recadrent en bouillie.
    d = api({"action": "query", "titles": "|".join(fichiers),
             "prop": "imageinfo", "iiprop": "url|size", "iiurlwidth": "400",
             "format": "json", "formatversion": "2"})
    infos = {}
    for p in d.get("query", {}).get("pages", []):
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("thumburl") or ii.get("url"):
            infos[p.get("title")] = ii

    def note(t):
        n = cle_comparaison(t)
        ii = infos.get(t, {})
        h, w = ii.get("height", 0), ii.get("width", 1)
        # L'anime passe avant tout : le dossier est en couleur. Vient
        # ensuite le cadrage, puis l'apres-ellipse, puis le nom.
        return (6 if "anime" in n else 0) \
             + (4 if h >= w else 0) \
             + (2 if "postellipse" in n else 0) \
             + (3 if base and base in n else 0)

    if not infos:
        return vrai, None
    meilleur = max(infos, key=note)
    return vrai, infos[meilleur].get("thumburl") or infos[meilleur].get("url")


def image_de(titre):
    """Repli : l'image principale que le wiki associe a la page."""
    d = api({"action": "query", "titles": titre, "prop": "pageimages",
             "piprop": "thumbnail|original", "pithumbsize": "400",
             "format": "json", "formatversion": "2", "redirects": "1"})
    pages = d.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None, None
    p = pages[0]
    src = (p.get("thumbnail") or {}).get("source") \
        or (p.get("original") or {}).get("source")
    return p.get("title"), src


def image_champ(titre):
    """
    Le portrait declare par l'infobox, pour les wikis qui ne nomment pas
    leurs fichiers. On lit le champ image du modele et on prend le
    premier fichier cite : c'est l'onglet par defaut de la fiche.
    """
    d = api({"action": "parse", "page": titre, "prop": "wikitext",
             "format": "json", "formatversion": "2", "redirects": "1"})
    if "error" in d:
        return None, None
    txt = d.get("parse", {}).get("wikitext", "")
    vrai = d.get("parse", {}).get("title") or titre
    conf = UNIVERS[UNIV]
    i = txt.find(conf["modele"])
    if i < 0:
        return vrai, None
    bloc = txt[i:i + 4000]
    for champ in conf["champs"]:
        m = re.search(r"^\|\s*" + re.escape(champ) + r"\s*=\s*(.*)$", bloc, re.M)
        if not m:
            continue
        f = re.search(r"\[\[\s*(?:Fichier|File|Image)\s*:\s*([^\]|]+)", m.group(1))
        if f:
            return vrai, url_fichier("Fichier:" + f.group(1).strip())
    return vrai, None


def resoudre(nom):
    """
    Trouve la page du wiki pour un personnage, puis son portrait.

    On tente d'abord le nom tel quel, puis la recherche. Le titre trouve
    doit rester proche du nom cherche : sans ce garde-fou, la recherche
    ramenerait volontiers un episode ou un chapitre, et on collerait la
    mauvaise tete sur la bonne fiche.
    """
    if UNIVERS[UNIV]["strategie"] == "fichier-anglais":
        # Un seul registre Minecraft : creatures, blocs et objets y sont
        # melanges, donc les deux tables de noms aussi.
        en = NOMS_EN.get(nom) or NOMS_EN_BLOCS.get(nom) or NOMS_EN_WIKI.get(nom)
        if not en:
            return None, None
        d = api({"action": "query", "titles": "File:%s.png" % en,
                 "prop": "imageinfo", "iiprop": "url", "redirects": "1",
                 "format": "json", "formatversion": "2"})
        for pg in d.get("query", {}).get("pages", []):
            for i in pg.get("imageinfo", []):
                return en, i.get("url")
        return None, None

    nom = ALIAS.get(slug(nom), nom)
    ordre = ((image_champ, image_de) if UNIVERS[UNIV]["strategie"] == "champ-image"
             else (image_infobox, image_de))
    for chercheur in ordre:
        titre, src = chercheur(nom)
        if src:
            return titre, src
    d = api({"action": "query", "list": "search", "srsearch": nom,
             "format": "json", "formatversion": "2", "srlimit": "5"})
    attendu = cle_comparaison(nom)
    for r in d.get("query", {}).get("search", []):
        t = cle_comparaison(r["title"])
        if attendu in t or t in attendu:
            for chercheur in (image_infobox, image_de):
                titre, src = chercheur(r["title"])
                if src:
                    return titre, src
    return None, None


def a_traiter():
    """Chaque personnage du registre, avec son slug de fichier et sa fiche."""
    reg = json.load(io.open(REGISTRE, encoding="utf-8"))
    return [(p["nom"], slug(p["nom"]), p) for p in reg["persos"]]


def main():
    os.makedirs(DOSSIER, exist_ok=True)
    liste = a_traiter()
    total, faits, sautes, echecs = len(liste), 0, 0, []

    for i, (nom, cle, fiche_perso) in enumerate(sorted(liste, key=lambda x: x[1]), 1):
        cible = os.path.join(DOSSIER, cle + ".jpg")
        if os.path.exists(cible) and not REFAIRE:
            sautes += 1
            continue
        try:
            # La carte d'URL fait foi quand elle connait le personnage :
            # ce sont des images choisies a la main. Sinon on interroge
            # le wiki, ce qui evite d'y recoller une URL a chaque ajout.
            # La carte accepte deux formes de cle : « univers:slug » pour
            # un cas isole hors One Piece, « slug » pour la longue liste
            # One Piece historique.
            url = URLS.get(UNIV + ":" + cle) or (URLS.get(cle) if UNIV == "one-piece" else None)
            via = "carte"
            brut = None
            if not url and UNIVERS[UNIV]["strategie"] == "url-directe":
                for gabarit in UNIVERS[UNIV]["gabarits"]:
                    # Un registre construit avant les formes
                    # alternatives n'a pas de champ « sprite » : le
                    # numero du Pokedex y tenait seul ce role.
                    champs = dict(fiche_perso)
                    champs.setdefault("sprite", champs.get("numero"))
                    essai = gabarit.format(**champs)
                    try:
                        req = urllib.request.Request(essai, headers=UA)
                        with urllib.request.urlopen(req, timeout=45) as r:
                            brut = r.read()
                        url, via = essai, "direct"
                        break
                    except Exception:
                        continue      # gabarit suivant
                if brut is None:
                    raise LookupError("aucun rendu a cette adresse")
            if not url:
                page, url = resoudre(nom)
                via = "wiki:" + (page or "?")
            if not url:
                raise LookupError("aucune image trouvee")
            if brut is None:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=45) as r:
                    brut = r.read()
            prepare(brut, cible)
            faits += 1
            print("[%3d/%d] %-34s %s" % (i, total, cle, via))
            time.sleep(0.25)
        except Exception as e:
            echecs.append(cle)
            print("[%3d/%d] ECHEC %-32s %s" % (i, total, cle, e))

    print("\n%d telecharges, %d deja presents, %d sans image."
          % (faits, sautes, len(echecs)))
    if echecs:
        print("Sans portrait (plaque aux initiales) :", ", ".join(echecs))


if __name__ == "__main__":
    main()
