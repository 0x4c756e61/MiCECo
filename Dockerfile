FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY miceco.py ./

CMD [ "python3", "./miceco.py" ]
