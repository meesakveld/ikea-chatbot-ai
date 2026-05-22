import time
import requests
import asyncio
import re
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import ollama
from fastapi import FastAPI, HTTPException
# FIX: Importeer de CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import traceback

# Docker Configuraties
OLLAMA_HOST = "http://ollama:11434"
QDRANT_HOST = "http://qdrant"
COLLECTION_NAME = "ikea_products_generiek_v13"
EMBED_MODEL_NAME = "nomic-embed-text:latest"
CHAT_MODEL_NAME = "llama3:latest"

ollama_client = ollama.Client(host=OLLAMA_HOST)
qdrant_client = QdrantClient(url=QDRANT_HOST, port=6333)
app = FastAPI(title="IKEA Chatbot API - Zelflerend (Scrape-on-Demand)")

# --- FIX: CORS CONFIGURATIE TOEVOEGEN ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],             # Staat alle domeinen toe
    allow_credentials=True,
    allow_methods=["*"],             # Staat alle HTTP methods toe (POST, GET, etc.)
    allow_headers=["*"],             # Staat alle HTTP headers toe
)
# ----------------------------------------

database_ready = False
sessions_db = {}
huidige_point_id = 1

# Instructie aangescherpt tegen geschiedenisvervuiling
SYSTEM_INSTRUCTIE = (
    "Jij bent een professionele en zakelijke IKEA assistent. "
    "Begin direct met het antwoord en gebruik geen amicale openingen zoals 'Lieve klant'.\n"
    "Beantwoord de vraag uitsluitend op basis van de direct meegeleverde CONTEXT uit de database. "
    "Gebruik NOOIT zinnen zoals 'Volgens de database' of 'Uit de context blijkt'.\n"
    "FOCUS-REGEL: Kijk kritisch naar de HUIDIGE KLANTVRAAG. Als de geschiedenis over een ander onderwerp "
    "ging (zoals JavaScript of programmeren), maar de huidige vraag gaat over IKEA producten of diensten, "
    "negeer het oude onderwerp dan volledig en focus je puur op de nieuwe vraag en de nieuwe CONTEXT.\n"
    "Als de context leeg is of het onderwerp is ongerelateerd aan IKEA, antwoord dan exact: "
    "'Excuses, daar heb ik geen informatie over.'"
)

class ChatRequest(BaseModel):
    session_id: str  
    message: str     

class ReferenceHref(BaseModel):
    title: str
    description: str
    href: str

class ChatResponse(BaseModel):
    response_message: str
    reference_hrefs: Optional[List[ReferenceHref]] = None  

def extraheer_productnaam_uit_url(url: str) -> str:
    if "/p/" in url:
        match = re.search(r'/p/([a-zA-Z0-9]+)-', url)
        if match:
            return match.group(1).lower()
    else:
        segmenten = [s for s in url.strip("/").split("/") if s]
        if segmenten:
            return segmenten[-1].lower()
    return "algemeen"

