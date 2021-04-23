import pynini

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
  # we use DFS to process the dependencies from finishing classes to starting classes
  # because we can only join a rule to a continuation class when the continuation class is finished processing
  # this is essentially finding a topological sort of a DAG
  # though we do not return the actual sort and only go in reverse topological sorted order
  # continuation classes are the vertices, and transitions between classes are edges

  slot_map = { slot.name:slot for slot in slots }
  starting_slots = { slot.name:slot for slot in slots if slot.start }

  if len(starting_slots) == 0:
    raise Exception('need at least 1 slot to be a starting slot')

  def visit(state, vertex): # do nothing
    return state
  def revisit(state, vertex): 
    # do nothing because graph is a DAG and this function will never be reached
    return state
  def finish(state, vertex):
    processed_slots = state
    
    if vertex == 'start': # finish the final state
      # union the starting classes
      starting_slot_fsts = [processed_slots[slot] for slot in starting_slots.keys()]
      final_fst = pynini.union(*starting_slot_fsts)
      processed_slots['start'] = final_fst
      return processed_slots

    # add current slot's FST to finished set of slots
    slot = slot_map[vertex]
    processed_slots[vertex] = slot.fst
    # go through each rule and take union of continuations, concatenate
    for (upper, lower, cont_classes, weight) in slot.rules:
      # transitions within same slot could have different continuation classes
      # concatenate the rule with the continuation class' FST

      # place lower on the input side so that FST can take in input from lower alphabet to perform analysis
      rule = pynini.cross(lower, upper)
      # assumes by the time a continuation class is finished, its neighbors are finished too
      if len(cont_classes) > 0:
        union_continuations = pynini.union(*[processed_slots[c] for c in cont_classes])
        slot.fst.union(pynini.concat(rule, union_continuations))
      else:
        slot.fst.union(rule)
    return processed_slots

  def neighbors(vertex):
    if vertex == 'start':
      return list(starting_slots.keys())
    conts = set()
    # we only care about visiting the continuation class so only retrieve its name
    # the linking of rules to continuation class' FSTs is done in the finish function
    slot = slot_map[vertex]
    for (_, _, continuation_classes, _) in slot.rules:
      conts |= set(continuation_classes)
    return list(conts)
  
  processed_slots = {} # maps Slot name to Slot FST
  visited = set()
  (processed_slots, _) = _dfs(processed_slots, set(), 'start', neighbors, visit, revisit, finish)
  final_fst = processed_slots['start']
  final_fst.optimize()

  # verify the FST
  if not final_fst.verify():
    raise Exception('FST malformed')

  return final_fst
