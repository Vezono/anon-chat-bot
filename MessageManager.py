from telebot import TeleBot, types
import utils
from db import User, Message, Room
import traceback
from telebot.apihelper import ApiTelegramException
from exceptions import blocked_exception, replied_message_exception


class MessageManager:
    def __init__(self, bot):
        self.id = bot.get_me().id
        self.bot: TeleBot = bot

    def form_room_menu(self, user: User) -> types.InlineKeyboardMarkup:
        keyboard = types.InlineKeyboardMarkup()
        for room in Room.objects():
            status = '👁✅' if room.name in user.monitoring else '👁☑️'
            if user.room == room.name:
                keyboard.add(types.InlineKeyboardButton(text=f"| {room.name} |", callback_data=f"rs_{room.name}"),
                             types.InlineKeyboardButton(text=status, callback_data=f"rw_{room.name}"))
            else:
                keyboard.add(types.InlineKeyboardButton(text=f"{room.name}", callback_data=f"r_{room.name}"),
                             types.InlineKeyboardButton(text=status, callback_data=f"rw_{room.name}"))
        return keyboard

    def get_reply_number(self, replying_message: types.Message, anon):
        pair = f"{replying_message.from_user.id} - {replying_message.reply_to_message.message_id}"
        message = Message.objects.get(pairs__in=[pair])
        return utils.get_value_by_key_from_list(anon.id, message.pairs)

    def get_message(self, replying_message):
        """
        replying_message must be from the bot. tries to get DB Message entry of the origin.
        """
        if replying_message.reply_to_message.from_user.id != self.id:
            return None

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

    def process_text_message(self, author: User, message):
        message_keys = []
        for anon in User.objects(skipped=False):
            if anon.room != author.room and author.room not in anon.monitoring:
                print(anon.nick)
                continue
            result = f'<b>{author.nick}</b>: {message.text}'
            result = f'<b>[{author.room}]</b>\n{result}' if author.room in anon.monitoring else result
            key = self.deliver_text(anon, result)
            message_keys.append(key)
        message = Message(pairs=message_keys, origin=f"{author.id} - {message.message_id}")
        message.save()

    def process_reply_text_message(self, author: User, message: types.Message):
        """
        Reply can have these possibilities:
        - reply on service message from the bot (no message entry in DB, handled by participation check)
        - reply on the own message (useless, being checked in the handler)

        - reply on PM message, currently useless (TODO: Implement private replies)
        - reply on the message from different room (crossreplying)
        - reply on the message in the same room
        """
        message_keys = []
        for anon in User.objects(skipped=False):
            m_entry = self.get_message(message)  # Returns None in case of a service message
            if not m_entry:
                return  # Service message it is
            if m_entry and m_entry.private:  # TODO: Implement private replies
                return

            if anon.id not in m_entry.participants:  # Message was never delivered to anon, hence no reply is possible
                continue

            result = f'<b>{author.nick}</b>: {message.text}'
            result = f'<b>[{author.room}]</b>\n{result}' if author.room in anon.monitoring else result

            reply_id = self.get_reply_number(message, anon)  # Any errors must be fixed by participation check
            key = self.deliver_text(anon, result, reply_id)

            message_keys.append(key)
        message = Message(pairs=message_keys, origin=f"{author.id} - {message.message_id}")
        message.save()

    def deliver_text(self, recipient: User, text, reply_id=0):
        """
        Delivers text to the recipient, handles Telegram exceptions. Returns keys in case of success
        """
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
