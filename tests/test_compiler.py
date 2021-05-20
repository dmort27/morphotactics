from morphotactics.morphotactics import compile
from morphotactics.slot import Slot
from morphotactics.stem_guesser import StemGuesser
import pytest
import pynini
import pywrapfst
import math

# helpers
# checks if input_str is in the language of the FSA
def accepts(fsa, input_str):
  return pynini.compose(input_str, fsa).num_states() != 0

# transducers input_str belonging to lower alphabet to string in upper alphabet
# the string() method only works for deterministic FSTs (i.e. only 1 path exists)
def analyze(fst, input_str):
  return pynini.compose(input_str, fst).string()

def all_strings_from_chain(automaton):
  """Return all strings implied by a non-cyclic automaton.
     Adapted from fststr library by David Mortensen
     Source: https://github.com/dmort27/fststr/blob/master/fststr/fststr.py

  Args:
      chain (Fst): a non-cyclic finite state automaton
  Returns:
      (list): a list of (transduced strings, weight) tuples
  """
  def dfs(graph, path, paths=[]):
    target, _, _ = path[-1]
    if graph.num_arcs(target):
      for arc in graph.arcs(target):
        new_target = arc.nextstate
        new_label = arc.olabel
        new_weight = arc.weight
        new_path = path + [(new_target, new_label, float(new_weight))]
        paths = dfs(graph, new_path, paths)
    else:
      paths += [path]
    return paths
  if automaton.properties(pywrapfst.CYCLIC, True) == pywrapfst.CYCLIC:
    raise Exception('FST is cyclic.')
  start = automaton.start()
  paths = dfs(automaton, [(start, 0, 0.0)])
  strings = []
  for path in paths:
    chars = []
    weight = 0.0
    for (_, k, w) in path:
      if k:
        chars.append(chr(k))
        weight += w
    strings.append((''.join(chars), weight))
  return strings

def correct_transduction_and_weights(fst, input_str, expected_paths):
  """Calculate all possible output paths of fst applied to input_str
     and see if they match in both symbol and weights with expected_paths

  Args:
    expected_paths (list): a list of (string, weight) tuples, sorted by weight
  Returns:
    (boolean): True if output paths matched expected_paths, False otherwise
  """
  output_paths = all_strings_from_chain(pynini.compose(input_str, fst))

  if len(output_paths) != len(expected_paths):
    return False

  output_paths = sorted(output_paths, key=lambda x: x[1])
  expected_paths = sorted(expected_paths, key=lambda x: x[1])

  for ((str1, weight1), (str2, weight2)) in zip(output_paths, expected_paths):
    if str1 != str2 or not math.isclose(weight1, weight2, rel_tol=1e-5):
      return False

  return True

def test_no_starting_slot_raises_exception():
  with pytest.raises(Exception) as excinfo:
    compile({ Slot('name', []) }) # start=False by default
  assert 'need at least 1 slot to be a starting slot' in str(excinfo.value)

def test_single_starting_class_no_continuation():
  fst = compile({ Slot('name', [('a', 'b', [], 0.0)], start=True) })
  
  assert analyze(fst, 'b') == 'a' # direction of morphological analysis

  # FST does not do morphological generation (FST rejects upper alphabet symbols)
  with pytest.raises(Exception):
    analyze(fst, 'a')

def test_single_starting_class_single_continuation():
  fst = compile({
    Slot('class1', [('a', 'b', ['class2'], 0.0)], start=True),
    Slot('class2', [('c', 'd', [], 0.0)]),
  })
  assert analyze(fst, 'bd') == 'ac'

def test_single_starting_class_multiple_continuations():
  fst = compile({
    Slot('class1', [('a', 'b', ['class2', 'class3'], 0.0)], start=True),
    Slot('class2', [('c', 'd', [], 0.0)]),
    Slot('class3', [('e', 'f', [], 0.0)]),
  })
  assert analyze(fst, 'bd') == 'ac'
  assert analyze(fst, 'bf') == 'ae'

  # must start with the starting class
  with pytest.raises(Exception):
    analyze(fst, 'd')
  with pytest.raises(Exception):
    analyze(fst, 'f')

