# Сборка Windows .exe

PyInstaller не умеет кросс-компиляцию: `.exe` собирается **на Windows-машине**. Spec уже проверен сборкой на Mac (фриз запускается), на Windows тот же spec даёт рабочий `.exe`.

## Требования
- Windows 10/11 (x64)
- Python 3.11 x64 (с python.org), при установке отметить «Add Python to PATH»

## Быстрый путь
В папке проекта дважды кликнуть `build.bat` (или из консоли):

```bat
build.bat
```

Готовый файл: `dist\CaseCutoutTool\CaseCutoutTool.exe`

## Вручную (если нужно)
```bat
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm casecut.spec
```

## Результат
- Папка `dist\CaseCutoutTool\` — переносимая (копируется целиком), внутри `CaseCutoutTool.exe`.
- Первый запуск может быть чуть дольше; антивирус иногда ругается на свежие PyInstaller-сборки (ложное срабатывание).

## Инсталлятор (необязательно)
Для одного установочного файла — [Inno Setup](https://jrsoftware.org/isinfo.php): создать скрипт, указать содержимое `dist\CaseCutoutTool\` и `CaseCutoutTool.exe` как точку входа.

## Иконка (необязательно)
Положить `icon.ico` в корень и в `casecut.spec` в `EXE(...)` добавить `icon='icon.ico'`.
