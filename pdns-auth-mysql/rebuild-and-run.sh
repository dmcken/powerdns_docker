#!/bin/bash

docker build . -t dmcken/pdns-auth-mysql:v0.0.1

docker run --env-file ../.env -it dmcken/pdns-auth-mysql:v0.0.1
