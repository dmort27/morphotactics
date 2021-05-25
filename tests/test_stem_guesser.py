from morphotactics.stem_guesser import StemGuesser
import pynini

nahuatl_alphabet = {
  'C': ['m', 'n', 'p', 't', 'k', 'kw', 'h', 'ts', 'tl', 'ch', 's', 'l', 'x', 'j', 'w'], 
  'V': ['a', 'e', 'i', 'o']
}
bimoraic_fsa = StemGuesser('[CV]*V[CV]*V[CV]*', '', [None], nahuatl_alphabet).fst
bimoraic_fsa_sigma_form = StemGuesser('.*V.*V.*', '', [None], nahuatl_alphabet).fst
# note: StemGuesser('.*V.*V.*', '', [None], nahuatl_alphabet) != StemGuesser('[CV]*V[CV]*V[CV]*', '', [None], nahuatl_alphabet)
# because of different state numberings during state optimization but they accept the same language still

def accepts(fst, input_str):
  return pynini.compose(input_str, fst).num_states() != 0

def is_bimoraic(oov_stem):
  return accepts(bimoraic_fsa, oov_stem)

def is_bimoraic_sigma_form(oov_stem):
  return accepts(bimoraic_fsa_sigma_form, oov_stem)


def test_sigma_concatenated():
  fst = StemGuesser('...', '', [None], nahuatl_alphabet).fst
  assert accepts(fst, 'tap')
  assert not accepts(fst, '')
  assert not accepts(fst, 'ta')
  assert not accepts(fst, 'main')

def test_sigma_in_middle():
  fst = StemGuesser('p.p', '', [None], nahuatl_alphabet).fst
  assert accepts(fst, 'pop')
  assert accepts(fst, 'pip')
  assert accepts(fst, 'psp')
  assert not accepts(fst, 'pp')

def test_sigma_star_alone():
  fst = StemGuesser('.*', '', [None], nahuatl_alphabet).fst
  assert accepts(fst, '')
  assert accepts(fst, 'a')
  assert accepts(fst, 'ann')
  assert accepts(fst, 'nn')

def test_sigma_star_preceding():
  fst = StemGuesser('.*t', '', [None], nahuatl_alphabet).fst
  assert accepts(fst, 't')
  assert not accepts(fst, '')
  assert accepts(fst, 'at')
  assert accepts(fst, 'att')
  assert not accepts(fst, 'ta')

def test_sigma_star_following():
  fst = StemGuesser('t.*', '', [None], nahuatl_alphabet).fst
  assert accepts(fst, 't')
  assert not accepts(fst, '')
  assert accepts(fst, 'ta')
  assert accepts(fst, 'tta')
  assert not accepts(fst, 'at')

def test_sigma_star_odd_number():
  fst = StemGuesser('.*.*.*', '', [None], nahuatl_alphabet).fst
  assert accepts(fst, 'at')
  assert accepts(fst, '')
  assert accepts(fst, 'a')
  assert accepts(fst, 't')
  assert accepts(fst, 'at')
  assert accepts(fst, 'atp')

def test_sigma_star_even_number():
  fst = StemGuesser('.*.*', '', [None], nahuatl_alphabet).fst
  assert accepts(fst, 'at')
  assert accepts(fst, '')
  assert accepts(fst, 'a')
  assert accepts(fst, 't')
  assert accepts(fst, 'at')
  assert accepts(fst, 'atp')

def test_sigma_star_following_sigma():
  fst = StemGuesser('..*', '', [None], {'C': ['b', 'c'], 'V': ['a']}).fst
  assert not accepts(fst, '')

  fst = StemGuesser('..*', '', [None], nahuatl_alphabet).fst
  assert accepts(fst, 'a')
  assert not accepts(fst, '')
  assert accepts(fst, 'at')
  assert accepts(fst, 'atp')

def test_sigma_star_preceding_sigma():
  fst = StemGuesser('.*.', '', [None], nahuatl_alphabet).fst
  assert accepts(fst, 'a')
  assert not accepts(fst, '')
  assert accepts(fst, 'at')
  assert accepts(fst, 'atp')

def test_sigma_star_sigma_sigma_star():
  fst = StemGuesser('.*..*', '', [None], nahuatl_alphabet).fst
  assert accepts(fst, 'a')
  assert not accepts(fst, '')
  assert accepts(fst, 'at')
  assert accepts(fst, 'atp')

def test_sigma_star_symbol_sigma_star():
  fst = StemGuesser('.*j.*', '', [None], nahuatl_alphabet).fst
  assert not accepts(fst, '')
  assert not accepts(fst, 'a')
  assert accepts(fst, 'j')

  fst = StemGuesser('[CV]*[CV][CV]*', '', [None], nahuatl_alphabet).fst
  assert not accepts(fst, '')

  fst = StemGuesser('.*..*', '', [None], nahuatl_alphabet).fst
  assert not accepts(fst, '')

def test_symbol_closure():
  fst = StemGuesser('a*', '', [None]).fst
  assert accepts(fst, '')
  assert accepts(fst, 'a')
  assert accepts(fst, 'aa')
  assert accepts(fst, 'aaa')
  assert accepts(fst, 'aaaa')
  assert not accepts(fst, 'ab')

