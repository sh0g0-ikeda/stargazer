FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8080
ENV TARGET_PROJECT_ID=demo-gcp-project

WORKDIR /app

RUN addgroup --system castorops && adduser --system --ingroup castorops castorops

COPY app ./app
COPY scripts ./scripts
COPY README.md ./README.md

USER castorops

EXPOSE 8080

CMD ["python", "scripts/serve_demo.py"]
