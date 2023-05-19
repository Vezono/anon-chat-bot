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
from MessageManager import MessageManager


connect(host=mongourl, db='mfhorning')
bot = TeleBot(bot_token)
rooms = ['Основная/Оффтоп', 'Ролеплей', 'Анкета']
log_chat = -1001593599607
mm = MessageManager(bot)


def generate_id():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(5))


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
        user = User(id=m.from_user.id, anon_key=id, room=rooms[0])
        user.save()
        bot.reply_to(m, f'Вьі новичок. Вам создан аккаунт с айди #{user.anon_key}.'
                        f' Надеюсь вьі ознакомленьі с правилами анон РП.')
        message_keys = []
        for anon in User.objects:
            botm = bot.send_message(anon.id, f'[BOT]: #{user.anon_key} присоединился (и попал в оффтоп комнату)!')
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
        num = mm.get_value_by_key_from_list(anon.id, pairs)
        bot.edit_message_text(f'#<b>{user.nick}</b>: {m.text}', anon.id, num, parse_mode="HTML")


@bot.message_handler(chat_types=['private'], commands=['list', 'lust'])
def nick_handler(m):
    tts = '<b>Для просмотра профиля, нажмите на емодзи!</b>\n'
    for room in rooms:
        tts += f'\n<b>{room}</b>:\n'
        for anon in User.objects(room=room).order_by('-online'):
            online = format_time(int(time.time() - anon.online))
            if anon.online != 0:
                tts += f'{anon.emoji_link}{anon.name} (#{anon.anon_key}) - писал {online} назад\n'
            else:
                tts += f'{anon.emoji_link}{anon.name} (#{anon.anon_key})\n'
    bot.reply_to(m, tts, parse_mode='HTML')


@bot.message_handler(chat_types=['private'], commands=['debug'])
def nick_handler(m):
    if m.from_user.id != admin or not m.reply_to_message:
        return

    bot.reply_to(m, f"[DEBUG]:\n\nORIGIN: {mm.get_origin(m).to_json()}\n")


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
    if m.text.count(' ') == 1:
        anon_id = m.text.split(' ')[1]
        if anon_id.isalpha() and len(anon_id) == 5:
            try:
                anon = User.objects.get(anon_key=anon_id)
                bot.reply_to(m, f'Профиль {anon.emoji}{anon.nick}:\n\n{anon.bio}')
            except:
                pass
            return
    bot.reply_to(m, '[BOT]: Командьі: \n\n'
                    '/nick - сменить ник\n'
                    '/list - список челиков (без деанона)\n'
                    '/emoji - сменить свое емоджи\n'
                    '/bio - сменить био\n'
                    '/switch - переключить комнату')


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


@bot.message_handler(chat_types=['private'], commands=['switch'])
def nick_handler(m):
    user = get_user(m)
    keyboard = types.InlineKeyboardMarkup()
    erooms = rooms.copy()
    erooms.remove(user.room)
    for room in erooms:
        keyboard.add(types.InlineKeyboardButton(text=f"{room}", callback_data=f"r_{room}"))
    bot.reply_to(m, 'Выберите комнату, в которую хотите перейти:', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data.startswith('r_'))
def switch_room_callback(c):
    user = get_user(c)
    room = c.data.split('_', 1)[1]
    old_room = user.room
    user.room = room
    user.save()
    bot.edit_message_text(f"Вы перешли в комнату {room}!", message_id=c.message.message_id, chat_id=c.message.chat.id)
    for anon in User.objects():
        bot.send_message(anon.id, f'[BOT]: {user.nick} перешел из "{old_room}" в "{room}"!')


@bot.message_handler(chat_types=['private'], commands=['bio'])
def nick_handler(m):
    if m.text.count(' ') < 1:
        bot.reply_to(m, '[BOT]: Использовать так - /bio любой текст.')
        return
    bio = m.text.split(' ', 1)[1].replace('<', '&lt;').replace('>', '&gt;')
    user = get_user(m)
    user.bio = bio
    user.save()
    bot.reply_to(m, '[BOT]: Био сохранено!')


