from db.User import User
from db.Message import Message


class MessageManager:
    def __init__(self, bot):
        self.id = bot.get_me().id
        self.bot = bot

    def get_reply_number(self, replying_message, anon):
        pair = f"{replying_message.from_user.id} - {replying_message.reply_to_message.message_id}"
        message = Message.objects.get(pairs__in=[pair])
        return self.get_value_by_key_from_list(anon.id, message.pairs)

    def get_value_by_key_from_list(self, key, lst):
        value = [pair for pair in lst if f"{key}" == pair.split(' - ')[0]][0].split(' - ')[1]
        return value

    def get_origin(self, replying_message):
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
