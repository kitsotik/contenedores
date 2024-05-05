
sudo apt-get install ufw
sudo ufw enable
sudo ufw status

sudo ufw allow http
sudo ufw allow https

sudo ufw allow 22/tcp
sudo ufw allow 8069/tcp
sudo ufw allow 8070/tcp
sudo ufw allow 587/tcp