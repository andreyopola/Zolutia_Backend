#!/usr/bin/env bash

docker build -t zol-backend:prod --no-cache .
docker logs zolutia_backend >> logs.txt
docker rm -f zolutia_backend
docker run -d --name zolutia_backend \
                --restart always -p 2020:80 \
                --link zolutia_mongodb:mongodb \
                --link zolutia_auth:authentication \
                --link zolutia_search:search \
                --link zolutia_payments:payment \
                --link zolutia_notifications:notification \
                zol-backend:prod
