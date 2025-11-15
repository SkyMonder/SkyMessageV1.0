FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV FLASK_APP=backend/app.py
ENV PYTHONUNBUFFERED=1
CMD ["gunicorn", "backend.app:app", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:10000"]
