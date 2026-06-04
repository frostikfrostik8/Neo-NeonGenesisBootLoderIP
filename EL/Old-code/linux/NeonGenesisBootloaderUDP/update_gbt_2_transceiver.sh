sudo systemctl stop modbus.service
sleep 1
sudo ./EasyLoader 18 $1 $2
sleep 1
sudo systemctl restart modbus.service
sleep 1