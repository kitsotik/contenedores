sudo docker run --rm --mount source=odoo16_odoo-db-data,target=/var/lib/postgresql/data/pgdata -v $(pwd):/backup busybox tar -czvf /backup/odoo16_odoo-db-data.tar.gz /var/lib/postgresql/data/pgdata

