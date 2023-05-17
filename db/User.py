from mongoengine import Document, StringField, IntField


class User(Document):
    id = IntField(primary_key=True)
    anon_key = StringField()
    name = StringField(default='!noname!')
    online = IntField(default=0)
    emoji = StringField(default="👤")
    bio = StringField()

    @property
    def nick(self):
        if not self.name or self.name == '!noname!':
            return f"#{self.anon_key}"
        else:
            return f'{self.name}'
