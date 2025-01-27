FROM python:3.9-alpine

WORKDIR /usr/src/app

COPY . .

EXPOSE 8080

CMD ["python3", "-m", "http.server", "8000", "--directory", "/usr/src/app"]
