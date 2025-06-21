#!/bin/bash
docker build . -t backup-service:latest
docker tag backup-service:latest "dixon961/backup-service:latest"
docker push "dixon961/backup-service:latest"