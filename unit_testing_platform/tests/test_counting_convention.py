"""Counting convention tests: '&&' classification, lambdas, preprocessor policy.

Every expected value is hand-derived (CCN = 1 + number of decision points: if, for, while, case,
catch, logical &&, ||, ?) and does NOT come from running the analyzer. Snippets are valid C/C++.
"""
import textwrap

import pytest

from core.complexity import ComplexityEngine
from core.complexity.backend import AppBackend
from models.analysis_result import Language

LAMBDA1 = "(lambda at line 1)"


def analyze(tmp_path, src, language=Language.CPP, ext=None, **kw):
    ext = ext or (".c" if language is Language.C else ".cpp")
    path = tmp_path / f"t{ext}"
    path.write_text(textwrap.dedent(src))
    file_result, funcs = ComplexityEngine().analyze_file(path, f"t{ext}", language)
    return file_result, [(f.function, f.ccn) for f in funcs], funcs


# ----------------------------------------------------------------------------- && (C++ and C)
CPP_AMP = [
    ("forwarding-reference parameter is not a decision",
     "template <typename T>\nvoid process(T&& value)\n{\n    if (value > 10)\n    {\n        execute();\n    }\n}\n", [("process", 2)]),
    ("rvalue-reference parameter", "void f(int&& a) { g(a); }", [("f", 1)]),
    ("rvalue reference + if", "void f(std::string&& s, int n) { if (n) g(s); }", [("f", 2)]),
    ("auto&& local", "void f() { auto&& x = get(); if (x) h(); }", [("f", 2)]),
    ("auto&& in range-for", "void f(V& v) { for (auto&& e : v) use(e); }", [("f", 2)]),
    ("static_cast<T&&>", "template<class T> void f(T& t) { g(static_cast<T&&>(t)); }", [("f", 1)]),
    ("C-style cast to rvalue ref", "void f(int& t) { g((int&&)t); }", [("f", 1)]),
    ("local rvalue ref with brace init", "void f() { int&& r{5}; g(r); }", [("f", 1)]),
    ("user type rvalue ref local", "void f() { std::string&& s = get(); g(s); }", [("f", 1)]),
    ("function-pointer type with rvalue param", "void f() { void (*cb)(int&&) = nullptr; }", [("f", 1)]),
    ("template argument with rvalue ref", "void f() { std::function<void(int&&)> cb; }", [("f", 1)]),
    ("move constructor", "struct S { S(S&& o) noexcept : m(o.m) {} int m; };", [("S::S", 1)]),
    ("move assignment with if", "struct S { S& operator=(S&& o) { if (this != &o) m = o.m; return *this; } int m; };",
     [("S::operator =", 2)]),
    ("rvalue ref-qualified member", "struct S { int get() && { return 1; } };", [("S::get", 1)]),
    ("rvalue return type then real &&", "int&& f(bool a, bool b) { return a && b ? 1 : 2; }", [("f", 3)]),
    ("forwarding ref parameter AND real &&", "template<class T> void f(T&& v, bool b) { if (v && b) g(); }", [("f", 3)]),
    ("real && after rvalue param", "void f(int&& a, bool b) { if (a && b) {} }", [("f", 3)]),
    ("variadic forwarding pack", "template<class... A> void f(A&&... a) { g(static_cast<A&&>(a)...); }", [("f", 1)]),
    ("real && with assignment in the right operand", "void f(int a, int b) { if (a && (b = 3)) {} }", [("f", 3)]),
    ("real && as expression statement", "void f(int c) { c && g(); }", [("f", 2)]),
    ("lambda parameter T&&", "void f() { auto l = [](auto&& x) { return x; }; }",
     [("f", 1), (f"f::{LAMBDA1}", 1)]),
    ("lambda parameter with user type", "template<class T> void f() { auto l = [](T&& x) { return 1; }; }",
     [("f", 1), (f"f::{LAMBDA1}", 1)]),
]


@pytest.mark.parametrize("name,src,expected", CPP_AMP, ids=[c[0] for c in CPP_AMP])
def test_cpp_amp_amp(tmp_path, name, src, expected):
    assert analyze(tmp_path, src)[1] == expected


