sudo docker network create -d macvlan \
  --subnet=192.168.0.0/24 \
  --ip-range=192.168.0.2/10 \
  --gateway=192.168.0.1 \
  -o parent=ens32 \
  mcvlan192
