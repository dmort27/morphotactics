import pynini
from morphotactics.slot import Slot

class StemGuesser(Slot):
  """
  A StemGuesser is a special type of Slot that guesses stems
  Converts a limited PCRE regex (scope, quantification) to an OpenFst FST.
  Substitutes phoneme classes with symbols.
  Assumes long vowels have been expanded. 
  Args:
    min_word_constraint: a minimal word constraint expressed as a limited regular expression of phone classes
    
    (same as that of Slot)
    name: name of the StemGuesser Slot
    cont_classes: list of continuation classes
        example: ['PluralSuffix']
        The StemGuesser's destination state is a final state if continuation classes are empty
    alphabet (optional): dictionary mapping phone classes to list of symbols; if sigma (.) is used in the regex, alphabet is required
    start (optional): the slot is one of root slots (root class in LEXC)
  """
  def __init__(self, min_word_constraint, name, cont_classes, alphabet={}, start=False):
    # phone classes could overlap so phones to set first
    symbols = {symb for symbol_class in alphabet.values() for symb in symbol_class}

    stack = [] # check for matching parens
    fst = None
    fst_stack = [] # to be used in union or scope mode
    regex = min_word_constraint

    # () means scope / grouping - concatenation
    # [] means match anything inside - union
    # . means match any character in the alphabet (not including epsilon) - sigma
    # quantifiers: ?, *, +
    for i in range(len(regex)):
      if regex[i] == '[':
        stack.append(regex[i])
        fst_stack.append(('union', pynini.accep('')))
      elif regex[i] == '(':
        stack.append(regex[i])
        fst_stack.append(('scope', pynini.accep('')))
      elif regex[i] == ')':
        if stack.pop(-1) != '(':
          raise Exception('Unmatched parentheses')
        fst_stack[-1] = ('processed', fst_stack[-1][1])
      elif regex[i] == ']':
        if stack.pop(-1) != '[':
          raise Exception('Unmatched brackets')
        fst_stack[-1] = ('processed', fst_stack[-1][1])
      elif fst_stack and fst_stack[-1][0] in ['scope', 'union']:
        if fst_stack[-1][0] == 'scope':
          # concatenate only the current chars
          if regex[i] not in alphabet:
            fst_stack[-1][1].concat(regex[i])
          else:
            fst_stack[-1][1].concat(pynini.union(*alphabet[regex[i]]))
        elif fst_stack[-1][0] == 'union':
          if fst_stack[-1][1].num_states() == 1:
            # make sure we don't union with empty string
            if regex[i] not in alphabet:
              fst_stack[-1][1].concat(regex[i])
            else:
              fst_stack[-1][1].concat(pynini.union(*alphabet[regex[i]]))
          else:
            # union only the current chars within the matching parens
            if regex[i] not in alphabet:
              fst_stack[-1][1].union(regex[i])
            else:
              fst_stack[-1][1].union(pynini.union(*alphabet[regex[i]]))
      # sigma
      elif regex[i] == '.':
        if not alphabet:
          raise Exception('Alphabet required if regex includes sigma')
        # make copy each time to avoid state issues
        sigma = pynini.union(*list(symbols))
        fst_stack.append(('sigma', sigma))
      # quantification - perform closure on last FST
      elif regex[i] == '?':
        if i == 0:
          raise Exception('Empty quantification')
        fst_stack[-1] = (fst_stack[-1][0], pynini.closure(fst_stack[-1][1], 0, 1))
      elif regex[i] == '*':
        if i == 0:
          raise Exception('Empty quantification')

        fst_stack[-1] = (fst_stack[-1][0], pynini.closure(fst_stack[-1][1]))
        
        # if the entire regex is a Kleene closure or previous character is sigma, accept empty string too
        if (len(fst_stack) == 1 and i == len(regex) - 1) or (fst_stack and fst_stack[-1][0] == 'sigma'):
          fst_stack[-1] = (fst_stack[-1][0], pynini.union(fst_stack[-1][1], ''))
      elif regex[i] == '+':
        if i == 0:
          raise Exception('Empty quantification')
        fst_stack[-1] = (fst_stack[-1][0], pynini.closure(fst_stack[-1][1], 1))
      else:
        if regex[i] not in alphabet:
          fst_stack.append(('symbol', pynini.accep(regex[i])))
        else:
          fst_stack.append(('symbol', pynini.union(*alphabet[regex[i]])))
    
    for (_, f) in fst_stack:
      if not fst: # first FST
        fst = f
      else:
        fst = fst + f

    if len(stack) > 0:
      raise Exception('Unmatched brackets')

    # upper/lower alphabet symbol transitions and weights not used by compiler
    rules = [('', '', cont_class, 0.0) for cont_class in cont_classes]
    super(StemGuesser, self).__init__(name, rules, start)
    self.fst = fst.optimize()