def test_single_starting_class_multiple_classes():
  fst = compile({
    Slot('class1', [('a', 'b', ['class2'], 0.0)], start=True),
    Slot('class2', [('c', 'd', ['class3'], 0.0)]),
    Slot('class3', [('e', 'f', ['class4'], 0.0)]),
    Slot('class4', [('g', 'h', [], 0.0)])
  })
  assert analyze(fst, 'bdfh') == 'aceg'
  
  # must start with the starting class
  with pytest.raises(Exception):
    analyze(fst, 'd')
  with pytest.raises(Exception):
    analyze(fst, 'f')
  with pytest.raises(Exception):
    analyze(fst, 'h')

def test_multiple_starting_classes_no_continuation():
  fst = compile({
    Slot('class1', [('a', 'b', [], 0.0)], start=True),
    Slot('class2', [('c', 'd', [], 0.0)], start=True)
  })

  assert analyze(fst, 'b') == 'a'
  assert analyze(fst, 'd') == 'c'

  # starting classes do not connect
  with pytest.raises(Exception):
    analyze(fst, 'bd')
  with pytest.raises(Exception):
    analyze(fst, 'db')

def test_multiple_starting_classes_same_continuation():
  fst = compile({
    Slot('class1', [('a', 'b', ['class3'], 0.0)], start=True),
    Slot('class2', [('c', 'd', ['class3'], 0.0)], start=True),
    Slot('class3', [('e', 'f', [], 0.0)])
  })
  assert analyze(fst, 'bf') == 'ae'
  assert analyze(fst, 'df') == 'ce'

  # not a starting class
  with pytest.raises(Exception):
    analyze(fst, 'f')

  # starting classes do not connect
  with pytest.raises(Exception):
    analyze(fst, 'bd')
  with pytest.raises(Exception):
    analyze(fst, 'db')

def test_multiple_starting_classes_some_have_continuation_others_do_not():
  fst = compile({
    Slot('class1', [('a', 'b', ['class3'], 0.0)], start=True),
    Slot('class2', [('c', 'd', [], 0.0)], start=True),
    Slot('class3', [('e', 'f', [], 0.0)])
  })
  assert analyze(fst, 'bf') == 'ae'
  assert analyze(fst, 'd') == 'c'

  # class2 has no transitions
  with pytest.raises(Exception):
    analyze(fst, 'df')

  # not a starting class
  with pytest.raises(Exception):
    analyze(fst, 'f')

def test_multiple_starting_classes_different_continuation():
  fst = compile({
    Slot('class1', [('a', 'b', ['class3'], 0.0)], start=True),
    Slot('class2', [('c', 'd', ['class4'], 0.0)], start=True),
    Slot('class3', [('e', 'f', [], 0.0)]),
    Slot('class4', [('g', 'h', [], 0.0)])
  })
  assert analyze(fst, 'bf') == 'ae'
  assert analyze(fst, 'dh') == 'cg'

  # class1 should not transition to class4
  with pytest.raises(Exception):
    analyze(fst, 'bh')
  # class2 should not transition to class3
  with pytest.raises(Exception):
    analyze(fst, 'df')

  # must start with a starting class
  with pytest.raises(Exception):
    analyze(fst, 'f')
  with pytest.raises(Exception):
    analyze(fst, 'h')

def test_multiple_starting_classes_single_rule_per_class_multiple_continuations():
  fst = compile({
    Slot('class1', [('a', 'b', ['class2', 'class3', 'class4'], 0.0)], start=True),
    Slot('class2', [('c', 'd', [], 0.0)]),
    Slot('class3', [('e', 'f', [], 0.0)]),
    Slot('class4', [('g', 'h', [], 0.0)]),
    Slot('class5', [('i', 'j', [], 0.0)], start=True)
  })
  assert analyze(fst, 'bd') == 'ac'
  assert analyze(fst, 'bf') == 'ae'
  assert analyze(fst, 'bh') == 'ag'
  assert analyze(fst, 'j') == 'i'

  # multiple continuation classes do not interfere with each other
  with pytest.raises(Exception):
    analyze(fst, 'bfh') # class3 not joined with class4
  with pytest.raises(Exception):
    analyze(fst, 'bdf') # class2 not joined with class3
  with pytest.raises(Exception):
    analyze(fst, 'bdh') # class2 not joined with class4

  # must start with a starting class
  for non_starting_class_symbol in ['b', 'd', 'f']:
    with pytest.raises(Exception):
      analyze(fst, non_starting_class_symbol)

