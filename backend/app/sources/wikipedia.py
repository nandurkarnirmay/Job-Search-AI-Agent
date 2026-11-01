"""Company overview from Wikipedia (free, no key). Used as the factual base for company research.
Wikimedia's API policy requires a descriptive User-Agent."""
import re
from urllib.parse import quote

from app.config import get_settings
from app.domain import CompanyWiki
from app.sources.base import ResilientAPI

SEARCH_URL = "https://en.wikipedia.org/w/api.php"
SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
USER_AGENT = "JobSearchAIAgent/0.3 (student project; https://github.com/nandurkarnirmay/job-search-ai-agent)"

_COMPANY_WORDS = re.compile(
    r"\b(company|companies|corporation|conglomerate|multinational|firm|startup|start-up|bank|manufacturer|"
    r"retailer|provider|platform|business|enterprise|group|services|consultancy|subsidiary|unicorn|"
    r"e-commerce|ecommerce|software|technology|automaker|airline|insurer|brand|marketplace)\b", re.I)
_STOP = {"and", "of", "the", "&"}

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

def _initials(title: str) -> str:
    words = [w for w in re.split(r"[\s\-]+", title.lower()) if w and w not in _STOP]
    return "".join(w[0] for w in words if w[0].isalnum())

def title_matches(company: str, title: str) -> bool:
    """Accept 'Infosys' for 'Infosys', 'TCS' for 'Tata Consultancy Services', 'L&T' for 'Larsen & Toubro'."""
    c, t = _norm(company), _norm(title)
    if not c:
        return False
    first = c.split()[0]
    # whole first word, or the name at a word start ('hcl' in 'hcltech', but not 'ola' in 'motorola')
    if first in t.split() or re.search(rf"\b{re.escape(c)}", t):
        return True
    compact = c.replace(" ", "")
    return len(compact) >= 2 and _initials(title).startswith(compact)

def looks_like_company(wiki: CompanyWiki) -> bool:
    return bool(_COMPANY_WORDS.search(f"{wiki.description or ''} {wiki.extract[:300]}"))

class WikipediaClient(ResilientAPI):
    name = "wikipedia"
    min_interval_seconds = 0.2
    max_retries = 1

    def is_configured(self) -> bool:
        return get_settings().wikipedia_enabled

    def _search(self, company: str) -> list[str]:
        params = {"action": "query", "list": "search", "srsearch": f"{company} company", "srlimit": 5,
                  "format": "json", "formatversion": 2}
        return self._call(
            lambda: self._client.build_request("GET", SEARCH_URL, params=params, headers={"User-Agent": USER_AGENT}),
            lambda p: [r["title"] for r in (p.get("query") or {}).get("search", [])],
        ) or []

    def _summary(self, title: str) -> CompanyWiki | None:
        url = SUMMARY_URL.format(title=quote(title.replace(" ", "_"), safe=""))

        def parse(p: dict) -> CompanyWiki | None:
            if p.get("type") != "standard":  # disambiguation pages, missing pages
                return None
            return CompanyWiki(title=p.get("title", title), description=p.get("description"),
                               extract=(p.get("extract") or "")[:1200],
                               url=((p.get("content_urls") or {}).get("desktop") or {}).get("page"))

        return self._call(lambda: self._client.build_request("GET", url, headers={"User-Agent": USER_AGENT}),
                          parse, not_found_ok=True)

    def lookup(self, company: str) -> CompanyWiki | None:
        """Best-matching company article, or None. Raises SourceError if Wikipedia is down."""
        if not self.is_configured():
            return None
        for title in self._search(company):
            if not title_matches(company, title):
                continue
            wiki = self._summary(title)
            if wiki and looks_like_company(wiki):
                return wiki
        return None