C_AMP = [
    ("basic", "int f(int a,int b){ int x = a && b; return x; }", [("f", 2)]),
    ("mixed with ||", "int f(int a,int b,int c){ return a && b || c; }", [("f", 3)]),
    ("chain", "int f(int a,int b,int c){ int x; x = a && b && c; return x; }", [("f", 3)]),
    # Regression: the previous heuristic treated this && as a reference because of the later '='.
    ("assignment inside right operand (while)", "void f(P* p){ int n; while (p && (n = next(p))) { use(n); } }", [("f", 3)]),
    ("assignment inside right operand (if)", "int f(int a){ int fd; if (a && (fd = open(\"x\",0)) > 0) { return fd; } return -1; }", [("f", 3)]),
    ("GNU label address is not a decision", "int f(int i){ static void* t[] = { &&a, &&b }; goto *t[i]; a: return 1; b: return 2; }", [("f", 1)]),
    ("&& in a string or comment", 'int f(int a){ /* a && b */ const char* s = "x && y"; return a; }', [("f", 1)]),
]


@pytest.mark.parametrize("name,src,expected", C_AMP, ids=[c[0] for c in C_AMP])
def test_c_amp_amp(tmp_path, name, src, expected):
    assert analyze(tmp_path, src, Language.C)[1] == expected


# ----------------------------------------------------------------------------- lambdas
def test_lambda_is_a_separate_function_and_not_part_of_the_enclosing_one(tmp_path):
    src = """\
        void process()
        {
            auto calculate = [](int value)
            {
                if (value > 10)
                    return true;

                return false;
            };
        }
        """
    file_result, rows, funcs = analyze(tmp_path, src)
    assert rows == [("process", 1), ("process::(lambda at line 3)", 2)]
    outer, lam = funcs
    assert (lam.start_line, lam.end_line) == (3, 9) and lam.parameters == 1
    assert any("lambda" in w.lower() for w in outer.warnings)      # visible note on the enclosing function


@pytest.mark.parametrize("name,src,expected", [
    ("outer decisions stay outer",
     "int f(int n) {\n if (n) {}\n auto g = [&](int v) { return v > 0 && v < 5; };\n return g(n);\n}",
     [("f", 2), ("f::(lambda at line 3)", 2)]),
    ("nested lambdas",
     "void f() { auto a = [](int x) { auto b = [](int y) { if (y) return 1; return 2; }; if (x) return b(x); return 0; }; }",
     [("f", 1), (f"f::{LAMBDA1}", 2), (f"f::{LAMBDA1}::{LAMBDA1}", 2)]),
    ("lambda as call argument", "void f(V& v) { std::for_each(v.begin(), v.end(), [](int x){ if (x) g(x); }); }",
     [("f", 1), (f"f::{LAMBDA1}", 2)]),
    ("mutable and trailing return type", "int f(int n) { auto g = [n](int a) mutable -> int { return a ? n : 0; }; return g(1); }",
     [("f", 1), (f"f::{LAMBDA1}", 2)]),
    ("no parameter list", "void f(int n) { auto g = [n]{ return n ? 1 : 0; }; }", [("f", 1), (f"f::{LAMBDA1}", 2)]),
    ("immediately invoked", "int f(int n) { return [&]{ if (n) return 1; return 0; }(); }", [("f", 1), (f"f::{LAMBDA1}", 2)]),
    ("structured binding is not a lambda", "void f(M& m) { auto [a, b] = get(); if (a) h(b); }", [("f", 2)]),
    ("array subscript is not a lambda", "int f(int* a, int i) { return a[i] ? a[i + 1] : 0; }", [("f", 2)]),
    ("attribute is not a lambda", "void f(int a) { [[maybe_unused]] int x = a; if (a) g(); }", [("f", 2)]),
])
def test_lambda_extraction(tmp_path, name, src, expected):
    assert analyze(tmp_path, src)[1] == expected


