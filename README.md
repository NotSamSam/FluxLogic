# ⚡ FluxLogic — Engineering-led Data Automation
### **Universal Data Connector · Upload · Process · Dispatch**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

**FluxLogic** est une preuve de concept (PoC) "SaaS-ready" conçue pour démontrer l'ingénierie de pipelines de données de bout en bout — de l'ingestion à l'envoi via API — avec un accent mis sur la validation, la résilience et l'observabilité.

---

## 📌 Problématique
Les entreprises SaaS modernes dépendent de nombreux services tiers (CRM, analytics, facturation). Le transfert de données entre ces systèmes repose souvent sur des scripts fragiles manquant de :
* **Validation de schéma** : Les données erronées se propagent silencieusement.
* **Logique de réessai (Retry)** : Les pannes temporaires d'API causent des pertes de données.
* **Auditabilité** : Aucun historique sur l'origine et la destination des flux.

**FluxLogic** résout cela avec un connecteur unique et configurable qui nettoie, valide et distribue les données de manière fiable vers n'importe quelle API REST.

---

## 🏗️ Architecture

```mermaid
graph TD
    A[Streamlit Dashboard] --> B[DataProcessor ETL]
    A --> C[ApiClient Dispatch]
    B --> D{Pydantic Validation}
    D -->|Success| C
    C --> E[External API / Webhooks]
    E --> F[Flow Logs & Audit]
