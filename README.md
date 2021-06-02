# morphotactics
morphotactics is a Python library for implementing morphotactic FSTs that uses OpenFST and Pynini (a Python wrapper for OpenFST).

Overview: https://www.youtube.com/watch?v=uEiBt6aTGGk

For the latest API, use help(...). 

## Installation
Use conda to install pynini and openfst. You need Python version 3.6+.

## Usage
1. Define Slots and StemGuessers
2. compile

TODO: full on example


## Slot class
Morphotactic rules specify the order in which morphemes can occur (e.g. suffix must occur after verb stem, prefix occurs before verb stem). We group types of morphemes together into classes. Each class specifies its continuation class (what can occur after). The Slot class is our version of a lexc continuation class. 

Note that the rules within a class are lazily evaluated and only compiled into an FST when passed into the compile function. 

You can think of a Slot as a union of different rules. 

TODO: example of a rule and its FST - explaining the different weights and how a rule can be both terminal and non-terminal
TODO: example of a Slot and its FST PRE-optimization


## StemGuesser
Languages have minimal word constraints, which are rules on what types of phonemes the smallest word must contain. For out of vocab stems, we want to guess which part of the word is the stem. 
We represent these minimal word constraints with regular expressions. StemGuesser converts
such regex into an FSA (finite state acceptor), which relies on the theorem that 
any regular expression can be recognized by a corresponding finite state acceptor. 

We support a limited form of regex: 
* () scope / grouping - concatenation
* [] union - match anything inside
* Sigma (.) - match any character in the alphabet (not including epsilon)
* Quantifiers: ?, *, +

Note that an FSA is just an FST with input and output transitions being the same. 

Also, a StemGuesser is-a Slot, so it can have continuation classes and weights. 

TODO: example

## compile
This is where we turn the rules into FSTs and we glue the different Slots together.  
Note, we cannot do a depth-first search and simply call pynini.concat() to join
a rule with its continuation class because upon the first or final visit to some class, the continuation class' FST may not be finished compiling. Suppose we're 
concatenating rule A to Slot B. We need to compile B first before we can concatenate
because if B's continuations (and their continuations, etc) are not fully processed,
we can no longer go back and update the copy of B concatenated to A after we have
destructively modified B to include all of its continuations. This is because 
pynini makes a copy of B in the concatenation instead of storing a pointer to B. 
Thus we need to ensure all of B's continuations (and their continuations and so on)
are processed first before concatenating to rule A. This introduces a topological sort, which does not exist for cyclic dependencies. 

Thus we perform two separate depth-first search passes:
1. create the rules with pynini.cross, copy each rule's FST into the final FST, store each rule's final state, store each Slot's start state in the final FST
2. manually add transitions (arcs) from each rule's final state to the start state of each Slot in the final FST

Note, we are searching through an implicit graph, wherein the Slots are vertices and 
rule-continuation class(es) pairs form edges. Also, we preserve non-deterministicness and only call pynini's optimize() method if the FST is deterministic. 

## debugging
### transduction
One way of testing the correctness of an FST is by seeing what strings can be transduced by the FST and with what weight (if weights are added). 

For an FSA (like StemGuesser), you can see if some input string is in the FSA:
```
def accepts(fsa, input_str):
  return pynini.compose(input_str, fsa).num_states() != 0
```

For deterministic FSTs, there should only be one output string that can be transduced
from one input string: 
```
def analyze(fst, input_str):
  return pynini.compose(input_str, fst).string()
```
We call this function analyze because we assume the FST's input alphabet is 
a language's lower alphabet and the FST's output alphabet is the upper alphabet. 
Transducing from the lower to the upper alphabet is called morphological analysis. 

For non-deterministic FSTs, there can be many output strings that can be transduced from one input string. We first compose the FST with the input_str in question,
which reduces the FST to only the transitions that input_str can follow. Next, we 
use a DFS to find all strings that can be transduced from input_str, along with their weights. Refer to the function ```all_strings_from_chain```. The weight of each
output string is obtained by taking the semiring product (⊗) of the weights along 
the path and the weight of the final state. We use the tropical semiring, so we add the weights.

Note, if the FST is deterministic but weighted, use ```all_strings_from_chain```. 

TODO: insert example


Note: if you see errors such as "start state invalid" or "_pywrapfst.FstOpError: Operation failed," this means the FST cannot perform the transduction because the FST
does not have a path for some input string. 

### drawing
Another way to debug FSTs is to draw them using the ```draw``` method of ```pynini.Fst```.
Suppose you have some FST defined, ```fst```, then you would draw it with:
```fst.draw(file_name, portrait=True)```

The file extension should be dot and can be viewed in VSCode with the graphviz extension (https://marketplace.visualstudio.com/items?itemName=joaompinto.vscode-graphviz). If you would like to convert the dot file into a png, try the following (source: https://github.com/kylebgorman/pynini/issues/35):

```
def draw(fst):
  fst.draw(‘tmp.dot’, portrait=True, isymbols=fst.input_symbols(), osymbols=fst.output_symbols())
  graphviz.render(‘dot’, ‘svg’, ‘tmp.dot’, renderer=‘cairo’)
  return display(SVG(url=‘file:tmp.dot.cairo.svg’))
```

### SymbolTable
At this point, you may be seeing a bunch of numbers. pynini converts each symbol
into its Unicode representation as an integer. For the FST's readability, 
attach a SymbolTable to the drawing.

Here is the SymbolTable for the English language:

```
import pywrapfst
alphabet = list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
st = pywrapfst.SymbolTable()
st.add_symbol('<epsilon>', 0)
for symb in alphabet:
  st.add_symbol(symb, ord(symb))
```
If you add more symbols (e.g. -, +, etc), you need to add them them to the SymbolTable as well. If some symbol in the FST is not covered, you will get the following error: 
  ERROR: FstDrawer: Integer _ is not mapped to any textual symbol

Finally, attach the SymbolTable to the FST as follows:
```fst.draw(file_name, portrait=True, isymbols=st, osymbols=st)```

## Tests
To run the tests, run
```python -m pytest``` from the root directory
