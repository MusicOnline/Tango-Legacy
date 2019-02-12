from tango.core.bot import Tango

db = Tango.db

# pylint: disable=no-member


class Entry(db.Model):  # type: ignore  # <entry>
    __tablename__ = "JMdict_Entry"

    id = db.Column(db.Integer, primary_key=True)  # <ent_seq>

    def __repr__(self) -> str:
        return "<Entry id={0.id}>".format(self)


class WritingElement(db.Model):  # type: ignore  # <k_ele>
    __tablename__ = "JMdict_WritingElement"

    entry_id = db.Column(db.ForeignKey("JMdict_Entry.id"), primary_key=True)
    literal = db.Column(db.String, primary_key=True)  # <keb>
    priority = db.Column(db.ARRAY(db.String), nullable=False)  # <ke_pri>
    info = db.Column(db.ARRAY(db.String), nullable=False)  # <ke_inf>

    def __repr__(self) -> str:
        return (
            "<JMdict_WritingElement entry_id={0.entry_id} "
            "literal={0.literal!r}>".format(self)
        )


class ReadingElement(db.Model):  # type: ignore  # <r_ele>
    __tablename__ = "JMdict_ReadingElement"

    entry_id = db.Column(db.ForeignKey("JMdict_Entry.id"), primary_key=True)
    literal = db.Column(db.String, primary_key=True)  # <reb>
    priority = db.Column(db.ARRAY(db.String), nullable=False)  # <re_pri>
    info = db.Column(db.ARRAY(db.String), nullable=False)  # <re_inf>

    def __repr__(self) -> str:
        return (
            "<JMdict_ReadingElement entry_id={0.entry_id} "
            "literal={0.literal!r}>".format(self)
        )


class Sense(db.Model):  # type: ignore  # <sense>
    __tablename__ = "JMdict_Sense"

    entry_id = db.Column(db.ForeignKey("JMdict_Entry.id"), primary_key=True)
    index = db.Column(db.Integer, primary_key=True)  # incremental id
    references = db.Column(db.ARRAY(db.String), nullable=False)  # <xref>
    antonyms = db.Column(db.ARRAY(db.String), nullable=False)  # <ant>
    parts_of_speech = db.Column(db.ARRAY(db.String), nullable=False)  # <pos>
    fields = db.Column(db.ARRAY(db.String), nullable=False)  # <field>
    misc = db.Column(db.ARRAY(db.String), nullable=False)  # <misc>
    dialects = db.Column(db.ARRAY(db.String), nullable=False)  # <dial>
    info = db.Column(db.ARRAY(db.String), nullable=False)  # <s_inf>

    def __repr__(self) -> str:
        return "<JMdict_Sense entry_id={0.entry_id} index={0.index}>".format(self)


class Gloss(db.Model):  # type: ignore  # <gloss> (within <sense>)
    __tablename__ = "JMdict_Gloss"

    entry_id = db.Column("entry_id", db.Integer)
    sense_index = db.Column("sense_index", db.Integer)
    text = db.Column(db.String, nullable=False)  # text
    lang = db.Column(db.String, nullable=False)  # xml:lang attr (implied: eng)
    gender = db.Column(db.String)  # g_gend attr
    type = db.Column(db.String)  # g_type attr

    __table_args__ = (
        db.ForeignKeyConstraint([entry_id, sense_index], [Sense.entry_id, Sense.index]),
    )

    def __repr__(self) -> str:
        return (
            "<JMdict_Gloss entry_id={0.entry_id} "
            "sense_index={0.sense_index}>".format(self)
        )


class LSource(db.Model):  # type: ignore  # <lsource> (within <sense>)
    __tablename__ = "JMdict_LSource"

    entry_id = db.Column("entry_id", db.Integer)
    sense_index = db.Column("sense_index", db.Integer)
    text = db.Column(db.String)  # text
    lang = db.Column(db.String, nullable=False)  # xml:lang attr (implied: eng)
    type = db.Column(db.String, nullable=False)  # ls_type attr (implied: full)
    wasei = db.Column(db.String)  # ls_type attr

    __table_args__ = (
        db.ForeignKeyConstraint([entry_id, sense_index], [Sense.entry_id, Sense.index]),
    )

    def __repr__(self) -> str:
        return (
            "<JMdict_LSource entry_id={0.entry_id} "
            "sense_index={0.sense_index}>".format(self)
        )


class ReadingWriting(db.Model):  # type: ignore
    __tablename__ = "JMdict_ReadingWriting"

    entry_id = db.Column("entry_id", db.Integer)
    reading_literal = db.Column("reading_literal", db.String)
    _entry_id = db.Column("_entry_id", db.Integer)
    writing_literal = db.Column("writing_literal", db.String)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [entry_id, reading_literal],
            [ReadingElement.entry_id, ReadingElement.literal],
        ),
        db.ForeignKeyConstraint(
            [_entry_id, writing_literal],
            [WritingElement.entry_id, WritingElement.literal],
        ),
    )

    def __repr__(self) -> str:
        return (
            "<JMdict_ReadingWriting entry_id={0.entry_id} "
            "reading_literal={0.reading_literal!r} "
            "writing_literal={0.writing_literal!r}>".format(self)
        )


class ReadingSense(db.Model):  # type: ignore
    __tablename__ = "JMdict_ReadingSense"

    entry_id = db.Column("entry_id", db.Integer)
    reading_literal = db.Column("reading_literal", db.String)
    _entry_id = db.Column("_entry_id", db.Integer)
    sense_index = db.Column("sense_index", db.Integer)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [entry_id, reading_literal],
            [ReadingElement.entry_id, ReadingElement.literal],
        ),
        db.ForeignKeyConstraint(
            [_entry_id, sense_index], [Sense.entry_id, Sense.index]
        ),
    )

    def __repr__(self) -> str:
        return (
            "<JMdict_ReadingSense entry_id={0.entry_id} "
            "reading_literal={0.reading_literal!r} "
            "sense_index={0.sense_index}>".format(self)
        )


class WritingSense(db.Model):  # type: ignore
    __tablename__ = "JMdict_WritingSense"

    entry_id = db.Column("entry_id", db.Integer)
    writing_literal = db.Column("writing_literal", db.String)
    _entry_id = db.Column("_entry_id", db.Integer)
    sense_index = db.Column("sense_index", db.Integer)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [entry_id, writing_literal],
            [WritingElement.entry_id, WritingElement.literal],
        ),
        db.ForeignKeyConstraint(
            [_entry_id, sense_index], [Sense.entry_id, Sense.index]
        ),
    )

    def __repr__(self) -> str:
        return (
            "<JMdict_WritingSense entry_id={0.entry_id} "
            "writing_literal={0.writing_literal!r} "
            "sense_index={0.sense_index}>".format(self)
        )
