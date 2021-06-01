from morphotactics.morphotactics import compile
from morphotactics.slot import Slot
from morphotactics.stem_guesser import StemGuesser
import pytest
import pynini
import pywrapfst
import math
import random

# helpers
def accepts(fsa, input_str):
  """
  Check if input_str is in the language of the FSA fsa
  Pynini converts input_str into a linear chain automaton and composes it 
  with the FSA. input_str is accepted if the composition has more than 1 state
  
  Args:
    fsa (Fst): a finite-state acceptor
    input_str (string): the string in question
  Returns:
    (boolean): True if input_str is in fsa's language
  """
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
    target, label, weight = path[-1]
    if graph.num_arcs(target):
      for arc in graph.arcs(target):
        new_target = arc.nextstate
        new_label = arc.olabel
        new_weight = arc.weight
        new_path = path + [(new_target, new_label, float(new_weight))]
        paths = dfs(graph, new_path, paths)
    else:
      path = path[:-1]
      path += [(target, label, weight + float(graph.final(target)))]
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
        weight += w # semiring product in the tropical semiring is addition
    strings.append((''.join(chars), weight))
  return strings

def correct_transduction_and_weights(fst, input_str, expected_paths):
  """Calculate all possible output paths of fst applied to input_str
     and see if they match in both symbol and weights with expected_paths

  Args:
    expected_paths (list): a list of (string, weight) tuples
  Returns:
    (boolean): True if output paths matched expected_paths, False otherwise
  """
  output_paths = all_strings_from_chain(pynini.compose(input_str, fst))

  if len(output_paths) != len(expected_paths):
    return False

  output_paths = sorted(output_paths, key=lambda x: x[1])
  expected_paths = sorted(expected_paths, key=lambda x: x[1])

  for ((str1, weight1), (str2, weight2)) in zip(output_paths, expected_paths):
    if str1 != str2:
      print(str1 + ' does not match ' + str2)
      return False
    if not math.isclose(weight1, weight2, abs_tol=1e-5):
      print('path ' + str(str1) + ': ' + str(weight1) + ' does not match ' + str(weight2))
      return False

  return True

def test_no_starting_slot_raises_exception():
  with pytest.raises(Exception) as excinfo:
    compile({ Slot('name', []) }) # start=False by default
  assert 'need at least 1 slot to be a starting slot' in str(excinfo.value)

def test_single_starting_class_no_continuation():
  fst = compile({ Slot('name', [('a', 'b', [(None, 0.0)], 0.0)], start=True) })
  
  assert analyze(fst, 'b') == 'a' # direction of morphological analysis

  # FST does not do morphological generation (FST rejects upper alphabet symbols)
  with pytest.raises(Exception):
    analyze(fst, 'a')

def test_single_starting_class_single_continuation():
  fst = compile({
    Slot('class1', [('a', 'b', [('class2', 0.0)], 0.0)], start=True),
    Slot('class2', [('c', 'd', [(None, 0.0)], 0.0)]),
  })
  assert analyze(fst, 'bd') == 'ac'

