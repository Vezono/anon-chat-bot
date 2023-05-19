from mongoengine import Document, ListField, SequenceField, StringField, BooleanField
from .User import User


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



