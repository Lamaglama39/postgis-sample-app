#!/bin/bash

# Lambda zip
zip -r db_handler.zip db_handler.py
zip -r rds_setup.zip rds_setup.py

# requirements.txtを作成
echo 'psycopg2-binary' > requirements.txt

# Dockerイメージを使ってインストール
docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.12:latest" /bin/sh -c "pip install --platform manylinux2014_x86_64 --target . --python-version 3.12 --only-binary=:all: -r requirements.txt -t python/; exit"

# zipファイルを作成
zip -r psycopg2-3.12.zip python/
