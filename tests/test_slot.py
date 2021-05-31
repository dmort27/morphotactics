from morphotactics.slot import Slot
import pytest

def test_slot_start_false_by_default():
  slot = Slot('', [])
  assert not slot.start

def test_slot_state():
  dummy_class = 'SomeClass'
  dummy_rule = ('', '', [(None, 0.0)], 0.0)
  slot = Slot('SomeClass', [dummy_rule], start=True)
  assert slot.start
  assert slot.name == dummy_class
  assert len(slot.rules) == 1
  assert slot.rules[0] == dummy_rule

def test_empty_cont_class_raises_exception():
  with pytest.raises(Exception) as excinfo:
    slot = Slot('', [('', '', [], 0.0)], start=True)
  assert 'Need to specify at least one continuation class' in str(excinfo.value)