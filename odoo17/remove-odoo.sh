sudo chmod 666 /var/run/docker.sock
sudo docker stop $(docker ps -a -q --filter="name=odoo")
sudo docker rm $(docker ps -a -q --filter="name=odoo")
#sudo docker rmi $(docker images odoo*)
sudo docker volume rm $(docker volume ls -q --filter="name=odoo")
sudo docker network rm $(docker network ls -q --filter="name=odoo")
docker system prune -a
docker volume prune

