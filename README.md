# 🏭 Tata Steel | SteelGuard AI

**Intelligent Maintenance Wizard for Integrated Steel Plants**

SteelGuard AI is an advanced, intelligent decision-support system built for maintenance engineers in steel manufacturing environments. It leverages Machine Learning (Isolation Forests) for real-time anomaly detection and Retrieval-Augmented Generation (RAG) powered by Large Language Models to diagnose equipment issues, predict remaining useful life, and generate comprehensive maintenance reports.

![Tata Steel Logo](Tata-Steel-logo.png)

## 🌟 Key Features
- **Real-Time Sensor Dashboard**: Live monitoring of critical equipment like Blast Furnaces, Rolling Mills, and Continuous Casters.
- **Dynamic Anomaly Detection**: Uses Scikit-Learn `IsolationForest` models trained on synthetic historical data to instantly flag threshold violations and anomalous behavior.
- **RAG-Powered AI Chat**: Multi-turn conversational AI contextually aware of live sensor readings and grounded in official equipment manuals, SOPs, and failure reports (via ChromaDB).
- **Automated Report Generation**: One-click generation of breakdown and maintenance reports.
- **Alert & Risk Monitor**: Plant-wide prioritization of equipment based on composite risk scoring and remaining useful life (RUL).
- **Maintenance Logbook**: Digital tracking of all preventive and corrective maintenance tasks.

## 🛠️ Technology Stack
- **Frontend / UI**: [Streamlit](https://streamlit.io/)
- **Machine Learning**: `scikit-learn`, `numpy`, `pandas`
- **Data Visualization**: `plotly`
- **Vector Database (RAG)**: `chromadb`
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`)
- **LLM Integration**: `langchain`, OpenRouter API (Gemma-4)
- **Database**: SQLite (for alerts, feedback, and logs)

---

## 🚀 How to Run Locally

### 1. Prerequisites
Ensure you have Python 3.9+ installed on your machine.

### 2. Setup Environment
Clone the repository and set up a virtual environment:
```bash
# Create a virtual environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\activate
# Activate it (Mac/Linux)
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. API Key Configuration
Create a `.env` file in the root directory and add your OpenRouter API key:
```env
OPENROUTER_API_KEY=your_api_key_here
```

### 5. Initialize the Knowledge Base
Before running the app, you must populate the local ChromaDB vector database with the equipment manuals:
```bash
python setup_kb.py
```
*Wait for the console to print "✅ Knowledge base ready."*

### 6. Start the App
```bash
streamlit run app.py
```

---

## ☁️ Deployment on Streamlit Community Cloud

Since this project uses local file generation (ChromaDB and Pickle ML models), it is perfectly suited for Streamlit Cloud, as these files will automatically generate on the cloud server during the first run.

1. **Push to GitHub**: Push this repository to your GitHub account. *(Ensure your `.env` file is excluded via `.gitignore` so your API key stays private!)*
2. **Deploy**: Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub repository.
3. **Set the Main File**: Point it to `app.py`.
4. **Configure Secrets**: In the Streamlit Cloud dashboard, go to your app settings -> **Secrets**, and paste your API key like this:
   ```toml
   OPENROUTER_API_KEY="your_api_key_here"
   ```
5. **Reboot / Deploy**: Click deploy! The app will install the `requirements.txt` and build the ML models on the fly. 

> **Note on ChromaDB in Cloud**: Streamlit Cloud is ephemeral. The ChromaDB knowledge base will need to be initialized on the cloud. You can add a button in your Streamlit UI to run the `setup_kb.py` logic, or simply rely on the "Init Knowledge Base" button already present in the app's sidebar!

---
*Developed for the Agentic AI Challenge Hackathon.*
