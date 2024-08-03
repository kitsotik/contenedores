sudo chmod 666 /var/run/docker.sock
sudo docker stop $(docker ps -a -q --filter="name=odoo16")
sudo docker rm $(docker ps -a -q --filter="name=odoo16")
sudo docker volume rm $(docker volume ls -q --filter="name=odoo16")
docker system prune -a
docker volume prune

