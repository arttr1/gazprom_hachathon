# FROM ollama/ollama:latest

# WORKDIR /app

# # System dependencies for OCR/PDF processing + Python runtime.
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     python3 \
#     python3-pip \
#     poppler-utils \
#     tesseract-ocr \
#     tesseract-ocr-rus \
#     tesseract-ocr-eng \
#     libgl1 \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt /app/requirements.txt
# RUN pip3 install --no-cache-dir --break-system-packages -r /app/requirements.txt

# Preload models into image layer so container starts offline-ready.
# RUN bash -lc " \
#     ollama serve & \
#     OLLAMA_PID=\$!; \
#     sleep 5; \
#     ollama pull qwen2.5:3b-instruct; \
#     ollama pull llava:7b; \
#     kill \${OLLAMA_PID}; \
#     wait \${OLLAMA_PID} || true \
# "

# COPY . /app

# EXPOSE 11434

# # By default container runs Ollama API server with preloaded models.
# CMD ["ollama", "serve"]

FROM ollama/ollama:latest

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /app/requirements.txt

COPY . /app

EXPOSE 11434

CMD ["serve"]