def test_single_starting_class_multiple_continuations():
  fst = compile({
    Slot('class1', [('a', 'b', [('class2', 0.0), ('class3', 0.0)], 0.0)], start=True),
    Slot('class2', [('c', 'd', [(None, 0.0)], 0.0)]),
    Slot('class3', [('e', 'f', [(None, 0.0)], 0.0)]),
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
    Slot('class1', [('a', 'b', [('class2', 0.0)], 0.0)], start=True),
    Slot('class2', [('c', 'd', [('class3', 0.0)], 0.0)]),
    Slot('class3', [('e', 'f', [('class4', 0.0)], 0.0)]),
    Slot('class4', [('g', 'h', [(None, 0.0)], 0.0)])
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
    Slot('class1', [('a', 'b', [(None, 0.0)], 0.0)], start=True),
    Slot('class2', [('c', 'd', [(None, 0.0)], 0.0)], start=True)
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
    Slot('class1', [('a', 'b', [('class3', 0.0)], 0.0)], start=True),
    Slot('class2', [('c', 'd', [('class3', 0.0)], 0.0)], start=True),
    Slot('class3', [('e', 'f', [(None, 0.0)], 0.0)])
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
    Slot('class1', [('a', 'b', [('class3', 0.0)], 0.0)], start=True),
    Slot('class2', [('c', 'd', [(None, 0.0)], 0.0)], start=True),
    Slot('class3', [('e', 'f', [(None, 0.0)], 0.0)])
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
    Slot('class1', [('a', 'b', [('class3', 0.0)], 0.0)], start=True),
    Slot('class2', [('c', 'd', [('class4', 0.0)], 0.0)], start=True),
    Slot('class3', [('e', 'f', [(None, 0.0)], 0.0)]),
    Slot('class4', [('g', 'h', [(None, 0.0)], 0.0)])
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
    Slot('class1', [('a', 'b', [('class2', 0.0), ('class3', 0.0), ('class4', 0.0)], 0.0)], start=True),
    Slot('class2', [('c', 'd', [(None, 0.0)], 0.0)]),
    Slot('class3', [('e', 'f', [(None, 0.0)], 0.0)]),
    Slot('class4', [('g', 'h', [(None, 0.0)], 0.0)]),
    Slot('class5', [('i', 'j', [(None, 0.0)], 0.0)], start=True)
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
        ('a', 'b', [(None, 0.0)], 0.0),
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [(None, 0.0)], 0.0),
        ('g', 'h', [(None, 0.0)], 0.0),
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
        ('a', 'b', [('class2', 0.0), ('class3', 0.0)], 0.0),
        ('c', 'd', [('class4', 0.0)], 0.0),
        ('e', 'f', [(None, 0.0)], 0.0),
        ('g', 'h', [(None, 0.0)], 0.0)
      ],
      start=True),
    Slot('class2', [('i', 'j', [(None, 0.0)], 0.0)]),
    Slot('class3', [('k', 'l', [(None, 0.0)], 0.0)]),
    Slot('class4', [('m', 'n', [(None, 0.0)], 0.0)])
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
        ('a', 'b', [('class2', 0.0)], 0.0),
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [('class2', 0.0), ('class3', 0.0)], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [(None, 0.0)], 0.0),
        ('i', 'j', [(None, 0.0)], 0.0),
        ('k', 'l', [('class3', 0.0)], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [(None, 0.0)], 0.0),
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [(None, 0.0)], 0.0),
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
  bimoraic_fsa = StemGuesser('.*V.*V', 'VerbStem', [('class2', 0.0), ('class3', 0.0)], 
    alphabet=nahuatl_alphabet, start=True)
  
  fst = compile({
    bimoraic_fsa,
    Slot('class2', 
      [
        ('g', 'h', [(None, 0.0)], 0.0),
        ('i', 'j', [(None, 0.0)], 0.0),
        ('k', 'l', [('class3', 0.0)], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [(None, 0.0)], 0.0),
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [(None, 0.0)], 0.0),
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
  bimoraic_fsa = StemGuesser('.*V.*V', 'VerbStem', [('class3', 0.0)], 
    alphabet=nahuatl_alphabet)

  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('VerbStem', 0.0)], 0.0),
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [('VerbStem', 0.0), ('class3', 0.0)], 0.0)
      ],
      start=True),
    bimoraic_fsa,
    Slot('class3', 
      [
        ('m', 'n', [(None, 0.0)], 0.0),
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [(None, 0.0)], 0.0),
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
  bimoraic_fsa = StemGuesser('.*V.*V', 'VerbStem', [(None, 0.0)],
    alphabet=nahuatl_alphabet)

  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('class2', 0.0)], 0.0),
        ('c', 'd', [('VerbStem', 0.0)], 0.0),
        ('e', 'f', [('class2', 0.0), ('class3', 0.0)], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('m', 'n', [('VerbStem', 0.0)], 0.0),
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [('VerbStem', 0.0)], 0.0),
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
        ('a', 'b', [('class1', 0.0)], 0.0),
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [(None, 0.0)], 0.0)
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
        ('a', 'b', [('class1', 0.0)], 0.0), # the cyclic rule
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [('class2', 0.0), ('class3', 0.0)], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [(None, 0.0)], 0.0),
        ('i', 'j', [(None, 0.0)], 0.0),
        ('k', 'l', [('class3', 0.0)], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [(None, 0.0)], 0.0),
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [(None, 0.0)], 0.0),
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
        ('a', 'b', [('class2', 0.0)], 0.0),
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [('class2', 0.0), ('class3', 0.0)], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [('class2', 0.0)], 0.0), # cyclic rule
        ('G', 'H', [('class2', 0.0)], 0.0), # cyclic rule
        ('i', 'j', [(None, 0.0)], 0.0),
        ('k', 'l', [('class3', 0.0)], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [(None, 0.0)], 0.0),
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [(None, 0.0)], 0.0),
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
    assert analyze(fst, 'fh')
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
        ('a', 'b', [('class2', 0.0)], 0.0),
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [('class2', 0.0), ('class3', 0.0)], 0.0)
      ],
      start=True),
    Slot('class2',
      [
        ('g', 'h', [(None, 0.0)], 0.0),
        ('i', 'j', [(None, 0.0)], 0.0),
        ('k', 'l', [('class3', 0.0)], 0.0),
      ]
    ),
    Slot('class3',
      [
        ('m', 'n', [('class3', 0.0)], 0.0), # cyclic rule
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [(None, 0.0)], 0.0),
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
        ('a', 'b', [('class2', 0.0)], 0.0),
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [('class2', 0.0), ('class3', 0.0)], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [(None, 0.0)], 0.0),
        ('i', 'j', [(None, 0.0)], 0.0),
        ('k', 'l', [('class3', 0.0)], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [('class1', 0.0)], 0.0), # cycle
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [(None, 0.0)], 0.0),
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
        ('a', 'b', [('class2', 0.0)], 0.0),
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [('class2', 0.0), ('class3', 0.0)], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [(None, 0.0)], 0.0),
        ('i', 'j', [(None, 0.0)], 0.0),
        ('k', 'l', [('class3', 0.0)], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [('class4', 0.0)], 0.0),
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [('class2', 0.0)], 0.0), # cycle
      ])
  })

  # class1 alone
  assert analyze(fst, 'd') == 'c'

  # class1 to class3 (terminal) - impossible for cycle to go back to class1
  assert analyze(fst, 'fp') == 'eo'

  # class1 to class3 (non-terminal) to class4 (terminal) - impossible for cycle to go back to class1
  assert analyze(fst, 'fnr') == 'emq'

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

