![Banner](/.github/banner.png)

# IKEA Chatbot

An intelligent chatbot application for IKEA-related inquiries in Belgium, built with React Native/Expo frontend and a FastAPI backend with local LLM support powered by Ollama.

## 📋 Project Overview

This project consists of two main components:

1. **ikea-chatbot-app**: A cross-platform mobile application (iOS, Android, Web) built with React Native and Expo
2. **ai-api-server**: A FastAPI backend server with AI capabilities via Ollama and local LLM processing

The chatbot specializes in IKEA customer service for Belgium, analyzing product information, answering assembly questions, providing store details, and responding to general inquiries through intelligent context detection and web scraping.

## 🗂️ Project Structure

```
dps2-project-2-comeos/
├── README.md
├── apps/
│   ├── ikea-chatbot-app/          # React Native/Expo frontend
│   │   ├── src/
│   │   │   ├── app/               # App routing (Expo Router)
│   │   │   ├── core/              # Business logic & API integration
│   │   │   └── style/             # Global styles
│   │   ├── hooks/                 # Custom React hooks (color scheme, theme)
│   │   ├── types/                 # TypeScript type definitions
│   │   ├── assets/                # Images and media files
│   │   ├── package.json           # npm dependencies
│   │   ├── tailwind.config.js      # Tailwind CSS configuration
│   │   └── tsconfig.json           # TypeScript configuration
│   │
│   └── ai-api-server/             # FastAPI backend
│       ├── main.py                # Main application server
│       ├── requirements.txt        # Python dependencies
│       ├── Dockerfile             # Docker configuration
│       └── docker-compose.yml      # Docker Compose setup
```

## 🚀 Getting Started

### Prerequisites

- **Node.js** (v18+) + npm/yarn
- **Python** (v3.10+) for backend
- **Docker** & **Docker Compose** (required for backend setup)
- **Ollama** (required - must be installed and Llama3 model downloaded)


### Frontend Setup (ikea-chatbot-app)

```bash
cd apps/ikea-chatbot-app
npm install
```

**Available scripts:**
```bash
npm start          # Start Expo development server
npm run android    # Run on Android emulator/device
npm run ios        # Run on iOS simulator/device
npm run web        # Run in browser
npm run lint       # Run ESLint
```

### Backend Setup (ai-api-server)
Prerequisites for Backend

Before running the backend, ensure **Ollama** is installed and **Llama3** model is downloaded:

1. **Install Ollama** from [ollama.ai](https://ollama.ai)
2. **Pull Llama3 model**:
   ```bash
   ollama pull llama3
   ```
   This downloads and caches the Llama3 model locally (required for the chatbot to function)

3. **Start Ollama service**:
   ```bash
   ollama serve
   ```
   This starts the Ollama server on `http://localhost:11434` (keep it running in the background)

#### Run Backend with Docker Compose

```bash
cd apps/ai-api-server
docker-compose up
```

The backend server runs on `http://localhost:8000` and connects to the Ollama instance running on your host machine.

**Note**: The Docker container is configured to connect to Ollama via `host.docker.internal` (macOS/Windows) or the gateway bridge (Linux), so ensure Ollama is running on your host before starting the container.

## 🔧 Technology Stack

### Frontend
- **React Native 0.81** - Cross-platform mobile framework
- **Expo 54** - Development and deployment platform
- **Expo Router 6** - File-based routing system
- **NativeWind 4** - Tailwind CSS for React Native
- **TypeScript** - Type-safe JavaScript
- **Axios** - HTTP client library
- **React Navigation** - Navigation primitives
- **Reanimated** - Smooth gesture-driven animations
- **AsyncStorage** - Persistent client-side storage

### Backend
- **FastAPI** - Modern async Python web framework
- **Ollama** - Local LLM inference engine
- **Llama3** - Large language model
- **BeautifulSoup4** - HTML/XML parsing and web scraping
- **Requests** - HTTP library
- **PDFPlumber** - PDF text extraction
- **Pydantic** - Data validation and serialization
- **Uvicorn** - ASGI server

## 💡 Key Features

### Intelligent Context Detection
The chatbot automatically detects message intent and provides relevant context:
- **Chitchat Detection**: Recognizes greetings, thanks, and small talk
- **Product Code Extraction**: Identifies IKEA product codes (e.g., 30541582) and scrapes product pages
- **Assembly Question Detection**: Identifies assembly/instruction questions and provides PDFs when available
- **Store Information**: Provides details about 12 IKEA stores across Belgium
- **General Search**: Falls back to search results for unidentified queries

### Frontend Features (ikea-chatbot-app)
The mobile application provides:
- Real-time chat interface with typing animations
- Session-based chat history (persisted locally)
- Cross-platform availability (iOS, Android, Web)
- Responsive design with NativeWind/Tailwind
- Reference links to product pages and assembly PDFs
- Typing indicator for bot responses

**Configuration:**
- `tailwind.config.js` - Theme and styling setup
- `expo-router` - File-system based navigation
- `src/core/networking/api.ts` - Axios API client configuration

### Backend Features (ai-api-server)
- **FastAPI REST endpoints** for chat interactions
- **Local LLM processing** via Ollama (no cloud dependency)
- **Web scraping** of IKEA product pages and store information
- **PDF extraction** for assembly instructions
- **Session management** for chat history per user
- **CORS-enabled** for cross-origin frontend requests
- **Dutch language optimization** - System instructions for Belgian Dutch responses

## 🔌 API Endpoints

### Chat Endpoint
**POST** `/chat`
```json
{
  "session_id": "unique-session-identifier",
  "message": "user-message"
}
```

Response:
```json
{
  "response_message": "chatbot-response",
  "reference_hrefs": [
    {
      "title": "Reference Title",
      "description": "Description",
      "href": "url"
    }
  ]
}
```

### Session Management Endpoints
**DELETE** `/session/{session_id}` - Clear entire session (chat history + products)

**DELETE** `/session/{session_id}/product` - Clear current product context

## 🛠️ Configuration

### Backend Environment

Configuration in `main.py`:
```python
OLLAMA_HOST = "http://host.docker.internal:11434"  # Ollama server URL
CHAT_MODEL_NAME = "llama3"                          # LLM model name
```

### IKEA Belgium Stores
Hardcoded store data for 12 locations:
- Ghent, Brussels, Antwerp, Liège, Namur, Bruges, Hasselt, Leuven, Kortrijk, Zellik

### System Instructions
The chatbot is configured with specific instructions to:
- Respond only in Dutch (for Belgium customers)
- Act as an IKEA service desk representative
- Use only provided context information
- Avoid ambiguous sourcing language
- Handle chitchat appropriately
- Stay factual and professional

### Frontend Styling
- **Tailwind (NativeWind) CSS** configuration: `tailwind.config.js`
- **Global styles**: `src/style/global.css`

## 📦 Key Dependencies

### Frontend (npm)
- `expo` ecosystem packages for native features
- `@react-navigation/*` for navigation
- `axios` for API communication
- `nativewind` for Tailwind integration
- `react-native-reanimated` for animations
- `@react-native-async-storage/async-storage` for local storage

### Backend (Python)
- `fastapi` & `uvicorn` for server framework
- `ollama` for LLM integration
- `beautifulsoup4` for web scraping
- `pdfplumber` for PDF processing
- `requests` for HTTP operations
- `pydantic` for data validation

### Contributors

- [Mees Akveld](https://www.linkedin.com/in/meesakveld/)
- [Darwin De Mits](https://www.linkedin.com/in/darwin-demits/)