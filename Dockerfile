FROM python:3.11-alpine3.21

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR app/

COPY . .

RUN pip install -r requirements.txt --no-cache-dir && \
    mkdir -p /vol/media && \
    mkdir /vol/static && \
    adduser \
        --disabled-password \
        --no-create-home \
        django-user && \
    chown -R django-user /vol/media /vol/static && \
    chmod 755 /vol/media /vol/static

USER django-user

