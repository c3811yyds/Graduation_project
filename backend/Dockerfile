FROM python:3.13-slim

WORKDIR /app

# Install backend dependencies first for better layer caching
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir gunicorn -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy backend source and third-party sensitive lexicon into image
COPY backend /app/backend
COPY third_party/Sensitive-lexicon /app/third_party/Sensitive-lexicon

WORKDIR /app/backend

# Let backend load lexicon from bundled submodule path
ENV SENSITIVE_LEXICON_DIR=/app/third_party/Sensitive-lexicon/Vocabulary

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