def test_single_weighted_class():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [(None, 0.0)], 0.5),
        ('c', 'd', [(None, 0.0)], 0.25),
        ('e', 'f', [(None, 0.0)], 0.75),
        ('g', 'h', [(None, 0.0)], 0.1)
      ],
      start=True)
  })

  # shortest distance from the start to final state is 0.1
  assert math.isclose(float(pywrapfst.shortestdistance(fst)[1]), 0.1, abs_tol=1e-5)

  # correct transduction and correct weight
  assert correct_transduction_and_weights(fst, 'b', [('a', 0.5)])
  assert correct_transduction_and_weights(fst, 'd', [('c', 0.25)])
  assert correct_transduction_and_weights(fst, 'f', [('e', 0.75)])
  assert correct_transduction_and_weights(fst, 'h', [('g', 0.1)])

def test_multiple_weighted_classes():
  weights = {}
  for transition in ['ba', 'dc', 'fe', 'hg', 'ji', 'lk', 'nm', 'po', 'rq', 'ts']:
    weights[transition] = random.random()
  
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('class2', 0.0)], weights['ba']),
        ('c', 'd', [(None, 0.0)], weights['dc']),
        ('e', 'f', [('class2', 0.0), ('class3', 0.0)], weights['fe'])
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [(None, 0.0)], weights['hg']),
        ('i', 'j', [(None, 0.0)], weights['ji']),
        ('k', 'l', [('class3', 0.0)], weights['lk']),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [(None, 0.0)], weights['nm']),
        ('o', 'p', [(None, 0.0)], weights['po']),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], weights['rq']),
        ('s', 't', [(None, 0.0)], weights['ts']),
      ], start=True)
  })

  # class1 alone
  assert correct_transduction_and_weights(fst, 'd', [('c', weights['dc'])])

  # class1 to class2
  assert correct_transduction_and_weights(fst, 'bh', [('ag', weights['ba'] + weights['hg'])])
  assert correct_transduction_and_weights(fst, 'bj', [('ai', weights['ba'] + weights['ji'])])
  assert correct_transduction_and_weights(fst, 'fh', [('eg', weights['fe'] + weights['hg'])])
  assert correct_transduction_and_weights(fst, 'fj', [('ei', weights['fe'] + weights['ji'])])

  # class1 to class2 to class3
  assert correct_transduction_and_weights(fst, 'bln', [('akm', weights['ba'] + weights['lk'] + weights['nm'])])
  assert correct_transduction_and_weights(fst, 'blp', [('ako', weights['ba'] + weights['lk'] + weights['po'])])
  assert correct_transduction_and_weights(fst, 'fln', [('ekm', weights['fe'] + weights['lk'] + weights['nm'])])
  assert correct_transduction_and_weights(fst, 'flp', [('eko', weights['fe'] + weights['lk'] + weights['po'])])

  # class1 to class3
  assert correct_transduction_and_weights(fst, 'fn', [('em', weights['fe'] + weights['nm'])])
  assert correct_transduction_and_weights(fst, 'fp', [('eo', weights['fe'] + weights['po'])])

  # class4
  assert correct_transduction_and_weights(fst, 'r', [('q', weights['rq'])])
  assert correct_transduction_and_weights(fst, 't', [('s', weights['ts'])])

