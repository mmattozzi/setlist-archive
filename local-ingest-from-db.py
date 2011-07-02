# 
# This is a script that reads from a local mysql database and imports data into GAE.
# This version of the script only imports the data into the local GAE test instance. 
# It can be modified by setting the EMAIL, API_KEY, and HOST constants.
#
# My legacy db table had the schema:
#    CREATE TABLE `setlist` (
#        `id` int(11) NOT NULL AUTO_INCREMENT,
#        `band` mediumtext,
#        `day` date DEFAULT NULL,
#        `venue` mediumtext,
#        `songs` mediumtext,
#        `poster` int(11) NOT NULL DEFAULT '0',
#        `notes` mediumtext,
#        PRIMARY KEY (`id`)
#    )
#

import MySQLdb
import json
import httplib, urllib
import json
import datetime
import sys
import time
import base64

# Connection to setlist archive site
EMAIL = "test@example.com"
API_KEY = "cnVxQWkOPa5wlsLG"
HOST = "localhost:8080"

# Connection to database
DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "mike"

errors = 0
ids_with_errors = list()

auth_string = "Basic " + base64.b64encode(":".join((EMAIL, API_KEY)))
headers = { "Content-Type": "application/json", "Authorization": auth_string }

conn = MySQLdb.connect(host=DB_HOST, user=DB_USER, db=DB_NAME)
cursor = conn.cursor();
cursor.execute("SELECT band, day, venue, songs, notes, id FROM setlist")
while (1):
    row = cursor.fetchone()
    if row == None:
        break
    setlist = dict()
    setlist["artist"] = row[0]
    setlist["day"] = row[1].strftime("%Y-%m-%d")
    setlist["venue"] = row[2]
    if row[3]:
        songs = row[3]
        songs = songs.replace("\\\'", "'")
        songs = songs.replace('\\\"', '"')
        setlist["songs"] = songs
    if row[4]:
        notes = row[4]
        notes = notes.replace("\\\'", "'")
        notes = notes.replace('\\\"', '"')
        setlist["notes"] = notes
    setlist["email"] = EMAIL
    print row[5]
    try:
        print json.dumps(setlist)
        httpconn = httplib.HTTPConnection(HOST)
        httpconn.request("POST", "/post?convertNewLines=false", json.dumps(setlist), headers)
        res = httpconn.getresponse()
        print res.status
        print res.read()
        # Some simple rate limiting
        time.sleep(1)
    except:
        print "Unexpected error:", sys.exc_info()[0]
        errors += 1
        ids_with_errors.append(row[5]);

cursor.close()
conn.close()

print "Errors = ", errors
for id in ids_with_errors:
    print id
    