#!/bin/bash

DATE_WITH_TIME=`date "+%Y%m%d-%H%M%S"`

echo "Creating timestamp $DATE_WITH_TIME"
docker-compose exec mysql sh -c 'mysqldump --all-databases --user=root --password=$MYSQL_ROOT_PASSWORD' > master-all-databases-$DATE_WITH_TIME.sql