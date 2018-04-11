import datetime


def strptime(date_str):
    return datetime.datetime.strptime(date_str, '%Y-%m-%d')
