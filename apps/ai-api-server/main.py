import re
import requests
from bs4 import BeautifulSoup
import ollama
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional

# --- CONFIGURATIE ---
OLLAMA_HOST = "http://host.docker.internal:11434"
CHAT_MODEL_NAME = "llama3"
ollama_client = ollama.Client(host=OLLAMA_HOST)

app = FastAPI(title="IKEA Intelligent Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
chat_history: Dict[str, List[dict]] = {}

# Bewaar per sessie de gescrapete productpagina:
# { session_id: { "product_code": str, "page_url": str, "text": str, "assembly_pdf": str|None } }
session_product: Dict[str, dict] = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str

# ---------------------------------------------------------------------------
# SYSTEM INSTRUCTIE
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTIE = """Je bent een IKEA-servicedesk medewerker voor België. Antwoord altijd in het Nederlands.

TAALREGEL: Begin NOOIT een zin met "Volgens", "Op basis van", "Uit de context", "De pagina vermeldt" of gelijkaardige bronverwijzingen. Spreek alsof je de informatie zelf kent.

INHOUDREGELS:
- Gebruik ALLEEN de informatie uit de meegeleverde context.
- Staat iets er NIET in? Zeg eerlijk dat je het niet weet en verwijs naar ikea.com/be/nl/stores/.
- Vul NOOIT zelf tijden, adressen of andere gegevens in die niet in de context staan.
- Benoem NOOIT de bron als "de context" of "de pagina". Zeg gewoon dat het zo is, alsof je het weet.
- Gebruik geen placeholders zoals [adres] of [...].
- Blijf zakelijk. Geen "vriend", "buddy" of andere informele aanspreekvormen.
- Chitchat beantwoord je kort en vriendelijk, zonder extra info op te halen.
- Na een bedankje: kort afsluiten, geen nieuw onderwerp starten."""

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
BASE = "https://www.ikea.com/be/nl"

BELGIUM_STORES = {
    "gent":       {"url": f"{BASE}/stores/gent/",      "adres": "Blijstraat 1, 9051 Sint-Denijs-Westrem"},
    "brussel":    {"url": f"{BASE}/stores/brussel/",   "adres": "Humaniteitslaan 19, 1070 Anderlecht"},
    "zellik":     {"url": f"{BASE}/stores/zellik/",    "adres": "Brusselsesteenweg 645, 1731 Zellik"},
    "antwerpen":  {"url": f"{BASE}/stores/antwerpen/", "adres": "Bolivarplaats 1, 2000 Antwerpen"},
    "luik":       {"url": f"{BASE}/stores/liege/",     "adres": "Rue de l'Expansion 2, 4460 Grâce-Hollogne"},
    "liège":      {"url": f"{BASE}/stores/liege/",     "adres": "Rue de l'Expansion 2, 4460 Grâce-Hollogne"},
    "liege":      {"url": f"{BASE}/stores/liege/",     "adres": "Rue de l'Expansion 2, 4460 Grâce-Hollogne"},
    "namen":      {"url": f"{BASE}/stores/namen/",     "adres": "Chaussée de Liège 811, 5100 Namur"},
    "namur":      {"url": f"{BASE}/stores/namen/",     "adres": "Chaussée de Liège 811, 5100 Namur"},
    "brugge":     {"url": f"{BASE}/stores/brugge/",    "adres": "Chartreuseweg 1, 8200 Brugge"},
    "hasselt":    {"url": f"{BASE}/stores/hasselt/",   "adres": "Gouverneur Verwilghensingel 70, 3500 Hasselt"},
    "leuven":     {"url": f"{BASE}/stores/leuven/",    "adres": "Interleuvenlaan 1, 3001 Heverlee"},
    "kortrijk":   {"url": f"{BASE}/stores/kortrijk/",  "adres": "Ringlaan 2, 8501 Kortrijk"},
}

# ---------------------------------------------------------------------------
# INTENT DETECTION
# ---------------------------------------------------------------------------
CHITCHAT_PATTERNS = [
    r"^(hoi|hey|hallo|goedemorgen|goedemiddag|goedenavond)[!.,]?$",
    r"^(bedankt|dankjewel|dank u|dankuwel|merci)[!.,]?$",
    r"^(doei|dag|tot ziens|bye|ciao)[!.,]?$",
    r"^(fijne dag|prettige dag|fijn weekend)[!.,]?$",
    r"^(ok|oke|oké|prima|goed zo|super)[!.,]?$",
]

# Productcodes: 8 cijfers, al dan niet gescheiden door punt/streep/spatie (bv. 305.415.82 of 30541582)
PRODUCT_CODE_RE = re.compile(r"\b(\d{3}[\s.-]?\d{3}[\s.-]?\d{2})\b")

ASSEMBLY_KEYWORDS = [
    "handleiding", "instructie", "montagegids", "montage-instructie",
    "hoe zet ik", "hoe monteer", "in elkaar", "assembly",
    "schroef", "schroeven", "bout", "plug", "pluggen",
    "stap voor stap", "onderdeel", "onderdelen", "overblijft", "tekort",
    "mist", "klopt dit", "heb ik over", "hoeveel schroeven",
]

STORE_KEYWORDS = [
    "winkel", "winkels", "belgi", "gent", "brussel", "antwerpen", "luik", "liège",
    "namen", "namur", "brugge", "hasselt", "leuven", "kortrijk",
    "opening", "openingsuren", "tijden", "open", "sluit", "adres",
]


def is_chitchat(message: str) -> bool:
    msg = message.strip().lower()
    return any(re.fullmatch(p, msg) for p in CHITCHAT_PATTERNS)


def extract_product_code(message: str) -> Optional[str]:
    """Geeft genormaliseerde 8-cijferige productcode terug, of None."""
    match = PRODUCT_CODE_RE.search(message)
    if match:
        return re.sub(r"[\s.\-]", "", match.group(1))
    return None


def is_assembly_question(message: str) -> bool:
    """Vraagt de gebruiker expliciet naar montage of handleiding?"""
    msg = message.lower()
    return any(k in msg for k in ASSEMBLY_KEYWORDS)


def is_store_question(message: str) -> bool:
    msg = message.lower()
    return any(k in msg for k in STORE_KEYWORDS)


# ---------------------------------------------------------------------------
# SCRAPING
# ---------------------------------------------------------------------------

def scrape_text(url: str, max_chars: int = 6000) -> str:
    try:
        res = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "svg"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:max_chars]
    except Exception as e:
        return f"Scraping mislukt: {e}"


