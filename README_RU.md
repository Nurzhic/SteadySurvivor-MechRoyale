# SteadySurvivor — подготовка к отправке на Mech Royale

**Статус:** бот прошёл официальный `check/check.py` на 300 реальных наблюдениях (на локальном окружении при подготовке этого архива). Это проверка протокола, а не оценка побед или места. **Docker-проверка ещё не проводилась** — её нужно выполнить на вашем Mac.

## 1. Распаковка

В Terminal перейдите в папку, где находятся оба архива. Например, если они в Downloads:

```bash
cd ~/Downloads
tar -xzf mechfight-kit.tar.gz
unzip SteadySurvivor_Submission_v1.zip -d SteadySurvivor_Submission_v1
cd SteadySurvivor_Submission_v1
```

Если `mechfight-kit` уже распакован, пропустите команду `tar`.

## 2. Официальная локальная проверка

```bash
bash test_official.sh
```

По умолчанию скрипт ищет `../mechfight-kit`. Если каталог находится в другом месте, передайте путь первым аргументом:

```bash
bash test_official.sh /полный/путь/к/mechfight-kit
```

Ожидаемый итог: `PASS`.

## 3. Docker-проверка (важно)

Поставьте Docker Desktop, запустите его и дождитесь запуска Docker Engine. На MacBook с Apple Silicon используется эмуляция архитектуры `linux/amd64`:

```bash
bash test_docker.sh
```

Этот скрипт собирает Docker-образ и запускает тот же изоляционный режим, что использует скорер: `--network none`, 1 CPU, 512 MB RAM, файловая система только для чтения, пользователь 65534. Запускайте из той же папки, где лежит `Dockerfile`.

**Важно:** на эмулированном `linux/amd64` на Mac времена отклика могут отличаться от нативного сервера, особенно на холодном запуске. При проблемах покажите полный вывод ошибки.

## 4. GitHub (только файлы этого архива)

Создайте **public** репозиторий, например `SteadySurvivor-MechRoyale`, в своём GitHub. Не добавляйте туда `mechfight-kit`, `arena/` и `check/`: сервер монтирует карту отдельно. В папке проекта:

```bash
git init
git add .
git commit -m "Initial SteadySurvivor Mech Royale bot"
git branch -M main
git remote add origin https://github.com/ВАШ_ЛОГИН/SteadySurvivor-MechRoyale.git
git push -u origin main
```

Замените `ВАШ_ЛОГИН` на свой GitHub username. Если GitHub просит аутентификацию — используйте `gh auth login` (при установленном GitHub CLI), SSH-ключ или token согласно подсказкам GitHub.

В корне репозитория должны лежать **`Dockerfile` и `example_bot.py`**. Отправляйте организаторам **URL публичного репозитория** на странице трека Mech Royale. После отправки ожидайте отчёт о 48 practice matches (если сборка и проверки прошли).

## 5. Что прислать мне дальше

- Полный вывод `bash test_docker.sh`, особенно последние строки с `PASS` или ошибкой;
- После первой отправки — место/score и замечания из leaderboard, чтобы улучшать стратегию на реальных результатах.

**Никаких API-ключей в репозитории нет.** Бот использует только Python standard library.