def test_three_non_deterministic_classes():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('class2', 0.0)], 1.0),
        ('a', 'b', [('class3', 0.0)], 2.0)
      ],
      start=True),
    Slot('class2',
      [
        ('c', 'd', [(None, 0.0)], 3.0)
      ]),
    Slot('class3',
      [
        ('c', 'd', [(None, 0.0)], 4.0)
      ]),
  })
  assert correct_transduction_and_weights(fst, 'bd', [('ac', 1.0 + 3.0), ('ac', 2.0 + 4.0)])

def test_three_non_deterministic_classes_equal_weights():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('class2', 0.0)], 1.0),
        ('a', 'b', [('class3', 0.0)], 1.0)
      ],
      start=True),
    Slot('class2',
      [
        ('c', 'd', [(None, 0.0)], 2.0)
      ]),
    Slot('class3',
      [
        ('c', 'd', [(None, 0.0)], 2.0)
      ]),
  })
  assert correct_transduction_and_weights(fst, 'bd', [('ac', 1.0 + 2.0), ('ac', 1.0 + 2.0)])

def test_three_non_deterministic_classes_different_outputs():
  fst = compile({
    Slot('class1',
      [
        ('c', 'b', [('class2', 0.0)], 1.0),
        ('a', 'b', [('class3', 0.0)], 2.0)
      ],
      start=True),
    Slot('class2',
      [
        ('d', 'd', [(None, 0.0)], 3.0)
      ]),
    Slot('class3',
      [
        ('f', 'f', [(None, 0.0)], 4.0)
      ]),
  })
  assert correct_transduction_and_weights(fst, 'bd', [('cd', 1.0 + 3.0)])
  assert correct_transduction_and_weights(fst, 'bf', [('af', 2.0 + 4.0)])

def test_three_non_deterministic_classes_different_inputs():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('class2', 0.0)], 1.0),
        ('a', 'd', [('class3', 0.0)], 2.0)
      ],
      start=True),
    Slot('class2',
      [
        ('f', 'f', [(None, 0.0)], 3.0)
      ]),
    Slot('class3',
      [
        ('h', 'h', [(None, 0.0)], 4.0)
      ]),
  })
  assert correct_transduction_and_weights(fst, 'bf', [('af', 1.0 + 3.0)])
  assert correct_transduction_and_weights(fst, 'dh', [('ah', 2.0 + 4.0)])

def test_both_terminal_and_non_terminal_rule():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('class2', 0.0), (None, 0.0)], 1.0),
      ],
      start=True),
    Slot('class2',
      [
        ('c', 'd', [(None, 0.0)], 2.0)
      ]),
  })
  
  assert correct_transduction_and_weights(fst, 'b', [('a', 1.0)])
  assert correct_transduction_and_weights(fst, 'bd', [('ac', 1.0 + 2.0)])

