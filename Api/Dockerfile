# Imagen base oficial y liviana
FROM python:3.11-slim-bookworm

# Variables de entorno (opcional)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para Playwright
RUN apt-get update && apt-get install -y \
    wget gnupg curl ca-certificates fonts-liberation libasound2 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdbus-1-3 libgdk-pixbuf-2.0-0 libnspr4 \
    libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 xdg-utils \
    libgbm1 libgtk-3-0 libxss1 libxshmfence1 libglu1-mesa libpango-1.0-0 \
    libxinerama1 libxext6 libxfixes3 libx11-6 libxcb1 libxtst6 libnss3-tools \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar los navegadores de Playwright
RUN playwright install --with-deps chromium

# Copiar el código fuente
COPY . .

# Eliminar posibles carpetas __pycache__
RUN find . -type d -name "__pycache__" -exec rm -r {} +

# Exponer el puerto deseado
EXPOSE 55055

# Comando de ejecución para producción
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:55055"]
