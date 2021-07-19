import pynini

from morphotactics.morphotactics import compile
from morphotactics.slot import Slot
from morphotactics.stem_guesser import StemGuesser
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
    StemGuesser('.*C', 'NounStemC', [
        ('C-Absolutive', 100.0),
        (None, 0.0),  # This rarer case mostly occurs when ending in -l or -s with more than one mora
        ('tsin', 100.0),
        ('Locative', 0.0)
    ], alphabet=nawat_alphabet),
    Slot('C-Absolutive', [('-ti', 'ti', [(None, 0.0)], 0.0)]),
    StemGuesser('.*V', 'NounStemV', [
        ('V-Absolutive', 100.0),
        ('tsin', 100.0),
        ('Locative', 0.0)
    ], alphabet=nawat_alphabet),
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
        ('in-', 'in', [('PossessedNounStem', 0.0)], 0.0),
        ('i:n-', 'i:n', [('PossessedNounStem', 0.0)], 0.0),
    ]),
    StemGuesser('.+', 'PossessedNounStem', [
        ('Possession', 0.0), ('InalienablePossession', 0.0), ('tsin', 0.0), ('Locative', 0.0)
    ], alphabet=nawat_alphabet),
    StemGuesser('o.+', 'oPossessedNounStem', [
        ('Possession', 0.0), ('InalienablePossession', 0.0), ('tsin', 0.0), ('Locative', 0.0)
    ], alphabet=nawat_alphabet),
    Slot('Possession', [
        ('-w', 'w', [(None, 0.0), ('tsin', 0.0)], 0.0),
        ('', '', [(None, 0.0), ('tsin', 0.0)], 0.0)
    ]),
    Slot('InalienablePossession', [
        ('-yo', 'yo', [(None, 0.0), ('tsin', 0.0)], 0.0)
    ]),
    Slot('tsin', [
        ('-tsin', 'tsin', [(None, 0.0)], 100.0),
        ('-tsini', 'tsini', [(None, 0.0)], 100.0),
        ('-tsi:n', 'tsi:n', [(None, 0.0)], 100.0),
        ('-tsi:ni', 'tsi:ni', [(None, 0.0)], 100.0),
        ('-tsín', 'tsín', [(None, 0.0)], 100.0),
        ('-tsíni', 'tsíni', [(None, 0.0)], 100.0),
        ('-tsí:n', 'tsí:n', [(None, 0.0)], 100.0),
        ('-tsí:ni', 'tsí:ni', [(None, 0.0)], 100.0),
    ]),
    Slot('Locative', [
        ('-ko', 'ko', [(None, 0.0)], 100.0),
        ('-pan', 'pan', [(None, 0.0)], 100.0),
        ('-ti-pan', 'tipan', [(None, 0.0)], 100.0),
        ('-tan-pa', 'tampa', [(None, 0.0)], 100.0),
        ('-nakas-tan', 'nakastan', [(None, 0.0)], 100.0),
        ('-tsi:n-tan', 'tsi:ntan', [(None, 0.0)], 100.0),
        ('-i:x-ko', 'i:xko', [(None, 0.0)], 100.0),
        ('-tikpak', 'tikpak', [(None, 0.0)], 100.0),
        ('-tah', 'tah', [(None, 0.0)], 100.0),
        ('-ti-tan', 'titan', [(None, 0.0)], 100.0),
        ('-yá:n', 'yá:n', [(None, 0.0)], 100.0),
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

    # imitsko - by its feet
    assert parses(sg_noun_parser, 'imitsko', '0-i-mits-ko')

    # nosiwa:w - my wife (my woman)
    assert parses(sg_noun_parser, 'nosiwa:w', '0-no-siwa:-w')


# Strictly speaking, FSTs cannot deal with reduplication properly.
# However, I take advantage of the small alphabet to handle all
# possible cases of reduplcation.

# Start with the case of no reduplication
long_vowel_reduplication = [('', '', [('NounStem', 0.0)], 0.0)]
# For each CV combination, add the reduplicated variant
for c in nawat_alphabet['C']:
    for v in nawat_alphabet['V']:
        syl = c + v
        if len(v) == 1:
            v += ':'
        dup = c + v
        long_vowel_reduplication.append((dup + '-' + syl, dup + syl, [('NounStem', 0.0)], 0.0))

# A simple Na:wat noun parser for simple (not compound) plural nouns.
# Note that only animate nouns and a few special inanimate nouns have plurals.
# Most inanimate nouns always use the singular.
pl_noun_parser = compile({
    # Nouns can act as predicates. For example, ti-ta:ka-h means "We are humans."
    # This structure can happen within a sentence too, so even though it doesn't
    # occur all too often, the best way to deal with it is to always include the
    # subject prefix that predicates take.
    Slot('Subject', [
        ('t-', 't', [('PluralNoun', 0.0), ('PossessedPluralNoun', 0.0)], 0.0),  # before a vowel
        ('ti-', 'ti', [('PluralNoun', 0.0), ('PossessedPluralNoun', 0.0)], 0.0),  # before a consonant
        ('am-', 'am', [('PluralNoun', 0.0), ('PossessedPluralNoun', 0.0)], 0.0),  # before p, m, or a vowel
        ('am-', 'an', [('PluralNoun', 0.0), ('PossessedPluralNoun', 0.0)], 0.0),  # before other consonants
        ('0-', '', [('PluralNoun', 0.0), ('PossessedPluralNoun', 0.0)], 100.0),  # the most common case by far
    ], start=True),
    Slot('PluralNoun', long_vowel_reduplication),
    Slot('NounStem', [
        ('', '', [('NounStemC', 0.0), ('NounStemV', 0.0)], 0.0),
    ]),
    StemGuesser('.*C', 'NounStemC', [
        ('meh', 100.0),
        ('tin', 100.0),
        ('tsitsin', 100.0),
        ('Locative', 0.0)  # I'm not too sure if this locative case can actually happen, but I'll leave it here
    ], alphabet=nawat_alphabet),
    StemGuesser('.*V', 'NounStemV', [
        ('h', 100.0),
        ('meh', 100.0),
        ('tsitsin', 100.0),
        ('Locative', 0.0)
    ], alphabet=nawat_alphabet),
    Slot('meh', [('-meh', 'meh', [(None, 0.0)], 0.0)]),
    Slot('tin', [('-tin', 'tin', [(None, 0.0)], 0.0)]),
    Slot('h', [('-h', 'h', [(None, 0.0)], 0.0)]),
    Slot('PossessedPluralNoun', [
        ('no-', 'no', [('PossessedPluralNounStem', 0.0)], 0.0),
        ('n-', 'n', [('oPossessedPluralNounStem', 0.0)], 0.0),
        ('mo-', 'mo', [('PossessedPluralNounStem', 0.0)], 0.0),
        ('m-', 'm', [('oPossessedPluralNounStem', 0.0)], 0.0),
        ('to-', 'to', [('PossessedPluralNounStem', 0.0)], 0.0),
        ('t-', 't', [('oPossessedPluralNounStem', 0.0)], 0.0),
        ('i-', 'i', [('PossessedPluralNounStem', 0.0)], 0.0),
        ('i:-', 'i:', [('PossessedPluralNounStem', 0.0)], 0.0),
        ('in-', 'in', [('PossessedPluralNounStem', 0.0)], 0.0),
        ('i:n-', 'i:n', [('PossessedPluralNounStem', 0.0)], 0.0),
    ]),
    StemGuesser('.+', 'PossessedPluralNounStem', [
        ('Possession', 0.0), ('tsitsin', 0.0), ('Locative', 0.0)
    ], alphabet=nawat_alphabet),
    StemGuesser('o.+', 'oPossessedPluralNounStem', [
        ('Possession', 0.0), ('tsitsin', 0.0), ('Locative', 0.0)
    ], alphabet=nawat_alphabet),
    Slot('Possession', [
        ('-wa:n', 'wa:n', [(None, 0.0), ('tsitsin', 0.0)], 0.0)
    ]),
    # Supposedly, the wa:n can also come after the tsitsi:n, but I have yet to see this
    Slot('tsitsin', [
        ('-tsi-tsin', 'tsitsin', [(None, 0.0)], 100.0),
        ('-tsi-tsini', 'tsitsini', [(None, 0.0)], 100.0),
        ('-tsi-tsi:n', 'tsitsi:n', [(None, 0.0)], 100.0),
        ('-tsi-tsi:ni', 'tsitsi:ni', [(None, 0.0)], 100.0),
        ('-tsi-tsín', 'tsitsín', [(None, 0.0)], 100.0),
        ('-tsi-tsíni', 'tsitsíni', [(None, 0.0)], 100.0),
        ('-tsi-tsí:n', 'tsitsí:n', [(None, 0.0)], 100.0),
        ('-tsi-tsí:ni', 'tsitsí:ni', [(None, 0.0)], 100.0),
    ]),
    Slot('Locative', [
        ('-ko', 'ko', [(None, 0.0)], 100.0),
        ('-pan', 'pan', [(None, 0.0)], 100.0),
        ('-ti-pan', 'tipan', [(None, 0.0)], 100.0),
        ('-tan-pa', 'tampa', [(None, 0.0)], 100.0),
        ('-nakas-tan', 'nakastan', [(None, 0.0)], 100.0),
        ('-tsi:n-tan', 'tsi:ntan', [(None, 0.0)], 100.0),
        ('-i:x-ko', 'i:xko', [(None, 0.0)], 100.0),
        ('-tikpak', 'tikpak', [(None, 0.0)], 100.0),
        ('-tah', 'tah', [(None, 0.0)], 100.0),
        ('-ti-tan', 'titan', [(None, 0.0)], 100.0),
        ('-yá:n', 'yá:n', [(None, 0.0)], 100.0),
    ])
})


def test_toy_nawat_pl_noun_parser():
    # ta:kah - the humans
    assert parses(pl_noun_parser, 'ta:kah', '0-ta:ka-h')

    # ko:koyoh - the coyotes
    assert parses(pl_noun_parser, 'ko:koyoh', '0-ko:-koyo-h')

    # siwa:h - the women
    assert parses(pl_noun_parser, 'siwa:h', '0-siwa:-h')

    # tichichimeh - We are dogs.
    assert parses(pl_noun_parser, 'tichichimeh', 'ti-chichi-meh')

    # nopilwa:n - my children
    assert parses(pl_noun_parser, 'nopilwa:n', '0-no-pil-wa:n')

    # okichtin - the men
    assert parses(pl_noun_parser, 'okichtin', '0-okich-tin')

    # tsikitsitsi:n - the small ones
    assert parses(pl_noun_parser, 'tsikitsitsi:n', '0-tsiki-tsi-tsi:n')

    # tokniwwa:n - our brothers
    # The w is usually degeminated, I'm assuming there's prior code that recognizes this special case
    assert parses(pl_noun_parser, 'tokniwwa:n', '0-to-kniw-wa:n')

    # okwilimeh - the wild animals
    assert parses(pl_noun_parser, 'okwilimeh', '0-okwili-meh')

    # pi:piltin - the children
    assert parses(pl_noun_parser, 'pi:piltin', '0-pi:-pil-tin')
