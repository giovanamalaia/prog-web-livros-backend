FROM python:3.9

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# pasta /app dentro do contêiner
WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

# docker vai rodar automaticamente quando ligar o projeto
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]