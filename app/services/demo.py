from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

@dataclass
class DemoCategory:
    id: int
    name: str

@dataclass
class DemoProject:
    id: int
    title: str
    description: str
    category_id: int
    invite_link: str
    status: str = "active"
    is_link_active: bool = True
    member_count: int = 12430
    rating_avg: float = 4.8
    rating_count: int = 342
    click_count: int = 817
    start_count: int = 392
    pin_attempts: int = 0
    listed_at: datetime = datetime.now(timezone.utc) - timedelta(days=12)
    owner_user_id: int = -1

DEMO_CATEGORIES = [
    DemoCategory(1, "Business"),
    DemoCategory(2, "Crypto"),
    DemoCategory(3, "Bons plans"),
    DemoCategory(4, "Gaming"),
    DemoCategory(5, "Communautés"),
]

DEMO_PROJECTS = [
    DemoProject(1001, "Crypto Alpha Club", "Signaux, actus et entraide crypto francophone.", 2, "https://t.me/demo_crypto_alpha", member_count=12430, rating_avg=4.8, rating_count=342, click_count=817, start_count=392),
    DemoProject(1002, "Business Elite FR", "Réseau entrepreneurs, business en ligne et opportunités.", 1, "https://t.me/demo_business_elite", member_count=21000, rating_avg=4.9, rating_count=510, click_count=1240, start_count=688),
    DemoProject(1003, "Bons Plans Premium", "Promos, deals et astuces tous les jours.", 3, "https://t.me/demo_bons_plans", member_count=8921, rating_avg=4.6, rating_count=221, click_count=602, start_count=241),
    DemoProject(1004, "Gaming France Hub", "Tournois, squads et communautés gaming.", 4, "https://t.me/demo_gaming_fr", member_count=15420, rating_avg=4.7, rating_count=298, click_count=730, start_count=314),
    DemoProject(1005, "Communauté VIP", "Un groupe actif avec lien de secours toujours accessible.", 5, "https://t.me/demo_communaute", member_count=18450, rating_avg=4.8, rating_count=401, click_count=920, start_count=507),
    DemoProject(1006, "Invest Club", "Idées, analyses et discussions business/investissement.", 1, "https://t.me/demo_invest_club", member_count=7200, rating_avg=4.5, rating_count=160, click_count=410, start_count=190),
]

DEMO_OWNER_PROJECT = DemoProject(
    9999,
    "Ton Groupe Démo",
    "Exemple de fiche owner : stats, lien de secours, visibilité et classement.",
    5,
    "https://t.me/ton_groupe_demo",
    member_count=14382,
    rating_avg=4.8,
    rating_count=287,
    click_count=817,
    start_count=392,
    pin_attempts=0,
)

def demo_categories():
    return DEMO_CATEGORIES

def demo_projects_by_category(category_id: int, page: int, per_page: int = 3):
    items = [p for p in DEMO_PROJECTS if p.category_id == category_id]
    start = (page - 1) * per_page
    return items[start:start + per_page], len(items) > start + per_page

def demo_top_projects(page: int, per_page: int = 3):
    items = sorted(DEMO_PROJECTS, key=lambda p: (p.rating_avg, p.start_count, p.click_count), reverse=True)
    start = (page - 1) * per_page
    return items[start:start + per_page], len(items) > start + per_page

def get_demo_project(project_id: int):
    if project_id == DEMO_OWNER_PROJECT.id:
        return DEMO_OWNER_PROJECT
    return next((p for p in DEMO_PROJECTS if p.id == project_id), None)