def test_non_deterministic_both_terminal_non_terminal_rule():
  fst = compile({
    Slot('class1',
      [
        ('c', 'b', [('class2', 0.0), (None, 0.0)], 1.0),
        ('a', 'b', [('class3', 0.0), (None, 0.0)], 2.0)
      ],
      start=True),
    Slot('class2',
      [
        ('d', 'd', [(None, 0.0)], 3.0)
      ]),
    Slot('class3',
      [
        ('f', 'f', [(None, 0.0)], 4.0)
      ]),
  })
  
  # non-terminal rules
  assert correct_transduction_and_weights(fst, 'bd', [('cd', 1.0 + 3.0)])
  assert correct_transduction_and_weights(fst, 'bf', [('af', 2.0 + 4.0)])

  # terminal rules
  assert correct_transduction_and_weights(fst, 'b', [('c', 1.0), ('a', 2.0)])

def test_multiple_weighted_classes_both_terminal_non_terminal_rules():
  weights = {}
  for transition in ['ba', 'dc', 'fe', 'hg', 'ji', 'lk', 'nm', 'po', 'rq', 'ts']:
    weights[transition] = random.random()
  
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('class2', 0.0), (None, 0.0)], weights['ba']),
        ('c', 'd', [(None, 0.0)], weights['dc']),
        ('e', 'f', [('class2', 0.0), ('class3', 0.0), (None, 0.0)], weights['fe'])
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [(None, 0.0)], weights['hg']),
        ('i', 'j', [(None, 0.0)], weights['ji']),
        ('k', 'l', [('class3', 0.0), (None, 0.0)], weights['lk']),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [(None, 0.0)], weights['nm']),
        ('o', 'p', [(None, 0.0)], weights['po']),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], weights['rq']),
        ('s', 't', [(None, 0.0)], weights['ts']),
      ], start=True)
  })

  # class1 alone
  assert correct_transduction_and_weights(fst, 'd', [('c', weights['dc'])])
  assert correct_transduction_and_weights(fst, 'b', [('a', weights['ba'])])
  assert correct_transduction_and_weights(fst, 'f', [('e', weights['fe'])])

  # class1 to class2
  assert correct_transduction_and_weights(fst, 'bh', [('ag', weights['ba'] + weights['hg'])])
  assert correct_transduction_and_weights(fst, 'bj', [('ai', weights['ba'] + weights['ji'])])
  assert correct_transduction_and_weights(fst, 'bl', [('ak', weights['ba'] + weights['lk'])])
  assert correct_transduction_and_weights(fst, 'fh', [('eg', weights['fe'] + weights['hg'])])
  assert correct_transduction_and_weights(fst, 'fj', [('ei', weights['fe'] + weights['ji'])])
  assert correct_transduction_and_weights(fst, 'fl', [('ek', weights['fe'] + weights['lk'])])

  # class1 to class2 to class3
  assert correct_transduction_and_weights(fst, 'bln', [('akm', weights['ba'] + weights['lk'] + weights['nm'])])
  assert correct_transduction_and_weights(fst, 'blp', [('ako', weights['ba'] + weights['lk'] + weights['po'])])
  assert correct_transduction_and_weights(fst, 'fln', [('ekm', weights['fe'] + weights['lk'] + weights['nm'])])
  assert correct_transduction_and_weights(fst, 'flp', [('eko', weights['fe'] + weights['lk'] + weights['po'])])

  # class1 to class3
  assert correct_transduction_and_weights(fst, 'fn', [('em', weights['fe'] + weights['nm'])])
  assert correct_transduction_and_weights(fst, 'fp', [('eo', weights['fe'] + weights['po'])])

  # class4
  assert correct_transduction_and_weights(fst, 'r', [('q', weights['rq'])])
  assert correct_transduction_and_weights(fst, 't', [('s', weights['ts'])])

