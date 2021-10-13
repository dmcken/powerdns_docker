#!/bin/bash

DATE_WITH_TIME=`date "+%Y%m%d-%H%M%S"`

echo "Creating timestamp $DATE_WITH_TIME"
docker-compose exec mysql sh -c 'mysqldump --complete-insert --all-databases --user=root --password=$MYSQL_ROOT_PASSWORD' | bzip2 > master-all-databases-$DATE_WITH_TIME.sql.bz2