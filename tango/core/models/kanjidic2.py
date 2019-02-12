from tango.core.bot import Tango

db = Tango.db

# pylint: disable=no-member


class Kanji(db.Model):  # type: ignore
    __tablename__ = "KANJIDIC2_Kanji"

    character = db.Column(db.String, primary_key=True)
    stroke_count = db.Column(db.SmallInteger, nullable=False)
    grade = db.Column(db.SmallInteger)
    old_jlpt_level = db.Column(db.SmallInteger)
    frequency_rank = db.Column(db.SmallInteger)
    nanori = db.Column(db.ARRAY(db.String), nullable=False)

    def __str__(self) -> str:
        return self.character


class KanjiMeaningsReadings(db.Model):  # type: ignore
    __tablename__ = "KANJIDIC2_KanjiMeaningsReadings"

    character = db.Column(None, db.ForeignKey("KANJIDIC2_Kanji.character"))
    meanings = db.Column(db.ARRAY(db.String), nullable=False)
    on_readings = db.Column(db.ARRAY(db.String), nullable=False)
    kun_readings = db.Column(db.ARRAY(db.String), nullable=False)
