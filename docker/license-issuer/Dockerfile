FROM python:3.11-slim

WORKDIR /app
COPY tools/license_issuer.py /app/license_issuer.py

# No dependencies beyond stdlib
ENTRYPOINT ["python", "/app/license_issuer.py"]