def test_stem_guesser_both_terminal_non_terminal():
  nahuatl_alphabet = {
    'C': ['m', 'n', 'p', 't', 'k', 'kw', 'h', 'ts', 'tl', 'ch', 's', 'l', 'x', 'j', 'w'], 
    'V': ['a', 'e', 'i', 'o']
  }
  bimoraic_fsa = StemGuesser('.*V.*V', 'VerbStem', [('class3', 0.0), (None, 0.0)], 
    alphabet=nahuatl_alphabet)

  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('VerbStem', 0.0), (None, 0.0)], 0.0),
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [('VerbStem', 0.0), ('class3', 0.0), (None, 0.0)], 0.0)
      ],
      start=True),
    bimoraic_fsa,
    Slot('class3', 
      [
        ('m', 'n', [(None, 0.0)], 0.0),
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [(None, 0.0)], 0.0),
      ], start=True)
  })
  
  # non-bimoraic stem (with valid prefix) rejected
  with pytest.raises(Exception):
    analyze(fst, 'b' + 'pak')
  
  # paki = fictitious verb stem
  # valid verb stem by itself not accepted (need a prefix in this case)
  with pytest.raises(Exception):
    analyze(fst, 'paaki')
  
  # class1 alone (terminal)
  assert analyze(fst, 'd') == 'c'
  assert analyze(fst, 'f') == 'e'

  # class1 then VerbStem (non-terminal) then class3
  assert analyze(fst, 'b' + 'paaki' + 'n') == 'a' + 'paaki' + 'm'
  assert analyze(fst, 'b' + 'paaki' + 'p') == 'a' + 'paaki' + 'o'
  assert analyze(fst, 'f' + 'paaki' + 'n') == 'e' + 'paaki' + 'm'
  assert analyze(fst, 'f' + 'paaki' + 'p') == 'e' + 'paaki' + 'o'

  # class1 then VerbStem (terminal)
  assert analyze(fst, 'b' + 'paaki') == 'a' + 'paaki'
  assert analyze(fst, 'b' + 'paaki') == 'a' + 'paaki'
  assert analyze(fst, 'f' + 'paaki') == 'e' + 'paaki'
  assert analyze(fst, 'f' + 'paaki') == 'e' + 'paaki'

  # class1 then class3
  assert analyze(fst, 'fn') == 'em'
  assert analyze(fst, 'fp') == 'eo'
  
  # the other starting class (class4) accepted
  assert analyze(fst, 'r') == 'q'
  assert analyze(fst, 't') == 's'

def test_cycle_period_one_both_terminal_non_terminal_rules():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('class2', 0.0), (None, 0.0)], 0.0),
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [('class2', 0.0), ('class3', 0.0), (None, 0.0)], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [('class2', 0.0), (None, 0.0)], 0.0), # cyclic rule
        ('G', 'H', [('class2', 0.0), (None, 0.0)], 0.0), # cyclic rule
        ('i', 'j', [(None, 0.0)], 0.0),
        ('k', 'l', [('class3', 0.0), (None, 0.0)], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [(None, 0.0)], 0.0),
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [(None, 0.0)], 0.0),
      ], start=True)
  })

  # class1 alone
  assert analyze(fst, 'b') == 'a'
  assert analyze(fst, 'd') == 'c'
  assert analyze(fst, 'f') == 'e'

  # class1 to class2, non-cyclic and terminal
  assert analyze(fst, 'bj') == 'ai'
  assert analyze(fst, 'fj') == 'ei'

  for i in range(5):
    # class1 to class2, cyclic to class2 (terminal)
    # i = 0 means no cycle - class1 to class2 (terminal)
    assert analyze(fst, 'b' + ('h' * i)) == 'a' + ('g' * i)
    assert analyze(fst, 'b' + ('H' * i)) == 'a' + ('G' * i)
    assert analyze(fst, 'f' + ('h' * i)) == 'e' + ('g' * i)
    assert analyze(fst, 'f' + ('H' * i)) == 'e' + ('G' * i)
    assert analyze(fst, 'b' + ('h' * i) + 'j') == 'a' + ('g' * i) + 'i'
    assert analyze(fst, 'b' + ('H' * i) + 'j') == 'a' + ('G' * i) + 'i'
    assert analyze(fst, 'f' + ('h' * i) + 'j') == 'e' + ('g' * i) + 'i'
    assert analyze(fst, 'f' + ('H' * i) + 'j') == 'e' + ('G' * i) + 'i'
    assert analyze(fst, 'b' + ('h' * i) + 'l') == 'a' + ('g' * i) + 'k'
    assert analyze(fst, 'b' + ('H' * i) + 'l') == 'a' + ('G' * i) + 'k'
    assert analyze(fst, 'f' + ('h' * i) + 'l') == 'e' + ('g' * i) + 'k'
    assert analyze(fst, 'f' + ('H' * i) + 'l') == 'e' + ('G' * i) + 'k'

    # class1 to class2 (cyclic) to class3
    # i = 0 means no cycle = class1 to class2 (non-cyclic) to class3
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