def test_multiple_rules_single_class_no_continuations():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [], 0.0),
        ('c', 'd', [], 0.0),
        ('e', 'f', [], 0.0),
        ('g', 'h', [], 0.0),
      ], 
      start=True),
  })

  assert analyze(fst, 'b') == 'a'
  assert analyze(fst, 'd') == 'c'
  assert analyze(fst, 'f') == 'e'
  assert analyze(fst, 'h') == 'g'

  # FST does not accept upper alphabet symbols
  for input_symbol in ['a', 'c', 'e', 'g']:
    with pytest.raises(Exception):
      analyze(fst, input_symbol)

  # a slot is a union of rules, not a concatenation
  for not_in_lang in ['bd', 'df', 'fh', 'bh', 'dh', 'bf']:
    with pytest.raises(Exception):
      analyze(fst, not_in_lang)

def test_multiple_rules_single_starting_class_with_multiple_continuations():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', ['class2', 'class3'], 0.0),
        ('c', 'd', ['class4'], 0.0),
        ('e', 'f', [], 0.0),
        ('g', 'h', [], 0.0)
      ],
      start=True),
    Slot('class2', [('i', 'j', [], 0.0)]),
    Slot('class3', [('k', 'l', [], 0.0)]),
    Slot('class4', [('m', 'n', [], 0.0)])
  })

  assert analyze(fst, 'bj') == 'ai'
  assert analyze(fst, 'bl') == 'ak'
  assert analyze(fst, 'dn') == 'cm'
  assert analyze(fst, 'h') == 'g'

  # rules within a slot should not be concatenated with wrong continuation class
  for not_in_lang in ['bf', 'bh', 'bd', 'bn', 'df', 'dh', 'db', 'dj', 'dl']:
    with pytest.raises(Exception):
      analyze(fst, not_in_lang)

def test_multiple_rules_multiple_classes_multiple_continuations():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', ['class2'], 0.0),
        ('c', 'd', [], 0.0),
        ('e', 'f', ['class2', 'class3'], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [], 0.0),
        ('i', 'j', [], 0.0),
        ('k', 'l', ['class3'], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [], 0.0),
        ('o', 'p', [], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [], 0.0),
        ('s', 't', [], 0.0),
      ], start=True)
  })
  
  # class1 alone
  assert analyze(fst, 'd') == 'c'

  # class1 to class2
  assert analyze(fst, 'bh') == 'ag'
  assert analyze(fst, 'bj') == 'ai'
  assert analyze(fst, 'fh') == 'eg'
  assert analyze(fst, 'fj') == 'ei'

  # class1 to class2 to class3
  assert analyze(fst, 'bln') == 'akm'
  assert analyze(fst, 'blp') == 'ako'
  assert analyze(fst, 'fln') == 'ekm'
  assert analyze(fst, 'flp') == 'eko'

  # class1 to class3
  assert analyze(fst, 'fn') == 'em'
  assert analyze(fst, 'fp') == 'eo'

  # class4
  assert analyze(fst, 'r') == 'q'
  assert analyze(fst, 't') == 's'

def test_multiple_rules_multiple_classes_multiple_continuations_with_stem_guesser_starting():
  nahuatl_alphabet = {
    'C': ['m', 'n', 'p', 't', 'k', 'kw', 'h', 'ts', 'tl', 'ch', 's', 'l', 'x', 'j', 'w'], 
    'V': ['a', 'e', 'i', 'o']
  }
  bimoraic_fsa = StemGuesser('.*V.*V', 'VerbStem', ['class2', 'class3'], 
    alphabet=nahuatl_alphabet, start=True)
  
  fst = compile({
    bimoraic_fsa,
    Slot('class2', 
      [
        ('g', 'h', [], 0.0),
        ('i', 'j', [], 0.0),
        ('k', 'l', ['class3'], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [], 0.0),
        ('o', 'p', [], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [], 0.0),
        ('s', 't', [], 0.0),
      ], start=True)
  })
  
  # non-bimoraic stem rejected
  with pytest.raises(Exception):
    analyze(fst, 'pak' + 'h')

  # paki = fictitious verb stem
  # valid verb stem by itself not accepted
  with pytest.raises(Exception):
    analyze(fst, 'paaki')
  
  # class2 and class3
  for upper, lower in [('g', 'h'), ('i', 'j'), ('m', 'n'), ('o', 'p')]:
    assert analyze(fst, 'paaki' + lower) == 'paaki' + upper

  # class2 then class3
  for upper, lower in [('m', 'n'), ('o', 'p')]:
    assert analyze(fst, 'paakil' + lower) == 'paakik' + upper

  # the other starting class (class4) accepted
  assert analyze(fst, 'r') == 'q'
  assert analyze(fst, 't') == 's'

