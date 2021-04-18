from morphotactics.slot import Slot

def test_slot_has_single_state():
  slot = Slot('', [])
  assert slot.fst.num_states() == 1

def test_slot_start_false_by_default():
  slot = Slot('', [])
  assert not slot.start

def test_slot_state():
  dummy_class = 'SomeClass'
  dummy_rule = ('', '', [], 0.0)
  slot = Slot('SomeClass', [dummy_rule], start=True)
  assert slot.start
  assert slot.name == dummy_class
  assert len(slot.rules) == 1
  assert slot.rules[0] == dummy_rule