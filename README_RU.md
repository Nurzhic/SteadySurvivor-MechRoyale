# SteadySurvivor v3 — новая экспериментальная версия

Трек Builders Buildathon / Mech Royale. Основа — **v1 (score 2.27)**, потому что **v2 дала 2.00**. У v2 были слишком большие изменения одновременно: A*-навигация, непрерывное движение к целевой точке, новая политика буста и сканирования. Нельзя уверенно сказать, какой фактор ухудшил итог без отдельных экспериментов.

В v3 мы вернули прямую навигацию и пороги перемещения из v1. Дополнительно исправили выбор улучшений по настоящим ID, добавили реагирование на скрытый урон и опасность лазерной зарядки при бегстве. Это **гипотезы**, а не доказанное улучшение.

## Проверка на Mac

Распаковать ZIP в `~/Downloads`, рядом должна находиться папка `mechfight-kit`.

```bash
cd ~/Downloads/SteadySurvivor_Submission_v3
python3 smoke_test.py
python3 test_strategy.py
bash test_official.sh
bash test_docker.sh
```

## Обновление текущего GitHub-репозитория

```bash
cd ~/Downloads/SteadySurvivor_Submission_v1
# Создать тег для текущей версии, если хочется
cp ../SteadySurvivor_Submission_v3/example_bot.py ./example_bot.py
cp ../SteadySurvivor_Submission_v3/test_strategy.py ./test_strategy.py
cp ../SteadySurvivor_Submission_v3/README.md ./README.md
cp ../SteadySurvivor_Submission_v3/README_RU.md ./README_RU.md
bash test_official.sh
bash test_docker.sh
git add example_bot.py test_strategy.py README.md README_RU.md
git commit -m 'Experiment with stealth and kiting v3'
git push origin main
```

Отправить репозиторий повторно через Buildathon. Лучший предыдущий результат сохраняется автоматически; финальную версию можно выбрать перед закрытием.

**Важно:** check.py проверяет формат и скорость ответа, но не способность победить в матче. Рост score станет известен только после очередной отправки.