# class1 -> class2 -> class3 -> class4 -> class2
def test_cycle_period_two_both_terminal_non_terminal_rules():
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('class2', 0.0), (None, 0.0)], 0.0),
        ('c', 'd', [(None, 0.0)], 0.0),
        ('e', 'f', [('class2', 0.0), ('class3', 0.0), (None, 0.0)], 0.0)
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [(None, 0.0)], 0.0),
        ('i', 'j', [(None, 0.0)], 0.0),
        ('k', 'l', [('class3', 0.0), (None, 0.0)], 0.0),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [('class4', 0.0), (None, 0.0)], 0.0),
        ('o', 'p', [(None, 0.0)], 0.0),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 0.0)], 0.0),
        ('s', 't', [('class2', 0.0), (None, 0.0)], 0.0), # cycle
      ])
  })

  # class1 alone
  assert analyze(fst, 'b') == 'a'
  assert analyze(fst, 'd') == 'c'
  assert analyze(fst, 'f') == 'e'

  # class1 to class3 (terminal) - impossible for cycle to go back to class1
  assert analyze(fst, 'fp') == 'eo'

  # class1 to class3 (non-terminal) to class4 (terminal) - impossible for cycle to go back to class1
  assert analyze(fst, 'fnr') == 'emq'
  assert analyze(fst, 'fnt') == 'ems'

  # the cycle is from class2 to class3 to class4
  # i = 0 means no cycle
  for i in range(5):
    # class2 to class3 to class4 (cyclic), class3 to class4 (cyclic)
    cyclic_lower, cyclic_upper = ('lnt', 'kms')

    # class1 to class2 to class3 to class4 (terminal)
    assert analyze(fst, 'b' + (cyclic_lower * i)) == 'a' + (cyclic_upper * i)
    assert analyze(fst, 'f' + (cyclic_lower * i)) == 'e' + (cyclic_upper * i)

    # class1 to class2 (terminal)
    assert analyze(fst, 'b' + (cyclic_lower * i) + 'h') == 'a' + (cyclic_upper * i) + 'g'
    assert analyze(fst, 'b' + (cyclic_lower * i) + 'j') == 'a' + (cyclic_upper * i) + 'i'
    assert analyze(fst, 'b' + (cyclic_lower * i) + 'l') == 'a' + (cyclic_upper * i) + 'k'
    assert analyze(fst, 'f' + (cyclic_lower * i) + 'h') == 'e' + (cyclic_upper * i) + 'g'
    assert analyze(fst, 'f' + (cyclic_lower * i) + 'j') == 'e' + (cyclic_upper * i) + 'i'
    assert analyze(fst, 'f' + (cyclic_lower * i) + 'l') == 'e' + (cyclic_upper * i) + 'k'
    
    # class1 to class2 to class3 (terminal)
    assert analyze(fst, 'b' + (cyclic_lower * i) + 'lp') == 'a' + (cyclic_upper * i) + 'ko'
    assert analyze(fst, 'f' + (cyclic_lower * i) + 'lp') == 'e' + (cyclic_upper * i) + 'ko'
    assert analyze(fst, 'b' + (cyclic_lower * i) + 'ln') == 'a' + (cyclic_upper * i) + 'km'
    assert analyze(fst, 'f' + (cyclic_lower * i) + 'ln') == 'e' + (cyclic_upper * i) + 'km'

    # class1 to class2 to class3 (non-terminal)
    #   class3 to class4 (terminal)
    assert analyze(fst, 'b' + (cyclic_lower * i) + 'ln' + 'r') == 'a' + (cyclic_upper * i) + 'km' + 'q'
    assert analyze(fst, 'f' + (cyclic_lower * i) + 'ln' + 'r') == 'e' + (cyclic_upper * i) + 'km' + 'q'
    assert analyze(fst, 'b' + (cyclic_lower * i) + 'ln' + 't') == 'a' + (cyclic_upper * i) + 'km' + 's'
    assert analyze(fst, 'f' + (cyclic_lower * i) + 'ln' + 't') == 'e' + (cyclic_upper * i) + 'km' + 's'

