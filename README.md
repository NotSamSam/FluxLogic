# ⚡ FluxLogic

**Universal Data Connector** — Un outil simple pour envoyer vos fichiers de données vers n'importe quelle API.

[![Site Statique](https://img.shields.io/badge/Demo-GitHub_Pages-22c55e?logo=github)](https://notsamsam.github.io/FluxLogic/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org)

---

## C'est quoi FluxLogic ?

En termes simples, **FluxLogic est un "facteur" pour vos données**. 

Imaginez que vous avez un fichier Excel (CSV) ou JSON avec une liste de clients, et que vous devez envoyer ces informations à un autre logiciel (comme un CRM, un outil d'emailing, ou une base de données).

Au lieu de le faire à la main, FluxLogic s'occupe de tout :
1. **Il prend votre fichier.**
2. **Il vérifie que les données sont valides** (ex: il vérifie que tout le monde a bien un nom et un email).
3. **Il les livre** automatiquement et de manière sécurisée au logiciel de destination via Internet.

Ce projet démontre des compétences clés en ingénierie logicielle (Data Engineering, API REST, Validation de données, et Webhooks).

---

## Mini-Tutoriel : Testez-le vous-même en 2 minutes !

Vous pouvez tester l'application directement sur le site web sans rien installer. Suivez ces étapes simples :

### Étape 1 : Créez une "Boîte aux lettres" de destination
1. Ouvrez un nouvel onglet et allez sur **[webhook.site](https://webhook.site/)**.
2. Ce site va vous générer une URL unique (ex: `https://webhook.site/1234-abcd-5678`). **Copiez cette URL**.

### Étape 2 : Configurez FluxLogic
1. Allez sur **FluxLogic**, dans l'onglet **"⚙️ Endpoints"**.
2. Ajoutez un Endpoint :
   - Name : `Mon Test API`
   - URL : *Collez l'URL que vous venez de copier*.
   - Cliquez sur **Save Endpoint**.

### Étape 3 : Chargez des données
1. Allez dans l'onglet **"📂 Data Upload"**.
2. Dans la zone "Paste JSON data", collez cet exemple :
   ```json
   [
     { "name": "Lucas", "email": "lucas@exemple.com" },
     { "name": "Alice", "email": "alice@exemple.com" }
   ]
   ```
3. Cliquez sur **Load JSON**.

### Étape 4 : Validez les données
1. Juste en dessous, dans **Required Fields**, tapez le nom des colonnes requises : `name, email`
2. Cliquez sur **▶️ Run Processing Pipeline**. Les données vont s'afficher en vert (Validées).

### Étape 5 : Expédiez ! (Dispatch)
1. Allez dans l'onglet **"🚀 Dispatch"**.
2. Sélectionnez `Mon Test API` et cliquez sur **📤 Dispatch Now**.
3. **Magie :** Retournez sur l'onglet de `webhook.site`, vous verrez que vos données (Lucas et Alice) viennent d'arriver en temps réel !

---

## Installation pour les développeurs (Version Python)

Ce dépôt contient aussi la vraie version Back-end en Python (Streamlit). Pour la lancer sur votre machine :

```bash
# 1. Cloner le projet
git clone https://github.com/VOTRE-USERNAME/fluxlogic.git
cd fluxlogic

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer l'application
streamlit run fluxlogic_app.py
```
