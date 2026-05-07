# Tous Les Liens — Bot Telegram complet

## Installation Railway

1. Ajoute PostgreSQL.
2. Mets les variables dans le service bot :

```env
BOT_TOKEN=
BOT_USERNAME=touslesliens_bot
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@postgres.railway.internal:5432/railway
SUPER_ADMIN_IDS=ton_id_telegram
SUPPORT_USERNAME=support
PAGE_SIZE=3
START_STATS_MIN=1000
MAX_BOT_WARNINGS=3
PENDING_CONNECT_HOURS=1
```

Important : `DATABASE_URL` doit commencer par `postgresql+asyncpg://` et ne doit pas avoir de guillemets.

## Commandes

- `/start`
- `/moderation`
- `/connect ID_PROJET` dans le groupe après avoir ajouté le bot admin.

## Reset DB si besoin

```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

## Inclus

- Listing gratuit
- Validation/refus avec motif
- Interface utilisateur
- Interface listeur
- Interface modération
- Mode démo ON/OFF
- Catégories
- Warning configurable par catégorie
- 3 groupes par page
- Fiche groupe
- Notes
- Signalements
- Message pin viral
- Détection bot retiré / absent
- 3 warnings = blacklist owner
- Modération optionnelle
- Mots interdits
- Anti-liens
- Vote quotidien automatique type sondage


## Correctif V2

- Boutons visibles :
  - 🔎 Trouver un groupe
  - 🎭 Voir la démo utilisateur
  - 📊 Voir la démo listeur
  - ➕ Lister mon groupe gratuitement
  - ⭐ Top groupes
  - ℹ️ Infos
  - 🛠️ Modération
- Emojis remis partout pour faciliter la navigation.
- Démo utilisateur et démo listeur accessibles même sans activer le mode démo.
