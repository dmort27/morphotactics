import pynini
from typing import List, Tuple

class Slot:
  """
  A slot is analogous to a continuation class in LEXC, which is a group of rules
  that can all serve as the continuation to some other class' rule. 
  It is acceptable that a slot for a rule's continuation class has not been declared by the time it is mentioned in a rule - compilation will handle this.
  This function only sets state, rules are processed lazily (i.e. only when compiled). 

  Attributes
  ----------
    name: str
      name of the slot
    fst: pynini.Fst
      a StemGuesser's compiled FSA
    rules: list[tuple[str, str, list[tuple[str, float]], float]]
      a list of tuples (upper alphabet symbols, lower alphabet symbols, list of continuation classes, rule weight)
        example: ('ni-', 'ni', [('RefObj', 0.8), (None, 0.3), ('VerbStem', 0.4)], 0.0)
        A rule's destination state is a final state if None is present in the continuation class list
        The rule weight is the weight of the transition from the slot's initial state to this particular rule
        When naming the continuation class, the weight of transitioning to it must be specified too in a tuple
        A StemGuesser can be both a terminal and non-terminal class (as shown in example above)
        Empty list of continuation classes not allowed
        If a cont class is None, then the weight of the accepting state is the weight specified in the tuple
    start: bool, optional
      if the slot is one of the starting slots (root class in LEXC)
    final_states: list[int]
      used by the compiler to store a Slot's accepting states in the compiled FST
  """

  def __init__(self, name: str, rules: List[Tuple[str, str, List[Tuple[str, float]], float]], start: bool=False):
    """
    Initializes Slot state
    Does not actually process the rules (i.e. rules are lazily evaluated)

    Args:
      name: string
      rules: list[tuple[str, str, list[tuple[str, float]], float]]
      start: bool
    """
    self.name = name
    self.fst = None
    for (_, _, cont_classes, _) in rules:
      if len(cont_classes) == 0:
        raise Exception('Need to specify at least one continuation class.\
            Use None to indicate if StemGuesser is terminal')
    self.rules = rules # list of rules and their continuation classes
    self.start = start
    self.final_states = []