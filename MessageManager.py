from telebot import TeleBot

from db.User import User
from db.Message import Message
import traceback
from telebot.apihelper import ApiTelegramException
from exceptions import blocked_exception, replied_message_exception


class MessageManager:
    def __init__(self, bot):
        self.id = bot.get_me().id
        self.bot: TeleBot = bot

    def get_reply_number(self, replying_message, anon):
        pair = f"{replying_message.from_user.id} - {replying_message.reply_to_message.message_id}"
        message = Message.objects.get(pairs__in=[pair])
        return self.get_value_by_key_from_list(anon.id, message.pairs)

    def get_value_by_key_from_list(self, key, lst):
        value = [pair for pair in lst if f"{key}" == pair.split(' - ')[0]][0].split(' - ')[1]
        return value

    def get_message(self, replying_message):
        pair = f"{replying_message.from_user.id} - {replying_message.reply_to_message.message_id}"
        try:
            result = Message.objects().get(pairs__in=[pair])
        except:
            result = None
        if result:
            return result

    def send_text_pm(self, user, anon, text):
        anon_m = self.bot.send_message(anon.id, f'[PM] {user.nick}: {text}')
        user_m = self.bot.send_message(user.id, f'[PM to {anon.nick}]: {text}')
        message = Message(origin=f"{user.id} - {user_m.message_id}", private=True,
                          pairs=[f'{anon.id} - {anon_m.message_id}', f'{user.id} - {user_m.message_id}'])
        message.save()

    def handle_user_block(self, user: User):
        user.skipped = True
        user.save()
        for anon in User.objects(skipped=False):
            try:
                self.bot.send_message(anon.id, f'[BOT]: {user.nick} кинул бота в чс. Ок.')
            except:
                self.handle_user_block(anon)

    def process_text_message(self, author, text, message, is_reply=False):
        message_keys = []
        for anon in User.objects(room=author.room):  # TODO: Room subscription
            if anon.skipped:
                continue
            if not is_reply:
                key = self.deliver_text(anon, f'<b>{author.nick}</b>: {text}')
                message_keys.append(key)
                continue
            message = self.get_message(message)
            if message and message.private:
                self.bot.reply_to(message, '[BOT] сорян, еще не запилил')  # TODO: Private replies
                return

            reply_id = self.get_reply_number(message, anon)
            key = self.deliver_text(anon, f'<b>{author.nick}</b>: {text}', reply_id)

            message_keys.append(key)
        message = Message(pairs=message_keys, origin=f"{author.id} - {message.message_id}")
        message.save()

    def deliver_text(self, recipient: User, text, reply_id=0):
        try:
            if reply_id:
                result = self.bot.send_message(recipient.id, text, reply_to_message_id=reply_id,
                                               parse_mode='HTML', allow_sending_without_reply=True)
            else:
                result = self.bot.send_message(recipient.id, text, parse_mode='HTML')
            return f"{recipient.id} - {result.message_id}"
        except ApiTelegramException as e:
            if e.description == blocked_exception:  # Handling the user, which blocked the bot
                self.handle_user_block(recipient)
                return
