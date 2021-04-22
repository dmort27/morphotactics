from morphotactics.stem_guesser import StemGuesser
import pynini

nahuatl_alphabet = {
  'C': ['m', 'n', 'p', 't', 'k', 'kw', 'h', 'ts', 'tl', 'ch', 's', 'l', 'x', 'j', 'w'], 
  'V': ['a', 'e', 'i', 'o']
}
bimoraic_fsa = StemGuesser('[CV]*V[CV]*V[CV]*', nahuatl_alphabet).fst
bimoraic_fsa_sigma_form = StemGuesser('.*V.*V.*', nahuatl_alphabet).fst
# note: StemGuesser('.*V.*V.*', nahuatl_alphabet) != StemGuesser('[CV]*V[CV]*V[CV]*', nahuatl_alphabet)
# because of different state numberings during state optimization but they accept the same language still

def accepts(fst, input_str):
  return pynini.compose(input_str, fst).num_states() != 0

def is_bimoraic(oov_stem):
  return accepts(bimoraic_fsa, oov_stem)

def is_bimoraic_sigma_form(oov_stem):
  return accepts(bimoraic_fsa_sigma_form, oov_stem)


def test_sigma_concatenated():
  assert accepts(StemGuesser('...', nahuatl_alphabet).fst, 'tap')
  assert not accepts(StemGuesser('...', nahuatl_alphabet).fst, '')
  assert not accepts(StemGuesser('...', nahuatl_alphabet).fst, 'ta')
  assert not accepts(StemGuesser('...', nahuatl_alphabet).fst, 'main')

def test_sigma_in_middle():
  assert accepts(StemGuesser('p.p', nahuatl_alphabet).fst, 'pop')
  assert accepts(StemGuesser('p.p', nahuatl_alphabet).fst, 'pip')
  assert accepts(StemGuesser('p.p', nahuatl_alphabet).fst, 'psp')
  assert not accepts(StemGuesser('p.p', nahuatl_alphabet).fst, 'pp')

def test_sigma_star_alone():
  assert accepts(StemGuesser('.*', nahuatl_alphabet).fst, '')
  assert accepts(StemGuesser('.*', nahuatl_alphabet).fst, 'a')
  assert accepts(StemGuesser('.*', nahuatl_alphabet).fst, 'ann')
  assert accepts(StemGuesser('.*', nahuatl_alphabet).fst, 'nn')

def test_sigma_star_preceding():
  assert accepts(StemGuesser('.*t', nahuatl_alphabet).fst, 't')
  assert not accepts(StemGuesser('.*t', nahuatl_alphabet).fst, '')
  assert accepts(StemGuesser('.*t', nahuatl_alphabet).fst, 'at')
  assert accepts(StemGuesser('.*t', nahuatl_alphabet).fst, 'att')
  assert not accepts(StemGuesser('.*t', nahuatl_alphabet).fst, 'ta')

def test_sigma_star_following():
  assert accepts(StemGuesser('t.*', nahuatl_alphabet).fst, 't')
  assert not accepts(StemGuesser('t.*', nahuatl_alphabet).fst, '')
  assert accepts(StemGuesser('t.*', nahuatl_alphabet).fst, 'ta')
  assert accepts(StemGuesser('t.*', nahuatl_alphabet).fst, 'tta')
  assert not accepts(StemGuesser('t.*', nahuatl_alphabet).fst, 'at')

def test_sigma_star_odd_number():
  assert accepts(StemGuesser('.*.*.*', nahuatl_alphabet).fst, 'at')
  assert accepts(StemGuesser('.*.*.*', nahuatl_alphabet).fst, '')
  assert accepts(StemGuesser('.*.*.*', nahuatl_alphabet).fst, 'a')
  assert accepts(StemGuesser('.*.*.*', nahuatl_alphabet).fst, 't')
  assert accepts(StemGuesser('.*.*.*', nahuatl_alphabet).fst, 'at')
  assert accepts(StemGuesser('.*.*.*', nahuatl_alphabet).fst, 'atp')

def test_sigma_star_even_number():
  assert accepts(StemGuesser('.*.*', nahuatl_alphabet).fst, 'at')
  assert accepts(StemGuesser('.*.*', nahuatl_alphabet).fst, '')
  assert accepts(StemGuesser('.*.*', nahuatl_alphabet).fst, 'a')
  assert accepts(StemGuesser('.*.*', nahuatl_alphabet).fst, 't')
  assert accepts(StemGuesser('.*.*', nahuatl_alphabet).fst, 'at')
  assert accepts(StemGuesser('.*.*', nahuatl_alphabet).fst, 'atp')

def test_sigma_star_following_sigma():
  assert not accepts(StemGuesser('..*', {'C': ['b', 'c'], 'V': ['a']}).fst, '')
  assert accepts(StemGuesser('..*', nahuatl_alphabet).fst, 'a')
  assert not accepts(StemGuesser('..*', nahuatl_alphabet).fst, '')
  assert accepts(StemGuesser('..*', nahuatl_alphabet).fst, 'at')
  assert accepts(StemGuesser('..*', nahuatl_alphabet).fst, 'atp')

