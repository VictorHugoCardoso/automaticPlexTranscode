import logging
from logging.handlers import RotatingFileHandler

def defineLogger():    
    log_formatter = logging.Formatter('%(levelname)s - %(asctime)s - %(message)s')
            
    my_handler = RotatingFileHandler(filename='loggin.log', mode='a', maxBytes=5*1024*1024, 
                                    backupCount=2, encoding=None)
    my_handler.setFormatter(log_formatter)
    my_handler.setLevel(logging.INFO)

    app_log = logging.getLogger('root')
    app_log.setLevel(logging.INFO)
    app_log.addHandler(my_handler)

    return app_log