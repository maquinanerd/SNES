import logging
import requests
import time
import json
import re 
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def _slugify(name: str) -> str:
    """Creates a simple, WordPress-compatible slug from a string."""
    s = name.strip().lower()
    # Remove characters that are not alphanumeric, whitespace, or hyphen
    s = re.sub(r'[^\w\s-]', '', s, flags=re.UNICODE)
    # Replace whitespace and underscores with a hyphen
    s = re.sub(r'[\s_-]+', '-', s, flags=re.UNICODE)
    # Strip leading/trailing hyphens and limit length
    return s.strip('-')[:190] or 'tag'

class WordPressClient:
    """A client for interacting with the WordPress REST API."""

    def __init__(self, config: Dict[str, str], categories_map: Dict[str, int]):
        base_url = (config.get('url') or "").rstrip('/')
        if not base_url:
            raise ValueError("WORDPRESS_URL is not configured.")
        
        # Ensure the API URL has the correct REST API path
        if '/wp-json/wp/v2' not in base_url:
            self.api_url = f"{base_url}/wp-json/wp/v2"
        else:
            self.api_url = base_url

        self.user = config.get('user')
        self.password = config.get('password')
        
        self.session = requests.Session()
        if self.user and self.password:
            self.session.auth = (self.user, self.password)
        self.session.headers.update({'User-Agent': 'VocMoney-Pipeline/1.0'})

        # Start with the static map from config, ensuring keys are lowercase
        self.categories_map = {k.lower(): v for k, v in categories_map.items()}
        logger.info("Loading all WordPress categories for caching...")
        
        # Augment with all categories from the WP site
        self.categories_map.update(self._fetch_all_categories())

    def _fetch_all_categories(self) -> Dict[str, int]:
        """Fetches all categories from WordPress and returns a name -> id map."""
        all_categories = {}
        page = 1
        per_page = 100
        endpoint = f"{self.api_url}/categories"
        
        while True:
            params = {
                "per_page": per_page,
                "page": page,
                "orderby": "count",
                "order": "desc",
                "_fields": "id,name,slug"
            }
            try:
                r = self.session.get(endpoint, params=params, timeout=30)
                r.raise_for_status()
                categories = r.json()
                if not categories:
                    break
                
                for cat in categories:
                    all_categories[cat['name'].lower()] = cat['id']
                    all_categories[cat['slug']] = cat['id']
                
                if len(categories) < per_page:
                    break
                page += 1
            except requests.RequestException as e:
                logger.error(f"Error fetching categories (page {page}): {e}")
                break
        
        logger.info(f"Fetched {len(all_categories)} category mappings from WordPress.")
        return all_categories

    def get_domain(self) -> str:
        """Extracts the domain from the WordPress URL."""
        try:
            return urlparse(self.api_url).netloc
        except Exception:
            return ""

    def _get_existing_tag_id(self, name: str) -> Optional[int]:
        """Searches for an existing tag by name or slug and returns its ID."""
        slug = _slugify(name)
        tags_endpoint = f"{self.api_url}/tags"
        params = {"search": name, "per_page": 100}

        try:
            r = self.session.get(tags_endpoint, params=params, timeout=20)
            r.raise_for_status()
            items = r.json()
            
            # WordPress search can be broad, so we verify the match
            for item in items:
                if item.get('name', '').strip().lower() == name.strip().lower():
                    return int(item['id'])
            for item in items:
                if item.get('slug') == slug:
                    return int(item['id'])
        except requests.RequestException as e:
            logger.error(f"Error searching for tag '{name}': {e}")
        
        return None

    def _create_tag(self, name: str) -> Optional[int]:
        """Creates a new tag and returns its ID."""
        tags_endpoint = f"{self.api_url}/tags"
        payload = {"name": name, "slug": _slugify(name)}
        
        try:
            r = self.session.post(tags_endpoint, json=payload, timeout=20)
            
            if r.status_code in (200, 201):
                tag_id = int(r.json()['id'])
                logger.info(f"Created new tag '{name}' with ID {tag_id}.")
                return tag_id
            
            # Handle race condition where tag was created between search and post
            if r.status_code == 400 and isinstance(r.json(), dict) and r.json().get("code") == "term_exists":
                logger.warning(f"Tag '{name}' already exists (race condition). Re-fetching ID.")
                return self._get_existing_tag_id(name)
            
            r.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Error creating tag '{name}': {e}")
            if e.response is not None:
                logger.error(f"Response body: {e.response.text}")

        return None

    def _ensure_tag_ids(self, tags: List[Any], max_tags: int = 10) -> List[int]:
        """Converts a list of tag names/IDs into a list of integer IDs, creating tags if necessary."""
        if not tags:
            return []

        # Normalize input (handles strings, ints, and comma-separated strings)
        norm_tags: List[str] = []
        for t in tags:
            if isinstance(t, int):
                norm_tags.append(str(t))
            elif isinstance(t, str):
                norm_tags.extend([p.strip() for p in t.split(',') if p.strip()])
        
        # Deduplicate and limit
        cleaned_tags = list(dict.fromkeys(norm_tags))[:max_tags]
        
        tag_ids: List[int] = []
        for tag_name in cleaned_tags:
            if tag_name.isdigit():
                tag_ids.append(int(tag_name))
            elif len(tag_name) >= 2:
                tag_id = self._get_existing_tag_id(tag_name) or self._create_tag(tag_name)
                if tag_id:
                    tag_ids.append(tag_id)
        
        logger.info(f"Resolved tags {tags} to IDs: {tag_ids}")
        return tag_ids

    def _get_existing_category_id(self, name: str) -> Optional[int]:
        """Searches for an existing category by name or slug and returns its ID."""
        slug = _slugify(name)
        endpoint = f"{self.api_url}/categories"
        # WordPress category search is not as reliable as tag search, so we get more results and filter
        params = {"search": name, "per_page": 100}

        try:
            r = self.session.get(endpoint, params=params, timeout=20)
            r.raise_for_status()
            items = r.json()
            
            # Exact match on name (case-insensitive)
            for item in items:
                if item.get('name', '').strip().lower() == name.strip().lower():
                    return int(item['id'])
            # Match on slug
            for item in items:
                if item.get('slug') == slug:
                    return int(item['id'])
        except requests.RequestException as e:
            logger.error(f"Error searching for category '{name}': {e}")
        
        return None

    def _create_category(self, name: str) -> Optional[int]:
        """Creates a new category and returns its ID."""
        endpoint = f"{self.api_url}/categories"
        payload = {"name": name, "slug": _slugify(name)}
        
        try:
            r = self.session.post(endpoint, json=payload, timeout=20)
            
            if r.status_code in (200, 201):
                cat_id = int(r.json()['id'])
                logger.info(f"Created new category '{name}' with ID {cat_id}.")
                return cat_id
            
            if r.status_code == 400 and isinstance(r.json(), dict) and r.json().get("code") == "term_exists":
                logger.warning(f"Category '{name}' already exists (race condition). Re-fetching ID.")
                return self._get_existing_category_id(name)
            
            r.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Error creating category '{name}': {e}")
            if e.response is not None:
                logger.error(f"Response body: {e.response.text}")

        return None

    def resolve_category_names_to_ids(self, category_names: List[str]) -> List[int]:
        """
        Converts a list of category names into a list of integer IDs.
        It uses a pre-loaded cache of categories and creates any that are missing.
        """
        if not category_names:
            return []

        cleaned_names = list(dict.fromkeys([name.strip() for name in category_names if name.strip() and len(name) >= 1]))
        
        cat_ids: List[int] = []
        for name in cleaned_names:
            slug = _slugify(name)
            # Check cache by name (lower) or slug
            cat_id = self.categories_map.get(name.lower()) or self.categories_map.get(slug)
            
            # If not in cache, it needs to be created
            if not cat_id:
                logger.info(f"Category '{name}' not found in cache, attempting to create.")
                cat_id = self._create_category(name)
                if cat_id:
                    # Add to cache for this run to avoid re-creating in the same cycle
                    logger.info(f"Adding newly created category '{name}' (ID: {cat_id}) to cache.")
                    self.categories_map[name.lower()] = cat_id
                    self.categories_map[slug] = cat_id

            if cat_id:
                cat_ids.append(cat_id)
        
        # Remove duplicates before returning
        final_ids = list(set(cat_ids))
        logger.info(f"Resolved category names {cleaned_names} to IDs: {final_ids}")
        return final_ids

    def upload_media_from_url(self, image_url: str, alt_text: str = "", max_attempts: int = 3) -> Optional[Dict[str, Any]]:
        """
        Downloads an image and uploads it to WordPress with a retry mechanism.
        """
        last_err = None
        for attempt in range(1, max_attempts + 1):
            try:
                # 1. Download the image with a reasonable timeout
                img_response = requests.get(image_url, timeout=25)
                img_response.raise_for_status()
                content_type = img_response.headers.get('Content-Type', 'image/jpeg')
                # Sanitize filename
                filename = (urlparse(image_url).path.split('/')[-1] or "image.jpg").split("?")[0]

                # 2. Upload to WordPress
                media_endpoint = f"{self.api_url}/media"
                headers = {
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': content_type,
                }
                wp_response = self.session.post(media_endpoint, headers=headers, data=img_response.content, timeout=40)
                wp_response.raise_for_status()
                logger.info(f"Successfully uploaded image: {image_url}")
                return wp_response.json() # Success

            except (requests.Timeout, requests.ConnectionError) as e:
                last_err = e
                logger.warning(f"Upload attempt {attempt}/{max_attempts} for '{image_url}' failed with network error: {e}. Retrying in {2*attempt}s...")
                time.sleep(2 * attempt)  # Simple backoff
            except Exception as e:
                last_err = e
                logger.error(f"Upload of '{image_url}' failed with non-retriable error: {e}")
                break # Don't retry on WP errors (4xx, 5xx) or other issues

        logger.error(f"Final failure to upload image '{image_url}' after {attempt} attempt(s): {last_err}")
        return None

    def set_media_alt_text(self, media_id: int, alt_text: str) -> bool:
        """Sets the alt text for a media item in WordPress."""
        if not alt_text:
            return False
        try:
            endpoint = f"{self.api_url}/media/{media_id}"
            payload = {"alt_text": alt_text}
            r = self.session.post(endpoint, json=payload, timeout=20)
            r.raise_for_status()
            logger.info(f"Successfully set alt text for media ID {media_id}.")
            return True
        except requests.RequestException as e:
            logger.warning(f"Failed to set alt_text on media {media_id}: {e}")
            if e.response is not None:
                logger.warning(f"Response body: {e.response.text}")
            return False

    def find_related_posts(self, term: str, limit: int = 3) -> List[Dict[str, str]]:
        """Searches for posts on the site and returns their title and URL."""
        if not term:
            return []
        try:
            endpoint = f"{self.api_url}/search"
            params = {"search": term, "per_page": limit, "_embed": "self"}
            resp = self.session.get(endpoint, params=params, timeout=15)
            resp.raise_for_status()
            # The 'url' in the search result is the API URL, we need the 'link' from the embedded post object
            return [{"title": i.get("title", ""), "url": i.get("_embedded", {}).get("self", [{}])[0].get("link", "")} for i in resp.json()]
        except requests.RequestException as e:
            logger.error(f"Error searching for related posts with term '{term}': {e}")
            return []

    def create_post(self, payload: Dict[str, Any]) -> Optional[int]:
        """Creates a new post in WordPress."""
        try:
            # Resolve tag names to integer IDs
            if 'tags' in payload and payload['tags']:
                payload['tags'] = self._ensure_tag_ids(payload['tags'])

            # Resolve category names to integer IDs
            if 'categories' in payload and payload['categories']:
                # Ensure categories are in list format, even if a single int/str is provided
                cat_input = payload['categories']
                if isinstance(cat_input, (int, str)):
                    cat_input = [cat_input]
                
                # Convert names to IDs
                category_names = [str(c) for c in cat_input if isinstance(c, str) and not c.isdigit()]
                category_ids = [int(c) for c in cat_input if isinstance(c, int) or (isinstance(c, str) and c.isdigit())]
                
                if category_names:
                    resolved_ids = self.resolve_category_names_to_ids(category_names)
                    category_ids.extend(resolved_ids)
                
                # Remove duplicates and assign back to payload
                payload['categories'] = list(set(category_ids))

            posts_endpoint = f"{self.api_url}/posts"
            payload.setdefault('status', 'publish')

            # Log a summary of the payload to avoid overly long logs
            try:
                logger.info(
                    "WP payload: title_len=%d content_len=%d cat=%s tags=%s",
                    len(payload.get('title', '')),
                    len(payload.get('content', '')),
                    payload.get('categories'),
                    payload.get('tags')
                )
                if logger.isEnabledFor(logging.DEBUG):
                    log_payload = json.dumps(payload, indent=2, ensure_ascii=False)
                    logger.debug(f"Sending full payload to WordPress:\n{log_payload}")
            except Exception as log_e:
                logger.warning(f"Could not serialize payload for logging: {log_e}")

            response = self.session.post(posts_endpoint, json=payload, timeout=60)
            
            if not response.ok:
                logger.error(f"WordPress post creation failed with status {response.status_code}: {response.text}")
                response.raise_for_status()

            return response.json().get('id')
        except requests.RequestException as e:
            logger.error(f"Failed to create WordPress post: {e}", exc_info=False)
            return None

    def get_published_posts(self, fields: List[str], max_posts: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetches published posts, handling pagination, with an optional limit.

        Args:
            fields: A list of fields to retrieve for each post.
            max_posts: Optional limit on the total number of posts to fetch.
        """
        all_posts = []
        page = 1
        per_page = 100
        
        fields_str = ','.join(fields)

        while True:
            # Exit if we have reached the desired number of posts
            if max_posts and len(all_posts) >= max_posts:
                logger.info(f"Reached max_posts limit of {max_posts}. Stopping fetch.")
                break

            endpoint = f"{self.api_url}/posts"
            params = {
                "status": "publish",
                "per_page": per_page,
                "page": page,
                "_fields": fields_str,
            }
            try:
                logger.info(f"Fetching page {page} of published posts...")
                r = self.session.get(endpoint, params=params, timeout=30)
                r.raise_for_status()
                
                posts = r.json()
                if not posts:
                    logger.info("No more posts found. Finished fetching.")
                    break
                
                all_posts.extend(posts)
                
                if len(posts) < per_page:
                    logger.info(f"Last page reached ({len(posts)} posts). Finished fetching.")
                    break
                    
                page += 1

            except requests.RequestException as e:
                logger.error(f"Error fetching published posts (page {page}): {e}")
                if e.response is not None:
                    logger.error(f"Response body: {e.response.text}")
                break
        
        # Trim the list to the exact number if max_posts is set
        if max_posts:
            all_posts = all_posts[:max_posts]

        logger.info(f"Successfully fetched a total of {len(all_posts)} posts.")
        return all_posts

    def get_tags_map_by_ids(self, tag_ids: List[int]) -> Dict[int, str]:
        """ 
        Fetches tag details from a list of IDs and returns a map of {id: name}.
        Handles pagination for large lists of IDs.
        """
        if not tag_ids:
            return {}

        tag_map = {}
        unique_ids = list(set(tag_ids))
        endpoint = f"{self.api_url}/tags"
        
        # The 'include' parameter can take a list of up to 100 IDs.
        # We chunk the requests to handle more than 100.
        for i in range(0, len(unique_ids), 100):
            chunk = unique_ids[i:i + 100]
            params = {
                "include": ",".join(map(str, chunk)),
                "per_page": 100, # Ensure we get all requested items in the chunk
                "_fields": "id,name"
            }
            try:
                logger.info(f"Fetching names for {len(chunk)} tag IDs...")
                r = self.session.get(endpoint, params=params, timeout=30)
                r.raise_for_status()
                tags_data = r.json()
                for tag in tags_data:
                    tag_map[tag['id']] = tag['name']
            except requests.RequestException as e:
                logger.error(f"Error fetching tag details: {e}")
                # Continue to next chunk even if one fails
                continue
        
        logger.info(f"Successfully mapped {len(tag_map)} tag IDs to names.")
        return tag_map

    def test_category_creation(self) -> (bool, str):
        """
        Tests if the client can create and then delete a category.
        Returns a tuple of (success: bool, message: str).
        """
        test_cat_name = f"Test Categoria {int(time.time())}"
        test_cat_id = None
        logger.info(f"--- Iniciando teste de criação de categoria: '{test_cat_name}' ---")

        # 1. Tentar criar a categoria
        try:
            logger.info(f"Passo 1: Tentando criar a categoria '{test_cat_name}'...")
            test_cat_id = self._create_category(test_cat_name)
            if not test_cat_id:
                msg = "FALHA: A função _create_category não retornou um ID. Verifique os logs para erros de requisição."
                logger.error(msg)
                return False, msg
            
            logger.info(f"SUCESSO: Categoria '{test_cat_name}' criada com ID: {test_cat_id}.")
        except Exception as e:
            msg = f"FALHA: Exceção durante a criação da categoria: {e}"
            logger.error(msg, exc_info=True)
            return False, msg

        # 2. Tentar deletar a categoria
        try:
            logger.info(f"Passo 2: Tentando deletar a categoria de teste (ID: {test_cat_id})...")
            delete_endpoint = f"{self.api_url}/categories/{test_cat_id}"
            # O WordPress exige force=true para deletar categorias com posts
            params = {'force': True}
            r = self.session.delete(delete_endpoint, params=params, timeout=20)

            if r.status_code == 200 and r.json().get('deleted'):
                msg = f"SUCESSO: Categoria de teste '{test_cat_name}' deletada com sucesso."
                logger.info(msg)
                logger.info("--- Teste de criação de categoria concluído com sucesso. ---")
                return True, msg
            else:
                r.raise_for_status() # Forçar exceção se o status não for OK
        except requests.RequestException as e:
            msg = f"FALHA: Erro ao deletar a categoria de teste. Resposta: {e.response.text if e.response else 'N/A'}"
            logger.error(msg)
            logger.error("--- Teste de criação de categoria FALHOU. A categoria de teste pode ter ficado no seu site. ---")
            return False, msg
        
        return False, "FALHA: Ocorreu um erro inesperado no final do teste."

    def close(self):
        """Closes the requests session."""
        self.session.close()