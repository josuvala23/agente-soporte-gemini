import json
import os
import sys
import time
import schedule
import gspread
from google import genai
from google.genai import types

# ==========================================
# CONFIGURACIÓN DEL AGENTE
# ==========================================
ARCHIVO_CREDENCIALES = "client_secrets.json"
NOMBRE_HOJA = "Respuestas de Quejas (Base de Datos)"

# Función auxiliar para cargar variables desde .env si existe
def cargar_env():
    ruta_env = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(ruta_env):
        with open(ruta_env, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    clave, valor = linea.split("=", 1)
                    os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))

cargar_env()

# Clave de Gemini (leída de forma segura desde .env o variable de entorno)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TU_API_KEY_AQUI")

INTERVALO_MINUTOS = 15

# Índices de columnas en Google Sheets (1-indexado para gspread)
COL_CLASIFICACION = 4   # Columna D: Clasificación IA
COL_SENTIMIENTO = 5     # Columna E: Sentimiento IA
COL_EJECUTADO = 6       # Columna F: Agente Ejecutado ('SI')

# Cliente global de Gemini
cliente_gemini = None


# ==========================================
# FUNCIONES DEL AGENTE
# ==========================================
def conectar_sheets():
    """Autentica con OAuth 2.0 y abre la primera hoja de cálculo de Google Sheets."""
    try:
        # Autenticación con OAuth 2.0 usando el archivo de credenciales descargado
        gc = gspread.oauth(credentials_filename=ARCHIVO_CREDENCIALES)
        
        # Intentar abrir la hoja por su nombre exacto
        try:
            hoja_calculo = gc.open(NOMBRE_HOJA)
        except gspread.exceptions.SpreadsheetNotFound:
            # Si no coincide exactamente, buscar si alguna hoja contiene el nombre
            archivos = gc.list_spreadsheet_files()
            coincidencias = [f for f in archivos if "Respuestas de Quejas" in f["name"]]
            if coincidencias:
                nombre_encontrado = coincidencias[0]["name"]
                print(f"[INFO] Abriendo hoja encontrada: '{nombre_encontrado}'")
                hoja_calculo = gc.open_by_key(coincidencias[0]["id"])
            else:
                print(f"[ERROR] No se encontró ninguna hoja con el nombre '{NOMBRE_HOJA}'.")
                print("Hojas encontradas en tu Google Drive:")
                for f in archivos[:5]:
                    print(f" - {f['name']}")
                return None
        
        # Retornar la primera hoja (sheet1)
        return hoja_calculo.sheet1
    except Exception as e:
        print(f"[ERROR] Error al conectar con Google Sheets: {e}")
        return None


def analizar_con_gemini(comentario):
    """
    Envía el comentario a Gemini 2.5 Flash para clasificar la categoría y detectar el sentimiento.
    Retorna un diccionario con las claves 'clasificacion' y 'sentimiento'.
    """
    instruccion_sistema = (
        "Eres un analista experto de soporte al cliente. "
        "Tu única tarea es analizar el comentario de un cliente y devolver ÚNICAMENTE una respuesta "
        "en formato JSON válido, sin texto adicional, sin explicaciones ni introducciones. "
        "El JSON debe tener exactamente esta estructura:\n"
        "{\n"
        '  "clasificacion": "Ventas" | "Soporte Técnico" | "Logística",\n'
        '  "sentimiento": "Positivo" | "Negativo" | "Neutro"\n'
        "}"
    )

    prompt_usuario = (
        f"Analiza el siguiente comentario de un cliente:\n\n"
        f"\"{comentario}\"\n\n"
        "Clasifícalo en una de estas 3 categorías: 'Ventas', 'Soporte Técnico' o 'Logística'. "
        "Detecta el sentimiento entre: 'Positivo', 'Negativo' o 'Neutro'."
    )

    config = types.GenerateContentConfig(
        system_instruction=instruccion_sistema,
        response_mime_type="application/json"
    )

    try:
        respuesta = cliente_gemini.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt_usuario,
            config=config
        )
    except Exception as err:
        if "404" in str(err):
            respuesta = cliente_gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_usuario,
                config=config
            )
        else:
            raise err

    texto_respuesta = respuesta.text.strip()

    # Limpiar posibles bloques de código markdown que el modelo pudiera agregar
    if texto_respuesta.startswith("```json"):
        texto_respuesta = texto_respuesta[len("```json"):].strip()
    if texto_respuesta.startswith("```"):
        texto_respuesta = texto_respuesta[len("```"):].strip()
    if texto_respuesta.endswith("```"):
        texto_respuesta = texto_respuesta[:-len("```")].strip()

    # Parsear JSON a diccionario de Python
    return json.loads(texto_respuesta)


