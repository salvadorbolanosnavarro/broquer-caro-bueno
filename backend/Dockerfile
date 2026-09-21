FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /app/backend
COPY shared /app/shared
WORKDIR /app/backend
RUN useradd --create-home broquer
USER broquer
EXPOSE 8000
CMD ["python","-m","uvicorn","broquer.main:app","--host","0.0.0.0","--port","8000"]
