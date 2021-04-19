import pynini

"""
Returns an OpenFST FST representing the morphotactic rules of an entire lexicon
Resolves all dependencies between continuation classes of multiple slots

Args:
  slots: set of Slot objects (not a list)
"""
def compile(slots):
  fst = pynini.Fst()
  s = fst.add_state()
  fst.set_start(s)
  fst.set_final(s)

  # union within a continuation class, gather all of the slots together - each slot will have one unioned FST
  # concatenate the slots based on continuation class - go slot by slot, rule by rule

  slot_map = { slot.name:slot.fst for slot in slots }
  for slot in slots:
    for (upper, lower, continuation_classes, weight) in slot.rules:
      # transitions within same slot could have different continuation classes
      # concatenate the rule with the continuation class' FST

      # place lower on the input alphabet
      # so that FST can take in input from lower alphabet to perform analysis
      rule = pynini.cross(lower, upper)
      # each transition could have many continuation_classes
      if len(continuation_classes) > 0:
        continuation_fsts = [slot_map[cont_class] for cont_class in continuation_classes]
        continuation_union = pynini.union(*continuation_fsts)
        slot.fst = pynini.union(slot.fst, pynini.concat(rule, continuation_union))
      else:
        slot.fst = rule

  # concatenate the FST with the starting classes
  starting_slots = list(map(lambda slot: slot.fst, filter(lambda slot: slot.start, slots)))
  if len(starting_slots) == 0:
    raise Exception('need at least 1 slot to be a starting slot')
  fst = pynini.concat(fst, pynini.union(*starting_slots))

  fst.optimize()

  # verify the FST
  if not fst.verify():
    raise Exception('FST malformed')

  return fst