def test_bimoraic_fsa():
  assert is_bimoraic('paaki') # CVVCV
  assert is_bimoraic('paak') # CVVC
  assert is_bimoraic('posteki') # CVCCVCV
  assert is_bimoraic('miktilia') # CVCCVCVV

  assert is_bimoraic('aa') # VV
  assert is_bimoraic('ai') # VV
  assert is_bimoraic('oatl') # VVC
  assert is_bimoraic('papiko') # CVCVCV
  assert is_bimoraic('moo') # CVV
  assert is_bimoraic('mio') # CVV
  assert is_bimoraic('tami') # CVCV
  assert is_bimoraic('xojlito') # CVCCVCV
  assert is_bimoraic('soomi') # CVVCV

  assert not is_bimoraic('atl') # VC
  assert not is_bimoraic('ak') # VC
  assert not is_bimoraic('ah') # VC
  assert not is_bimoraic('a') # V
  assert not is_bimoraic('p') # C
  assert not is_bimoraic('pa') # CV

def test_bimoraic_fsa_sigma_form():
  # bimoraic regex with sigma instead of [CV]
  assert is_bimoraic_sigma_form('paaki') # CVVCV
  assert is_bimoraic_sigma_form('paak') # CVVC
  assert is_bimoraic_sigma_form('posteki') # CVCCVCV
  assert is_bimoraic_sigma_form('miktilia') # CVCCVCVV

  assert is_bimoraic_sigma_form('aa') # VV
  assert is_bimoraic_sigma_form('ai') # VV
  assert is_bimoraic_sigma_form('oatl') # VVC
  assert is_bimoraic_sigma_form('papiko') # CVCVCV
  assert is_bimoraic_sigma_form('moo') # CVV
  assert is_bimoraic_sigma_form('mio') # CVV
  assert is_bimoraic_sigma_form('tami') # CVCV
  assert is_bimoraic_sigma_form('xojlito') # CVCCVCV
  assert is_bimoraic_sigma_form('soomi') # CVVCV

  assert not is_bimoraic_sigma_form('atl') # VC
  assert not is_bimoraic_sigma_form('ak') # VC
  assert not is_bimoraic_sigma_form('ah') # VC
  assert not is_bimoraic_sigma_form('a') # V
  assert not is_bimoraic_sigma_form('p') # C
  assert not is_bimoraic_sigma_form('pa') # CV

def test_closure_no_alphabet():
  fst = StemGuesser('CV*', '', [None]).fst
  assert accepts(fst, 'C')
  assert accepts(fst, 'CV')
  assert accepts(fst, 'CVV')
  assert accepts(fst, 'CVVV')
  assert not accepts(fst, 'CVC')

def test_closure_of_scope_no_alphabet():
  fst = StemGuesser('(CV)*', '', [None]).fst
  assert accepts(fst, '')
  assert accepts(fst, 'CV')
  assert accepts(fst, 'CVCV')
  assert not accepts(fst, 'CVV')
  assert not accepts(fst, 'CCV')

def test_closure_of_union_no_alphabet():
  fst = StemGuesser('[CV]*V[CV]*V[CV]*', '', [None]).fst
  assert accepts(fst, 'CVVCV') # bimoraic
  assert accepts(fst, 'VV') # bimoraic
  assert accepts(fst, 'VVC') # bimoraic
  assert accepts(fst, 'CVCV') # bimoraic
  assert accepts(fst, 'CVCVC') # bimoraic
  assert not accepts(fst, 'CV') # not bimoraic
  assert not accepts(fst, 'CC') # not bimoraic
  assert not accepts(fst, 'CCV') # not bimoraic

def test_closure_of_scope_preceding_symbol():
  fst = StemGuesser('(CV)*C', '', [None]).fst
  assert not accepts(fst, 'CCV')
  assert accepts(fst, 'CVC')
  assert accepts(fst, 'CVCVC')
  assert accepts(fst, 'C')
  assert not accepts(fst, '')

def test_concat():
  fst = StemGuesser('CVCV', '', [None]).fst
  assert accepts(fst, 'CVCV')
  assert not accepts(fst, 'CVC')
  assert not accepts(fst, 'CVV')

def test_union_concat_union():
  fst = StemGuesser('[abc][abc]', '', [None]).fst
  assert not accepts(fst, 'abcabc')
  assert accepts(fst, 'ab')

def test_scope_concat_scope():
  fst = StemGuesser('(abc)(abc)', '', [None]).fst
  assert accepts(fst, 'abcabc')
  assert not accepts(fst, 'ab')

  fst = StemGuesser('(abef)', '', [None]).fst
  assert accepts(fst, 'abef')

def test_union_concat_scope():
  fst = StemGuesser('[abc](de)', '', [None]).fst
  assert accepts(fst, 'cde')

  fst = StemGuesser('[abc](de)[fgh]', '', [None]).fst
  assert accepts(fst, 'cdef')
  assert accepts(fst, 'adeg')

  fst = StemGuesser('[abc](ce)[fgh]', '', [None]).fst
  assert accepts(fst, 'acef')