def test_multiple_rules_multiple_classes_multiple_continuations_with_stem_guesser_in_middle():
  nahuatl_alphabet = {
    'C': ['m', 'n', 'p', 't', 'k', 'kw', 'h', 'ts', 'tl', 'ch', 's', 'l', 'x', 'j', 'w'], 
    'V': ['a', 'e', 'i', 'o']
  }
  bimoraic_fsa = StemGuesser('.*V.*V', 'VerbStem', ['class3'], 
    alphabet=nahuatl_alphabet)

  fst = compile({
    Slot('class1',
      [
        ('a', 'b', ['VerbStem'], 0.0),
        ('c', 'd', [], 0.0),
        ('e', 'f', ['VerbStem', 'class3'], 0.0)
      ],
      start=True),
    bimoraic_fsa,
    Slot('class3', 
      [
        ('m', 'n', [], 0.0),
        ('o', 'p', [], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [], 0.0),
        ('s', 't', [], 0.0),
      ], start=True)
  })
  
  # non-bimoraic stem (with valid prefix) rejected
  with pytest.raises(Exception):
    analyze(fst, 'b' + 'pak')
  
  # paki = fictitious verb stem
  # valid verb stem by itself not accepted
  with pytest.raises(Exception):
    analyze(fst, 'paaki')
  
  # class1 alone
  assert analyze(fst, 'd') == 'c'

  # class1 then VerbStem then class3
  assert analyze(fst, 'b' + 'paaki' + 'n') == 'a' + 'paaki' + 'm'
  assert analyze(fst, 'b' + 'paaki' + 'p') == 'a' + 'paaki' + 'o'
  assert analyze(fst, 'f' + 'paaki' + 'n') == 'e' + 'paaki' + 'm'
  assert analyze(fst, 'f' + 'paaki' + 'p') == 'e' + 'paaki' + 'o'

  # class1 then class3
  assert analyze(fst, 'fn') == 'em'
  assert analyze(fst, 'fp') == 'eo'
  
  # the other starting class (class4) accepted
  assert analyze(fst, 'r') == 'q'
  assert analyze(fst, 't') == 's'

def test_multiple_rules_multiple_classes_multiple_continuations_with_stem_guesser_ending():
  nahuatl_alphabet = {
    'C': ['m', 'n', 'p', 't', 'k', 'kw', 'h', 'ts', 'tl', 'ch', 's', 'l', 'x', 'j', 'w'], 
    'V': ['a', 'e', 'i', 'o']
  }
  bimoraic_fsa = StemGuesser('.*V.*V', 'VerbStem', [], 
    alphabet=nahuatl_alphabet)

  fst = compile({
    Slot('class1',
      [
        ('a', 'b', ['class2'], 0.0),
        ('c', 'd', ['VerbStem'], 0.0),
        ('e', 'f', ['class2', 'class3'], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('m', 'n', ['VerbStem'], 0.0),
        ('o', 'p', [], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('q', 'r', [], 0.0),
        ('s', 't', ['VerbStem'], 0.0),
      ]),
    bimoraic_fsa
  })

  # non-bimoraic stem (with valid prefix) rejected
  with pytest.raises(Exception):
    analyze(fst, 'd' + 'pak')

  # class1 to VerbStem
  assert analyze(fst, 'dpaki') == 'cpaki'

  # class1 to class2
  assert analyze(fst, 'bp') == 'ao'
  assert analyze(fst, 'fp') == 'eo'

  # class1 to class3
  assert analyze(fst, 'fr') == 'eq'

  # class1 to class2 to VerbStem
  assert analyze(fst, 'bn' + 'paki') == 'am' + 'paki'
  assert analyze(fst, 'fn' + 'paki') == 'em' + 'paki'

  # class1 to class3 to VerbStem
  assert analyze(fst, 'ft' + 'paki') == 'es' + 'paki'

def test_single_cyclic_class():
  # starting class connects to itself
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', ['class1'], 0.0),
        ('c', 'd', [], 0.0),
        ('e', 'f', [], 0.0)
      ],
      start=True),
  })

  # need another transition to reach accepting state
  with pytest.raises(Exception):
    assert analyze(fst, 'b')

  # repeat transitions
  for i in range(1, 5):
    assert analyze(fst, ('b' * i) + 'd') == ('a' * i) + 'c'
    assert analyze(fst, ('b' * i) + 'f') == ('a' * i) + 'e'

  # not all transitions repeat
  assert analyze(fst, 'd') == 'c'
  assert analyze(fst, 'f') == 'e'

  for repeat in (['d' * i for i in range(2, 6)] + ['f' * i for i in range(2, 6)]):
    with pytest.raises(Exception):
      assert analyze(fst, repeat)
    with pytest.raises(Exception):
      assert analyze(fst, 'b' + repeat)
    with pytest.raises(Exception):
      assert analyze(fst, 'bb' + repeat)
    with pytest.raises(Exception):
      assert analyze(fst, 'bbb' + repeat)