def scrape_en_splits(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200: return []
        
        soup = BeautifulSoup(res.text, "html.parser")
        for s in soup(["script", "style", "nav", "footer", "header", "aside"]): 
            s.decompose()
            
        hoofd_tekst = soup.get_text(separator=" ")
        url_type = "PRODUCT" if "/p/" in url else "INFO_PAGINA"
        item_name = extraheer_productnaam_uit_url(url)
        
        volledige_data = f"[{url_type}: {item_name.upper()}] BODY: {hoofd_tekst}"
        
        woorden = volledige_data.split()
        chunks = []
        for i in range(0, len(woorden), 120 - 30):
            chunk = " ".join(woorden[i:i + 120])
            if len(chunk.strip()) > 30: 
                chunks.append(chunk)
        return chunks
    except Exception as e:
        print(f"❌ [SCRAPER] Fout bij {url}: {e}")
        return []

def ontdek_en_scrape_product_live(zoekterm: str) -> bool:
    global huidige_point_id
    
    schone_zoekterm = zoekterm.replace(".", "")
    print(f"🔍 [ON-DEMAND] Directe product-URL opbouwen voor IKEA.nl: '{schone_zoekterm}'...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    directe_url = f"https://www.ikea.com/nl/nl/p/{schone_zoekterm}/"
    try:
        res = requests.get(directe_url, headers=headers, timeout=10)
        
        if res.status_code != 200:
            print(f"⚠️ [ON-DEMAND] NL pagina gaf {res.status_code}. Proberen van BE variant...")
            directe_url = f"https://www.ikea.com/be/nl/p/{schone_zoekterm}/"
            res = requests.get(directe_url, headers=headers, timeout=10)
            
        if res.status_code != 200:
            print(f"❌ [ON-DEMAND] Product {schone_zoekterm} niet direct vindbaar op IKEA NL of BE.")
            return False
            
        print(f"🎯 [ON-DEMAND] Productpagina succesvol geladen: {directe_url}")
        rauwe_html = res.text
        soup = BeautifulSoup(rauwe_html, "html.parser")
        
        manual_url = warme_url = directe_url
        
        gevonden_via_tag = False
        for a_tag in soup.find_all("a", href=True):
            href_attr = a_tag["href"]
            text_attr = a_tag.get_text().lower()
            
            if "montage" in text_attr or "instructie" in text_attr or "manual" in text_attr or ".pdf" in href_attr.lower():
                manual_url = f"https://www.ikea.com{href_attr}" if href_attr.startswith("/") else href_attr
                print(f"📄 [ON-DEMAND] Succes! Handleiding gevonden via HTML-tag: {manual_url}")
                gevonden_via_tag = True
                break
                
        if not gevonden_via_tag:
            pdf_matches = re.findall(r'https://www\.ikea\.com/[^\s"\'\>]+/assembly_instructions/[^\s"\'\>]+\.pdf', rauwe_html)
            if pdf_matches:
                manual_url = pdf_matches[0]
                print(f"📄 [ON-DEMAND] Succes! Handleiding gevonden via rauwe Regex-scan: {manual_url}")
        
        for s in soup(["script", "style", "nav", "footer", "header", "aside"]): 
            s.decompose()
        prod_tekst = soup.get_text(separator=" ")
        
        volledige_prod_data = (
            f"[PRODUCT: DIRECT_MATCH] \n"
            f"PRODUCTNUMMER: {schone_zoekterm} \n"
            f"DIRECTE HANDLEIDING LINK: {manual_url} \n"
            f"CONTEXT: Dit document bevat de officiële montage-instructies en de handleiding voor het IKEA product met nummer {schone_zoekterm}. "
            f"De klant kan de handleiding direct inzien en downloaden via de volgende link: {manual_url}."
        )
        
        product_chunks = []
        woorden_prod = volledige_prod_data.split()
        for i in range(0, len(woorden_prod), 120 - 30):
            chunk = " ".join(woorden_prod[i:i + 120])
            if len(chunk.strip()) > 30: 
                product_chunks.append(chunk)
                
        for chunk in product_chunks:
            vector = ollama_client.embeddings(model=EMBED_MODEL_NAME, prompt=chunk)["embedding"]
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=huidige_point_id, 
                        vector=vector, 
                        payload={
                            "text": chunk, 
                            "source": manual_url, 
                            "item_name": schone_zoekterm,
                            "url_type": "product"
                        }
                    )
                ]
            )
            huidige_point_id += 1
            
        print(f"✅ [ON-DEMAND] Handleiding-vectoren succesvol weggeschreven naar Qdrant!")
        return True
        
    except Exception as e:
        print(f"❌ [ON-DEMAND] Fout tijdens het direct scrapen van de productpagina: {e}")
        return False

def voeg_initiele_urls_toe(urls):
    global huidige_point_id
    for url in urls:
        item_name = extraheer_productnaam_uit_url(url)
        url_type = "product" if "/p/" in url else "pagina"
        chunks = scrape_en_splits(url)
        for chunk in chunks:
            vector = ollama_client.embeddings(model=EMBED_MODEL_NAME, prompt=chunk)["embedding"]
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(id=huidige_point_id, vector=vector, payload={"text": chunk, "source": url, "item_name": item_name, "url_type": url_type})]
            )
            huidige_point_id += 1

