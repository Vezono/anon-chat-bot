def format_time(seconds):
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    weeks = days // 7
    if weeks:
        return f'{weeks} недель'
    elif days:
        return f'{days} дней'
    elif hours:
        return f'{hours} часов'
    elif minutes:
        return f'{minutes} минут'
    else:
        return f'{seconds} секунд'
