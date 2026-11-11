FROM python:3.12-slim

WORKDIR /app
COPY common.py io_app.py ./

EXPOSE 8003
CMD ["python", "io_app.py"]
