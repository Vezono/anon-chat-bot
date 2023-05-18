import traceback
import emoji as emj
from telebot import TeleBot, types
from db.User import User
from db.Message import Message
from mongoengine import connect
import random
import string
import time
from config import mongourl, bot_token, admin

connect(host=mongourl, db='mfhorning')
bot = TeleBot(bot_token)


def generate_id():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(5))


def get_reply_number(m, anon):
    message = Message.objects.get(pairs__in=[f"{m.from_user.id} - {m.reply_to_message.message_id}"])
    num = message.pairs
    num = [pair for pair in num if f"{anon.id}" in pair][0].split(' - ')[1]
    return num


def get_origin(m):
    try:
        return Message.objects.get(pairs__in=[f"{m.from_user.id} - {m.reply_to_message.message_id}"])
    except:
        print(traceback.format_exc())
        return


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


def get_user(m):
    try:
        user = User.objects.get(id=m.from_user.id)
    except:
        id = generate_id()
        user = User(id=m.from_user.id, anon_key=id)
        user.save()
        bot.reply_to(m, f'Вьі новичок. Вам создан аккаунт с айди #{user.anon_key}.'
                        f' Надеюсь вьі ознакомленьі с правилами анон РП.')
        message_keys = []
        for anon in User.objects:
            botm = bot.send_message(anon.id, f'[BOT]: #{user.anon_key} присоединился!')
            message_keys.append(f"{anon.id} - {botm.message_id}")
        message = Message(pairs=message_keys)
        message.save()
    return user


def update_online(user):
    user.online = time.time()
    user.save()


@bot.edited_message_handler(chat_types=['private'], content_types=['text'])
def edited_handler(m):
    user = get_user(m)
    update_online(user)
    try:
        pairs = Message.objects.get(origin=f"{m.from_user.id} - {m.message_id}").pairs
    except:
        print(traceback.format_exc())
        return
    for anon in User.objects:
        num = [pair for pair in pairs if f"{anon.id}" in pair][0].split(' - ')[1]
        bot.edit_message_text(f'#<b>{user.nick}</b>: {m.text}', anon.id, num, parse_mode="HTML")


@bot.message_handler(chat_types=['private'], commands=['list'])
def nick_handler(m):
    tts = '[BOT]: Список участников:\n'
    for anon in User.objects.order_by('-online'):
        online = format_time(int(time.time() - anon.online))
        tts += f'\n{anon.emoji}{anon.name if anon.name != "!noname!" else ""} ' \
               f'(#{anon.anon_key}) - писал {online} назад'\
            if anon.online != 0 else f'\n{anon.emoji}{anon.name if anon.name != "!noname!" else ""} (#{anon.anon_key})'
    bot.reply_to(m, tts)


@bot.message_handler(chat_types=['private'], commands=['debug'])
def nick_handler(m):
    if m.from_user.id != admin or not m.reply_to_message:
        return

    bot.reply_to(m, f"[DEBUG]:\n\nORIGIN: {get_origin(m).to_json()}\n")


@bot.message_handler(chat_types=['private'], commands=['emoji'])
def nick_handler(m):
    if m.text.count(' ') < 1:
        bot.reply_to(m, '[BOT]: Использовать так - /emoji твое емоджи. И только емоджи!!!')
        return
    emoji = m.text.split(' ', 1)[1]
    if not emj.is_emoji(emoji):
        bot.reply_to(m, '[BOT]: Использовать так - /emoji твое емоджи. И только емоджи!!!')
        return
    user = get_user(m)
    user.emoji = emoji
    user.save()
    bot.reply_to(m, '[BOT]: Емоджи сохранен!')


@bot.message_handler(chat_types=['private'], commands=['start'])
def nick_handler(m):
    user = get_user(m)
    bot.reply_to(m, '[BOT]: Командьі: \n\n'
                    '/nick - сменить ник\n'
                    '/list - список челиков (без деанона)\n'
                    '/emoji - сменить свое емоджи')


@bot.message_handler(chat_types=['private'], commands=['nick'])
def nick_handler(m):
    if m.text.count(' ') < 1 or len(m.text) > 30:
        bot.reply_to(m, '[BOT]: Использовать так - /nick твой ник. И не слишком длинно!!!')
        return
    nick = m.text.split(' ', 1)[1].replace('<', '&lt;').replace('>', '&gt;')
    if "#" in nick:
        bot.reply_to(m, '[BOT]: Нельзя хештеги.')
        return
    user = get_user(m)
    user.name = nick
    user.save()
    bot.reply_to(m, '[BOT]: Ник сохранен!')


