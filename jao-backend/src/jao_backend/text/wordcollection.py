"""
Manage collections of words.
"""

from itertools import chain


class WordCollectionMeta(type):
    def __new__(cls, name, bases, dct):
        # Words, seperated by spaces, in the order they appeared in the class definition.
        word_lists = {
            key: value.split() for key, value in dct.items() if isinstance(value, str)
        }

        all_words = list(chain(*word_lists.values()))

        new_attributes = {"ALL": " ".join(all_words), "ALL_SET": set(all_words)}

        # Add the set of words for each key to the class
        for key, words in word_lists.items():
            new_attributes[f"{key}_SET"] = set(words)

        dct.update(**new_attributes)

        return super().__new__(cls, name, bases, dct)


class WordCollection(metaclass=WordCollectionMeta):
    ALL = ""
    """All words in the collection as a space separated string"""

    ALL_SET = set()
    """All words in the collection as a set"""


class ShortWords(WordCollection):
    ARTICLES = "AN THE"
    PREPOSITIONS = "AS AT BY IN OF ON TO UP"
    CONJUNCTIONS = "IF OR"
    VERBS = "BE IS"
    PRONOUNS = "IT MY"


class GovWords(WordCollection):
    ORGANISATIONS = "EU"
    COUNTRIES = "US"


class CivilServiceGrades(WordCollection):
    GRADES = "AA AO EO HEO SEO G7 G6 SCS"


class GenderedLanguage(WordCollection):
    GENDERED_WORDS = {
        "chairman": "chairperson",
        "fireman": "firefighter",
        "policeman": "police officer",
        "salesman": "salesperson",
        "stewardess": "flight attendant",
        # Add more words as needed
    }
