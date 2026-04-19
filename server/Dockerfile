FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgl1 \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-rus \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -L -o /usr/share/tesseract-ocr/5/eng.traineddata https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata \
    && curl -L -o /usr/share/tesseract-ocr/5/rus.traineddata https://github.com/tesseract-ocr/tessdata/raw/main/rus.traineddata \
    && mkdir -p /usr/share/tesseract-ocr/5/tessdata \
    && cp /usr/share/tesseract-ocr/5/eng.traineddata /usr/share/tesseract-ocr/5/tessdata/ \
    && cp /usr/share/tesseract-ocr/5/rus.traineddata /usr/share/tesseract-ocr/5/tessdata/

COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt

COPY core /app/core
COPY server/app /app/server/app
COPY server/storage /app/server/storage

# Verify tesseract installation
RUN tesseract --version && tesseract --list-langs

WORKDIR /app/server

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
