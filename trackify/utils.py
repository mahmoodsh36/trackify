import uuid
import time
import urllib.parse
import string
import random
import datetime

def generate_id(length=None):
    if not length:
        return str(uuid.uuid4())
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# time since the unix epoch in milliseconds
current_time = lambda: int(round(time.time() * 1000))

def uri_encode(text):
    return urllib.parse.quote(text)

def get_largest_elements(list_to_sort, limit, compare):
    begin = current_time()
    mylist = list_to_sort.copy()
    final_list = []
    cnt = 0
    while True:
        if limit > -1 and cnt >= limit:
            return final_list
        if not mylist:
            return final_list
        biggest = mylist[0]
        for j in range(len(mylist)):
            element = mylist[j]
            if compare(element, biggest):
                biggest = element
        final_list.append(biggest)
        mylist.remove(biggest)
        cnt += 1
    return final_list

def hrs_from_ms(ms):
    return ms // 3600000

def mins_from_ms(ms):
    return (ms // 60000) % 60

def secs_from_ms(ms):
    return (ms // 1000) % 60

def str_to_bool(val):
    if val == 'True':
        return True
    return False

def timestamp_to_date(timestamp):
    digits = len(str(timestamp))
    # get rid of extra digits if timestamp is in milliseconds/nanoseconds
    timestamp = int(timestamp / (10 ** (digits - 10)))
    return datetime.datetime.fromtimestamp(timestamp)

def one_day_ago():
    return current_time() - 24 * 3600 * 1000

def one_week_ago():
    return current_time() - 7 * 24 * 3600 * 1000
