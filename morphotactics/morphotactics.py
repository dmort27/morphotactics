import pynini
from morphotactics.stem_guesser import StemGuesser

# A recursive, polymorphic depth-first graph search algorithm
# Runs in O(|V| + |E|) if the state updates are O(1)
# Adapted from CMU 15-210, Parallel & Sequential Data Structures & Algorithms
# state: DFS state
# visited: set of visited vertices
# vertex: a vertex
# neighbors: function to get the neighbors of a vertex as a list
# visit: function that updates state upon first visit to a vertex
# revisit: function that updates state upon second visit to a vertex
# finish: function that updates state after iterating through all neighbors of a vertex
def _dfs(state, visited, vertex, neighbors, visit, revisit, finish):
  if vertex in visited:
    return (revisit(state, vertex), visited)
  else:
    state = visit(state, vertex)
    visited.add(vertex)
    nbors = neighbors(vertex)
    for nbor in nbors:
      (state, visited) = _dfs(state, visited, nbor, neighbors, visit, revisit, finish)
    return (finish(state, vertex), visited)

"""
Returns an OpenFST FST representing the morphotactic rules of an entire lexicon
Resolves all dependencies between continuation classes of multiple slots
Requires that the slot dependencies are acyclic and form a directed acyclic graph
Note: no slot can be named 'start'

Args:
  slots: set of Slot objects (not a list)
"""
def compile(slots):
  # if dependencies are cyclic, we cannot use pynini to concatenate
  # rules to continuation classes' FSTs since pynini creates a copy of the 
  # continuation class' FST, and we might not have finished mutating it
  # by the time we are doing the concatenation
  # thus we must manually add the arcs from the rules to the continuation classes
  # through 2 passes (1 pass to create the rules, 1 pass to add the arcs)
  
  # we use DFS to process the Slots that are reachable from the starting Slots
  # Slots are the vertices, and transitions between classes are edges

  slot_map = { slot.name:slot for slot in slots }
  starting_slots = { slot.name:slot for slot in slots if slot.start }
  fst = pynini.Fst()

  if len(starting_slots) == 0:
    raise Exception('need at least 1 slot to be a starting slot')

  # copy the FST for each rule or the Slot's FSA into the main fst with pywrapfst
  # store each Slot's start state in this main FST as DFS state
  # store each rule's/FSA's final state in the Slot
  def first_visit(state, vertex):
    start_states = state

    if vertex == 'start':
      s = fst.add_state()
      fst.set_start(s)
      start_states[vertex] = s
      return start_states
    
    slot = slot_map[vertex]
    slot_start_state = fst.add_state()

    if isinstance(slot, StemGuesser):
      # copy the regex FSA to fst with pywrapfst
      fsa = slot.fst
      old_num_states = fst.num_states()
      fst.add_states(fsa.num_states() - 1) # do not need to copy over slot_start_state again
      for state in fsa.states():
        new_state = slot_start_state if state == 0 else (old_num_states + state - 1)

        # final state of FST may not be accepting, so must manually find the final state
        # there will only be one final state in fsa since it was optimized
        if fsa.final(state) == pynini.Weight.one('tropical'):
          fsa_final_state = new_state

        for arc in fsa.arcs(state):
          nextstate = slot_start_state if arc.nextstate == 0 else (old_num_states + arc.nextstate - 1)
          fst.add_arc(new_state, pynini.Arc(arc.ilabel, arc.olabel, arc.weight, nextstate))

      slot.final_states.append(fsa_final_state)
    else: # regular Slot
      # create an FST for each rule with pynini and copy over to fst with pywrapfst
      for (upper, lower, cont_classes, weight) in slot.rules:
        # transitions within same slot could have different continuation classes
        # we will concatenate the rule with the continuation class' FST in the second DFS

        # place lower on the input side so that FST can take in input from lower alphabet to perform analysis
        rule = pynini.cross(lower, upper)

        # copy rule to fst arc by arc, starting from state start_slot
        old_num_states = fst.num_states()
        fst.add_states(rule.num_states() - 1) # do not need to copy over slot_start_state again
        
        for state in rule.states():
          new_state = slot_start_state if state == 0 else (old_num_states + state - 1)
          for arc in rule.arcs(state):
            nextstate = slot_start_state if arc.nextstate == 0 else (old_num_states + arc.nextstate - 1)
            fst.add_arc(new_state, pynini.Arc(arc.ilabel, arc.olabel, arc.weight, nextstate))

        rule_final_state = fst.num_states() - 1
        slot.final_states.append(rule_final_state)
        
    # add current slot's FST to finished set of slots
    start_states[vertex] = slot_start_state
    return start_states
  
  def revisit(state, vertex): 
    # do nothing because Slot only needs to be processed once
    return state
  
  def finish(state, vertex): # do nothing
    return state

  def neighbors(vertex):
    if vertex == 'start':
      return list(starting_slots.keys())
    conts = set()
    # we only care about visiting the continuation class so only retrieve its name
    # the linking of rules to continuation class' FSTs is done in the finish function
    slot = slot_map[vertex]
    # works if the slot is a Slot or StemGuesser
    for (_, _, continuation_classes, _) in slot.rules:
      conts |= set(continuation_classes)
    return list(conts)
  
  # make a first pass through all of the Slots with DFS
  # convert each Slot's rules into an FST
  # DFS guarantees that the Slots processed are reachable from the start

  # start_states maps Slot name to start state of the Slot so that we can concatenate a rule with its continuation classes
  start_states = {}
  (start_states, _) = _dfs(start_states, set(), 'start', neighbors, first_visit, revisit, finish)

  # second pass through all of the Slots
  # by this time, all Slots reachable from the start have been converted into FSTs
  # add transition from each rule to continuation class' start state
  # glue all Slots together, Slot by Slot
  # note that we cannot concatenate each Slot to its continuation's FST 
  #    because its continuation's FST is not guaranteed to have finished processing
  def second_pass(state, vertex):
    if vertex == 'start':
      # add an epsilon transition between each starting state and starting slots
      # will be removed during optimization
      # we do not union the starting slots because we do not know when the slots will be finished processing
      s = start_states[vertex]
      for start_slot in starting_slots.keys():
        # note: we currently do not support setting weights for starting classes
        arc = pynini.Arc(0, 0, 0.0, start_states[start_slot])
        fst.add_arc(s, arc)
      return
    
    slot = slot_map[vertex]
    if isinstance(slot, StemGuesser):
      # only care about a StemGuesser's continuation classes
      # StemGuesser does not assign weights or transitions
      cont_classes = slot.rules[0][2]
      final_state = slot.final_states[0] # Slot only has 1 final state
      if len(cont_classes) == 0:
        # final state of the rule should be an accepting state
        fst.set_final(final_state)
      else:
        # add epsilon transition between FSA's final state and continuation classes
        for continuation_class in cont_classes:
          arc = pynini.Arc(0, 0, 0.0, start_states[continuation_class])
          fst.add_arc(final_state, arc)
    else: # regular Slot
      for ((_, _, cont_classes, _), final_state) in zip(slot.rules, slot.final_states):
        if len(cont_classes) == 0:
          # final state of the rule should be an accepting state
          fst.set_final(final_state)
        else:
          # add epsilon transition between each rule's final state and continuation classes
          # note: we currently do not support setting weights for continuation classes
          for continuation_class in cont_classes:
            arc = pynini.Arc(0, 0, 0.0, start_states[continuation_class])
            fst.add_arc(final_state, arc)
    return
  
  _dfs(None, set(), 'start', neighbors, second_pass, revisit, finish)

  # verify the FST
  if not fst.verify():
    raise Exception('FST malformed')

  fst.optimize()

  return fst
