import os
from dotenv import load_dotenv
from typing import Dict, List, Any

# Carrega variáveis de ambiente de um arquivo .env
load_dotenv()

# --- Ordem de processamento dos feeds ---
PIPELINE_ORDER: List[str] = [
    'as_es_laliga',
    'as_es_copa',
    'as_es_laliga_hypermotion',
    'ole_primera',
    'ole_ascenso',
    'as_cl_futbol',
    'as_co_futbol',
    'as_mx_futbol',
    'the_guardian_football',
    'bbc_football',
    'fox_sports_nfl',
    'fox_sports_nba',
]

# --- Feeds RSS ---
RSS_FEEDS: Dict[str, Dict[str, Any]] = {
    'as_es_laliga': {
        'urls': ['https://aprenderpoker.site/feeds/as_es/primera/rss'],
        'category': 'futebol-internacional',
        'source_name': 'AS España',
    },
    'as_es_copa': {
        'urls': ['https://aprenderpoker.site/feeds/as_es/copa_del_rey/rss'],
        'category': 'futebol-internacional',
        'source_name': 'AS España',
    },
    'as_es_laliga_hypermotion': {
        'urls': ['https://aprenderpoker.site/feeds/as_es/segunda/rss'],
        'category': 'futebol-internacional',
        'source_name': 'AS España',
    },
    'ole_primera': {
        'urls': ['https://aprenderpoker.site/feeds/ole/primera/rss'],
        'category': 'futebol-internacional',
        'source_name': 'Olé',
    },
    'ole_ascenso': {
        'urls': ['https://aprenderpoker.site/feeds/ole/ascenso/rss'],
        'category': 'futebol-internacional',
        'source_name': 'Olé',
    },
    'as_cl_futbol': {
        'urls': ['https://aprenderpoker.site/feeds/as_cl/futbol/rss'],
        'category': 'futebol-internacional',
        'source_name': 'AS Chile',
    },
    'as_co_futbol': {
        'urls': ['https://aprenderpoker.site/feeds/as_co/futbol/rss'],
        'category': 'futebol-internacional',
        'source_name': 'AS Colombia',
    },
    'as_mx_futbol': {
        'urls': ['https://aprenderpoker.site/feeds/as_mx/futbol/rss'],
        'category': 'futebol-internacional',
        'source_name': 'AS México',
    },
    'the_guardian_football': {
        'urls': ['https://aprenderpoker.site/feeds/theguardian/football/rss'],
        'category': 'futebol-internacional',
        'source_name': 'The Guardian',
    },
    'bbc_football': {
        'urls': ['https://aprenderpoker.site/feeds/bbc/sport_football/rss'],
        'category': 'futebol-internacional',
        'source_name': 'BBC Sport',
    },
    'fox_sports_nfl': {
        'urls': ['https://api.foxsports.com/v2/content/optimized-rss?partnerKey=MB0Wehpmuj2lUhuRhQaafhBjAJqaPU244mlTDK1i&size=30&tags=fs/nfl'],
        'category': 'outros-esportes',
        'source_name': 'Fox Sports',
    },
    'fox_sports_nba': {
        'urls': ['https://api.foxsports.com/v2/content/optimized-rss?partnerKey=MB0Wehpmuj2lUhuRhQaafhBjAJqaPU244mlTDK1i&size=30&tags=fs/nba'],
        'category': 'outros-esportes',
        'source_name': 'Fox Sports',
    },
}

# --- HTTP ---
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/91.0.4472.124 Safari/537.36'
)

# --- Configuração da IA ---
def _load_ai_keys() -> List[str]:
    """
    Lê todas as chaves GEMINI_* do ambiente e as retorna em uma lista única e ordenada.
    """
    keys = {}
    for key, value in os.environ.items():
        if value and key.startswith('GEMINI_'):
            keys[key] = value
    
    # Sort by key name for predictable order (e.g., GEMINI_KEY_1, GEMINI_KEY_2)
    sorted_key_names = sorted(keys.keys())
    
    return [keys[k] for k in sorted_key_names]

AI_API_KEYS = _load_ai_keys()

# Caminho para o prompt universal na raiz do projeto
PROMPT_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..',
    'universal_prompt.txt'
)

AI_MODEL = os.getenv('AI_MODEL', 'gemini-1.5-flash-latest')

AI_GENERATION_CONFIG = {
    'temperature': 0.7,
    'top_p': 1.0,
    'max_output_tokens': 4096,
}

# --- WordPress ---
WORDPRESS_CONFIG = {
    'url': os.getenv('WORDPRESS_URL'),
    'user': os.getenv('WORDPRESS_USER'),
    'password': os.getenv('WORDPRESS_PASSWORD'),
}

# --- Posts Pilares para Linkagem Interna ---
# Adicione aqui as URLs completas dos seus posts mais importantes.
PILAR_POSTS: List[str] = [
    # Ex: "https://seusite.com/guia-completo-de-futebol",
]

# IDs das categorias no WordPress (ajuste os IDs conforme o seu WP)
WORDPRESS_CATEGORIES: Dict[str, int] = {
    'futebol': 8,
    'futebol-internacional': 9,
    'outros-esportes': 10,
    'Notícias': 1,
    'noticias': 31,
}

# --- Sinônimos de Categorias ---
CATEGORY_ALIASES: Dict[str, str] = {
    "liga ea sports": "la-liga",
}

# --- Agendador / Pipeline ---
SCHEDULE_CONFIG = {
    'check_interval_minutes': int(os.getenv('CHECK_INTERVAL_MINUTES', 15)),
    'max_articles_per_feed': int(os.getenv('MAX_ARTICLES_PER_FEED', 3)),
    'per_article_delay_seconds': int(os.getenv('PER_ARTICLE_DELAY_SECONDS', 8)),
    'per_feed_delay_seconds': int(os.getenv('PER_FEED_DELAY_SECONDS', 15)),
    'cleanup_after_hours': int(os.getenv('CLEANUP_AFTER_HOURS', 72)),
}

PIPELINE_CONFIG = {
    'images_mode': os.getenv('IMAGES_MODE', 'hotlink'),
    'attribution_policy': 'Fonte: {domain}',
    'publisher_name': 'The Sport',
    'publisher_logo_url': os.getenv(
        'PUBLISHER_LOGO_URL',
        'https://exemplo.com/logo.png'
    ),
}