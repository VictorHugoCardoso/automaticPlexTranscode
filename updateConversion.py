import sched
import time
import datetime
import os
import logger
import requests
import sys

from datetime import timedelta
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from bs4 import BeautifulSoup

DELAY = 3
APP_LOG = logger.defineLogger()
S = sched.scheduler(time.time, time.sleep)


def log_error(e):
    APP_LOG.error(e)


def log(mode, pausado, text):
    p = 'paused' if pausado == 1 else 'unpaused'
    string = '[' + p + '] - ' + text
    if mode:
        APP_LOG.warning(string)
    else:
        APP_LOG.info(string)


def requests_retry_session(retries=7, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None):
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
        log_error('It failed :(' + str(x.__class__.__name__))
        return None
    else:
        return response


def getEstado(token):
    url = 'http://localhost:32400/transcode/sessions?X-Plex-Token='
    response = tryCatchResponse(url+token)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'xml')
        pause = int(soup.TranscodeSession['throttled'])
        return pause
    else:
        log_error('Failed response from: '+url)


def getSomeoneWatching(token):
    url = 'http://localhost:32400/status/sessions?X-Plex-Token='
    response = tryCatchResponse(url+token)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, features="xml")
        someone = int(soup.MediaContainer['size'])
        return someone
    else:
        log_error('Failed response from: ' + url)


def updateEstado(state, token):
    url = 'http://localhost:32400/:/prefs?BackgroundQueueIdlePaused='
    return requests.put(url+str(state)+'&X-Plex-Token='+token)


def openTokenFile():
    try:
        auth = open('auth.txt', 'r').read().splitlines()

        headers = {
            'X-Plex-Client-Identifier': 'Script do Vituxo',
            'X-Plex-Product': 'Badass Hetzner Machine',
            'X-Plex-Version': 'v2'
        }

        r = requests.post(
            'https://plex.tv/users/sign_in.json',
            auth=(auth[0], auth[1]),
            headers=headers
        )

        return r.json()['user']['authToken']
    except BaseException:
        log_error('Falha ao obter token')


def run_script(sc, token):
    try:
        pausado = getEstado(token)
        someone = getSomeoneWatching(token)
        if (not(pausado) is None) or (not(someone) is None):
            statuscode = 200

            if someone == 0 and pausado == 1:
                retorno = updateEstado(0, token)
                statuscode = retorno.status_code
                text = 'STARTED'
                mode = 1
            elif someone == 0 and pausado == 0:
                text = 'IDLE'
                mode = 0
            elif someone > 0 and pausado == 0:
                retorno = updateEstado(1, token)
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
    except BaseException:
        log_error('Issue when getting the status, ignoring this result and retrying')

    S.enter(DELAY, 1, run_script, (sc,token))


if __name__ == "__main__":
    try:
        token = openTokenFile()
        APP_LOG.info('Got Token: {}'.format(token))
        S.enter(DELAY, 1, run_script, (S, token))
        S.run()
    except KeyboardInterrupt:
        print('Interrupcao de teclado')
