sudo systemctl stop astra-monitor.service
sleep 1
sudo ./EasyLoader 705 $1 $2
sleep 1
sudo systemctl restart astra-monitor.service
sleep 1