FROM apache/spark:4.2.0-scala2.13-java21-python3-ubuntu@sha256:fc64959c04bd87b0ac686be9aaa9008b69cdb1afc695400528279c8b01f43d89
USER root
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir --target /opt/pm10-deps -r /tmp/requirements.txt
WORKDIR /app
COPY requirements.txt Dockerfile /app/
COPY pm10 /app/pm10
COPY config /app/config
COPY sql /app/sql
COPY tests /app/tests
COPY scripts /app/scripts
ENV PYTHONPATH=/app:/opt/pm10-deps:/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.9-src.zip PYTHONUNBUFFERED=1 SPARK_LOCAL_IP=127.0.0.1
USER 185
ENTRYPOINT ["/app/scripts/entrypoint.sh", "python3", "-m", "pm10"]