def test_lambda_extraction_is_off_for_c(tmp_path):
    # C has no lambdas: designated array initialisers must never be read as one.
    src = "int f(int i){ int a[3] = { [0] = 1, [2] = 3 }; if (i) return a[0]; return a[2]; }"
    assert analyze(tmp_path, src, Language.C)[1] == [("f", 2)]


def test_lambda_outside_a_function_is_reported_not_silently_dropped(tmp_path):
    file_result, rows, _ = analyze(tmp_path, "static auto cmp = [](int a, int b) { return a < b; };\nint f(int x) { return x; }\n")
    assert rows == [("f", 1)]
    assert any("Lambda outside any function" in w for w in file_result.warnings)


def test_unreadable_lambda_like_construct_is_warned(tmp_path):
    file_result, rows, funcs = analyze(tmp_path, "void f() { auto g = [](int a) requires true { return a; }; }")
    assert any("Lambda-like construct" in w for w in funcs[0].warnings + file_result.warnings)


# ----------------------------------------------------------------------------- preprocessor
PP = [
    ("#ifdef is not a decision", "int f(int x) {\n#ifdef DEBUG\n log(x);\n#endif\n return x;\n}", 1),
    ("#ifndef is not a decision", "int f(int x) {\n#ifndef NDEBUG\n check(x);\n#endif\n return x;\n}", 1),
    ("#if/#elif/#else are not decisions", "int f(int x) {\n#if A\n return 1;\n#elif B\n return 2;\n#else\n return 3;\n#endif\n}", 1),
    ("#if with && in its condition is not counted", "int f(int x) {\n#if defined(A) && defined(B)\n return 1;\n#endif\n return 0;\n}", 1),
    ("both branches analysed together (union)",
     "int f(int x) {\n#if defined(A)\n if (x) return 1;\n#else\n if (x > 1) return 2;\n#endif\n return 0;\n}", 3),
    ("#if 0 region is excluded", "int f(int x) {\n#if 0\n if (x) return 1;\n if (x > 5) return 2;\n#endif\n return 0;\n}", 1),
    ("#if 0 with live #else", "int f(int x) {\n#if 0\n if (x) return 1;\n#else\n if (x > 5) return 2;\n#endif\n return 0;\n}", 2),
    ("#if 1 excludes its #else", "int f(int x) {\n#if 1\n if (x) return 1;\n#else\n if (x>1) return 2; if (x>2) return 3;\n#endif\n return 0;\n}", 2),
    ("nested #if 0 inside live region", "int f(int x) {\n#ifdef A\n#if 0\n if (x) return 1;\n#endif\n if (x>2) return 3;\n#endif\n return 0;\n}", 2),
    ("#elif after #if 0 is live", "int f(int x) {\n#if 0\n if (x) return 1;\n#elif B\n if (x>2) return 3;\n#endif\n return 0;\n}", 2),
]


@pytest.mark.parametrize("name,src,ccn", PP, ids=[c[0] for c in PP])
def test_preprocessor_convention(tmp_path, name, src, ccn):
    assert analyze(tmp_path, src, Language.C)[1] == [("f", ccn)]


def test_dead_region_keeps_line_numbers_and_is_reported(tmp_path):
    src = "int a(void) { return 0; }\n#if 0\nint dead(int x) { if (x) return 1; return 0; }\n#endif\nint b(int x) { if (x) return 1; return 0; }\n"
    file_result, rows, funcs = analyze(tmp_path, src, Language.C)
    assert rows == [("a", 1), ("b", 2)] and funcs[1].start_line == 5
    assert any("Constant-false preprocessor region" in w for w in file_result.warnings)


def test_conditional_branch_warning_explains_the_union_convention(tmp_path):
    _, _, funcs = analyze(tmp_path, "int f(int x) {\n#ifdef A\n if (x) return 1;\n#endif\n return 0;\n}", Language.C)
    assert any("union of all configurations" in w for w in funcs[0].warnings)


def test_braces_split_by_conditional_compilation_are_flagged_not_silent(tmp_path):
    src = "int f(int x) {\n#if A\n    if (x) {\n#else\n    if (x > 2) {\n#endif\n        return 1;\n    }\n    return 0;\n}\n"
    file_result, rows, _ = analyze(tmp_path, src, Language.C)
    assert any("splits code blocks" in w for w in file_result.warnings)


