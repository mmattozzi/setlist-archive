from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.dist import use_library
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import users

from Setlist import Setlist
from Setlist import SetlistDecoder
from Setlist import SetlistEncoder

import os
import logging
import datetime
import simplejson
import string
import random
import base64
import re

class AppUser(db.Model):
    ''' GAE datastore representation of our app's user '''
    user_email = db.StringProperty(required=True)
    api_key = db.StringProperty(required=True)
    superuser = db.BooleanProperty(required=True, default=False)
    banned = db.BooleanProperty(default=False)

# Make a setlist decoder available for later use
setlistDecoder = SetlistDecoder()

class MainPage(webapp.RequestHandler):
    ''' Render the main index page '''
    def get(self):
        user = users.get_current_user()
        if user:
            user_url = users.create_logout_url(self.request.uri)
            matching_users = db.GqlQuery("SELECT * FROM AppUser WHERE user_email = :1", user.email())
            if matching_users.count() == 0:
                logging.info("New user: " + user.email())
                api_key = "".join(random.sample(string.letters + string.digits, 16))
                logging.info("Generated api key: " + api_key)
                app_user = AppUser(user_email=user.email(), api_key=api_key, superuser=False)
                app_user.put();
            else:
                app_user = matching_users.get()
                api_key = app_user.api_key
                logging.info("API Key = " + api_key)
        else:
            user_url = users.create_login_url(self.request.uri)
        
        self.response.headers['Content-Type'] = 'text/html'
        template_values = { 
            "user_url": user_url, 
            "user": user, 
            "date": datetime.date.today().strftime("%Y-%m-%d")
        }
        if user:
            template_values["auth_header"] = "Basic " + base64.b64encode(":".join((user.email(), api_key)))
            template_values["api_key"] = api_key
        
        self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'index.html'), template_values))

class SetlistBody(webapp.RequestHandler):
    ''' Render set lists '''
    def get(self):
        auth_header = self.request.headers.get('Authorization')
        app_user = None
        if auth_header is not None:
            app_user = basic_auth(self.request, self.response)
        sort = self.request.get("sort")
        if not sort or sort == "date":
            setlists = db.GqlQuery("SELECT * FROM Setlist ORDER BY day DESC")
        elif sort == "artist":
            setlists = db.GqlQuery("SElECT * FROM Setlist ORDER BY artist")
        elif sort == "venue":
            setlists = db.GqlQuery("SELECT * FROM Setlist ORDER BY venue")
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'setlist.html'), {"setlists": setlists, "app_user": app_user}))
        
class PostSet(webapp.RequestHandler):
    ''' Given a setlist POSTed as JSON, add it to the data store. '''
    def post(self):
        app_user = basic_auth(self.request, self.response)
        if app_user:
            convertNewLines = True
            if "convertNewLines" in self.request.str_GET:
                param_str = self.request.str_GET["convertNewLines"]
                if param_str.lower() == "false":
                    convertNewLines = False
            
            setlist = setlistDecoder.decode(self.request.body)
            logging.info(setlist.songs)
            if setlist.songs and convertNewLines is True:
                setlist.songs = re.sub("(\r\n)|(\n)", "<br/>", setlist.songs)
            if setlist.notes and convertNewLines is True:
                setlist.notes = re.sub("(\r\n)|(\n)", "<br/>", setlist.notes)
            setlist.email = app_user.user_email
            key = setlist.put()
            self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write('{ "result": "stored", "id": "%s" }' % (key.id()))

class DeleteSet(webapp.RequestHandler):
    ''' Given the id of a setlist, delete it. '''
    def post(self):
        app_user = basic_auth(self.request, self.response, True)
        delete_id = self.request.get("id")
        if delete_id and app_user:
            setlist_k = db.Key.from_path("Setlist", int(delete_id))
            setlist = db.get(setlist_k)
            if setlist:
                setlist.delete()
                self.response.set_status(200)
            else:
                self.response.set_status(404)
                self.response.out.write("Can't find key " + delete_id)

class Dump(webapp.RequestHandler):
    ''' Dump out all setlists in a JSON array '''
    def get(self):
        if basic_auth(self.request, self.response, True):
            query = db.GqlQuery("SELECT * FROM Setlist ORDER BY day desc")
            objs = list()
            for result in query:
                objs.append(result)
            self.response.out.write(simplejson.dumps(objs, cls=SetlistEncoder))
        
class Clear(webapp.RequestHandler):
    ''' Remove all setlists '''
    def post(self):
        if basic_auth(self.request, self.response, True):
            query = db.GqlQuery("SELECT * FROM Setlist")
            for result in query:
                result.delete()
            self.response.out.write("Gone")

application = webapp.WSGIApplication([
    ('/', MainPage), 
    ('/sets', SetlistBody),
    ('/post', PostSet), 
    ('/dump', Dump), 
    ('/delete', DeleteSet),
    ('/clear', Clear)], debug=True)

def basic_auth(request, response, superuser_req=False):
    ''' Given a request and a response, verify the API key is correctly passed via http basic auth. '''
    auth_header = request.headers.get('Authorization')
    if auth_header is None:
        response.set_status(401)
        response.out.write("Authorization required.")
        return None
    user_info = base64.b64decode(auth_header[6:])
    username, password = user_info.split(':')
    matched_users = db.GqlQuery("SELECT * FROM AppUser WHERE user_email = :1 AND api_key = :2", username, password)
    if matched_users.count() > 0:
        matched_user = matched_users.get()
        if matched_user.banned is True:
            response.set_status(401)
            response.out.write("User banned.")
            return None
        if superuser_req and matched_user.superuser is not True:
            response.set_status(401)
            response.out.write("Superuser required.")
            return None
        else:
            return matched_user
    else:
        response.set_status(401)
        response.out.write("Authorization required.")
        return None

def main():
    logging.getLogger().setLevel(logging.DEBUG)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
