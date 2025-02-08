
FROM python:3.13

WORKDIR /opt/amnezia_api

ENV SECRET_URL_STRING="dev"
# RUN python3 -m venv .venv
# RUN . .venv/bin/activate
RUN pip install --no-cache-dir flask
RUN pip install --no-cache-dir docker
RUN pip install --no-cache-dir gunicorn

COPY ./amnezia_api ./amnezia_api
COPY wsgi.py .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:42674", "wsgi:app"]
# CMD ["ls"]