def test_sigma_star_preceding_sigma():
  assert accepts(StemGuesser('.*.', nahuatl_alphabet).fst, 'a')
  assert not accepts(StemGuesser('.*.', nahuatl_alphabet).fst, '')
  assert accepts(StemGuesser('.*.', nahuatl_alphabet).fst, 'at')
  assert accepts(StemGuesser('.*.', nahuatl_alphabet).fst, 'atp')

def test_sigma_star_sigma_sigma_star():
  assert accepts(StemGuesser('.*..*', nahuatl_alphabet).fst, 'a')
  assert not accepts(StemGuesser('.*..*', nahuatl_alphabet).fst, '')
  assert accepts(StemGuesser('.*..*', nahuatl_alphabet).fst, 'at')
  assert accepts(StemGuesser('.*..*', nahuatl_alphabet).fst, 'atp')

def test_sigma_star_symbol_sigma_star():
  assert not accepts(StemGuesser('.*j.*', nahuatl_alphabet).fst, '')
  assert not accepts(StemGuesser('.*j.*', nahuatl_alphabet).fst, 'a')
  assert accepts(StemGuesser('.*j.*', nahuatl_alphabet).fst, 'j')
  assert not accepts(StemGuesser('[CV]*[CV][CV]*', nahuatl_alphabet).fst, '')
  assert not accepts(StemGuesser('.*..*', nahuatl_alphabet).fst, '')

def test_symbol_closure():
  assert accepts(StemGuesser('a*').fst, '')
  assert accepts(StemGuesser('a*').fst, 'a')
  assert accepts(StemGuesser('a*').fst, 'aa')
  assert accepts(StemGuesser('a*').fst, 'aaa')
  assert accepts(StemGuesser('a*').fst, 'aaaa')
  assert not accepts(StemGuesser('a*').fst, 'ab')

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
  assert accepts(StemGuesser('CV*').fst, 'C')
  assert accepts(StemGuesser('CV*').fst, 'CV')
  assert accepts(StemGuesser('CV*').fst, 'CVV')
  assert accepts(StemGuesser('CV*').fst, 'CVVV')
  assert not accepts(StemGuesser('CV*').fst, 'CVC')

def test_closure_of_scope_no_alphabet():
  assert accepts(StemGuesser('(CV)*').fst, '')
  assert accepts(StemGuesser('(CV)*').fst, 'CV')
  assert accepts(StemGuesser('(CV)*').fst, 'CVCV')
  assert not accepts(StemGuesser('(CV)*').fst, 'CVV')
  assert not accepts(StemGuesser('(CV)*').fst, 'CCV')

def test_closure_of_union_no_alphabet():
  assert accepts(StemGuesser('[CV]*V[CV]*V[CV]*').fst, 'CVVCV') # bimoraic
  assert accepts(StemGuesser('[CV]*V[CV]*V[CV]*').fst, 'VV') # bimoraic
  assert accepts(StemGuesser('[CV]*V[CV]*V[CV]*').fst, 'VVC') # bimoraic
  assert accepts(StemGuesser('[CV]*V[CV]*V[CV]*').fst, 'CVCV') # bimoraic
  assert accepts(StemGuesser('[CV]*V[CV]*V[CV]*').fst, 'CVCVC') # bimoraic
  assert not accepts(StemGuesser('[CV]*V[CV]*V[CV]*').fst, 'CV') # not bimoraic
  assert not accepts(StemGuesser('[CV]*V[CV]*V[CV]*').fst, 'CC') # not bimoraic
  assert not accepts(StemGuesser('[CV]*V[CV]*V[CV]*').fst, 'CCV') # not bimoraic

def test_closure_of_scope_preceding_symbol():
  assert not accepts(StemGuesser('(CV)*C').fst, 'CCV')
  assert accepts(StemGuesser('(CV)*C').fst, 'CVC')
  assert accepts(StemGuesser('(CV)*C').fst, 'CVCVC')
  assert accepts(StemGuesser('(CV)*C').fst, 'C')
  assert not accepts(StemGuesser('(CV)*C').fst, '')

def test_concat():
  assert accepts(StemGuesser('CVCV').fst, 'CVCV')
  assert not accepts(StemGuesser('CVCV').fst, 'CVC')
  assert not accepts(StemGuesser('CVCV').fst, 'CVV')

def test_union_concat_union():
  assert not accepts(StemGuesser('[abc][abc]').fst, 'abcabc')
  assert accepts(StemGuesser('[abc][abc]').fst, 'ab')

def test_scope_concat_scope():
  assert accepts(StemGuesser('(abc)(abc)').fst, 'abcabc')
  assert not accepts(StemGuesser('(abc)(abc)').fst, 'ab')
  assert accepts(StemGuesser('(abef)').fst, 'abef')

def test_union_concat_scope():
  assert accepts(StemGuesser('[abc](de)').fst, 'cde')
  assert accepts(StemGuesser('[abc](de)[fgh]').fst, 'cdef')
  assert accepts(StemGuesser('[abc](de)[fgh]').fst, 'adeg')
  assert accepts(StemGuesser('[abc](ce)[fgh]').fst, 'acef')
