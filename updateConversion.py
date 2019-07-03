import sched, time, datetime, os
from datetime import timedelta
import logger
import requests
import sys
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from bs4 import BeautifulSoup

delay = 3

def openTokenFile(name):
    try:
        f = open(name, 'r')
        return f.read()
    except IOError:
        print ("Falha na leitura do arquivo token: ", name)
        sys.exit()

app_log = logger.defineLogger()
token = openTokenFile('token.txt')
s = sched.scheduler(time.time, time.sleep)

def main():

    pausado = getEstado()
    someone = getSomeoneWatching()
    if (not(pausado) is None) or (not(someone) is None):
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
    else:
        log_error('Someone or paused return none ')    

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
    
    url = 'https://plex.cvnflix.com/transcode/sessions?X-Plex-Token='
    response = tryCatchResponse(url+token)
    if response.status_code==200:
        soup = BeautifulSoup(response.text, 'xml')
        pause = int(soup.TranscodeSession['throttled'])
        return pause
    else:
        log_error('Failed response from: '+url)
        

def getSomeoneWatching():

    url = 'https://plex.cvnflix.com/status/sessions?X-Plex-Token='
    response = tryCatchResponse(url+token)
    if response.status_code==200:
        soup = BeautifulSoup(response.text, features="xml")
        someone = int(soup.MediaContainer['size'])
        return someone
    else:
        log_error('Failed response from: '+ url)

def updateEstado(state):

    url = 'https://plex.cvnflix.com/:/prefs?BackgroundQueueIdlePaused=' 
    return requests.put(url+str(state)+'&X-Plex-Token='+token)


def run_script(sc):

    main()
    s.enter(delay, 1, run_script, (sc,))

if __name__ == "__main__":
    s.enter(delay, 1, run_script, (s,))
    s.run()
