FROM python:3.12-slim
WORKDIR /srv/app
# Repository-root entrypoint. The flat archive keeps its existing website Dockerfile.
ARG INSTALL_AI=false
ARG BGE_MODEL=BAAI/bge-small-zh-v1.5
ENV HF_HOME=/srv/models
COPY ["MuscleCore分析資料/website/requirements-cloud.txt", "MuscleCore分析資料/website/requirements-cloud-ai.txt", "./"]
RUN if [ "$INSTALL_AI" = "true" ]; then pip install --no-cache-dir -r requirements-cloud-ai.txt; \
    else pip install --no-cache-dir -r requirements-cloud.txt; fi \
    && useradd --system --uid 10001 --create-home appuser
RUN if [ "$INSTALL_AI" = "true" ]; then \
        python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('$BGE_MODEL')" \
        && chmod -R a+rX "$HF_HOME"; \
    fi
COPY ["MuscleCore分析資料/website/app", "./app"]
COPY ["VibeCart_AI/services/cart_service.py", "VibeCart_AI/services/sku_cart_service.py", "VibeCart_AI/services/review_service.py", "./VibeCart_AI/services/"]
COPY ["MuscleCore分析資料/website/cloud_runtime.py", "./"]
USER appuser
ENV PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 60 'cloud_runtime:create_cloud_app()'"]
