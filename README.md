# cloudphoto
 
## Сборка приложения

* Необходимо установить PyInstaller для компиляции:

pip install pyinstaller

* Перейдите в каталог репозитория через Терминал:

cd <путь/к/cloudphoto>

* Запустите компиляцию с помощью следующей команды:

pyinstaller --onefile cloudphoto.py

* Скомпилированный файл появится в папке **dist**. Запустите приложение оттуда:

./dist/cloudphoto init
