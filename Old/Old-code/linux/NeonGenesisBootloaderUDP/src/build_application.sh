sudo rm -r dist/
sudo rm -r build/
sudo rm -r EasyLoader.spec
pyinstaller --additional-hooks-dir=. --onefile EasyLoader.py 