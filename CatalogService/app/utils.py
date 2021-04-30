import threading
import json

def synchronized(func):
    '''
    synchronized decorator
    '''

    func.__lock__ = threading.Lock()

    def synced_func(*args, **kws):
        with func.__lock__:
            return func(*args, **kws)

    return synced_func

@synchronized
def log_write_request(log_request):
    fd = open('write_requests.json', "r+")
    data = json.loads(fd.read())
    if ("request_id" in log_request):
        key = "request_id_" + str(log_request["request_id"])
        data[key] = log_request
    else:
        key = "update_request"
        if (key not in data):
            data[key] = []
        data[key].append(log_request)
    fd.seek(0)
    json.dump(data, fd)
    fd.truncate()
    fd.close()

@synchronized
def log_read_request(log_request):
    fd = open('read_requests.json', "r+")
    data = json.loads(fd.read())
    data.append(log_request)
    fd.seek(0)
    json.dump(data, fd)
    fd.truncate()
    fd.close()