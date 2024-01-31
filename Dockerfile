FROM python:3.7.17

WORKDIR /opt/async-download-service
COPY requirements.txt /opt/async-download-service
COPY . .
RUN pip3 install -r requirements.txt
CMD ["python3", "server.py"]
