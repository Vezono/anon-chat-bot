import traceback
import emoji as emj
from telebot import TeleBot, types
from db import User, Message, Room
from mongoengine import connect
import time
from config import mongourl, bot_token, admin
from MessageManager import MessageManager
from telebot.apihelper import ApiTelegramException
from exceptions import blocked_exception, replied_message_exception
import utils

connect(host=mongourl, db='mfhorning')
bot = TeleBot(bot_token)
log_chat = -1001593599607
mm = MessageManager(bot)

for user in User.objects:
    user.skipped = False
    user.save()


def get_user(m):
    try:
        user = User.objects.get(id=m.from_user.id)
        user.skipped = False
        user.save()
    except:
        id = utils.generate_id()
        user = User(id=m.from_user.id, anon_key=id, room="Основная/Оффтоп")
        user.save()
        bot.reply_to(m, f'Приветствую! Вам создан аккаунт с айди #{user.anon_key}.')
        message_keys = []
        for anon in User.objects(skipped=False):
            botm = bot.send_message(anon.id, f'🆕 #{user.anon_key} зарегистрировался!')
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
        num = utils.get_value_by_key_from_list(anon.id, pairs)
        bot.edit_message_text(f'#<b>{user.nick}</b>: {m.text}', anon.id, num, parse_mode="HTML")


@bot.message_handler(chat_types=['private'], commands=['list', 'lust'])
def nick_handler(m):
    tts = '<b>Для просмотра профиля, нажмите на емодзи!</b>\n'
    for room in Room.objects():
        tts += f'\n<b>{room.name}</b>:\n'
        for anon in room.members.order_by('-online'):
            tts += f'{anon.list_entry}\n'
    bot.reply_to(m, tts, parse_mode='HTML')


@bot.message_handler(chat_types=['private'], commands=['debug'])
def nick_handler(m):
    if m.from_user.id != admin or not m.reply_to_message:
        return
    bot.reply_to(m, f"[DEBUG]:\n\nORIGIN: {mm.get_message(m).to_json()}\n")


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


@bot.message_handler(chat_types=['private'], commands=['start'], func=lambda m: m.text.count(' '))
def profile_link_handler(m):
    user = get_user(m)
    anon_id = m.text.split(' ')[1]
    try:
        anon = User.objects.get(anon_key=anon_id)
        bot.reply_to(m, f'Профиль {anon.emoji}{anon.nick}:\n\n{anon.bio}')
    except:
        pass


@bot.message_handler(chat_types=['private'], commands=['start'], func=lambda m: not m.text.count(' '))
def start_handler(m):
    user = get_user(m)
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


@bot.message_handler(chat_types=['private'], commands=['switch', 'rooms'])
def switch_handler(m):
    user = get_user(m)
    keyboard = mm.form_room_menu(user)
    bot.reply_to(m, '<b>[BOT]: Меню комнат</b>', reply_markup=keyboard, parse_mode='HTML')


@bot.callback_query_handler(func=lambda c: c.data.startswith('r_'))
def switch_room_callback(c):
    user = get_user(c)
    room = c.data.split('_', 1)[1]
    old_room = user.room
    user.monitoring.append(old_room) if old_room not in user.monitoring else None
    user.room = room
    user.monitoring.remove(room) if room in user.monitoring else None
    user.save()
    bot.edit_message_text(f"<b>[BOT]: Меню комнат</b>", message_id=c.message.message_id, chat_id=c.message.chat.id,
                          reply_markup=mm.form_room_menu(user))
    for anon in User.objects(skipped=False):
        try:
            bot.send_message(anon.id, f'➡️{user.nick} перешел из "{old_room}" в "{room}"!')
        except ApiTelegramException as e:
            if e.description == blocked_exception:
                mm.handle_user_block(anon)


@bot.callback_query_handler(func=lambda c: c.data.startswith('rw_'))
def monitor_room_callback(c):
    user = get_user(c)
    room = c.data.split('_', 1)[1]
    user.monitoring.append(room) if room not in user.monitoring else user.monitoring.remove(room)
    user.save()
    keyboard = mm.form_room_menu(user)
    bot.edit_message_text(f"<b>[BOT]: Меню комнат</b>", message_id=c.message.message_id,
                          chat_id=c.message.chat.id, reply_markup=keyboard, parse_mode='HTML')


@bot.message_handler(chat_types=['private'], commands=['bio'])
def bio_handler(m):
    if m.text.count(' ') < 1:
        bot.reply_to(m, '[BOT]: Использовать так - /bio любой текст.')
        return
    bio = m.text.split(' ', 1)[1].replace('<', '&lt;').replace('>', '&gt;')
    user = get_user(m)
    user.bio = bio
    user.save()
    bot.reply_to(m, '[BOT]: Био сохранено!')


@bot.message_handler(chat_types=['private'], commands=['msg', 'mgs', 'pm', 'msh', 'tell'])
def msg_handler(m):
    if not m.reply_to_message:
        bot.reply_to(m, '[BOT]: Реплай на юзера, которому хотите написать приватное сообщение!')
        return
    if m.text.count(' ') < 1:
        bot.reply_to(m, '[BOT]: Использовать так - /nick твой ник. И не слишком длинно!!!')
        return
    text = m.text.split(' ', 1)[1].replace('<', '&lt;').replace('>', '&gt;')
    user = get_user(m)
    message = mm.get_message(m)
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
    if not m.reply_to_message:
        mm.process_text_message(user, m)
    elif m.reply_to_message.from_user.id == mm.id:
        mm.process_reply_text_message(user, m)


@bot.message_handler(chat_types=['private'], content_types=['animation', 'photo', 'sticker'])
def media_handler(m):
    user = get_user(m)
    update_online(user)
    message_keys = []
    keyboard = None
    caption = None
    if m.content_type == 'sticker':
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text=f"{user.nick}", callback_data="lmao"))
    else:
        caption = f"{user.nick}: {m.caption if m.caption else ''}"
    for anon in User.objects(room=user.room):
        if anon.skipped:
            continue
        if m.reply_to_message:
            try:
                num = mm.get_reply_number(m, anon)
                botm = bot.copy_message(anon.id, user.id, m.message_id, caption,
                                        parse_mode="HTML", reply_to_message_id=num, reply_markup=keyboard,
                                        allow_sending_without_reply=True)
            except ApiTelegramException as e:
                if e.description == blocked_exception:  # Handling the user, which blocked the bot
                    mm.handle_user_block(anon)
                print(traceback.format_exc())
        else:
            botm = bot.copy_message(anon.id, user.id, m.message_id, caption, parse_mode="HTML", reply_markup=keyboard)
        message_keys.append(f"{anon.id} - {botm.message_id}")
    message = Message(pairs=message_keys, origin=f"{m.from_user.id} - {m.message_id}")
    message.save()


print(7777)
bot.infinity_polling()
