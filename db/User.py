from mongoengine import Document, StringField, IntField, BooleanField
from utils import format_time
import time


class User(Document):
    id = IntField(primary_key=True)
    anon_key = StringField()
    name = StringField(default='')
    online = IntField(default=0)
    emoji = StringField(default="👤")
    room = StringField(default="Основная/Оффтоп", required=True)
    bio = StringField(default="Анон еще ничего сюда не написал!")
    banned = BooleanField(default=False)
    skipped = BooleanField(default=False)

    @property
    def nick(self):
        if not self.name or self.name == '!noname!':
            return f"#{self.anon_key}"
        else:
            return f'{self.name}'

    @property
    def emoji_link(self):
        return f'<a href="t.me/mf_horning_bot?start={self.anon_key}">{self.emoji}</a>'

    @property
    def list_entry(self):
        online = format_time(int(time.time() - self.online))
        if self.online != 0:
            text = f'{self.emoji_link}{self.name} (#{self.anon_key}) - писал {online} назад'
        else:
            text = f'{self.emoji_link}{self.name} (#{self.anon_key}) - писал {online} назад'
        if self.skipped:
            text = f'<s>{text}</s>'
        return text
