FROM python:3.12-slim
WORKDIR /srv/app
COPY requirements-cloud.txt ./
RUN pip install --no-cache-dir -r requirements-cloud.txt \
    && useradd --system --uid 10001 --create-home appuser
COPY app ./app
COPY VibeCart_AI/services ./VibeCart_AI/services
COPY cloud_runtime.py ./
USER appuser
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 60 'cloud_runtime:create_cloud_app()'"]
