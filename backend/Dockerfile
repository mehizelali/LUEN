FROM python:3.13-slim

WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
COPY app ./app
RUN uv pip install --system -e .

ENV DATABASE_URL=postgresql+psycopg://pms:pms@postgres:5432/pms
EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
