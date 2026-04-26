# MalariaGEN NLP Data Portal

A natural-language interface for querying MalariaGEN genomic data. Users can ask questions in plain English — like *"How many samples are from Kenya?"* or *"Show kdr mutation frequencies in Kenya"* — and the system translates them into Python API calls, returning interactive data tables and Plotly visualizations.

Built as a prototype for **GSoC 2026 — Project 2: Natural Language Interfaces for Genomic Data**.

## Features

- **Natural Language Queries** — Ask questions in plain English, no coding required
- **Interactive Visualizations** — Plotly charts for bar plots, time series, frequency distributions
- **Data Tables** — Tabular results with CSV export
- **Reproducible Code** — Every response includes the generated Python code with one-click copy
- **Conversation Memory** — Context-aware follow-up queries (e.g., "filter that to gambiae")
- **Error Recovery** — Automatic retry with corrected parameters when API calls fail
- **Google OAuth** — Secure authentication linked to MalariaGEN data access
- **Chat Interface** — Full chat UI with message history, timestamps, and New Chat button

## How It Works

1. **User** sends a natural-language query through the chat interface
2. **LLM (Gemini 2.5 Flash)** interprets the query using a schema registry of all available `malariagen_data` API methods, their parameters, and docstrings
3. **Backend** executes the selected method with the extracted parameters against the MalariaGEN GCS data store
4. **Frontend** renders the results as interactive Plotly charts or HTML data tables with export options

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask (Python), Blueprint architecture |
| LLM | Google Gemini 2.5 Flash via OpenAI SDK |
| Data | `malariagen_data` Python package (Ag3, Af1, Pf8) |
| Auth | Google OAuth 2.0 via Authlib |
| Frontend | Vanilla HTML/CSS/JS, Plotly.js |
| Deployment | Firebase Studio / Cloud Workstations |

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/malariagen-nlp-portal.git
cd malariagen-nlp-portal
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Linux/Mac
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create a `.env` file

Create a `.env` file in the project root with your credentials:

```
SECRET_KEY=your-flask-secret-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GEMINI_API_KEY=your-gemini-api-key
```

> **Note:** You need a Google Cloud project with OAuth 2.0 credentials and a Gemini API key from Google AI Studio.

### 5. Run the app

```bash
python run.py
```

The app will be available at `http://127.0.0.1:5000`.

## Data Access

This app queries **MalariaGEN** public genomic datasets. To access the data, your Google account must be registered with MalariaGEN. If you haven't already, submit a data access request at:
https://forms.gle/d1NV3aL3EaVQ6ShYA