def test_cyclic_class_starting():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', ['class1'], 0.0), # the cyclic rule
        ('c', 'd', [], 0.0),
        ('e', 'f', ['class2', 'class3'], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [], 0.0),
        ('i', 'j', [], 0.0),
        ('k', 'l', ['class3'], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [], 0.0),
        ('o', 'p', [], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [], 0.0),
        ('s', 't', [], 0.0),
      ], start=True)
  })
  
  # cyclic class' non-cyclic (and terminal) rule
  assert analyze(fst, 'd') == 'c'

  # need another transition to reach accepting state
  with pytest.raises(Exception):
    assert analyze(fst, 'b')

  # repeat applications of the cyclic rule
  for i in range(1, 5):
    assert analyze(fst, ('b' * i) + 'd') == ('a' * i) + 'c'

  for i in range(0, 5): # i = 0 means no b's prepended
    prepend_input = 'b' * i
    prepend_output = 'a' * i
    
    # class1 to class2
    assert analyze(fst, prepend_input + 'fh') == prepend_output + 'eg'
    assert analyze(fst, prepend_input + 'fj') == prepend_output + 'ei'

    # class1 to class2 to class3
    assert analyze(fst, prepend_input + 'fln') == prepend_output + 'ekm'
    assert analyze(fst, prepend_input + 'flp') == prepend_output + 'eko'

    # class1 to class3
    assert analyze(fst, prepend_input + 'fn') == prepend_output + 'em'
    assert analyze(fst, prepend_input + 'fp') == prepend_output + 'eo'

    # cannot get to class4 from class1
    if i > 0:
      with pytest.raises(Exception):
        assert analyze(fst, prepend_input + 'r') == prepend_output + 'q'
      with pytest.raises(Exception):
        assert analyze(fst, prepend_input + 't') == prepend_output + 's'
  
  # class4
  assert analyze(fst, 'r') == 'q'
  assert analyze(fst, 't') == 's'

