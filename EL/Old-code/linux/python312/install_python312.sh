# Установка зависимостей
sudo apt update
sudo apt install -y wget build-essential libreadline-dev \
libncursesw5-dev libssl-dev libsqlite3-dev tk-dev \
libgdbm-dev libc6-dev libbz2-dev libffi-dev zlib1g-dev \
liblzma-dev

# Скачивание и установка Python 3.12.7
cd /tmp
#https://www.python.org/ftp/python/3.12.7/Python-3.12.7.tgz
tar -xf Python-3.12.7.tgz
cd Python-3.12.7

# Конфигурация и сборка
./configure --enable-optimizations --prefix=/usr/local --enable-shared
make -j$(nproc)
sudo make altinstall

# Обновление кэша библиотек
sudo ldconfig

# Проверка
python3.12 --version