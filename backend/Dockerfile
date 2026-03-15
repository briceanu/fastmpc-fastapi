FROM python:3.13-slim

# Install uv
RUN pip install uv --no-cache-dir

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (skip project install — app code is copied separately)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY app/ ./app/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" , "--reload"]
