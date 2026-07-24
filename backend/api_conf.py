import multiprocessing

workers = multiprocessing.cpu_count()
bind = "0.0.0.0:8080"
keepalive = 120
timeout = 120
errorlog = '-'
accesslog = '-'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'
loglevel = 'info'
pidfile = '/tmp/quantumpacs.pid'
