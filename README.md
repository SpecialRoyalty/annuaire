# TousLesLiens Bot — version complète

Bot Telegram Railway + PostgreSQL pour lister des groupes Telegram, avec mode démo, interface utilisateur, interface listeur, modération, catégories, stats, signalements et système de sanctions.

## Installation Railway

1. Crée un projet Railway.
2. Ajoute PostgreSQL.
3. Ajoute les variables dans le service bot :

```env
BOT_TOKEN=ton_token_botfather
BOT_USERNAME=touslesliens_bot
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres.railway.internal:5432/railway
SUPER_ADMIN_IDS=ton_id_telegram
SUPPORT_USERNAME=ton_support_sans_@
PAGE_SIZE=3
START_STATS_MIN=1000
PENDING_CONNECT_HOURS=1
MAX_BOT_WARNINGS=3
INACTIVE_DAYS_BEFORE_DELIST=10
```

Important : `DATABASE_URL` doit commencer par `postgresql+asyncpg://`, sans guillemets.

4. Déploie.

## Fonctions incluses

- Mode démo activable/désactivable depuis modération.
- Accueil avec nombre d'utilisateurs affiché seulement à partir de 1000.
- Listing gratuit.
- 3 groupes par page.
- Fiche groupe détaillée.
- Note 1 à 5 étoiles.
- Signalement lien mort / scam / contenu interdit.
- Suggestion catégorie avec validation/refus + motif.
- Interface listeur après création d'un groupe.
- Validation humaine des projets.
- Motif obligatoire en cas de refus.
- Ajout obligatoire du bot comme admin dans le groupe.
- Alerte après 1h si bot non ajouté.
- 3 warnings bot absent/retiré = projet banni + owner bloqué pour relister.
- Modération gratuite optionnelle.
- Mots interdits : suppression + mute 1 jour, puis 7 jours si récidive.
- Anti-liens : suppression + ban direct.
- Blacklist globale : après 3 bans réseau, accès au bot refusé.

## Commandes utiles

- `/start`
- `/moderation` pour les super admins
- `/connect PROJECT_ID` à envoyer dans le groupe après ajout du bot admin