def scrape_product_page(product_code: str) -> dict:
    """
    Scrape de IKEA-productpagina via /be/nl/p/{code}/.

    Geeft terug:
      page_url     — de gescrapete URL
      text         — leesbare productinfo (naam, beschrijving, maten, prijs, opties…)
      assembly_pdf — directe PDF-link als die op de pagina staat, anders None
    """
    url = f"{BASE}/p/{product_code}/"
    result: dict = {"page_url": url, "text": "", "assembly_pdf": None}

    try:
        res = requests.get(url, headers=HEADERS, timeout=12)

        if res.status_code == 404:
            result["text"] = (
                f"Geen productpagina gevonden voor code {product_code}. "
                "Controleer of de code correct is of zoek op ikea.com/be/nl."
            )
            return result

        soup = BeautifulSoup(res.text, "html.parser")

        # Zoek assembly PDF-link (staat als <a href="...assembly_instructions/....pdf">)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "assembly_instructions" in href and href.endswith(".pdf"):
                result["assembly_pdf"] = (
                    href if href.startswith("http") else f"https://www.ikea.com{href}"
                )
                break

        # Strip ruis en extraheer leesbare tekst
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "svg"]):
            tag.decompose()
        result["text"] = soup.get_text(separator=" ", strip=True)[:7000]

    except Exception as e:
        result["text"] = f"Productpagina kon niet worden geladen: {e}"

    return result


def get_store_context(message: str) -> tuple[str, list[dict]]:
    """
    Bouw winkelcontext op basis van hardcoded basisdata + optionele scrape.
    Geeft (context_text, reference_hrefs) terug.
    """
    msg = message.lower()
    matched: dict[str, dict] = {}

    for city, info in BELGIUM_STORES.items():
        if city in msg:
            matched[info["url"]] = {"city": city, **info}

    # Geen stad gevonden → alle winkels
    if not matched:
        matched = {info["url"]: {"city": city, **info}
                   for city, info in BELGIUM_STORES.items()}

    parts = []
    hrefs = []
    seen_urls: set = set()

    for url, info in matched.items():
        if url in seen_urls:
            continue
        seen_urls.add(url)

        city_name = info["city"].title()
        adres = info["adres"]

        # Probeer extra info te scrapen (winkel-specifieke promos, uitzonderingen)
        extra = scrape_text(url, max_chars=2000)
        store_block = f"IKEA {city_name}\nAdres: {adres}\nPagina: {url}"
        if extra and len(extra) > 150:
            store_block += f"\nExtra info: {extra}"

        parts.append(store_block)
        hrefs.append({
            "title": f"IKEA {city_name}",
            "description": f"{adres} — openingstijden en winkelinfo.",
            "href": url,
        })

    return "\n\n---\n\n".join(parts), hrefs


