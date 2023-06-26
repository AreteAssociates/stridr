#!/bin/sh

RESOURCES_DIR=/home/oot/STRIDR/scripts/resources

cat $RESOURCES_DIR/config.dump | /usr/bin/sqlite3 config.db
sudo mv config.db /var
