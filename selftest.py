"""Validate the TestBench-Forge signal WITHOUT any API key.

Proves the two things judges will ask about:
  1. The gym runs and scores deterministically (mutation kill rate).
  2. There is real RFT headroom : a WEAK suite (happy-path only) kills few mutants, while a
     THOROUGH suite kills ~all of them AND still passes the over-spec gate (so the 1.0
     ceiling is real and reachable, not blocked by equivalent mutants).

Run: .venv/bin/python selftest.py   (from repo root: ../.venv/bin/python rewardforge/selftest.py)
"""
import testbench

# A weak, happy-path-only suite per module (one obvious case). Low kill rate.
WEAK = {
    "merge_intervals": "def test_basic():\n    assert merge_intervals([[1,3],[2,6]]) == [[1,6]]\n",
    "is_balanced": "def test_basic():\n    assert is_balanced('()') == True\n",
    "two_sum": "def test_basic():\n    assert two_sum([2,7,11,15], 9) == [0,1]\n",
    "run_length_encode": "def test_basic():\n    assert run_length_encode('aaab') == 'a3b1'\n",
    "binary_search": "def test_basic():\n    assert binary_search([1,3,5,7], 5) == 2\n",
    "roman_to_int": "def test_basic():\n    assert roman_to_int('III') == 3\n",
    "gcd": "def test_basic():\n    assert gcd(12, 8) == 4\n",
    "flatten": "def test_basic():\n    assert flatten([1,2,3]) == [1,2,3]\n",
    "is_palindrome": "def test_basic():\n    assert is_palindrome('aba') == True\n",
    "fizzbuzz": "def test_basic():\n    assert fizzbuzz(3) == ['1','2','Fizz']\n",
}

# A thorough suite per module: edge/boundary coverage. Should kill ~all mutants and pass
# the gate (reference + equivalent refactor).
THOROUGH = {
    "merge_intervals": (
        "def test_overlap():\n    assert merge_intervals([[1,3],[2,6],[8,10]]) == [[1,6],[8,10]]\n"
        "def test_touching():\n    assert merge_intervals([[1,2],[2,3]]) == [[1,3]]\n"
        "def test_empty():\n    assert merge_intervals([]) == []\n"
        "def test_single():\n    assert merge_intervals([[1,4]]) == [[1,4]]\n"
        "def test_unsorted():\n    assert merge_intervals([[8,10],[1,3],[2,6]]) == [[1,6],[8,10]]\n"
        "def test_nested():\n    assert merge_intervals([[1,10],[2,3]]) == [[1,10]]\n"
        "def test_duplicate_starts():\n    assert merge_intervals([[1,2],[1,5],[6,7]]) == [[1,5],[6,7]]\n"
        "def test_contained_after_two():\n    assert merge_intervals([[1,2],[4,7],[5,6]]) == [[1,2],[4,7]]\n"
    ),
    "is_balanced": (
        "def test_ok():\n    assert is_balanced('([{}])') == True\n"
        "def test_empty():\n    assert is_balanced('') == True\n"
        "def test_wrong_type():\n    assert is_balanced('(]') == False\n"
        "def test_interleaved():\n    assert is_balanced('([)]') == False\n"
        "def test_unclosed():\n    assert is_balanced('(((') == False\n"
        "def test_extra_close():\n    assert is_balanced('())') == False\n"
        "def test_pair():\n    assert is_balanced('()') == True\n"
    ),
    "two_sum": (
        "def test_found():\n    assert two_sum([2,7,11,15], 9) == [0,1]\n"
        "def test_none():\n    assert two_sum([1,2,3], 7) is None\n"
        "def test_indices_not_values():\n    assert two_sum([3,3], 6) == [0,1]\n"
        "def test_no_reuse():\n    assert two_sum([3,2,4], 6) == [1,2]\n"
        "def test_first_pair():\n    assert two_sum([0,4,3,0], 0) == [0,3]\n"
        "def test_earliest_pair():\n    assert two_sum([1,2,3,4], 5) == [1,2]\n"
    ),
    "run_length_encode": (
        "def test_run():\n    assert run_length_encode('aaab') == 'a3b1'\n"
        "def test_empty():\n    assert run_length_encode('') == ''\n"
        "def test_single():\n    assert run_length_encode('a') == 'a1'\n"
        "def test_all_singletons():\n    assert run_length_encode('abc') == 'a1b1c1'\n"
        "def test_mixed():\n    assert run_length_encode('aabbbc') == 'a2b3c1'\n"
    ),
    "binary_search": (
        "def test_mid():\n    assert binary_search([1,3,5,7], 5) == 2\n"
        "def test_first():\n    assert binary_search([1,3,5,7], 1) == 0\n"
        "def test_last():\n    assert binary_search([1,3,5,7], 7) == 3\n"
        "def test_absent():\n    assert binary_search([1,3,5,7], 4) == -1\n"
        "def test_empty():\n    assert binary_search([], 5) == -1\n"
        "def test_single_hit():\n    assert binary_search([2], 2) == 0\n"
        "def test_single_miss():\n    assert binary_search([2], 3) == -1\n"
    ),
    "roman_to_int": (
        "def test_iv():\n    assert roman_to_int('IV') == 4\n"
        "def test_ix():\n    assert roman_to_int('IX') == 9\n"
        "def test_lviii():\n    assert roman_to_int('LVIII') == 58\n"
        "def test_big():\n    assert roman_to_int('MCMXCIV') == 1994\n"
        "def test_xl():\n    assert roman_to_int('XL') == 40\n"
        "def test_cd():\n    assert roman_to_int('CD') == 400\n"
        "def test_dcccxc():\n    assert roman_to_int('DCCCXC') == 890\n"
        "def test_xliv():\n    assert roman_to_int('XLIV') == 44\n"
    ),
    "gcd": (
        "def test_basic():\n    assert gcd(12, 8) == 4\n"
        "def test_coprime():\n    assert gcd(17, 5) == 1\n"
        "def test_multiple():\n    assert gcd(100, 10) == 10\n"
        "def test_equal():\n    assert gcd(7, 7) == 7\n"
        "def test_one():\n    assert gcd(1, 1) == 1\n"
        "def test_one_other():\n    assert gcd(1, 9) == 1\n"
        "def test_swapped():\n    assert gcd(36, 48) == 12\n"
    ),
    "flatten": (
        "def test_basic():\n    assert flatten([[1,2],[3]]) == [1,2,3]\n"
        "def test_empty():\n    assert flatten([]) == []\n"
        "def test_mixed():\n    assert flatten([[1,2],3,[4]]) == [1,2,3,4]\n"
        "def test_flat():\n    assert flatten([1,2,3]) == [1,2,3]\n"
        "def test_singletons():\n    assert flatten([[1],[2],[3]]) == [1,2,3]\n"
    ),
    "is_palindrome": (
        "def test_pal():\n    assert is_palindrome('aba') == True\n"
        "def test_not():\n    assert is_palindrome('ab') == False\n"
        "def test_empty():\n    assert is_palindrome('') == True\n"
        "def test_single():\n    assert is_palindrome('a') == True\n"
        "def test_even():\n    assert is_palindrome('abba') == True\n"
        "def test_even_not():\n    assert is_palindrome('abca') == False\n"
        "def test_long_pal():\n    assert is_palindrome('abcba') == True\n"
        "def test_case_sensitive():\n    assert is_palindrome('Aa') == False\n"
    ),
    "fizzbuzz": (
        "def test_one():\n    assert fizzbuzz(1) == ['1']\n"
        "def test_three():\n    assert fizzbuzz(3) == ['1','2','Fizz']\n"
        "def test_five():\n    assert fizzbuzz(5) == ['1','2','Fizz','4','Buzz']\n"
        "def test_fifteen():\n    assert fizzbuzz(15)[-1] == 'FizzBuzz'\n"
        "def test_zero():\n    assert fizzbuzz(0) == []\n"
    ),
}


