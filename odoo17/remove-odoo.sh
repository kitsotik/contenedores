sudo rm -R extra-addons/*
sudo chmod 666 /var/run/docker.sock
sudo docker stop $(docker ps -a -q --filter="name=odoo17")
sudo docker rm $(docker ps -a -q --filter="name=odoo17")
#sudo docker rmi $(docker images odoo17*)
sudo docker volume rm $(docker volume ls -q --filter="name=odoo17")
sudo docker network rm $(docker network ls -q --filter="name=odoo17")
docker system prune -a
docker volume prune

