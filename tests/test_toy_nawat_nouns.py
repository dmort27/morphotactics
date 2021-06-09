from morphotactics.morphotactics import compile
from morphotactics.slot import Slot
from morphotactics.stem_guesser import StemGuesser
import pynini
from tests.test_compiler import all_strings_from_chain


# helper function that transduces input_str belonging to lower alphabet to string in upper alphabet
def analyze(fst, input_str):
    return pynini.compose(input_str, fst).string()


# this is for Puebla Na:wat, not for Classical Nahuatl
nawat_alphabet = {
    'C': ['ch', 'h', 'k', 'kw', 'l', 'm', 'n', 'p', 's', 't', 'ts', 'w', 'x', 'y'],
    'V': ['a', 'e', 'i', 'o', 'a:', 'e:', 'i:', 'o:']
}


# A simple Na:wat noun parser that detects nouns with a given stem structure.
# stem is a string containing a simple regex used to construct a StemGuesser.
# This was used to debug how compile handles StemGuessers.
def parser_from_stem(stem):
    return compile({
        StemGuesser(stem, 'NounStem', [('Absolutive', 0.0)], alphabet=nawat_alphabet, start=True),
        Slot('Absolutive',
             [
                 ('-t', 't', [(None, 0.0)], 0.0),
                 ('-ti', 'ti', [(None, 0.0)], 0.0),
                 ('l-li', 'li', [(None, 0.0)], 0.0)  # This case actually has l in the stem
             ]),
    })


def _test_stem(stem):
    assert analyze(parser_from_stem(stem), 'o:kichti') == 'o:kich-ti'


def test_okich():
    _test_stem('o:kich')


def test_dot_plus():
    _test_stem('o:ki.+')


def test_dot_star():
    _test_stem('o:ki.*')


def test_ch_question():
    _test_stem('o:ki(ch)?')


def test_ch_plus():
    _test_stem('o:ki(ch)+')


def test_ch_star():
    _test_stem('o:ki(ch)*')


def test_ch_ch_question():
    _test_stem('o:kich(ch)?')


def test_ch_ch_star():
    _test_stem('o:kich(ch)*')


# A simple Na:wat noun parser for simple (not compound) singular nouns.
sg_noun_parser = compile({
    # Nouns can act as predicates. For example, ni-ta:ka-t means "I am a human."
    # This structure can happen within a sentence too, so even though it doesn't
    # occur all too often, the best way to deal with it is to always include the
    # subject prefix that predicates take.
    Slot('Subject', [
        ('n-', 'n', [('NounStem', 0.0), ('PossessedNoun', 0.0)], 0.0),
        ('ni-', 'ni', [('NounStem', 0.0), ('PossessedNoun', 0.0)], 0.0),
        ('t-', 't', [('NounStem', 0.0), ('PossessedNoun', 0.0)], 0.0),
        ('ti-', 'ti', [('NounStem', 0.0), ('PossessedNoun', 0.0)], 0.0),
        ('0-', '', [('NounStem', 0.0), ('PossessedNoun', 0.0)], 100.0),  # the most common case by far
    ], start=True),
    Slot('NounStem', [
        ('', '', [('NounStemC', 0.0), ('NounStemV', 0.0)], 0.0),
    ]),
    StemGuesser('.*VC', 'NounStemC', [
        ('C-Absolutive', 100.0),
        (None, 0.0)  # This rarer case mostly occurs when ending in -l or -s with more than one mora
    ], alphabet=nawat_alphabet),
    Slot('C-Absolutive', [('-ti', 'ti', [(None, 0.0), ('tsin', 0.0)], 0.0)]),
    StemGuesser('.*V', 'NounStemV', [('V-Absolutive', 0.0), ('tsin', 0.0)], alphabet=nawat_alphabet),
    Slot('V-Absolutive', [
        ('-t', 't', [(None, 0.0)], 0.0),
        ('l-li', 'li', [(None, 0.0)], 0.0)  # Here, l is actually part of the stem, but easier to do this way
    ]),
    Slot('PossessedNoun', [
        ('no-', 'no', [('PossessedNounStem', 0.0)], 0.0),
        ('n-', 'n', [('oPossessedNounStem', 0.0)], 0.0),
        ('mo-', 'mo', [('PossessedNounStem', 0.0)], 0.0),
        ('m-', 'm', [('oPossessedNounStem', 0.0)], 0.0),
        ('to-', 'to', [('PossessedNounStem', 0.0)], 0.0),
        ('t-', 't', [('oPossessedNounStem', 0.0)], 0.0),
        ('i-', 'i', [('PossessedNounStem', 0.0)], 0.0),
        ('i:-', 'i:', [('PossessedNounStem', 0.0)], 0.0),
    ]),
    StemGuesser('.+', 'PossessedNounStem', [
        (None, 0.0), ('InalienablePossession', 0.0), ('tsin', 0.0)
    ], alphabet=nawat_alphabet),
    StemGuesser('o.+', 'oPossessedNounStem', [
        (None, 0.0), ('InalienablePossession', 0.0), ('tsin', 0.0)
    ], alphabet=nawat_alphabet),
    Slot('InalienablePossession', [
        ('-yo', 'yo', [(None, 0.0), ('tsin', 0.0)], 0.0)
    ]),
    Slot('tsin', [
        ('-tsin', 'tsin', [(None, 0.0)], 0.0),
        ('-tsini', 'tsini', [(None, 0.0)], 0.0),
        ('-tsi:n', 'tsi:n', [(None, 0.0)], 0.0),
        ('-tsi:ni', 'tsi:ni', [(None, 0.0)], 0.0),
    ])
})


def parses(fst, s1, s2):
    return any(s == s2 for s, _ in all_strings_from_chain(pynini.compose(s1, fst)))


# Testing the noun parser. More tests will be added in the near future.
def test_toy_nawat_sg_noun_parser():
    # o:kichti - man, male. Standard noun with absolutive.
    assert analyze(sg_noun_parser, 'o:kichti') == '0-o:kich-ti'

    # mowih - a certain type of plant. An abnormal noun since it takes no absolutive.
    assert parses(sg_noun_parser, 'mowih', '0-mowih')

    # pahti - medicine
    assert parses(sg_noun_parser, 'pahti', '0-pah-ti')

    # topah - our medicine
    assert parses(sg_noun_parser, 'topah', '0-to-pah')

    # ixo:chiyotsi:n - its flower (part of a plant)
    assert parses(sg_noun_parser, 'ixo:chiyotsi:n', '0-i-xo:chi-yo-tsi:n')

    # ixo:chi - its/his/her flower (perhaps bought)
    assert parses(sg_noun_parser, 'ixo:chi', '0-i-xo:chi')

    # kowit - tree, wood
    assert parses(sg_noun_parser, 'kowit', '0-kowi-t')

    # tipili - you are a child
    assert parses(sg_noun_parser, 'tipili', 'ti-pil-li')

    # ta:l - earth. Takes no absolutive.
    assert parses(sg_noun_parser, 'ta:l', '0-ta:l')
