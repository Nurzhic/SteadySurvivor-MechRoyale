FROM python:3.13-slim
WORKDIR /bot
COPY example_bot.py /bot/example_bot.py
USER 65534:65534
ENTRYPOINT ["python3", "-u", "/bot/example_bot.py"]
