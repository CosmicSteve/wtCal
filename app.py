import functools
import os
import requests
from ics_parser import ics_parse
from diff import difference
import flask
from flask import Flask, render_template, flash, redirect, url_for, request
from authlib.client import OAuth2Session
import google.oauth2.credentials
import googleapiclient.discovery
import google_auth
from progressbar import ProgressBar
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from forms import AuthForm
import json
import pickle
from pymongo import MongoClient
from threading import Thread
import time

# Initialize App
app = flask.Flask(__name__)
app.register_blueprint(google_auth.app)

# Next 3 lines connect to our database, where users contains all users and their attributes
client = MongoClient("")
db = client.wtcal
users = db.user

# Used to insert a user into the database
def insert_user(ical, uid, calcreds, sync, calendardata):
    new_user = {
        "icalurl": ical,
        "googleuid": uid,
        "calcreds": calcreds,
        "initSync": sync,
        "caldata": calendardata
    }
    users.insert_one(new_user)

app.route('/upload')
def upload():
    return redirect(url_for('index'))
	
@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
   if request.method == 'POST':
      f = request.files['file']
      f.save(f.filename)
      #return 'file uploaded successfully'
      return redirect(url_for('index'))

# The first route reached by accessing the website;
# checks login status and redirects to other routes
@app.route('/', methods=['GET', 'POST'])
def index():
    form = AuthForm()
    # This block runs after the user logs in with Google and submits the form data.
    if form.validate_on_submit():
        if request.method == 'POST':
            f = request.files['file']
            f.save("learn.ics")
        # Grab WTClass calendar URL
        iCalLink = form.icalURL.data
        # Grab Google user information, will be using UID
        user_info = google_auth.get_user_info()
        # Create flow object that generates permissions for calendar access
        scopes = ['https://www.googleapis.com/auth/calendar']
        flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", scopes=scopes, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
        # Grab calendar permission token from form
        flow.fetch_token(code=form.auth.data)
        # Once token is given to the flow, credentials are created
        # for the user allowing us to access their calendar via the 
        # Google API, convert these crendentials to binary for database
        pickled_data = pickle.dumps(flow.credentials)
        # Insert the user into the database
        insert_user(iCalLink, user_info['id'], pickled_data, False, None)
        # Convert the binary credentials back for later use
        restored_data = pickle.loads(pickled_data)
        # Redirect to next page
        return redirect(url_for('index'))
        
    if google_auth.is_logged_in():
        # Get user's Google information
        user_info = google_auth.get_user_info()
        # Tell the user to go to the authorization URL.
        authURL = 'https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=53539138489-5d8chv0kvpesoo7qkrc8h6n8gkjpk4n6.apps.googleusercontent.com&redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar&state=wZGgkhnab3HiagE4p3tKjAPmOkohh2&prompt=consent&access_type=offline'
        
        # User is logged in, check if they exist in the database:
        userID = users.find_one({ "googleuid": str(user_info['id']) })

        # If they exist, redirect to main page
        if userID:
            return flask.redirect(url_for('logged_in'))

        # If not, redirect to form page until valid information is provided
        else:
            return render_template('index.html', url=authURL, form=form)
    
    return render_template('login.html')

@app.route('/loggedin')
def logged_in():
    # This is the main page users will see once they've logged in and provided
    # valid form entries - the script is run from this page
    # This block will run only if the user is logged in with Google.
    if google_auth.is_logged_in():
        # Find the current user and prepare to update their calendar
        # Get user's Google information which contains their google uid
        user_info = google_auth.get_user_info()
        # From that UID, get user from database
        user = users.find_one({ "googleuid": str(user_info['id']) })
        # Retrieve their Google calendar credentials, use pickle to read binary file.
        creds = pickle.loads(user['calcreds'])
        # syncedBefore is boolean to check if user has already synced their calendar before
        syncedBefore = user['initSync']
        # Initialize service to build calendar events
        service = build("calendar", "v3", credentials=creds)
        result = service.calendarList().list().execute()
        # Begin a new thread to process the calendar in the background so that the next webpage can load.
        thread = Thread(target=process_calendar, args=(user,service,result,syncedBefore))
        thread.daemon = True
        # Start the process
        thread.start()
        return render_template('main.html')
    else:
        return redirect(url_for('index'))

def process_calendar(user,service,result,syncedBefore):
    # This function runs in the background and adds events to the user's Google Calendar
    icsURL = user['icalurl']
    currentCalendar = requests.get(icsURL).text
    
    if not syncedBefore:
        # No previous calendar, add every event
        cal = currentCalendar
        icsFileName = "learn.ics"
    else:
        # Previous events added, only add new events
        # by comparing their last synced calendar
        # against a new pull and storing the difference 
        oldCalendar = pickle.loads(user['caldata'])
        cal = difference(oldCalendar, currentCalendar)
        icsFileName = "write.ics"
    # If there are new events to be added:
    if cal.strip():
        # Write events to an ics file
        with open('write.ics', 'w', newline='') as outfile:
            outfile.write(str(cal))
            #print("Wrote to write.ics")
        
        # Parse the ics and build a calendar event object
        # one-by-one for each event, store into an array
        icsName = icsFileName
        calendar_events = ics_parse(icsName)
        calendar_id = result['items'][0]['id']

        # There is at least 1 event to be pushed to the calendar,
        # begin inserting and update progress to progress bar
        pbar = ProgressBar()
        print("Adding",len(calendar_events),"new events to the calendar:\n")
        for event in pbar(calendar_events):
            service.events().insert(calendarId=calendar_id, body=event).execute()

        # All events have been inserted, convert the user's ics file to binary
        # and update their last synced calendar to include these events
        caldata = pickle.dumps(currentCalendar)
        newvalues = { "$set": { "initSync": True, "caldata": caldata} }
        users.update_one(user, newvalues)

        if icsName == 'learn.ics':
            os.remove('learn.ics')


    # No new calendar entries were found, do not do anything
    else:
        print("No new events to add.")
