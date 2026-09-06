-- ===================================================================
--  Bureau des Primes — schéma MySQL / MariaDB
--
--  Appliqué par  php outils/migrer.php  (ou collé tel quel dans
--  phpMyAdmin). Ré-exécutable sans risque : tout est en CREATE TABLE
--  IF NOT EXISTS.
--
--  utf8mb4 partout : les noms de personnages portent des accents et
--  des apostrophes, et les pseudos Discord peuvent contenir n'importe
--  quel caractère, emoji compris.
-- ===================================================================

CREATE TABLE IF NOT EXISTS joueurs (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  discord_id   VARCHAR(32)  NOT NULL,
  pseudo       VARCHAR(64)  NOT NULL,
  nom_affiche  VARCHAR(64)      NULL,
  avatar       VARCHAR(64)      NULL,
  cree_le      DATETIME     NOT NULL,
  vu_le        DATETIME     NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY joueur_discord (discord_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Une ligne par avis résolu. La clé unique (joueur, univers, mode,
-- jour) fait respecter la règle du jeu : un seul résultat par registre,
-- par mode et par jour, le premier enregistré est le bon.
--
-- Le DEFAULT 'one-piece' sur `univers` sert la montée de version : les
-- parties écrites avant l'ouverture du second registre lui restent
-- rattachées sans reprise de données.
CREATE TABLE IF NOT EXISTS parties (
  id          BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
  joueur_id   BIGINT UNSIGNED  NOT NULL,
  univers     VARCHAR(24)      NOT NULL DEFAULT 'one-piece',
  mode        VARCHAR(16)      NOT NULL,
  jour        DATE             NOT NULL,
  numero_avis INT              NOT NULL,
  cible       VARCHAR(96)      NOT NULL,
  fiches      SMALLINT UNSIGNED NOT NULL,
  resolu_le   DATETIME         NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY partie_unique (joueur_id, univers, mode, jour),
  KEY classement_jour (univers, mode, jour, fiches),
  KEY historique (joueur_id, resolu_le),
  CONSTRAINT fk_parties_joueur FOREIGN KEY (joueur_id)
    REFERENCES joueurs (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Le détail des fiches versées, dans l'ordre. Sert à rejouer une
-- partie passée ; le serveur l'a déjà validée avant de l'écrire.
CREATE TABLE IF NOT EXISTS propositions (
  partie_id  BIGINT UNSIGNED   NOT NULL,
  rang       SMALLINT UNSIGNED NOT NULL,
  personnage VARCHAR(96)       NOT NULL,
  PRIMARY KEY (partie_id, rang),
  CONSTRAINT fk_propositions_partie FOREIGN KEY (partie_id)
    REFERENCES parties (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Compteurs dérivés de `parties`, tenus à jour à chaque enregistrement.
-- Recalculables à tout moment (voir outils/migrer.php --recalculer) ;
-- ils existent parce qu'un classement par série en cours, calculé à la
-- volée sur tous les joueurs, coûte bien trop cher.
CREATE TABLE IF NOT EXISTS series (
  joueur_id       BIGINT UNSIGNED NOT NULL,
  univers         VARCHAR(24)     NOT NULL DEFAULT 'one-piece',
  mode            VARCHAR(16)     NOT NULL,
  parties         INT UNSIGNED    NOT NULL DEFAULT 0,
  fiches_total    INT UNSIGNED    NOT NULL DEFAULT 0,
  serie           INT UNSIGNED    NOT NULL DEFAULT 0,
  meilleure_serie INT UNSIGNED    NOT NULL DEFAULT 0,
  dernier_jour    DATE                NULL,
  PRIMARY KEY (joueur_id, univers, mode),
  KEY classement_serie (univers, mode, serie),
  KEY classement_parties (univers, mode, parties),
  CONSTRAINT fk_series_joueur FOREIGN KEY (joueur_id)
    REFERENCES joueurs (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
