FROM postgres:17
# init script baked into the image: runs on first boot of a fresh volume,
# with deterministic permissions (no host bind-mount involved)
COPY init-airflow-db.sh /docker-entrypoint-initdb.d/10-airflow-db.sh
RUN chmod 0755 /docker-entrypoint-initdb.d/10-airflow-db.sh
