FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home commerce
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
USER commerce
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--no-access-log"]