def test_legacy_mode_reproduces_the_original_counting(tmp_path):
    path = tmp_path / "a.c"
    path.write_text("int f(int x) {\n#ifdef DEBUG\n log(x);\n#endif\n#ifndef Z\n y();\n#endif\n#if A\n z();\n#elif B\n w();\n#endif\n return x;\n}\n")
    legacy = AppBackend().analyze_file(str(path), cpp=False, preprocessor="legacy").function_list[0]
    default = AppBackend().analyze_file(str(path), cpp=False).function_list[0]
    assert legacy.cyclomatic_complexity == 1 + 3      # #ifdef, #if, #elif (upstream: #ifndef is not counted)
    assert default.cyclomatic_complexity == 1


def test_unknown_preprocessor_mode_is_rejected(tmp_path):
    path = tmp_path / "a.c"; path.write_text("int f(void){return 0;}\n")
    with pytest.raises(ValueError):
        AppBackend().analyze_file(str(path), cpp=False, preprocessor="bogus")


# ----------------------------------------------------------------------------- failure is never silent
def test_parse_failure_is_reported_as_failed_file(tmp_path):
    class Exploding:
        accepts_options = True
        def analyze_file(self, path, cpp=None):
            raise RecursionError("maximum recursion depth exceeded")
    path = tmp_path / "a.cpp"; path.write_text("int f(){return 0;}\n")
    file_result, funcs = ComplexityEngine(Exploding()).analyze_file(path, "a.cpp", Language.CPP)
    assert file_result.status.value == "Failed" and "RecursionError" in file_result.error and funcs == []


