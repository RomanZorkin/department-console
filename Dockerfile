FROM python:3.11-slim

# Установка системных зависимостей для геопространственных библиотек
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка переменных окружения для GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Установка рабочей директории
WORKDIR /app

# Установка uv для управления зависимостями через pip
RUN pip install --no-cache-dir uv

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

# Копирование всего кода приложения
COPY . .

# Установка зависимостей (после копирования для лучшего кеширования)
RUN uv sync --frozen --no-dev

# Открытие порта
EXPOSE 8000

# Переменные окружения по умолчанию
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000
ENV UVICORN_WORKERS=1
ENV UVICORN_RELOAD=false
ENV PATH="/app/.venv/bin:$PATH"

# Запуск приложения
CMD ["uv", "run", "uvicorn", "app.app:asgi_app", "--host", "0.0.0.0", "--port", "8000"]
