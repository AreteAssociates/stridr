#!/bin/sh

RESOURCES_DIR=/home/oot/STRIDR/scripts/resources

/usr/bin/sqlite3 /var/config.db > $RESOURCES_DIR/config.dump << EOF
.dump
EOF
