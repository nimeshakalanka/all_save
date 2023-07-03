FROM python:3

WORKDIR /app

COPY req.txt /app/

RUN pip3 install -r req.txt

COPY . /app

CMD python bot.py