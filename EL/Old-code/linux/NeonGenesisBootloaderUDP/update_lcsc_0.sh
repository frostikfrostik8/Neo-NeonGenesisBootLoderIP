sudo systemctl stop astra-monitor.service
sleep 1
sudo ./EasyLoader F0 $1 $2
sleep 1
sudo systemctl restart astra-monitor.service
sleep 1