def test_cyclic_class_in_middle():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', ['class2'], 0.0),
        ('c', 'd', [], 0.0),
        ('e', 'f', ['class2', 'class3'], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', ['class2'], 0.0), # cyclic rule
        ('G', 'H', ['class2'], 0.0), # cyclic rule
        ('i', 'j', [], 0.0),
        ('k', 'l', ['class3'], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [], 0.0),
        ('o', 'p', [], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [], 0.0),
        ('s', 't', [], 0.0),
      ], start=True)
  })

  # class1 alone
  assert analyze(fst, 'd') == 'c'

  # class1 to class2, non-cyclic and terminal
  assert analyze(fst, 'bj') == 'ai'
  assert analyze(fst, 'fj') == 'ei'

  # class1 to class2, cyclic
  # need another transition to reach accepting state
  with pytest.raises(Exception):
    assert analyze(fst, 'bh')
  with pytest.raises(Exception):
    assert analyze(fst, 'bH')
  with pytest.raises(Exception):
    assert analyze(fst, 'fH')
  with pytest.raises(Exception):
    assert analyze(fst, 'fH')
  for i in range(1, 5):
    assert analyze(fst, 'b' + ('h' * i) + 'j') == 'a' + ('g' * i) + 'i'
    assert analyze(fst, 'b' + ('H' * i) + 'j') == 'a' + ('G' * i) + 'i'
    assert analyze(fst, 'f' + ('h' * i) + 'j') == 'e' + ('g' * i) + 'i'
    assert analyze(fst, 'f' + ('H' * i) + 'j') == 'e' + ('G' * i) + 'i'

  # class1 to class2 (non-cyclic) to class3
  assert analyze(fst, 'bln') == 'akm'
  assert analyze(fst, 'blp') == 'ako'
  assert analyze(fst, 'fln') == 'ekm'
  assert analyze(fst, 'flp') == 'eko'

  # class1 to class2 (cyclic) to class3
  for i in range(1, 5):
    assert analyze(fst, 'b' + ('h' * i) + 'ln') == 'a' + ('g' * i) + 'km'
    assert analyze(fst, 'b' + ('h' * i) + 'lp') == 'a' + ('g' * i) + 'ko'
    assert analyze(fst, 'b' + ('H' * i) + 'ln') == 'a' + ('G' * i) + 'km'
    assert analyze(fst, 'b' + ('H' * i) + 'lp') == 'a' + ('G' * i) + 'ko'
    assert analyze(fst, 'f' + ('h' * i) + 'ln') == 'e' + ('g' * i) + 'km'
    assert analyze(fst, 'f' + ('h' * i) + 'lp') == 'e' + ('g' * i) + 'ko'
    assert analyze(fst, 'f' + ('H' * i) + 'ln') == 'e' + ('G' * i) + 'km'
    assert analyze(fst, 'f' + ('H' * i) + 'lp') == 'e' + ('G' * i) + 'ko'

  # class1 to class3
  assert analyze(fst, 'fn') == 'em'
  assert analyze(fst, 'fp') == 'eo'

  # class4
  assert analyze(fst, 'r') == 'q'
  assert analyze(fst, 't') == 's'

def test_cyclic_class_ending():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', ['class2'], 0.0),
        ('c', 'd', [], 0.0),
        ('e', 'f', ['class2', 'class3'], 0.0)
      ],
      start=True),
    Slot('class2',
      [
        ('g', 'h', [], 0.0),
        ('i', 'j', [], 0.0),
        ('k', 'l', ['class3'], 0.0),
      ]
    ),
    Slot('class3',
      [
        ('m', 'n', ['class3'], 0.0), # cyclic rule
        ('o', 'p', [], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [], 0.0),
        ('s', 't', [], 0.0),
      ], start=True)
  })

  # class1 alone
  assert analyze(fst, 'd') == 'c'

  # class1 to class2
  assert analyze(fst, 'bh') == 'ag'
  assert analyze(fst, 'bj') == 'ai'
  assert analyze(fst, 'fh') == 'eg'
  assert analyze(fst, 'fj') == 'ei'

  # class1 to class2 to class3 (non-cyclic and terminal)
  assert analyze(fst, 'blp') == 'ako'
  assert analyze(fst, 'flp') == 'eko'

  # class1 to class2 to class3 (cyclic)
  for i in range(1, 5):
    assert analyze(fst, 'bl' + ('n' * i) + 'p') == 'ak' + ('m' * i) + 'o'
    assert analyze(fst, 'fl' + ('n' * i) + 'p') == 'ek' + ('m' * i) + 'o'

  # class1 to class3 (non-cyclic and terminal)
  assert analyze(fst, 'fp') == 'eo'

  # class1 to class3 (cyclic)
  for i in range(1, 5):
    assert analyze(fst, 'f' + ('n' * i) + 'p') == 'e' + ('m' * i) + 'o'

  # class4
  assert analyze(fst, 'r') == 'q'
  assert analyze(fst, 't') == 's'