# ----------------------------------------------------------------------------- templates, folds, constructors
L1 = "f::(lambda at line 1)"
CPP_MORE = [
    ("enable_if with && in the template header", "template<class T, class = std::enable_if_t<A<T>::v && B<T>::v>> void f(T&& x) { if (x) g(); }", [("f", 2)]),
    ("requires clause with &&", "template<class T> requires (A<T> && B<T>) void f(T x) { if (x) g(); }", [("f", 2)]),
    ("noexcept(A && B) in the signature", "template<class T> void f(T x) noexcept(A<T>::v && B<T>::v) { if (x) g(); }", [("f", 2)]),
    ("if constexpr counts the if and its &&", "template<class T> int f(T x) { if constexpr (A<T>::v && B<T>::v) return 1; else return 0; }", [("f", 3)]),
    ("right fold expression: one decision", "template<class... A> bool f(A... a) { return (a && ...); }", [("f", 2)]),
    ("left fold expression", "template<class... A> bool f(A... a) { return (... && a); }", [("f", 2)]),
    ("binary fold expression: one decision per && written", "template<class... A> bool f(A... a) { return (true && ... && a); }", [("f", 3)]),
    ("fold over a trait", "template<class... A> bool f() { return (A::v && ...); }", [("f", 2)]),
    ("unnamed forwarding pack", "template<class... A> void f(A&&...) { g(); }", [("f", 1)]),
    ("named forwarding pack + if", "template<class... A> void f(A&&... a) { if (sizeof...(a)) g(); }", [("f", 2)]),
    ("pack inside std::function<void(A&&...)>", "template<class... A> void f() { std::function<void(A&&...)> cb; if (cb) cb(); }", [("f", 2)]),
    ("decltype(x)&& local", "void f(int x) { decltype(x)&& r = 5; g(r); }", [("f", 1)]),
    ("decltype(auto) return type with forwarding", "template<class T> decltype(auto) f(T&& t) { return static_cast<T&&>(t); }", [("f", 1)]),
    ("typename T::type&& local", "template<class T> void f() { typename T::type&& r = get(); use(r); }", [("f", 1)]),
    ("user-type rvalue reference in range-for", "void f(Vec& v) { for (Item&& e : v) use(e); }", [("f", 2)]),
    ("rvalue reference in an if-initialiser", "void f() { if (T&& x = get()) use(x); }", [("f", 2)]),
    ("operator&& overload definition", "bool operator&&(const A& a, const B& b) { return true; }", [("operator &&", 1)]),
    ("negations with real &&", "void f(bool done) { bool ok; while (!done && (ok = poll())) { use(ok); } }", [("f", 3)]),
    ("&= followed by a real &&", "void f(bool a,bool b,bool c) { bool ok = true; ok &= a && b; use(c); }", [("f", 2)]),
    ("static_assert is counted like any expression (documented)", "template<class T> void f() { static_assert(A<T>::v && B<T>::v, \"x\"); }", [("f", 2)]),
    ("lambda with explicit template parameters", "void f() { auto l = []<class T>(T&& x) { if (x) return 1; return 0; }; }", [("f", 1), (f"{L1}", 2)]),
    ("lambda capture with initialiser", "void f(int n) { auto l = [m = n * 2, &n](int a) { return a ? m : n; }; }", [("f", 1), (L1, 2)]),
    ("lambda with noexcept", "void f() { auto l = [](int a) noexcept { return a ? 1 : 0; }; }", [("f", 1), (L1, 2)]),
    ("lambda with noexcept(expr) and trailing return", "void f() { auto l = [](int a) noexcept(true) -> int { return a ? 1 : 0; }; }", [("f", 1), (L1, 2)]),
    ("lambda returning a lambda", "auto f() { return [](int a) { return [a](int b) { return a && b; }; }; }",
     [("f", 1), (L1, 1), (f"{L1}::(lambda at line 1)", 2)]),
    ("lambda assigned inside a constructor", "struct S { S() { cb = [](int a) { if (a) return 1; return 0; }; } int (*cb)(int); };",
     [("S::S", 1), ("S::S::(lambda at line 1)", 2)]),
    ("lambda in a default argument is not extracted, outer unaffected", "void g(std::function<int(int)> h = [](int a) { return a ? 1 : 0; }) { if (h) h(1); }", [("g", 2)]),
    ("two lambdas on one line", "void f() { auto a = [](int x){ return x ? 1 : 0; }; auto b = [](int y){ return y && 1; }; }",
     [("f", 1), (L1, 2), (L1, 2)]),
    # ---- constructors: decisions in the member-initialiser list belong to the constructor
    ("ctor init list: && and ?", "struct S { S(int a, int b) : ok(a && b), n(a ? 1 : 0) { } bool ok; int n; };", [("S::S", 3)]),
    ("out-of-class ctor with || and a body decision", "S::S(int a, int b) : ok(a || b) { if (a) g(); }", [("S::S", 3)]),
    ("brace member initialiser", "struct S { S(int a) : n{a ? 1 : 0}, m(2) { } int n, m; };", [("S::S", 2)]),
    ("noexcept ctor with init list", "struct S { S(int a) noexcept : n(a ? 1 : 0) { } int n; };", [("S::S", 2)]),
    ("base-class initialiser with nested parentheses", "struct S : B { S(int a) : B((a && 1) ? 1 : 0) { } };", [("S::S", 3)]),
    ("two constructors do not leak into each other", "struct S { S(int a) : n(a ? 1 : 0) {} S() : n(0) { } int n; };", [("S::S", 2), ("S::S", 1)]),
    ("ternary at namespace scope is not a ctor initialiser", "int a = c ? (y) : z;\nint f(int x){ return x ? 1 : 0; }", [("f", 2)]),
    ("default argument decisions are not the function's", "struct S { S(int a = x && y) { } };", [("S::S", 1)]),
    ("lambda inside an initialiser list: attributed to the constructor (documented)",
     "struct S { S(int a) : n([](int x){ return x ? 1 : 0; }(a)) { } int n; };", [("S::S", 2)]),
    ("out-of-class template member", "template<class T> int Box<T>::get() const { return v ? 1 : 0; }", [("Box<T>::get", 2)]),
    ("try/catch", "int f(){ try { g(); } catch (const A&) { return 1; } catch (...) { return 2; } return 0; }", [("f", 3)]),
    ("range-for with if constexpr", "template<class T> int f(T& v){ int c=0; for (auto& e : v) { if constexpr (X<T>) c += e; } return c; }", [("f", 3)]),
]