@bot.message_handler(chat_types=['private'], commands=['msg', 'pm'])
def nick_handler(m):
    if not m.reply_to_message:
        bot.reply_to(m, '[BOT]: Реплай на юзера, которому хотите написать приватное сообщение!')
        return
    if m.text.count(' ') < 1:
        bot.reply_to(m, '[BOT]: Использовать так - /nick твой ник. И не слишком длинно!!!')
        return
    text = m.text.split(' ', 1)[1].replace('<', '&lt;').replace('>', '&gt;')
    user = get_user(m)
    message = get_origin(m)
    if not message:
        bot.reply_to(m, 'Ошибка!')
        return
    if message.origin == 'NO_ORIGIN':
        bot.reply_to(m, 'Ошибка!')
        return
    anon = User.objects.get(id=int(message.origin.split(' - ')[0]))
    anonm = bot.send_message(anon.id, f'[PM] {user.nick}: {text}')
    userm = bot.send_message(user.id, f'[PM to {anon.nick}]: {text}')
    message = Message(origin=f"{user.id} - {userm.message_id}", private=True, pairs=[f'{anon.id} - {anonm.message_id}', f'{user.id} - {userm.message_id}'])
    message.save()


@bot.message_handler(chat_types=['private'], content_types=['text'])
def pm_handler(m):
    user = get_user(m)
    update_online(user)
    m.text = m.text.replace('<', '&lt;').replace('>', '&gt;')
    message_keys = []
    for anon in User.objects:
        if m.reply_to_message:
            message = get_origin(m)
            if message:
                if message.private:
                    bot.reply_to(m, '[BOT] сорян, еще не запилил')
                    return
            try:
                num = get_reply_number(m, anon)
                botm = bot.send_message(anon.id, f'<b>{user.nick}</b>: {m.text}',
                                        reply_to_message_id=num, parse_mode="HTML")
            except:
                print(traceback.format_exc())
                botm = bot.send_message(anon.id, f'<b>{user.nick}</b>: {m.text}', parse_mode="HTML")
        else:
            botm = bot.send_message(anon.id, f'<b>{user.nick}</b>: {m.text}', parse_mode="HTML")
        message_keys.append(f"{anon.id} - {botm.message_id}")
    message = Message(pairs=message_keys, origin=f"{m.from_user.id} - {m.message_id}")
    message.save()


@bot.message_handler(chat_types=['private'], content_types=['animation'])
def pm_handler(m):
    user = get_user(m)
    update_online(user)
    message_keys = []
    gif = m.animation.file_id
    caption = m.caption
    for anon in User.objects:
        if m.reply_to_message:
            try:
                num = get_reply_number(m, anon)
                botm = bot.send_animation(anon.id, gif, reply_to_message_id=num,
                                      caption=f"{user.nick}: {caption if caption else ''}")
            except:
                print(traceback.format_exc())
                botm = bot.send_animation(anon.id, gif,
                                      caption=f"{user.nick}: {caption if caption else ''}")
        else:
            botm = bot.send_animation(anon.id, gif,
                                  caption=f"{user.nick}: {caption if caption else ''}")
        message_keys.append(f"{anon.id} - {botm.message_id}")
    message = Message(pairs=message_keys, origin=f"{m.from_user.id} - {m.message_id}")
    message.save()


@bot.message_handler(chat_types=['private'], content_types=['sticker'])
def pm_handler(m):
    user = get_user(m)
    update_online(user)
    message_keys = []
    sticker = m.sticker.file_id
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text=f"{user.nick}", callback_data="lmao"))
    for anon in User.objects:
        if m.reply_to_message:
            try:
                num = get_reply_number(m, anon)
                botm = bot.send_sticker(anon.id, sticker, reply_markup=keyboard, reply_to_message_id=num)
            except:
                print(traceback.format_exc())
                botm = bot.send_sticker(anon.id, sticker, reply_markup=keyboard)
        else:
            botm = bot.send_sticker(anon.id, sticker, reply_markup=keyboard)
        message_keys.append(f"{anon.id} - {botm.message_id}")
    message = Message(pairs=message_keys, origin=f"{m.from_user.id} - {m.message_id}")
    message.save()


@bot.message_handler(chat_types=['private'], content_types=['photo'])
def pm_handler(m):
    user = get_user(m)
    update_online(user)
    message_keys = []
    photo = m.photo[0].file_id
    caption = m.caption
    for anon in User.objects:
        if m.reply_to_message:
            try:
                num = get_reply_number(m, anon)
                botm = bot.send_photo(anon.id, photo, reply_to_message_id=num,
                                      caption=f"{user.nick}: {caption if caption else ''}")
            except:
                print(traceback.format_exc())
                botm = bot.send_photo(anon.id, photo,
                                      caption=f"{user.nick}: {caption if caption else ''}")
        else:
            botm = bot.send_photo(anon.id, photo,
                                      caption=f"{user.nick}: {caption if caption else ''}")
        message_keys.append(f"{anon.id} - {botm.message_id}")
    message = Message(pairs=message_keys, origin=f"{m.from_user.id} - {m.message_id}")
    message.save()




print(7777)
# bot.send_message(-1001251705571, 'Бот запущен~~~')
bot.infinity_polling()
