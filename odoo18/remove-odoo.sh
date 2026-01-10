#!/bin/bash
set -e

PROJECT=odoo18

echo "🛑 Bajando proyecto $PROJECT..."
docker compose -p $PROJECT down --remove-orphans

echo "🗑 Borrando volúmenes del proyecto $PROJECT..."
docker compose -p $PROJECT down -v

echo "🧹 Limpieza de volúmenes anónimos..."
docker volume prune -f

echo "🧹 Limpieza de imágenes colgantes..."
docker system prune -a

echo "✅ Odoo eliminado (sin tocar Portainer ni Traefik)"


