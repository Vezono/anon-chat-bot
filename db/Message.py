from mongoengine import Document, ListField, SequenceField, StringField, BooleanField


class Message(Document):
    id = SequenceField(primary_key=True, auto_increment=True)
    pairs = ListField()
    origin = StringField(default="NO_ORIGIN")
    private = BooleanField(default=False)

    meta = {'collection': 'messages'}

    @property
    def author(self):
        return int(self.origin.split(' - ')[0]) if self.origin != 'NO_ORIGIN' else None