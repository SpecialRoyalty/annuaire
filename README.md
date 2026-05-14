# TousLesLiens Bot V5 complet

## Railway variables

```env
BOT_TOKEN=
BOT_USERNAME=touslesliens_bot
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@postgres.railway.internal:5432/railway
SUPER_ADMIN_IDS=123456789
SUPPORT_USERNAME=support
PAGE_SIZE=3
START_STATS_MIN=1000
MAX_BOT_WARNINGS=3
PENDING_CONNECT_HOURS=1
```

Important : pas de guillemets autour de `DATABASE_URL`.

## Inclus V5

- Menus avec emojis
- Mode démo ON/OFF depuis modération
- Boutons démo visibles seulement si mode démo ON
- Listing gratuit
- Notification admins nouvelle demande
- Approbation/refus avec motif
- Bouton automatique `🤖 Ajouter le bot au groupe`
- Connexion automatique via `startgroup=connect_ID`
- `/connect ID` en secours
- Message pin viral
- Warning configurable par catégorie
- Pagination 3 groupes/page
- Fiche groupe
- Notes instantanées
- Clics instantanés
- Signalements
- Suggestion catégorie + notifications
- Modération optionnelle
- Anti-liens = ban
- Après 3 bans réseau : ban bot + ban automatique dans tous les groupes connectés
- Refresh membres/croissance toutes les 30 minutes
- `/dbcheck` pour vérifier les tables
- `/moderation` pour admin

## Reset DB

```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```
