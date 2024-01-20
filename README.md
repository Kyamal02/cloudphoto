# cloudphoto
 
## Сборка

* Установите PyInstaller с помощью команды:
```
pip install pyinstaller
```
* Откройте терминал и перейдите в директорию репозитория CloudPhoto:
```
cd <path/to/cloudphoto>
```
* Выполните команду для сборки исполняемого файла:
```
pyinstaller --onefile cloudphoto.py
```
* Исполняемый файл будет создан в директории "./dist". Вы можете запускать скрипт оттуда:
```
./dist/cloudphoto init
```
* Для удобства запуска из любой точки системы, добавьте исполняемый файл в переменную PATH. Переместите файл в "/usr/local/bin":
```
mv ./dist/cloudphoto /usr/local/bin/cloudphoto
```