def initialiseer_database(urls):
    global database_ready
    time.sleep(5)
    try:
        collections_response = qdrant_client.get_collections()
        bestaat_al = any(c.name == COLLECTION_NAME for c in collections_response.collections)
        
        if bestaat_al:
            print(f"💾 [DATABASE-INIT] Collectie {COLLECTION_NAME} gevonden!")
            info = qdrant_client.get_collection(collection_name=COLLECTION_NAME)
            global huidige_point_id
            huidige_point_id = info.points_count + 1
            database_ready = True
            return

        print(f"📦 [DATABASE-INIT] Bouwen van collectie: {COLLECTION_NAME}")
        test_emb = ollama_client.embeddings(model=EMBED_MODEL_NAME, prompt="test")["embedding"]
        vector_size = len(test_emb)
        
        qdrant_client.create_collection(collection_name=COLLECTION_NAME, vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE))
        voeg_initiele_urls_toe(urls)
        database_ready = True
        print(f"✅ [DATABASE-INIT] Database succesvol gevuld!")
    except Exception as e:
        traceback.print_exc()

def zoek_relevante_context_en_bronnen(vraag, top_k=10, loop_retry=True):
    vraag_vector = ollama_client.embeddings(model=EMBED_MODEL_NAME, prompt=vraag)["embedding"]
    qdrant_url = f"{QDRANT_HOST}:6333/collections/{COLLECTION_NAME}/points/search"
    
    payload = {"vector": vraag_vector, "limit": top_k, "with_payload": True}
    
    STAD_MAPPING = {"antwerpen": "wilrijk", "brussel": "anderlecht"}
    bekende_steden = ["anderlecht", "arlon", "gent", "hasselt", "liege", "mons", "wilrijk", "zaventem"]
    bekende_producten = ["kallax", "billy"]
    
    woorden_in_vraag = [w.strip("?,!").lower() for w in vraag.split()]
    is_brede_vraag = "belgië" in woorden_in_vraag or "belgie" in woorden_in_vraag or "winkels" in woorden_in_vraag
    
    it_keywords = ["javascript", "python", "html", "css", "code", "programmeren", "script", "bug", "functies"]
    is_it_vraag = any(it in woorden_in_vraag for it in it_keywords)

    actieve_stad_in_vraag = None
    for woord in woorden_in_vraag:
        if woord in STAD_MAPPING:
            actieve_stad_in_vraag = STAD_MAPPING[woord]
            break
        elif woord in bekende_steden:
            actieve_stad_in_vraag = woord
            break

    product_nummer_term = None
    for woord in woorden_in_vraag:
        schoon_woord = woord.replace(".", "")
        if schoon_woord.isdigit() and len(schoon_woord) >= 6:
            product_nummer_term = schoon_woord
            break

    gedetecteerde_naam = actieve_stad_in_vraag if not product_nummer_term else product_nummer_term
    if not gedetecteerde_naam:
        for woord in woorden_in_vraag:
            if woord in bekende_producten:
                gedetecteerde_naam = woord
                break

    if gedetecteerde_naam:
        payload["filter"] = {"must": [{"key": "item_name", "match": {"value": gedetecteerde_naam}}]}
    elif is_brede_vraag:
        payload["filter"] = {"must": [{"key": "url_type", "match": {"value": "pagina"}}]}

    res = requests.post(qdrant_url, json=payload, timeout=5)
    hits = res.json().get("result", [])
    
    minimale_score_drempel = 0.58 if is_it_vraag else 0.48
    hoge_scores = [h for h in hits if h.get("score", 0) > minimale_score_drempel]
    
    if not hoge_scores and loop_retry and not actieve_stad_in_vraag and not is_brede_vraag and not is_it_vraag:
        if product_nummer_term:
            succes = ontdek_en_scrape_product_live(product_nummer_term)
            if succes:
                return zoek_relevante_context_en_bronnen(vraag, top_k=top_k, loop_retry=False)
        else:
            stopwoorden = ["wat", "is", "het", "de", "een", "van", "voor", "heeft", "afmetingen", "prijs", "winkel", "waar", "ikea", "producten", "weet", "over", "je", "manual", "handleiding", "doorsturen"]
            mogelijke_termen = [w for w in woorden_in_vraag if w not in stopwoorden and len(w) > 3]
            if mogelijke_termen:
                succes = ontdek_en_scrape_product_live(mogelijke_termen[0])
                if succes:
                    return zoek_relevante_context_en_bronnen(vraag, top_k=top_k, loop_retry=False)

    context_teksten = []
    bron_urls = set()  

    for hit in hits:
        score = hit.get("score", 0)
        hit_payload = hit.get("payload", {})
        source_url = hit_payload.get("source", "")
        
        if score > minimale_score_drempel:
            if actieve_stad_in_vraag and hit_payload.get("url_type") == "pagina":
                if actieve_stad_in_vraag not in source_url.lower():
                    continue

            context_teksten.append(hit_payload.get("text", ""))
            if "source" in hit_payload:
                if not source_url.endswith("/stores/"):
                    bron_urls.add(source_url)
            
    full_context = "\n\n".join(context_teksten)
    return full_context, list(bron_urls)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    global database_ready
    if not database_ready:
        raise HTTPException(status_code=503, detail="Database start nog op...")

    session_id = request.session_id
    vraag = request.message

    if session_id not in sessions_db:
        sessions_db[session_id] = []

    try:
        context, bronnen = zoek_relevante_context_en_bronnen(vraag)
        messages_payload = [{"role": "system", "content": SYSTEM_INSTRUCTIE}]
        
        for past_msg in sessions_db[session_id]:
            messages_payload.append(past_msg)
            
        if context:
            print(f"   -> Context succesvol geladen. Aantal bronnen: {len(bronnen)}")
            geoptimaleerde_prompt = (
                f"CONTEXT UIT DATABASE:\n{context}\n\n"
                f"⚠️ BELANGRIJKE INSTRUCTIE:\n"
                f"1. Antwoord ALTIJD in het Nederlands.\n"
                f"2. De klant vraagt naar een handleiding/manual. Bevestig dat deze beschikbaar is.\n"
                f"3. De link wordt automatisch onderaan de chat als knop getoond, dus je hoeft de URL zelf NIET in je tekst te typen.\n"
                f"HUIDIGE KLANTVRAAG: {vraag}"
            )
        else:
            print("   -> Geen context gevonden.")
            geoptimaleerde_prompt = vraag
            
        messages_payload.append({"role": "user", "content": geoptimaleerde_prompt})

        response = ollama_client.chat(model=CHAT_MODEL_NAME, messages=messages_payload)
        antwoord = response["message"]["content"]

        sessions_db[session_id].append({"role": "user", "content": vraag})
        sessions_db[session_id].append({"role": "assistant", "content": antwoord})

        reference_hrefs = None
        if bronnen:
            print(f"🔗 [API] Links meesturen naar de klant: {bronnen}")
            reference_hrefs = [
                ReferenceHref(
                    title="Handleiding / Document bekijken", 
                    description="Klik hier om de officiële montage-instructies (PDF) te openen.", 
                    href=url
                )
                for url in bronnen
            ]

        return ChatResponse(response_message=antwoord, reference_hrefs=reference_hrefs)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    ikea_urls = [
        "https://www.ikea.com/be/nl/stores/",
        "https://www.ikea.com/be/nl/stores/anderlecht/",
        "https://www.ikea.com/be/nl/stores/arlon/",
        "https://www.ikea.com/be/nl/stores/gent/",
        "https://www.ikea.com/be/nl/stores/hasselt/",
        "https://www.ikea.com/be/nl/stores/liege/",
        "https://www.ikea.com/be/nl/stores/mons/",
        "https://www.ikea.com/be/nl/stores/wilrijk/",
        "https://www.ikea.com/be/nl/stores/zaventem/",
    ]
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, initialiseer_database, ikea_urls)
    print("\n🚀 FastAPI Server start nu op poort 8000. Database vult op de achtergrond...")