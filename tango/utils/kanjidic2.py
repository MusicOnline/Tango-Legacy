from typing import BinaryIO, List, Optional, Tuple, Union
from xml.dom import minidom  # type: ignore

from tango.core.models import Kanji, KanjiMeaningsReadings


def _get_single_data(element: minidom.Element, tag_name: str) -> str:
    return element.getElementsByTagName(tag_name)[0].childNodes[0].data


def _get_optional_int(element: minidom.Element, tag_name: str) -> Optional[int]:
    try:
        return int(_get_single_data(element, tag_name))
    except IndexError:
        return None


def _make_kanji(element: minidom.Element) -> Tuple[Kanji, List[KanjiMeaningsReadings]]:
    character: str = _get_single_data(element, "literal")
    nanori: List[str] = [
        nanori.childNodes[0].data for nanori in element.getElementsByTagName("nanori")
    ]

    kanji: Kanji = Kanji(
        character=character,
        stroke_count=int(_get_single_data(element, "stroke_count")),
        grade=_get_optional_int(element, "grade"),
        old_jlpt_level=_get_optional_int(element, "jlpt"),
        frequency_rank=_get_optional_int(element, "freq"),
        nanori=nanori,
    )

    meanings_readings: List[KanjiMeaningsReadings] = []

    rm_groups: List[minidom.Element] = element.getElementsByTagName("rmgroup")
    for rm_group in rm_groups:
        meanings: List[str] = list(
            meaning.childNodes[0].data
            for meaning in element.getElementsByTagName("meaning")
            if not meaning.hasAttributes()
        )

        on_readings: List[str] = []
        kun_readings: List[str] = []
        for reading in rm_group.getElementsByTagName("reading"):
            if reading.getAttribute("r_type") == "ja_on":
                on_readings.append(reading.childNodes[0].data)
            elif reading.getAttribute("r_type") == "ja_kun":
                kun_readings.append(reading.childNodes[0].data)

        meanings_readings.append(
            KanjiMeaningsReadings(
                character=character,
                meanings=meanings,
                on_readings=on_readings,
                kun_readings=kun_readings,
            )
        )

    return (kanji, meanings_readings)


def parse(
    path: Union[BinaryIO, str]
) -> List[Tuple[Kanji, List[KanjiMeaningsReadings]]]:
    dom: minidom.Document = minidom.parse(path)
    elements: List[minidom.Element] = dom.getElementsByTagName("character")
    return [_make_kanji(e) for e in elements]
