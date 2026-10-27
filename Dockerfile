# 1. Partir de la imagen base oficial de Python 3.12 (Linux ligero)
FROM python:3.12-slim

# 2. Forzar a Python a emitir la salida de print() en tiempo real sin almacenarla en búfer
ENV PYTHONUNBUFFERED=1

# 3. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 4. Copiar únicamente requirements.txt primero para aprovechar el caché de capas de Docker
COPY requirements.txt .

# 5. Instalar dependencias sin guardar caché temporal para mantener la imagen ligera
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copiar el script principal del agente a la carpeta de trabajo
COPY agente_soporte.py .

# 7. Definir el comando ejecutable principal en formato lista JSON
ENTRYPOINT ["python", "agente_soporte.py"]