def ejecutar_agente():
    """Orquesta el ciclo completo de lectura, análisis y actualización."""
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando ciclo de revisión del agente...")

    hoja = conectar_sheets()
    if hoja is None:
        print("[AVISO] No se pudo conectar a Google Sheets. Se reintentará en el próximo ciclo.")
        return

    try:
        # Obtener todas las filas (lista de listas)
        todas_las_filas = hoja.get_all_values()
    except Exception as e:
        print(f"[ERROR] Error al leer los datos de la hoja: {e}")
        return

    if len(todas_las_filas) <= 1:
        print("[INFO] La hoja solo contiene encabezados o está vacía. No hay filas que procesar.")
        return

    # Omitimos la primera fila (índice 0, encabezados)
    filas_datos = todas_las_filas[1:]
    filas_procesadas = 0

    for idx, fila in enumerate(filas_datos):
        numero_fila_sheet = idx + 2  # En Sheets las filas inician en 1, y la fila 1 es encabezado

        # Columna F (índice 5 en lista base 0) indica si ya fue procesado
        estado_ejecutado = fila[5].strip() if len(fila) > 5 else ""

        if estado_ejecutado.upper() == "SI":
            continue  # Fila ya procesada anteriormente

        # Extraer nombre (Columna B / índice 1) y comentario (Columna C / índice 2)
        nombre = fila[1].strip() if len(fila) > 1 else "Anónimo"
        comentario = fila[2].strip() if len(fila) > 2 else ""

        if not comentario:
            print(f"[AVISO] Fila {numero_fila_sheet}: Comentario vacío. Saltando...")
            continue

        print(f"\n--- Procesando fila {numero_fila_sheet} ---")
        print(f"Cliente: {nombre}")
        print(f"Comentario: {comentario}")

        try:
            resultado = analizar_con_gemini(comentario)
            clasificacion = resultado.get("clasificacion", "Desconocido")
            sentimiento = resultado.get("sentimiento", "Desconocido")

            print(f"-> Clasificación detectada: {clasificacion}")
            print(f"-> Sentimiento detectado: {sentimiento}")

            # Escribir en Google Sheets
            hoja.update_cell(numero_fila_sheet, COL_CLASIFICACION, clasificacion)
            hoja.update_cell(numero_fila_sheet, COL_SENTIMIENTO, sentimiento)
            hoja.update_cell(numero_fila_sheet, COL_EJECUTADO, "SI")

            print(f"-> Fila {numero_fila_sheet} actualizada con éxito en Google Sheets.")
            filas_procesadas += 1

        except json.JSONDecodeError as err:
            print(f"[ERROR] Gemini no devolvió un JSON válido para la fila {numero_fila_sheet}: {err}")
        except Exception as e:
            print(f"[ERROR] Error inesperado procesando la fila {numero_fila_sheet}: {e}")

    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ciclo completado. Filas procesadas en este ciclo: {filas_procesadas}.")


# ==========================================
# PUNTO DE ENTRADA PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("       AGENTE DE SOPORTE CON PYTHON Y GEMINI")
    print("=" * 60)

    # 1. Validar la API Key
    if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_API_KEY_AQUI":
        print("[ERROR] Debes configurar tu GEMINI_API_KEY dentro de agente_soporte.py antes de iniciar.")
        print("Obtén tu clave gratuita en: https://aistudio.google.com/app/api-keys")
        sys.exit(1)

    # 2. Validar archivo de credenciales OAuth
    if not os.path.exists(ARCHIVO_CREDENCIALES):
        print(f"[ERROR] No se encontró el archivo '{ARCHIVO_CREDENCIALES}' en la carpeta del script.")
        print("Descarga las credenciales OAuth 2.0 desde Google Cloud Console y colócalas aquí.")
        sys.exit(1)

    # 3. Inicializar el cliente de Gemini
    try:
        cliente_gemini = genai.Client(api_key=GEMINI_API_KEY)
        print("[OK] Cliente de Gemini inicializado correctamente.")
    except Exception as e:
        print(f"[ERROR] No se pudo inicializar el cliente de Gemini: {e}")
        sys.exit(1)

    # 4. Ejecutar inmediatamente la primera vez
    print(f"\n[INICIO] Ejecutando agente por primera vez...")
    ejecutar_agente()

    # 5. Programar ejecuciones automáticas
    schedule.every(INTERVALO_MINUTOS).minutes.do(ejecutar_agente)
    print(f"\n[PROGRAMACIÓN] El agente revisará automáticamente la hoja cada {INTERVALO_MINUTOS} minutos.")
    print("Presiona Ctrl + C en cualquier momento para detener el agente.\n")

    # 6. Bucle de ejecución
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n[FIN] Agente detenido por el usuario.")
