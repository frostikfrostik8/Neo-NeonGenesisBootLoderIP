sudo systemctl stop modbus.service
sleep 1
sudo ./EasyLoader 2 $1 $2
sleep 1
sudo systemctl restart modbus.service
sleep 1