# class1 -> class2 -> class3 -> class1
def test_cycle_period_at_least_two_cycle_includes_starting_class():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', ['class2'], 0.0),
        ('c', 'd', [], 0.0),
        ('e', 'f', ['class2', 'class3'], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [], 0.0),
        ('i', 'j', [], 0.0),
        ('k', 'l', ['class3'], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', ['class1'], 0.0), # cycle
        ('o', 'p', [], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [], 0.0),
        ('s', 't', [], 0.0),
      ], start=True)
  })

  # the cycle is from class1 to class2 to class3
  # i = 0 means no cycle
  for i in range(5):
    # class1 to class2 to class3 (cyclic) or class1 to class3 (cyclic)
    for cyclic_lower, cyclic_upper in [('bln', 'akm'), ('fln', 'ekm')] + [('fn', 'em')]:
      # class1 alone
      assert analyze(fst, (cyclic_lower * i) + 'd') == (cyclic_upper * i) + 'c'

      # class1 to class2
      assert analyze(fst, (cyclic_lower * i) + 'bh') == (cyclic_upper * i) + 'ag'
      assert analyze(fst, (cyclic_lower * i) + 'bj') == (cyclic_upper * i) + 'ai'
      assert analyze(fst, (cyclic_lower * i) + 'fh') == (cyclic_upper * i) + 'eg'
      assert analyze(fst, (cyclic_lower * i) + 'fj') == (cyclic_upper * i) + 'ei'

      # class1 to class2 to class3 (non-cyclic and terminal)
      assert analyze(fst, (cyclic_lower * i) + 'blp') == (cyclic_upper * i) + 'ako'
      assert analyze(fst, (cyclic_lower * i) + 'flp') == (cyclic_upper * i) + 'eko'

      # class1 to class3 (non-cyclic and terminal)
      assert analyze(fst, (cyclic_lower * i) + 'fp') == (cyclic_upper * i) + 'eo'

  # class4
  assert analyze(fst, 'r') == 'q'
  assert analyze(fst, 't') == 's'

# class1 -> class2 -> class3 -> class4 -> class2
def test_cycle_period_at_least_two_cycle_excludes_starting_class():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', ['class2'], 0.0),
        ('c', 'd', [], 0.0),
        ('e', 'f', ['class2', 'class3'], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [], 0.0),
        ('i', 'j', [], 0.0),
        ('k', 'l', ['class3'], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', ['class4'], 0.0),
        ('o', 'p', [], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [], 0.0),
        ('s', 't', ['class2'], 0.0), # cycle
      ])
  })

  # class1 alone
  assert analyze(fst, 'd') == 'c'

  # class1 to class3 (terminal) - impossible for cycle to go back to class1
  assert analyze(fst, 'fp') == 'eo'

  # class1 to class3 (non-terminal) to class4 (terminal) - impossible for cycle to go back to class1
  assert analyze(fst, 'fnr') == 'emq'

  fst.draw('uwu.dot')

  # the cycle is from class2 to class3 to class4
  # i = 0 means no cycle
  for i in range(5):
    # class2 to class3 to class4 (cyclic), class3 to class4 (cyclic)
    cyclic_lower, cyclic_upper = ('lnt', 'kms')

    # class1 to class2 (terminal)
    assert analyze(fst, 'b' + (cyclic_lower * i) + 'h') == 'a' + (cyclic_upper * i) + 'g'
    assert analyze(fst, 'b' + (cyclic_lower * i) + 'j') == 'a' + (cyclic_upper * i) + 'i'
    assert analyze(fst, 'f' + (cyclic_lower * i) + 'h') == 'e' + (cyclic_upper * i) + 'g'
    assert analyze(fst, 'f' + (cyclic_lower * i) + 'j') == 'e' + (cyclic_upper * i) + 'i'

    # class1 to class2 to class3 (terminal)
    assert analyze(fst, 'b' + (cyclic_lower * i) + 'lp') == 'a' + (cyclic_upper * i) + 'ko'
    assert analyze(fst, 'f' + (cyclic_lower * i) + 'lp') == 'e' + (cyclic_upper * i) + 'ko'

    # class1 to class2 to class3 (non-terminal)
    #   class3 to class4 (terminal)
    assert analyze(fst, 'b' + (cyclic_lower * i) + 'ln' + 'r') == 'a' + (cyclic_upper * i) + 'km' + 'q'
    assert analyze(fst, 'f' + (cyclic_lower * i) + 'ln' + 'r') == 'e' + (cyclic_upper * i) + 'km' + 'q'
