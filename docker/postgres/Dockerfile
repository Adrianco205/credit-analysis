FROM postgres:16

# Inicializacion de esquema en primer arranque del volumen
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
