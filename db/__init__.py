from mongoengine import Document, StringField, IntField, BooleanField, ListField, SequenceField
from utils import format_time
import time


class Room(Document):
    name = StringField(primary_key=True)

    @property
    def members(self):
        return User.objects(room=self.name)


class Message(Document):
    id = SequenceField(primary_key=True, auto_increment=True)
    pairs = ListField()
    origin = StringField(default="")
    private = BooleanField(default=False)

    meta = {'collection': 'messages'}

    @property
    def author(self):
        return int(self.origin.split(' - ')[0]) if self.has_origin else None

    @property
    def has_origin(self):
        return self.origin and self.origin != 'NO_ORIGIN'


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

    def get_room(self):
        return Room.objects.get(name=self.room)

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
