import pynini

class Slot:
  """
  A slot is analogous to a continuation class in LEXC.
  It is acceptable that a slot for a rule's continuation class has not been declared by the time it is mentioned in a rule - compilation will handle this.
  This function only sets state, rules are processed lazily (i.e. only when compiled). 

  Attributes:
    name: name of the slot
    rules: a list of tuples (upper alphabet symbols, lower alphabet symbols, list of continuation classes, rule weight)
        example: ('ni-', 'ni', [('RefObj', 0.8), (None, 0.3), ('VerbStem', 0.4)], 0.0)
        A rule's destination state is a final state if None is present in the continuation class list
        The rule weight is the weight of the transition from the slot's initial state to this particular rule
        When naming the continuation class, the weight of transitioning to it must be specified too in a tuple
        A StemGuesser can be both a terminal and non-terminal class (as shown in example above)
        Empty list of continuation classes not allowed
        If a cont class is None, then the weight of the accepting state is the weight specified in the tuple
    start (optional): the slot is one of the starting slots (root class in LEXC)
  """
  def __init__(self, name, rules, start=False):
    self.name = name
    self.fst = None
    for (_, _, cont_classes, _) in rules:
      if len(cont_classes) == 0:
        raise Exception('Need to specify at least one continuation class.\
            Use None to indicate if StemGuesser is terminal')
    self.rules = rules # list of rules and their continuation classes
    self.start = start
    self.final_states = []