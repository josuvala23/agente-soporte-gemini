# 🤖 Agente de Soporte Inteligente con Python y Google Gemini

Agente autónomo de Inteligencia Artificial que monitoriza las quejas o comentarios de clientes registrados en un **Google Form**, los clasifica por categoría y analiza su sentimiento utilizando la API de **Google Gemini**, y actualiza los resultados en tiempo real en una base de datos de **Google Sheets**.

---

## 🏗️ Arquitectura del Sistema

```
Google Forms (Entrada del usuario) 
       ⬇
Google Sheets (Base de datos de respuestas)
       ⬇
Script Python (Agente Autónomo) 
       ⬇
Google Gemini API (Análisis y Clasificación IA)
       ⬇
Google Sheets (Actualización de columnas D, E y F con resultados)
```

---

## 🛠️ Tecnologías y Librerías

- **Python 3.9+**
- **[google-genai](https://pypi.org/project/google-genai/)**: SDK oficial de Google para interactuar con modelos Gemini.
- **[gspread](https://pypi.org/project/gspread/)**: Cliente Python para Google Sheets API.
- **[google-auth](https://pypi.org/project/google-auth/)**: Autenticación OAuth 2.0 segura con Google Cloud.
- **[schedule](https://pypi.org/project/schedule/)**: Programación de tareas recurrentes para ejecución periódica.

---

## 📋 Requisitos Previos

1. Tener instalado **Python 3.9 o superior**.
2. Una cuenta de Google para acceder a **Google Forms**, **Google Sheets**, **Google Cloud Console** y **Google AI Studio**.

---

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
cd TU_REPOSITORIO
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar Credenciales

#### A. Google Sheets API (OAuth 2.0)
1. En [Google Cloud Console](https://console.cloud.google.com/), crea un proyecto y habilita **Google Sheets API** y **Google Drive API**.
2. Configura la **Pantalla de consentimiento de OAuth** (tipo *External*) y añade tu correo a **Test users**.
3. En **Credenciales**, crea un **ID de cliente de OAuth 2.0** de tipo *Aplicación de escritorio* (Desktop).
4. Descarga el archivo JSON, nómbralo `client_secrets.json` y colócalo en la raíz del proyecto.

#### B. API Key de Google Gemini
1. Obtén tu clave gratuita en [Google AI Studio](https://aistudio.google.com/app/api-keys).
2. Copia el archivo `.env.example` como `.env`:
   ```bash
   cp .env.example .env
   ```
3. Coloca tu clave dentro de `.env`:
   ```env
   GEMINI_API_KEY=tu_api_key_aqui
   ```

---

## ▶️ Ejecución del Agente

Inicia el agente con:
```bash
python agente_soporte.py
```

- La primera vez se abrirá automáticamente tu navegador para autorizar la conexión con Google Sheets.
- El agente se ejecutará de inmediato para revisar las quejas pendientes y luego continuará ejecutándose automáticamente cada 15 minutos.
