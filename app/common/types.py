import re


def strphone(phone):
    return re.sub('[^0-9]', '', phone)
