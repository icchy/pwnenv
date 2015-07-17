# pwnenv
auto container build tool for pwn

## Requirements
```
apt-get install docker.io
sudo usermod -G <user> docker
git clone https://github.com/icchyr/pwnenv
cd pwnenv
echo "export PATH=$PATH:`pwd`" >> ~/.bashrc
```

## Start daemon
```
pwnenv.py start <binary_path> [-f flag_path] [-p port] [-l libc_path] [-n service_name]
```
## Stop daemon
```
pwnenv.py stop <servine_name>
```

## Check daemon
```
pwnenv.py status <service_name>
```
