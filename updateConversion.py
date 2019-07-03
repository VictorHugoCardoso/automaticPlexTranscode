import sched, time, datetime, os
from datetime import timedelta
import logging
from logging.handlers import RotatingFileHandler
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from bs4 import BeautifulSoup

delay = 3
token = open("token.txt").read()

log_formatter = logging.Formatter('%(levelname)s - %(asctime)s - %(message)s')
        
my_handler = RotatingFileHandler(filename='loggin.log', mode='a', maxBytes=5*1024*1024, 
                                backupCount=2, encoding=None)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)

app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)
app_log.addHandler(my_handler)

s = sched.scheduler(time.time, time.sleep)

def main():

    pausado = getEstado()
    someone = getSomeoneWatching()
    statuscode = 200

    if someone == 0 and pausado == 1:
        retorno = updateEstado(0)
        statuscode = retorno.status_code
        text = 'STARTED'
        mode = 1
    else:
        if someone == 0 and pausado == 0:    
            text = 'IDLE'
            mode = 0
        else:
            if someone > 0 and pausado == 0:
                retorno = updateEstado(1)
                statuscode = retorno.status_code
                text = 'STOPPED'
                mode = 1
            else:
                text = 'IDLE'
                mode = 0
    
    if statuscode == 200:
        log(mode, pausado, text)
    else:
        log_error('Erro ao fazer o put: '+str(statuscode))

def log_error(e):
    app_log.error(e)

def log(mode, pausado, text):

    p = 'paused' if pausado == 1 else 'unpaused'
    string = '['+ p +'] - '+ text
    if mode:
        app_log.warning(string)
    else:
        app_log.info(string)

def requests_retry_session(
    retries=7,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def tryCatchResponse(url):
    try:
        response = requests_retry_session().get(url)
    except Exception as x:
        log_error('It failed :('+ str(x.__class__.__name__))
        return None
    else:
        return response

def getEstado():
    
    response = tryCatchResponse('https://plex.cvnflix.com/transcode/sessions?X-Plex-Token='+token)
    if response.status_code==200:
        soup = BeautifulSoup(response.text, 'xml')
        pause = int(soup.TranscodeSession['throttled'])
        return pause
    else:
        log_error('Failed response')
        

def getSomeoneWatching():

    response = tryCatchResponse('https://plex.cvnflix.com/status/sessions?X-Plex-Token='+token)
    if response.status_code==200:
        soup = BeautifulSoup(response.text, features="xml")
        someone = int(soup.MediaContainer['size'])
        return someone
    else:
        log_error('Failed response')

def updateEstado(state):

    if state:
        response = requests.put('https://plex.cvnflix.com/:/prefs?BackgroundQueueIdlePaused=1&X-Plex-Token='+token)
    else:
        response = requests.put('https://plex.cvnflix.com/:/prefs?BackgroundQueueIdlePaused=0&X-Plex-Token='+token)
    return response

def run_script(sc):

    main()
    s.enter(delay, 1, run_script, (sc,))

s.enter(delay, 1, run_script, (s,))
s.run()