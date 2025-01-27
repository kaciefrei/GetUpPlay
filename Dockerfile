FROM alpine:3.15.4

RUN apk add thttpd

RUN adduser -D static
USER static
WORKDIR /home/static

COPY . .

CMD ["thttpd", "-D", "-h", "0.0.0.0", "-p", "3000", "-d", "/home/static", "-u", "static", "-l", "-", "-M", "60"]
