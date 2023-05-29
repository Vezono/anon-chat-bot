import random
import string


def get_value_by_key_from_list(key, lst):
    value = [pair for pair in lst if f"{key}" == pair.split(' - ')[0]][0].split(' - ')[1]
    return value


def format_time(seconds):
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    weeks = days // 7
    years = days // 365
    if years:
        return f'{years} лет'
    elif weeks:
        return f'{weeks} недель'
    elif days:
        return f'{days} дней'
    elif hours:
        return f'{hours} часов'
    elif minutes:
        return f'{minutes} минут'
    else:
        return f'{seconds} секунд'


def generate_id():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(5))