from google.appengine.ext import db
import simplejson
import datetime

class Setlist(db.Model):
    ''' GAE datastore representation of a setlist '''
    artist = db.StringProperty(required=True)
    day = db.DateProperty(required=True)
    venue = db.StringProperty(required=True)
    songs = db.TextProperty()
    email = db.StringProperty(required=True)
    notes = db.TextProperty()

class SetlistEncoder(simplejson.JSONEncoder):
    ''' A custom JSON encoder for Setlist objects '''
    def default(self, clazz):
        if not isinstance (clazz, Setlist):
            return default(clazz)
        return { 'artist': clazz.artist, 'day': clazz.day.strftime("%Y-%m-%d"), 'venue': clazz.venue, 'songs': clazz.songs, 'email': clazz.email, 'notes': clazz.notes }

class SetlistDecoder(simplejson.JSONDecoder):
    ''' A custom JSON decoder for Setlist objects '''
    def decode(self, jsonString):
        obj = simplejson.loads(jsonString);
        (year, month, day) = obj["day"].split('-')
        setlist = Setlist(artist=obj["artist"], 
                          day=datetime.date(int(year), int(month), int(day)), 
                          venue=obj["venue"], 
                          email=obj["email"]);
        if ("songs" in obj):
            setlist.songs = obj["songs"]
        if ("notes" in obj):
            setlist.notes = obj["notes"]
        return setlist