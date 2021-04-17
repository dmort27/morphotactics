import pynini

class Slot:
  """
  A slot is analogous to a continuation class in LEXC.
  It is acceptable that a slot for a rule's continuation class has not been declared by the time it is mentioned in a rule - compilation will handle this.
  This function only sets state, rules are processed lazily (i.e. only when compiled). 

  Attributes:
    name: name of the slot
    rules: a list of tuples (upper alphabet symbols, lower alphabet symbols, list of continuation classes, weight)
        example: ('ni-', 'ni', ['RefObj', 'VerbStem'], 0.0)
        a rule's destination state is a final state if continuation classes are empty
    start: the slot is one of root slots (root class in LEXC)
  """
  def __init__(name, rules, start=False):
    self.name = name
    # empty FST
    fst = pynini.Fst()
    s = fst.add_state()
    fst.set_start(s)
    fst.set_final(s)
    self.fst = fst
    self.rules = rules # list of rules and their continuation classes
    self.start = start
