FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Install exact runtime deps directly (do NOT use requirements.txt: SnapDeploy's
# build scanner injects stdlib "zoneinfo" and dev-only "pytest", which break pip).
RUN pip install --no-cache-dir \
    "yfinance>=0.2.40,<1" \
    "pandas>=2.0,<3" \
    "twilio>=9.0,<10" \
    "flask>=3.0,<4" \
    "gunicorn>=22.0,<24" \
    "python-dotenv>=1.0,<2"

COPY . .

EXPOSE 5000

CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 120 app:app