def test_weight_continuation_classes():
  weights = {}
  for transition in ['ba', 'dc', 'fe', 'hg', 'ji', 'lk', 'nm', 'po', 'rq', 'ts']:
    weights[transition] = random.random()
  
  fst = compile({
    Slot('class1',
      [
        ('a', 'b', [('class2', 1.0), (None, 2.0)], weights['ba']),
        ('c', 'd', [(None, 3.0)], weights['dc']),
        ('e', 'f', [('class2', 4.0), ('class3', 5.0), (None, 6.0)], weights['fe'])
      ],
      start=True),
    Slot('class2', 
      [
        ('g', 'h', [(None, 7.0)], weights['hg']),
        ('i', 'j', [(None, 8.0)], weights['ji']),
        ('k', 'l', [('class3', 9.0), (None, 10.0)], weights['lk']),
      ]
    ),
    Slot('class3', 
      [
        ('m', 'n', [(None, 11.0)], weights['nm']),
        ('o', 'p', [(None, 12.0)], weights['po']),
      ]
    ),
    Slot('class4', 
      [
        ('q', 'r', [(None, 13.0)], weights['rq']),
        ('s', 't', [(None, 14.0)], weights['ts']),
      ], start=True)
  })

  # class1 alone
  assert correct_transduction_and_weights(fst, 'd', [('c', weights['dc'] + 3.0)])
  assert correct_transduction_and_weights(fst, 'b', [('a', weights['ba'] + 2.0)])
  assert correct_transduction_and_weights(fst, 'f', [('e', weights['fe'] + 6.0)])

  # class1 to class2
  assert correct_transduction_and_weights(fst, 'bh', [('ag', weights['ba'] + 1.0 + weights['hg'] + 7.0)])
  assert correct_transduction_and_weights(fst, 'bj', [('ai', weights['ba'] + 1.0 + weights['ji'] + 8.0)])
  assert correct_transduction_and_weights(fst, 'bl', [('ak', weights['ba'] + 1.0 + weights['lk'] + 10.0)])
  assert correct_transduction_and_weights(fst, 'fh', [('eg', weights['fe'] + 4.0 + weights['hg'] + 7.0)])
  assert correct_transduction_and_weights(fst, 'fj', [('ei', weights['fe'] + 4.0 + weights['ji'] + 8.0)])
  assert correct_transduction_and_weights(fst, 'fl', [('ek', weights['fe'] + 4.0 + weights['lk'] + 10.0)])

  # class1 to class2 to class3
  assert correct_transduction_and_weights(fst, 'bln', [('akm', weights['ba'] + 1.0 + weights['lk'] + 9.0 + weights['nm'] + 11.0)])
  assert correct_transduction_and_weights(fst, 'blp', [('ako', weights['ba'] + 1.0 + weights['lk'] + 9.0 + weights['po'] + 12.0)])
  assert correct_transduction_and_weights(fst, 'fln', [('ekm', weights['fe'] + 4.0 + weights['lk'] + 9.0 + weights['nm'] + 11.0)])
  assert correct_transduction_and_weights(fst, 'flp', [('eko', weights['fe'] + 4.0 + weights['lk'] + 9.0 + weights['po'] + 12.0)])

  # class1 to class3
  assert correct_transduction_and_weights(fst, 'fn', [('em', weights['fe'] + 5.0 + weights['nm'] + 11.0)])
  assert correct_transduction_and_weights(fst, 'fp', [('eo', weights['fe'] + 5.0 + weights['po'] + 12.0)])

  # class4
  assert correct_transduction_and_weights(fst, 'r', [('q', weights['rq'] + 13.0)])
  assert correct_transduction_and_weights(fst, 't', [('s', weights['ts'] + 14.0)])
