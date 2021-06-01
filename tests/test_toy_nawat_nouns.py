from morphotactics.morphotactics import compile
from morphotactics.slot import Slot
from morphotactics.stem_guesser import StemGuesser
import pynini
import pywrapfst
from IPython.display import SVG, display


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


# A simple Na:wat noun parser that accepts stems in any form. In reality, Na:wat noun
# stems must have more than one mora, but it's meaningless to add this restriction for
# our purposes.
sg_noun_parser = compile({
    StemGuesser('.+', 'NounStem', [('Absolutive', 0.0)], alphabet=nawat_alphabet, start=True),
    Slot('Absolutive',
         [
             ('-t', 't', [(None, 0.0)], 0.0),
             ('-ti', 'ti', [(None, 0.0)], 0.0),
             ('l-li', 'li', [(None, 0.0)], 0.0)  # This case actually has l in the stem
         ]),
    Slot('Possession',
         [
             ('no-', 'no', [('PossessedNounStem', 0.0)], 0.0),
             ('mo-', 'mo', [('PossessedNounStem', 0.0)], 0.0),
             ('i:-', 'i:', [('PossessedNounStem', 0.0)], 0.0),
             ('to-', 'to', [('PossessedNounStem', 0.0)], 0.0),
         ], start=True),
    StemGuesser('.*', 'PossessedNounStem', [('Inalienable', 0.0), ('Alienable', 0.0)], alphabet=nawat_alphabet),
    Slot('Inalienable', [('-yo', 'yo', [(None, 0.0)], 0.0)]),
    Slot('Alienable', [('-w', 'w', [(None, 0.0)], 0.0), ('-0', '', [(None, 0.0)], 0.0)])
})


# Testing the noun parser. More tests will be added in the near future.
def test_toy_nawat_sg_noun_parser():
    assert analyze(sg_noun_parser, 'o:kichti') == 'o:kich-ti'
