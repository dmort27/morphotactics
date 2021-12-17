# morphotactics
morphotactics is a Python library for implementing morphotactic FSTs that uses OpenFST and Pynini (a Python wrapper for OpenFST).

Overview: https://www.youtube.com/watch?v=uEiBt6aTGGk

For the latest API, use help(...). 

## Installation
Use conda to install pynini and openfst. You need Python version 3.6+.

## Usage
1. Define Slots and StemGuessers
2. compile

```python
from morphotactics.slot import Slot
from morphotactics.morphotactics import compile
from morphotactics.stem_guesser import StemGuesser


def symbol_table():
  alphabet = list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') + ['-']
  st = pywrapfst.SymbolTable()
  st.add_symbol('ϵ', 0)
  for symb in alphabet:
    st.add_symbol(symb, ord(symb))
  return st

st = symbol_table()

fst = compile({
  Slot('class1',
    [
      ('a', 'b', [('class2', 1.0), (None, 2.0)], 100.0),
      ('c', 'd', [(None, 3.0)], 200.0),
      ('e', 'f', [('class2', 4.0), ('class3', 5.0), (None, 6.0)], 300.0)
    ],
    start=True),
  Slot('class2', 
    [
      ('g', 'h', [(None, 7.0)], 400.0),
      ('i', 'j', [(None, 8.0)], 500.0),
      ('k', 'l', [('class3', 9.0), (None, 10.0)], 600.0),
    ]
  ),
  Slot('class3', 
    [
      ('m', 'n', [(None, 11.0)], 700.0),
      ('o', 'p', [(None, 12.0)], 800.0),
    ]
  )
})
fst.draw('example.dot', portrait=True, isymbols=st, osymbols=st)
```

![image](https://user-images.githubusercontent.com/20138687/120417885-6e2ae800-c314-11eb-9ff4-9bc2d0a57411.png)

Note the FST above was purposely not optimized for the sake of illustration. 

## Slot class
Morphotactic rules specify the order in which morphemes can occur (e.g. suffix must occur after verb stem, prefix occurs before verb stem). We group types of morphemes together into classes. Each class specifies its continuation class (what can occur after). The Slot class is our version of a lexc continuation class. 

Note that the rules within a class are lazily evaluated and only compiled into an FST when passed into the compile function. 

Consider the following rule: ```('a', 'b', [('class2', 1.0), (None, 2.0)], 100.0)```

You can think of a Slot as a union of different rules. Different rules can have 
different weights (highlighted in yellow; 100.0 in the rule above), which represent the weight of transitioning to that particular rule from the Slot's starting state. 
Each rule can have continuation classes, and None is used to indicate that a rule can be terminal. A rule can be both terminal and non-terminal. If a rule is purely terminal, its continuation class is None. 

We can also assign weights to continuation classes (highlighted in green; 1.0 and 2.0 in the example above), which represent the weight of transitioning to a particular continuation class from some rule. Observe that 
some of the rules' accepting states have weights on them. These are the weights specified
along with None in the rule and indicate the weight of being accepted. This final state's weight is 
counted in the weight of the path by ```all_strings_from_chain```. 

Note that setting the weight of any state to any non-semiring zero value (anything non-infinity in the tropical semiring) makes the state an accepting state. 


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

An example of a minimal word constraint is the bimoraic constraint, which requires
a word to have at least two mora.
```python
nahuatl_alphabet = {
  'C': ['m', 'n', 'p', 't', 'k', 'kw', 'h', 'ts', 'tl', 'ch', 's', 'l', 'x', 'j', 'w'], 
  'V': ['a', 'e', 'i', 'o']
}
acceptor = StemGuesser('[CV]*V[CV]*V[CV]*', 'stem', [(None, 0.0)], nahuatl_alphabet)
```

Note, the actual FST stored in StemGuesser is accessed via ```acceptor.fst```

![image](https://user-images.githubusercontent.com/20138687/120419500-78021a80-c317-11eb-9801-5b62f351b572.png)

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
```python
def accepts(fsa, input_str):
  return pynini.compose(input_str, fsa).num_states() != 0
```

For deterministic FSTs, there should only be one output string that can be transduced
from one input string: 
```python
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
the path and the weight of the final state. We use the tropical semiring, so we add the weights. To test if the weights are as expected, you can use the function
```correct_transduction_and_weights```. 

Note, if the FST is deterministic but weighted, use ```all_strings_from_chain```. 

Consider the following non-deterministic FST. The input string 'bd' can be transduced 
into 'ac' through two paths, each with different paths. 
```python
from tests.test_compiler import correct_transduction_and_weights

fst = compile({
  Slot('class1',
    [
      ('a', 'b', [('class2', 0.0)], 1.0),
      ('a', 'b', [('class3', 0.0)], 2.0)
    ],
    start=True),
  Slot('class2',
    [
      ('c', 'd', [(None, 0.0)], 3.0)
    ]),
  Slot('class3',
    [
      ('c', 'd', [(None, 0.0)], 4.0)
    ]),
})
assert correct_transduction_and_weights(fst, 'bd', [('ac', 1.0 + 3.0), ('ac', 2.0 + 4.0)])
```

![image](https://user-images.githubusercontent.com/20138687/120420060-6f5e1400-c318-11eb-8e6a-c3e205da7ccb.png)



Consider the following deterministic FST. The input string 'bd' can be transduced
into 'ce' and 'ae'. 

```python
fst = compile({
  Slot('class1',
    [
      ('c', 'b', [('class2', 0.0), (None, 0.0)], 1.0),
      ('a', 'b', [('class2', 0.0), (None, 0.0)], 2.0)
    ],
    start=True),
  Slot('class2',
    [
      ('e', 'd', [(None, 0.0)], 3.0)
    ]),
})
assert correct_transduction_and_weights(fst, 'b', [('c', 1.0), ('a', 2.0)])
assert correct_transduction_and_weights(fst, 'bd', [('ce', 1.0 + 3.0), ('ae', 2.0 + 3.0)])
```

![image](https://user-images.githubusercontent.com/20138687/120420770-ddefa180-c319-11eb-9132-ff431114919e.png)



Note: if you see errors such as "start state invalid" or "_pywrapfst.FstOpError: Operation failed," this means the FST cannot perform the transduction because the FST
does not have a path for some input string. 

### drawing
Another way to debug FSTs is to draw them using the ```draw``` method of ```pynini.Fst```.
Suppose you have some FST defined, ```fst```, then you would draw it with:
```fst.draw(file_name, portrait=True)```

The file extension should be dot and can be viewed in VSCode with the graphviz extension (https://marketplace.visualstudio.com/items?itemName=joaompinto.vscode-graphviz). If you would like to convert the dot file into a png, try the following (source: https://github.com/kylebgorman/pynini/issues/35):

```python
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

```python
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
To run the tests,
1. Build the app. Run ```pip3 install --editable .``` from the root directory
2. Run ```python -m pytest``` from the root directory
