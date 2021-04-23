from morphotactics.morphotactics import compile
from morphotactics.slot import Slot
import pytest
import pynini

# helpers
# checks if input_str is in the language of the FSA
def accepts(fsa, input_str):
  return pynini.compose(input_str, fsa).num_states() != 0

# transducers input_str belonging to lower alphabet to string in upper alphabet
def analyze(fst, input_str):
  return pynini.compose(input_str, fst).string()


def test_no_starting_slot_raises_exception():
  with pytest.raises(Exception) as excinfo:
    compile({ Slot('name', []) }) # start=False by default
  assert 'need at least 1 slot to be a starting slot' in str(excinfo.value)

def test_single_starting_class_no_continuation():
  fst = compile({ Slot('name', [('a', 'b', [], 0.0)], start=True) })
  
  assert analyze(fst, 'b') == 'a' # direction of morphological analysis

  # FST does not do morphological generation
  with pytest.raises(Exception):
    analyzed(fst, 'a')

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
    analyzed(fst, 'd')
  with pytest.raises(Exception):
    analyzed(fst, 'f')

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
    analyzed(fst, 'd')
  with pytest.raises(Exception):
    analyzed(fst, 'f')
  with pytest.raises(Exception):
    analyzed(fst, 'h')

def test_multiple_starting_classes_no_continuation():
  fst = compile({
    Slot('class1', [('a', 'b', [], 0.0)], start=True),
    Slot('class2', [('c', 'd', [], 0.0)], start=True)
  })

  assert analyze(fst, 'b') == 'a'
  assert analyze(fst, 'd') == 'c'

  # starting classes do not connect
  with pytest.raises(Exception):
    analyzed(fst, 'bd')
  with pytest.raises(Exception):
    analyzed(fst, 'db')

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
    analyzed(fst, 'f')

  # starting classes do not connect
  with pytest.raises(Exception):
    analyzed(fst, 'bd')
  with pytest.raises(Exception):
    analyzed(fst, 'db')

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
    analyzed(fst, 'df')

  # not a starting class
  with pytest.raises(Exception):
    analyzed(fst, 'f')

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
    analyzed(fst, 'bh')
  # class2 should not transition to class3
  with pytest.raises(Exception):
    analyzed(fst, 'df')

  # must start with a starting class
  with pytest.raises(Exception):
    analyzed(fst, 'f')
  with pytest.raises(Exception):
    analyzed(fst, 'h')

def test_multiple_starting_classes_multiple_continuations():
  fst = compile({
    Slot('class1', [('a', 'b', ['class3'], 0.0)], start=True),
    Slot('class3', [('e', 'f', [], 0.0)]),
    Slot('class2', [('c', 'd', ['class4'], 0.0)], start=True),
    Slot('class4', [('g', 'h', [], 0.0)], start=True)
  })
  assert analyze(fst, 'dh') == 'cg'