def main():
    print("=== TestBench-Forge: hidden-mutant kill rate (the focus) ===")
    weaks, thoros = [], []
    for mid in testbench.MODULES:
        pool = testbench.get_mutant_pool(mid)
        wr, winfo = testbench.score_suite(mid, WEAK[mid])
        tr, tinfo = testbench.score_suite(mid, THOROUGH[mid])
        weaks.append(wr)
        thoros.append(tr)
        wstr = "gate-FAIL" if not winfo.get("gate") else f"{winfo['killed']}/{winfo['mutants']}"
        tstr = "gate-FAIL" if not tinfo.get("gate") else f"{tinfo['killed']}/{tinfo['mutants']}"
        print(f"  {mid:20s} mutants={len(pool):2d}  weak={wr:.3f} ({wstr})  "
              f"thorough={tr:.3f} ({tstr})  headroom={tr - wr:+.3f}")
    print(f"  -> mean: weak {sum(weaks)/len(weaks):.3f}  vs  thorough "
          f"{sum(thoros)/len(thoros):.3f}   (this is the live RFT demo arc)\n")

    print("=== non-gameability checks ===")
    # assert-False must fail the reference gate -> reward 0
    r, info = testbench.score_suite("merge_intervals", "def test_x():\n    assert False\n")
    print(f"  assert-False suite:        reward={r:.3f}  ({info.get('reason', 'gate ok')})")
    # an empty / no-tests suite -> gate fails -> 0
    r, info = testbench.score_suite("merge_intervals", "x = 1\n")
    print(f"  no-test suite:             reward={r:.3f}  ({info.get('reason', 'gate ok')})")

    print("\n=== headline diff (a bug the weak suite misses, the thorough suite catches) ===")
    bug = testbench.MODULES["is_balanced"]["extra_mutants"][0]  # ignores bracket type
    weak_kills = not testbench._run_suite_once(bug, WEAK["is_balanced"])
    thoro_kills = not testbench._run_suite_once(bug, THOROUGH["is_balanced"])
    print(f"  bug = 'ignores bracket type' (accepts '(]')")
    print(f"  weak suite catches it:     {weak_kills}")
    print(f"  thorough suite catches it: {thoro_kills}")


if __name__ == "__main__":
    main()
