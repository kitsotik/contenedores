sudo chmod 666 /var/run/docker.sock
sudo docker stop $(docker ps -a -q --filter="name=odoo")
sudo docker rm $(docker ps -a -q --filter="name=odoo")
sudo docker volume rm $(docker volume ls -q --filter="name=odoo")
docker system prune -f
docker volume prune -f

