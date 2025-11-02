FROM python:3.12-slim
WORKDIR /app
COPY arbitrage_bot.py arbitrage_config.sample.yaml ./
RUN pip install aiohttp pyyaml
CMD ["python", "arbitrage_bot.py", "--config", "arbitrage_config.sample.yaml"]
