FROM python:3.13

ARG APP_VERSION = "0.0.9"

RUN mkdir /opt/amnezia-api/
WORKDIR /opt/amnezia-api/

RUN pip install ../dist/amnezia_api-${APP_VERSION}-py2.py3-none-any.whl
RUN pip install gunicorn

COPY /opt/amnezia-api/secret-url-string.txt .
COPY /opt/amnezia-api/templates/ .

CMD ["gunicorn", "-w", "4", "'amnezia_api:create_app()'"]
