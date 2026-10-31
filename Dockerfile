FROM python:3.12-slim

WORKDIR /app

COPY marketspace_backend.py .
COPY marketspace.html .

EXPOSE 8080

CMD ["python", "marketspace_backend.py"]
