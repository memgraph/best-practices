FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PG_MAJOR=19
ENV PATH=/usr/lib/postgresql/19/bin:$PATH
ENV PGDATA=/var/lib/postgresql/data

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg \
    && install -d /etc/apt/keyrings \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        | gpg --dearmor -o /etc/apt/keyrings/pgdg.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/pgdg.gpg] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg-snapshot main ${PG_MAJOR}" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && install -d /etc/postgresql-common \
    && echo "create_main_cluster = false" > /etc/postgresql-common/createcluster.conf \
    && apt-get install -y --no-install-recommends -t bookworm-pgdg-snapshot postgresql-${PG_MAJOR} \
    && rm -rf /var/lib/apt/lists/* \
    && install -d -o postgres -g postgres ${PGDATA}

USER postgres
RUN initdb -D ${PGDATA} --auth=trust --username=postgres \
    && echo "listen_addresses='*'" >> ${PGDATA}/postgresql.conf \
    && echo "host all all 0.0.0.0/0 trust" >> ${PGDATA}/pg_hba.conf

EXPOSE 5432
CMD ["postgres", "-D", "/var/lib/postgresql/data"]
