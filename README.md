# TousLesLiens Bot

Bot Telegram complet pour lister des groupes, noter les projets, suivre les clics, gérer les owners/admins, valider les listings par super admin et forcer un message épinglé de lien de secours dans les groupes.

## Fonctionnalités incluses

- Menu principal 100% boutons Telegram
- Listing par catégories
- Pagination 5 groupes par page
- Notes 1 à 5 étoiles
- Interdiction de noter son propre projet
- Clics trackés
- Statistiques owner
- Ajout de projet par formulaire Telegram
- Owner/admin projet
- Super admin via `SUPER_ADMIN_IDS`
- Validation/refus/ban des projets
- Connexion du bot dans un groupe avec `/connect`
- Message de secours épinglé
- Détection du changement de pin avec 3 tentatives avant ban
- Rappel après 1h si le bot n’est pas branché
- Délisting automatique si lien inactif depuis 10 jours
- PostgreSQL
- Déploiement Railway

## Stack

- Python 3.11+
- aiogram 3
- PostgreSQL
- SQLAlchemy async
- APScheduler
- Railway

## Installation locale

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Remplis `.env` :

```env
BOT_TOKEN=token_botfather
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/touslesliens
SUPER_ADMIN_IDS=123456789
BOT_USERNAME=touslesliens_bot
```

Lance en polling local :

```bash
python -m app.main
```

Ne mets pas `WEBHOOK_URL` en local si tu veux utiliser le polling.

## Déploiement Railway

1. Crée un projet Railway.
2. Ajoute un service PostgreSQL.
3. Ajoute ce code depuis GitHub ou upload.
4. Mets les variables :

```env
BOT_TOKEN=...
DATABASE_URL=${{Postgres.DATABASE_URL}}
SUPER_ADMIN_IDS=ton_telegram_id
WEBHOOK_URL=https://ton-service.up.railway.app
WEBHOOK_SECRET=une-valeur-random
BOT_USERNAME=touslesliens_bot
PORT=8080
```

Important : Railway donne souvent une URL PostgreSQL sous forme `postgresql://...`. Le projet attend `postgresql+asyncpg://...`. Remplace le début si nécessaire.

## Utilisation

### Utilisateur

- `/start`
- Trouver un groupe
- Top groupes
- Noter
- Signaler

### Owner

- `/start`
- `➕ Lister mon groupe`
- Remplir nom, description, catégorie, lien
- Ajouter le bot dans le groupe comme admin
- Dans le groupe, envoyer `/connect`
- Attendre validation super admin

### Super admin

Ton ID Telegram doit être dans `SUPER_ADMIN_IDS`.

Ensuite :

- `/start`
- `👑 Super admin`
- Valider/refuser/bannir les projets

## Permissions Telegram nécessaires

Dans les groupes, le bot doit être admin avec :

- envoyer des messages
- épingler des messages
- voir les messages de service
- idéalement voir les membres pour les stats membres

## Notes importantes

Telegram impose des limites :

- Le bot ne peut épingler que s’il a la permission.
- Le bot ne peut pas empêcher quelqu’un de le retirer du groupe, mais il peut le détecter selon les updates reçus et sanctionner ensuite.
- Pour les groupes privés, le comptage membres et la validation du lien peuvent dépendre des droits du bot.

## Améliorations recommandées après MVP

- Vérification réelle des liens avec tentative d’accès Telegram
- Table `pin_messages` pour garder l’ID du message épinglé
- Dashboard web admin optionnel
- Système de badges : vérifié, tendance, partenaire
- Score viral : note + clics + starts générés - signalements
- Recherche texte par nom de groupe
- Modération anti-spam
- Blacklist permanente par group_chat_id

## Mode démo commercial

Cette version contient un mode démo activable sans modifier le code.

Dans Telegram :

1. Lance le bot avec ton compte super admin.
2. Clique sur `🛠 Modération`.
3. Clique sur `🎭 Mode démo ON/OFF`.

Quand le mode démo est actif :

- le menu affiche `🎭 Voir la démo utilisateur` ;
- le menu affiche `📊 Voir la démo listeur` ;
- les catégories, groupes, notes, membres et stats sont fictifs ;
- les prospects peuvent comprendre ce que verront les utilisateurs et ce que verra un propriétaire de groupe ;
- tu peux le désactiver depuis le même bouton pour revenir au mode réel.

Le mode démo est stocké dans la base de données, table `app_settings`, clé `demo_mode`.
