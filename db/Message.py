from mongoengine import Document, ListField, SequenceField, StringField


class Message(Document):
    id = SequenceField(primary_key=True, auto_increment=True)
    pairs = ListField()
    origin = StringField(default="NO_ORIGIN")

    meta = {'collection': 'messages'}

