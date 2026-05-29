import requests
from bs4 import BeautifulSoup
import ollama
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List

# --- CONFIGURATIE ---
OLLAMA_HOST = "http://host.docker.internal:11434"
CHAT_MODEL_NAME = "llama3"

ollama_client = ollama.Client(host=OLLAMA_HOST)
app = FastAPI(title="IKEA Intelligent Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

chat_history: Dict[str, List[dict]] = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str

# --- SYSTEM INSTRUCTIE ---
SYSTEM_INSTRUCTIE = (
    "Je bent een professionele IKEA-service desk medewerker. "
    "REGELS: "
    "1. Je werkt enkel op basis van de meegeleverde 'Pagina Context'. Verzin NOOIT productnamen, prijzen of voorraden. "
    "2. Als een product niet in de context staat, zeg: 'Ik kan op dit moment geen specifiek model vinden, ik raad aan om even in de winkel in Gent te kijken.' "
    "3. Presenteer informatie als eigen kennis; gebruik NOOIT 'volgens de website' of 'ik zie in de tekst'. "
    "4. Gebruik geen informele aanspreekvormen als 'vriend' of 'buddy'. Blijf zakelijk en behulpzaam. "
    "5. Beëindig het gesprek na een bedankje. Start niet uit jezelf een nieuw onderwerp."
)

def get_ikea_url(message: str):
    base = "https://www.ikea.com/be/nl"
    # Winkelcheck
    if any(w in message.lower() for w in ["gent", "opening", "tijden", "open", "sluit"]):
        return f"{base}/stores/gent/"
    # Zoekopdracht met volledige query
    return f"{base}/search/?q={message.replace(' ', '%20')}"

def smart_scrape(url: str):
    """Scrapt tekst en producttitels met taal-dwang."""
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "nl-BE"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Specifieke extractie voor productnamen
        producten = [el.get_text(strip=True) for el in soup.find_all(class_="pip-product-summary__title")]
        
        for s in soup(["script", "style", "nav", "footer", "header", "aside", "svg"]): 
            s.decompose()
        
        tekst = soup.get_text(separator=" ", strip=True)
        return f"Producten gevonden: {', '.join(producten)} | Details: {tekst[:6000]}"
    except: return "Informatie niet direct beschikbaar."

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if request.session_id not in chat_history: chat_history[request.session_id] = []
    
    url = get_ikea_url(request.message)
    context = smart_scrape(url)
    
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTIE}] + chat_history[request.session_id] + \
               [{"role": "user", "content": f"Pagina Context: {context}\n\nVraag: {request.message}"}]
    
    resp = ollama_client.chat(model=CHAT_MODEL_NAME, messages=messages)
    antwoord = resp["message"]["content"]
    
    chat_history[request.session_id].append({"role": "user", "content": request.message})
    chat_history[request.session_id].append({"role": "assistant", "content": antwoord})
    
    return {"response_message": antwoord}