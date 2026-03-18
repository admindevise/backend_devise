# Levantar servicios para tokens (Celery + RabbitMQ + Redis + Django)

## 1) Terminal 1: Infra en Docker (RabbitMQ + Redis)
# Si ya existen contenedores creados:
docker start rabbitmq redis

# Verificar que estén arriba:
docker ps | grep -E "rabbitmq|redis"

# (Opcional) Si NO existen, crearlos:
# docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
# docker run -d --name redis -p 6379:6379 redis:7

## 2) Terminal 2: Celery Worker
# Asegurar variables de entorno (si no están en .env)
export CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
export CELERY_RESULT_BACKEND=redis://localhost:6379/0

celery -A config worker --pool=solo -l info

## 3) Terminal 3: Django API
python manage.py runserver

## 4) (Opcional) Terminal 4: Celery Beat (si usas tareas programadas)
celery -A config beat -l info

## 5) (Opcional) Monitoreo Flower
# pip install flower
celery -A config flower --port=5555