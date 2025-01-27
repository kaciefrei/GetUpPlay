FROM node:alpine

WORKDIR /usr/src/app

COPY . .

RUN npm install -g http-server

EXPOSE 8080

CMD ["http-server", ".", "-p", "8080"]