def get_search_context(query: str) -> str:
    url = f"{BASE}/search/?q={requests.utils.quote(query)}"
    return scrape_text(url, max_chars=6000)


# ---------------------------------------------------------------------------
# CONTEXT BUILDER
# ---------------------------------------------------------------------------

def build_context(message: str, session_id: str) -> tuple[str, list[dict]]:
    """
    Geeft (context_text, reference_hrefs) terug.
    reference_hrefs is een lijst van { title, description, href }.

    Logica:
      1. Chitchat          → geen context, geen hrefs
      2. Productcode       → scrape productpagina, sla op in sessie
                             + voeg PDF toe als assembly-vraag
      3. Assembly-vraag    → gebruik sessie-productpagina + PDF indien beschikbaar
      4. Winkelvraag       → winkelinfo scrapen
      5. Overig            → zoekresultaten
    """
    if is_chitchat(message):
        return "", []

    product_code = extract_product_code(message)

    if product_code:
        data = scrape_product_page(product_code)
        session_product[session_id] = {**data, "product_code": product_code}

        context = f"[Productpagina {product_code} — {data['page_url']}]\n{data['text']}"
        hrefs = [
            {
                "title": f"Productpagina {product_code}",
                "description": "Officiële IKEA-productpagina met info, maten en opties.",
                "href": data["page_url"],
            }
        ]

        if is_assembly_question(message) and data["assembly_pdf"]:
            context += f"\n\n[Montagehandleiding PDF]: {data['assembly_pdf']}"
            hrefs.append({
                "title": "Montagehandleiding (PDF)",
                "description": "Stap-voor-stap montage-instructies voor dit product.",
                "href": data["assembly_pdf"],
            })

        return context, hrefs

    if is_assembly_question(message) and session_id in session_product:
        saved = session_product[session_id]
        context = (
            f"[Productpagina {saved['product_code']} — {saved['page_url']}]\n"
            f"{saved['text']}"
        )
        hrefs = [
            {
                "title": f"Productpagina {saved['product_code']}",
                "description": "Officiële IKEA-productpagina met info, maten en opties.",
                "href": saved["page_url"],
            }
        ]
        pdf = saved.get("assembly_pdf")
        if pdf:
            context += f"\n\n[Montagehandleiding PDF]: {pdf}"
            hrefs.append({
                "title": "Montagehandleiding (PDF)",
                "description": "Stap-voor-stap montage-instructies voor dit product.",
                "href": pdf,
            })
        return context, hrefs

    if is_store_question(message):
        store_text, store_hrefs = get_store_context(message)
        return store_text, store_hrefs

    return get_search_context(message), []


# ---------------------------------------------------------------------------
# CHAT ENDPOINT
# ---------------------------------------------------------------------------

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    sid = request.session_id
    if sid not in chat_history:
        chat_history[sid] = []

    context, reference_hrefs = build_context(request.message, sid)

    if context:
        user_content = (
            f"Pagina Context:\n{context}\n\n"
            f"Beantwoord de volgende vraag UITSLUITEND op basis van bovenstaande context. "
            f"Als de context onvoldoende info bevat, zeg dat eerlijk en verwijs naar ikea.com/be/nl.\n\n"
            f"Vraag: {request.message}"
        )
    else:
        user_content = request.message

    messages = (
        [{"role": "system", "content": SYSTEM_INSTRUCTIE}]
        + chat_history[sid]
        + [{"role": "user", "content": user_content}]
    )

    resp = ollama_client.chat(model=CHAT_MODEL_NAME, messages=messages)
    antwoord = resp["message"]["content"]

    chat_history[sid].append({"role": "user", "content": request.message})
    chat_history[sid].append({"role": "assistant", "content": antwoord})

    return {
        "response_message": antwoord,
        "reference_hrefs": reference_hrefs,
    }


# ---------------------------------------------------------------------------
# BEHEER-ENDPOINTS
# ---------------------------------------------------------------------------

@app.delete("/session/{session_id}/product")
async def clear_product(session_id: str):
    """Verwijder het actieve product voor een sessie."""
    session_product.pop(session_id, None)
    return {"status": "product cleared"}


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Verwijder de volledige sessie."""
    chat_history.pop(session_id, None)
    session_product.pop(session_id, None)
    return {"status": "session cleared"}