@bot.message_handler(chat_types=['private'], commands=['ban'])
def nick_handler(m):
    if m.from_user.id != admin or not m.reply_to_message:
        return
    if not m.reply_to_message:
        bot.reply_to(m, '[BOT]: Реплай на юзера, которому бан!')
        return
    message = mm.get_origin(m)
    if not message:
        bot.reply_to(m, 'Ошибка!')
        return
    if message.origin == 'NO_ORIGIN':
        bot.reply_to(m, 'Ошибка!')
        return
    anon = User.objects.get(id=int(message.origin.split(' - ')[0]))
    anon.banned = True
    anon.save()


@bot.message_handler(chat_types=['private'], commands=['msg', 'mgs', 'pm'])
def nick_handler(m):
    if not m.reply_to_message:
        bot.reply_to(m, '[BOT]: Реплай на юзера, которому хотите написать приватное сообщение!')
        return
    if m.text.count(' ') < 1:
        bot.reply_to(m, '[BOT]: Использовать так - /nick твой ник. И не слишком длинно!!!')
        return
    text = m.text.split(' ', 1)[1].replace('<', '&lt;').replace('>', '&gt;')
    user = get_user(m)
    message = mm.get_origin(m)
    if not message:
        bot.reply_to(m, 'Ошибка!')
        return
    if not message.has_origin:
        bot.reply_to(m, 'Ошибка!')
        return
    anon = User.objects.get(id=int(message.origin.split(' - ')[0]))
    mm.send_text_pm(user, anon, text)


@bot.message_handler(chat_types=['private'], content_types=['text'])
def pm_handler(m):
    user = get_user(m)
    update_online(user)
    m.text = m.text.replace('<', '&lt;').replace('>', '&gt;')
    message_keys = []
    for anon in User.objects(room=user.room):
        if m.reply_to_message:
            message = mm.get_origin(m)
            if message:
                if message.private:
                    bot.reply_to(m, '[BOT] сорян, еще не запилил')
                    return
            try:
                num = mm.get_reply_number(m, anon)
                botm = bot.send_message(anon.id, f'<b>{user.nick}</b>: {m.text}',
                                        reply_to_message_id=num, parse_mode="HTML")
            except Exception as e:
                print(traceback.format_exc())
                botm = bot.send_message(anon.id, f'<b>{user.nick}</b>: {m.text}', parse_mode="HTML")
        else:
            botm = bot.send_message(anon.id, f'<b>{user.nick}</b>: {m.text}', parse_mode="HTML")
        message_keys.append(f"{anon.id} - {botm.message_id}")
    message = Message(pairs=message_keys, origin=f"{m.from_user.id} - {m.message_id}")
    message.save()


@bot.message_handler(chat_types=['private'], content_types=['animation', 'photo'])
def pm_handler(m):
    user = get_user(m)
    update_online(user)
    message_keys = []
    if m.content_type == 'animation':
        file_id = m.animation.file_id
        send = bot.send_animation
    else:
        file_id = m.photo[0].file_id
        send = bot.send_photo
    caption = m.caption if m.caption else ''
    for anon in User.objects(room=user.room):
        if m.reply_to_message:
            try:
                num = mm.get_reply_number(m, anon)
                botm = send(anon.id, file_id, reply_to_message_id=num, caption=f"{user.nick}: {caption}")
            except:
                print(traceback.format_exc())
                botm = send(anon.id, file_id, caption=f"{user.nick}: {caption}")
        else:
            botm = send(anon.id, file_id, caption=f"{user.nick}: {caption}")
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
    for anon in User.objects(room=user.room):
        if m.reply_to_message:
            try:
                num = mm.get_reply_number(m, anon)
                botm = bot.send_sticker(anon.id, sticker, reply_markup=keyboard, reply_to_message_id=num)
            except:
                print(traceback.format_exc())
                botm = bot.send_sticker(anon.id, sticker, reply_markup=keyboard)
        else:
            botm = bot.send_sticker(anon.id, sticker, reply_markup=keyboard)
        message_keys.append(f"{anon.id} - {botm.message_id}")
    message = Message(pairs=message_keys, origin=f"{m.from_user.id} - {m.message_id}")
    message.save()


print(7777)
# bot.send_message(-1001251705571, 'Бот запущен~~~')
bot.infinity_polling()
