# Nota: Este Dockerfile será movido a la carpeta deployment
# Todas las rutas COPY deben usar '../' para acceder al proyecto

FROM python:3.9-slim

WORKDIR /app

# Copiar requirements primero para cachear
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto
COPY ../ .

# Puerto expuesto
EXPOSE 8000

# Comando para producción
CMD ["gunicorn", "-c", "deployment/gunicorn_conf.py", "main:app"]

