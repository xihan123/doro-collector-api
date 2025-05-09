# 修改后的 Dockerfile
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN mkdir -p failed for path /nonexistent/.config/matplotlib

RUN apt-get update && apt-get install -y libpq5 && \
rm -rf /var/lib/apt/lists/*

WORKDIR /app

#ARG UID=10001
#RUN adduser \
#    --disabled-password \
#    --gecos "" \
#    --home "/nonexistent" \
#    --shell "/sbin/nologin" \
#    --no-create-home \
#    --uid "${UID}" \
#    appuser

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install --upgrade pip && \
    pip install "psycopg[binary,pool]" && \
    pip install -r requirements.txt

#USER appuser

COPY . .

EXPOSE 8000

# 使用 JSON 格式的 CMD 指令
CMD ["python", "main.py"]
