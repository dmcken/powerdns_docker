#!/bin/bash

envtpl --keep-template 90-extra.cnf.tpl

docker-compose up -d db
