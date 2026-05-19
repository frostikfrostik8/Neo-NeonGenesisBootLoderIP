sudo systemctl stop modbus.service
sleep 1
sudo ./EasyLoader 1 8007 $1 192.168.1.$2
sleep 1
sudo systemctl restart modbus.service
sleep 1