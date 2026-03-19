FROM python:3.12-slim
COPY agent.py /app/agent.py
WORKDIR /app
ENV HTTP_PROXY=http://10.0.2.2:9080
ENV HTTPS_PROXY=http://10.0.2.2:9080
CMD ["python3", "/app/agent.py"]
