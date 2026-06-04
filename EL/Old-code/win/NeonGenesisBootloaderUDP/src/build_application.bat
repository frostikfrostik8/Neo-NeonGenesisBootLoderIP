rmdir /s /q .\build
rmdir /s /q .\dist
del EasyLoader.spec
pyinstaller --additional-hooks-dir=. --onefile EasyLoader.py