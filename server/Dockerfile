FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY sentinel ./sentinel
COPY server/requirements.txt server/requirements.txt
COPY server ./server
RUN pip install --no-cache-dir -r server/requirements.txt
ENV PYTHONPATH=/app
ENV SENTINEL_ROOT=/app
EXPOSE 8000
CMD ["python", "-m", "sentinel"]
