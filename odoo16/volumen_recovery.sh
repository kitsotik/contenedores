sudo docker compose down
sudo docker run --rm --mount source=odoo16_odoo-db-data,target=/var/lib/postgresql/data/pgdata -v $(pwd):/backup busybox tar -xzvf /backup/odoo16_odoo-db-data.tar.gz -C /
sudo docker compose up -d