@pytest.mark.parametrize("name,src,expected", CPP_MORE, ids=[c[0] for c in CPP_MORE])
def test_cpp_templates_folds_lambdas_and_constructors(tmp_path, name, src, expected):
    assert sorted(analyze(tmp_path, src)[1]) == sorted(expected)


@pytest.mark.xfail(strict=True, reason="inherited parser limitation: a trailing C++20 'requires' clause makes the "
                                         "bundled core report a function called 'requires' instead of 'f'")
def test_limitation_trailing_requires_clause(tmp_path):
    src = "template<class T> void f(T x) requires (A<T> && B<T>) { if (x) g(); }"
    assert analyze(tmp_path, src)[1] == [("f", 2)]


@pytest.mark.xfail(strict=True, reason="inherited parser limitation: member functions of classes declared inside a "
                                         "function body are not extracted; their decisions stay in the enclosing function")
def test_limitation_local_class_member_functions(tmp_path):
    src = "void f() { struct L { int operator()(int a) const { return a ? 1 : 0; } }; }"
    assert sorted(analyze(tmp_path, src)[1]) == [("f", 1), ("f::L::operator ()", 2)]


# ----------------------------------------------------------------------------- C control flow and macros
C_MORE = [
    ("for with && and ||", "int f(int* a,int n,int ok,int b){ int c=0; for (int i = 0; i < n && ok; i++) if (a[i] || b) c++; return c; }", 5),
    ("nested ternary", "int f(int a,int b){ return a ? (b ? 1 : 2) : 3; }", 3),
    ("switch: each case counts, default does not", "int f(int x){ int y; switch(x){ case 1: case 2: y=1; break; case 3: y=2; break; default: y=0; } return y; }", 4),
    ("do-while with &&", "int f(int x,int y){ do { x--; } while (x > 0 && y); return x; }", 3),
    ("else-if chain", "int f(int a,int b,int c){ if(a){return 1;}else if(b){return 2;}else if(c){return 3;}else{return 4;} }", 4),
    ("GNU ?: operator", "int f(int a,int b){ return a ?: b; }", 2),
    ("while(1) counts", "void f(void){ while (1) { g(); } }", 2),
    ("negations mixed", "int f(int a,int b){ return !a && !b || (a && !b); }", 4),
    ("macro body is not expanded", "#define IS_OK(x) ((x) && (x) < 5)\nint f(int a){ return IS_OK(a) ? 1 : 0; }", 2),
    ("macro argument is counted", "void f(int a,int b){ CHECK(a && b); }", 2),
    ("multi-line macro with if/while is dropped", "#define SAFE_FREE(p) do { if (p) { free(p); (p) = 0; } } while (0)\nvoid f(char* p) { SAFE_FREE(p); }", 1),
    ("#define with a ternary is not counted", "#define MAX(a,b) ((a) > (b) ? (a) : (b))\nint f(int a,int b){ return MAX(a,b); }", 1),
    ("line continuation inside a macro", "#define M(x) \\\n  ((x) ? 1 : \\\n   (x) && 2)\nint f(int a){ return a; }", 1),
    ("keywords inside strings and comments", 'int f(int a){ /* if (a) for while */ const char* s = "if (a) && ||"; return a; }', 1),
]


@pytest.mark.parametrize("name,src,ccn", C_MORE, ids=[c[0] for c in C_MORE])
def test_c_control_flow_and_macros(tmp_path, name, src, ccn):
    assert analyze(tmp_path, src, Language.C)[1] == [("f", ccn)]


def test_include_of_a_commented_out_header_is_not_evidence():
    from tests.test_header_resolution import PLAIN, resolved
    got = resolved({"x.h": PLAIN, "m.c": b'/* #include "x.h" */\nint m(void){return 0;}\n',
                    "n.cpp": b'// #include "x.h"\nint n(){return 0;}\n'})
    assert got == {"x.h": (Language.C, True)}
