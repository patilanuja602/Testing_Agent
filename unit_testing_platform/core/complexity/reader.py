"""Application-owned C/C++ reader built ON TOP of the bundled Lizard reader.

Why this module exists
----------------------
The bundled core (``third_party/lizard``, upstream 1.24.3) is kept byte-identical to upstream
for every file that is not marked "modified". The corrections below are therefore NOT made
inside the vendored files: this module subclasses the upstream ``CLikeReader`` and replaces
four behaviours. Everything else (tokenizer, function detection, NLOC, token counting, the
counting of ``if/for/while/case/catch/||/?``) is still upstream code.

1. ``&&`` classification (logical AND vs. reference declarator)
   Upstream counts every ``&&`` token as a decision and then tries to cancel the ones that are
   rvalue references by looking for a following ``=``. That under-counts real decisions such
   as ``p && (n = next(p))`` (also in C) and over-counts ``for (auto&& e : v)``,
   ``static_cast<T&&>(x)``, ``std::function<void(int&&)>`` and lambda parameters ``(T&& x)``.
   :class:`AmpAmpStates` decides each ``&&`` from its token context and only counts the
   ones that are logical AND. It is deliberately conservative: it treats a ``&&`` as a
   reference only on syntactic evidence that cannot be a logical AND (see ``_decide``).
   Anything ambiguous is counted as logical AND (the established convention).

2. Lambda extraction (C++ only)
   A lambda body is reported as its own function (``outer::(lambda at line N)``) and its
   decisions are no longer added to the enclosing function. This is the same convention the
   upstream core applies to nested functions in other languages. Detection is structural
   (introducer ``[...]`` + optional template/parameter list + specifiers + ``{``); a
   construct that looks like a lambda but cannot be read is reported as a parser warning and
   is never silently guessed.

3. Constructor initialiser lists (C++)
   Decisions in ``S() : a(x && y), b(c ? 1 : 0) {}`` are executed by the constructor but the core
   restarts the count when the body begins, so upstream drops them. They are added back.

4. Preprocessor policy
   Compile-time directives are not runtime decisions. By default no directive adds to the
   complexity (upstream added +1 for ``#if``, ``#ifdef`` and ``#elif`` but not for
   ``#ifndef``/``#else``, which is inconsistent). Regions that are dead for every
   configuration (``#if 0``; the ``#else`` part of ``#if 1``) are skipped. All other
   conditional branches are analysed together. ``preprocessor="legacy"`` restores the
   upstream counting for comparison with reports produced by the original tool.
"""
from __future__ import annotations

import re
from typing import Callable, List, Optional, Tuple

from third_party.lizard.lizard_languages.clike import CLikeNestingStackStates, CLikeReader
from third_party.lizard.lizard_languages.clike_states import CLikeStates
from third_party.lizard.lizard_languages.code_reader import CodeStateMachine

PREPROCESSOR_IGNORE = "ignore"     # default: directives are not decision points
PREPROCESSOR_LEGACY = "legacy"     # upstream Lizard 1.24.3 behaviour (#if/#ifdef/#elif = +1)

WarnFn = Callable[[int, str], None]

_BUILTIN_TYPE_WORDS = frozenset({
    "auto", "int", "char", "short", "long", "float", "double", "bool", "void", "signed", "unsigned",
    "wchar_t", "char8_t", "char16_t", "char32_t", "const", "volatile",
})
# A binary operator needs a left operand, so '&&' directly after one of these can only be the
# unary GNU "address of label" operator (``&&label``), never a decision.
_UNARY_PREV = frozenset({"=", "(", ",", "return", "[", "?", "{"})
# After one of these tokens a '[' starts a lambda introducer (and not a subscript, an array
# declarator or a structured binding such as ``auto [a, b]``).
_INTRODUCER_PREV = frozenset({"=", "(", ",", "return", "{", ";", "?", ":"})
# Tokens that can never start the right operand of '&&'.
_NO_OPERAND_NEXT = frozenset({">", ")", ",", ";", "{", "=", "]", "}", "->"})
# Token before the '(' of an expression group: tells ``(pack && ...)`` (a fold expression) from the
# parameter list ``f(A&&...)``.
_EXPR_PREV = frozenset({"return", "if", "while", "switch", "for", "=", "&&", "||", "!", "?", ":", ",", "(", "{", ";",
                        "static_assert", "noexcept", "requires", "co_return", "co_yield", "co_await",
                        "+", "-", "*", "/", "==", "!=", "<", ">"})
_STATEMENT_WORDS = frozenset({
    "return", "case", "throw", "else", "do", "goto", "delete", "new", "co_return", "co_yield", "co_await",
    "sizeof", "typeid", "default", "if", "while", "for", "switch", "using", "namespace", "and", "or", "not",
})
_DECL_BOUNDARY = frozenset({";", "{", "}"})
_CONTROL_WORDS = frozenset({"if", "while", "for", "switch"})
_LAMBDA_SPEC_WORDS = frozenset({"mutable", "constexpr", "consteval", "static"})


def _is_ident(token: Optional[str]) -> bool:
    return bool(token) and (token[0].isalpha() or token[0] == "_")


# --------------------------------------------------------------------------- constructor initialiser lists
class _InitListShared:
    """Decisions found inside a constructor's member-initialiser list (``S() : a(x && y), b(c ? 1 : 0) {}``).
    The core restarts a function's count when its body begins, which silently drops them; they
    are collected here and added once the body starts."""
    __slots__ = ("active", "extra", "and_extra")

    def __init__(self) -> None:
        self.active, self.extra, self.and_extra = False, 0, 0


class InitListStates(CodeStateMachine):
    """C++ only. Active from the ':' that follows a parameter list (at class/namespace scope, i.e.
    outside any function body) to the '{' that opens the constructor body."""

    def __init__(self, context, shared: _InitListShared, conditions) -> None:
        super().__init__(context)
        self._shared, self._conditions = shared, conditions
        self._prev: Optional[str] = None
        self._parens = self._braces = 0
        self._fobj = None

    def __call__(self, token, reader=None):
        sh = self._shared
        if not sh.active:
            if token == ":" and self._prev in (")", "noexcept") and self.context.last_function is None:
                sh.active, sh.extra, sh.and_extra = True, 0, 0
                self._parens = self._braces = 0
                self._fobj = self.context.current_function
        else:
            self._active(token)
        self._prev = token

    def _active(self, token: str) -> None:
        sh = self._shared
        if token == "(":
            self._parens += 1
        elif token == ")":
            self._parens -= 1
        elif token == "{":
            if self._parens == 0 and self._braces == 0 and self._prev in (")", "}"):
                fn = self.context.current_function
                if fn is self._fobj:
                    # CLikeStates has just confirmed the function (count reset to 1): add what was lost.
                    fn.cyclomatic_complexity += sh.extra
                    if sh.and_extra:
                        fn.logical_and_count = getattr(fn, "logical_and_count", 0) + sh.and_extra
                sh.active = False
            else:
                self._braces += 1
        elif token == "}":
            self._braces -= 1
            if self._braces < 0:
                sh.active = False
        elif token == ";" and self._parens == 0 and self._braces == 0:
            sh.active = False          # it was not a constructor initialiser list
        elif token in self._conditions:
            sh.extra += 1


# --------------------------------------------------------------------------- && classifier
class _Pending:
    __slots__ = ("func", "prev", "chain", "chain_prev", "chain_prev2", "in_lambda_params", "la", "after_decltype")

    def __init__(self, func, prev, chain, chain_prev, chain_prev2, in_lambda_params, after_decltype=False):
        self.after_decltype = after_decltype
        self.func, self.prev, self.chain = func, prev, chain
        self.chain_prev, self.chain_prev2, self.in_lambda_params = chain_prev, chain_prev2, in_lambda_params
        self.la: List[str] = []


class AmpAmpStates(CodeStateMachine):
    """Counts ``&&`` only where it is a logical AND. See the module docstring."""

    _HISTORY = 120
    _UNKNOWN = "<?>"

    def __init__(self, context, cpp: bool = True, init_list: Optional[_InitListShared] = None) -> None:
        super().__init__(context)
        self.cpp = cpp
        self._init_list = init_list
        self._hist: List[str] = []
        self._seen = 0
        self._pending: List[_Pending] = []
        self._brackets: List[Tuple[str, bool]] = []   # ('[', is_introducer) | ('(', is_lambda_params) | others
        self._after_introducer = False
        self._lt_depth = 0            # inside the '<...>' template parameter list of a lambda

    # The class counts through ``__call__`` (one call per token); the base class state hook is unused.
    def __call__(self, token, reader=None):
        self._step(token)

    def statemachine_before_return(self):
        for p in self._pending:
            self._apply(p, self._decide(p, final=True))
        self._pending = []

    # ---- token step
    def _step(self, token: str) -> None:
        # 1. feed look-ahead of earlier '&&' and resolve what is decidable
        still: List[_Pending] = []
        for p in self._pending:
            p.la.append(token)
            verdict = self._decide(p, final=len(p.la) >= 2)
            if verdict is None:
                still.append(p)
            else:
                self._apply(p, verdict)
        self._pending = still
        # 2. bracket tracking (needed to recognise lambda parameter lists)
        in_lambda_params = bool(self._brackets) and self._brackets[-1] == ("(", True)
        if token == "&&":
            chain, chain_prev, chain_prev2 = self._walk_chain()
            self._pending.append(_Pending(self.context.current_function, self._hist[-1] if self._hist else None,
                                          chain, chain_prev, chain_prev2, in_lambda_params,
                                          self._after_decltype_group()))
        self._track_brackets(token)
        self._hist.append(token)
        self._seen += 1
        if len(self._hist) > self._HISTORY:
            del self._hist[: len(self._hist) - self._HISTORY]

    def _after_decltype_group(self) -> bool:
        """True if the previous token closes a ``decltype( ... )`` group (``decltype(x)&& r``)."""
        hist = self._hist
        if not hist or hist[-1] != ")":
            return False
        depth = 0
        for i in range(len(hist) - 1, -1, -1):
            if hist[i] == ")":
                depth += 1
            elif hist[i] == "(":
                depth -= 1
                if depth == 0:
                    return i >= 1 and hist[i - 1] == "decltype"
        return False

    def _track_brackets(self, token: str) -> None:
        prev = self._hist[-1] if self._hist else None
        if self._lt_depth:                       # '[]<class T>(T&& x)': keep the introducer across '<...>'
            self._lt_depth += (token == "<") - (token == ">")
            if not self._lt_depth:
                self._after_introducer = True
            return
        if token == "<" and self._after_introducer:
            self._lt_depth, self._after_introducer = 1, False
            return
        if token == "[":
            introducer = self.cpp and prev in _INTRODUCER_PREV
            self._brackets.append(("[", introducer))
            self._after_introducer = False
        elif token == "]":
            introducer = False
            while self._brackets:
                kind, flag = self._brackets.pop()
                if kind == "[":
                    introducer = flag
                    break
            self._after_introducer = introducer
        elif token == "(":
            self._brackets.append(("(", self._after_introducer))
            self._after_introducer = False
        elif token == ")":
            while self._brackets:
                kind, _ = self._brackets.pop()
                if kind == "(":
                    break
            self._after_introducer = False
        else:
            self._after_introducer = False
        if len(self._brackets) > 200:          # unbalanced input: never grow without bound
            self._brackets = self._brackets[-100:]

    def _walk_chain(self):
        """Walk back over a type-like token chain (``std::vector<int>``, ``const T*``...) that
        ends right before the current ``&&``. Returns (chain, token_before_chain, token_before_that)."""
        hist, i, chain, depth = self._hist, len(self._hist) - 1, [], 0
        while i >= 0:
            t = hist[i]
            if depth:
                if t == ">":
                    depth += 1
                elif t == "<":
                    depth -= 1
                chain.append(t)
            elif t == ">":
                depth = 1
                chain.append(t)
            elif (_is_ident(t) and t not in _STATEMENT_WORDS) or t in ("::", "*", "&", "..."):
                chain.append(t)
            else:
                break
            i -= 1
        if depth:                                  # angle brackets never closed within the window
            return chain, self._UNKNOWN, self._UNKNOWN
        if i < 0:
            before = None if self._seen <= len(hist) else self._UNKNOWN
            return chain, before, None
        return chain, hist[i], (hist[i - 1] if i >= 1 else None)

    # ---- decision
    def _decide(self, p: _Pending, final: bool) -> Optional[str]:
        """'logical' | 'ref' | 'unary', or None while more look-ahead is needed."""
        la1 = p.la[0] if p.la else None
        la2 = p.la[1] if len(p.la) > 1 else None
        if la1 is None:
            return "logical" if final else None
        # Unary GNU label address: ``&&label`` after '=', '(', ',', 'return', '[', '?', '{'.
        if p.prev in _UNARY_PREV and _is_ident(la1):
            return "unary"
        # E1: a type keyword right before: ``auto&&``, ``int&&``, ``const&&``, ``decltype(x)&&``.
        if p.prev in _BUILTIN_TYPE_WORDS or p.after_decltype:
            return "ref"
        # Fold expressions: ``(pack && ...)``, ``(init && ... && pack)`` are logical ANDs (one decision
        # per '&&' written); ``A&&... a`` / ``f(A&&...)`` declare a reference pack.
        if la1 == "...":
            if la2 is None and not final:
                return None
            if la2 == "&&":
                return "logical"
            if la2 == ")" and p.chain_prev == "(" and p.chain_prev2 in _EXPR_PREV:
                return "logical"
            return "ref"
        # E2: the next token cannot start an operand: ``T&&>``, ``(T&&)``, ``T&&,``, ``T&&...``,
        #     ``f() && {``, ``f() && -> ...``.
        if la1 in _NO_OPERAND_NEXT:
            return "ref"
        if la1 == "noexcept":
            if la2 is None and not final:
                return None
            return "logical" if la2 == "(" else "ref"
        if la1 in ("override", "final"):
            if la2 is None and not final:
                return None
            return "ref" if la2 in ("{", ";", "=") else "logical"
        if not self.cpp:
            return "logical"
        # E4: inside a lambda parameter list ``[](T&& x)``.
        if p.in_lambda_params:
            return "ref"
        # E7/E9: a declaration ``T&& name = ...;`` / ``T&& name{...};`` / ``T&& name;`` at statement
        # start, or the declaration of an ``if/while/for/switch`` (``for (T&& e : v)``).
        if _is_ident(la1) and p.chain:
            if la2 is None and not final:
                return None
            if la2 in ("=", "{", ";") and p.chain_prev in (None, *_DECL_BOUNDARY):
                return "ref"
            if la2 in ("=", ":", "{") and p.chain_prev == "(" and p.chain_prev2 in _CONTROL_WORDS:
                return "ref"
        return "logical"

    def _apply(self, p: _Pending, verdict: str) -> None:
        if verdict == "logical":
            if self._init_list is not None and self._init_list.active:
                self._init_list.extra += 1          # added when the constructor body starts
                self._init_list.and_extra += 1
                return
            p.func.cyclomatic_complexity += 1
            # Testing aid: '&&' counted inside a confirmed function body (a '&&' in a parameter list
            # is added to a function that is reset when the body starts, so it is not tallied).
            if self.context.last_function is p.func:
                p.func.logical_and_count = getattr(p.func, "logical_and_count", 0) + 1


# --------------------------------------------------------------------------- lambdas
class LambdaStates(CodeStateMachine):
    """Recognises ``[captures](params) specifiers -> ret { body }`` and starts a separate function
    for the body (inside function bodies only). Constructs that look like a lambda but cannot be
    read completely are reported through ``warn`` and left untouched."""

    def __init__(self, context, warn: WarnFn) -> None:
        super().__init__(context)
        self._warn = warn
        self._prev: Optional[str] = None
        self._state = self._idle
        self._depth = 0
        self._cap_line = 0
        self._cap_empty = True
        self._params: List[str] = []
        self._pdepth = 0
        self._adepth = 0
        self.extracted = 0

    def __call__(self, token, reader=None):
        self._state(token)
        self._prev = token

    # ---- states
    def _idle(self, token: str) -> None:
        if token == "[" and self._prev in _INTRODUCER_PREV:
            self._cap_line = self.context.current_line
            self._depth, self._cap_empty = 1, True
            self._state = self._capture

    def _abort(self, token: str, message: Optional[str]) -> None:
        if message:
            self._warn(self._cap_line, message)
        self._state = self._idle
        self._prev = None            # the aborted token must not be taken as an introducer context
        self._idle(token)

    def _capture(self, token: str) -> None:
        if token == "[" and self._cap_empty and self._depth == 1:
            self._state = self._idle           # '[[attribute]]'
            return
        self._cap_empty = False
        if token in ("[", "(", "{"):
            self._depth += 1
        elif token in ("]", ")", "}"):
            self._depth -= 1
            if self._depth == 0:
                self._params, self._state = [], self._post_capture
        elif token == ";":
            self._abort(token, None)

    def _post_capture(self, token: str) -> None:
        if token == "(":
            self._pdepth, self._adepth = 1, 0
            self._state = self._params_state
        elif token == "<":
            self._depth = 1
            self._state = self._template_params
        elif token == "{":
            self._begin_body()
        elif token in _LAMBDA_SPEC_WORDS or token in ("noexcept", "->"):
            self._specs(token)
        else:
            self._abort(token, None)           # e.g. ``[0] = 1`` (designated initialiser): not a lambda

    def _template_params(self, token: str) -> None:
        if token == "<":
            self._depth += 1
        elif token == ">":
            self._depth -= 1
            if self._depth == 0:
                self._state = self._post_capture
        elif token in (";", "{", "}"):
            self._abort(token, MSG_UNREADABLE_LAMBDA)

    def _params_state(self, token: str) -> None:
        if token in ("(", "[", "{"):
            self._pdepth += 1
        elif token in (")", "]", "}"):
            self._pdepth -= 1
            if self._pdepth == 0:
                self._state = self._specs
                return
        elif token == ";":
            self._abort(token, MSG_UNREADABLE_LAMBDA)
            return
        if token == "<":
            self._adepth += 1
        elif token == ">":
            self._adepth = max(0, self._adepth - 1)
        if self._pdepth == 1 and token not in (")", "void") and not (token == "," and self._adepth):
            self._params.append(token)

    def _specs(self, token: str) -> None:
        if token in _LAMBDA_SPEC_WORDS:
            self._state = self._specs
        elif token == "noexcept":
            self._state = self._noexcept
        elif token == "->":
            self._depth = 0
            self._state = self._return_type
        elif token == "{":
            self._begin_body()
        elif token == "[":                     # [[attribute]] after the parameter list
            self._depth = 1
            self._state = self._skip_attribute
        else:                                   # 'requires', 'throw(...)', or something that is not a lambda
            self._abort(token, MSG_UNREADABLE_LAMBDA)

    def _skip_attribute(self, token: str) -> None:
        if token == "[":
            self._depth += 1
        elif token == "]":
            self._depth -= 1
            if self._depth == 0:
                self._state = self._specs
        elif token in (";", "{", "}"):
            self._abort(token, MSG_UNREADABLE_LAMBDA)

    def _noexcept(self, token: str) -> None:
        if token == "(":
            self._depth = 1
            self._state = self._noexcept_expr
        else:
            self._state = self._specs
            self._specs(token)

    def _noexcept_expr(self, token: str) -> None:
        if token == "(":
            self._depth += 1
        elif token == ")":
            self._depth -= 1
            if self._depth == 0:
                self._state = self._specs

    def _return_type(self, token: str) -> None:
        if token in ("(", "<", "["):
            self._depth += 1
        elif token in (")", ">", "]"):
            self._depth -= 1
        elif token == "{" and self._depth <= 0:
            self._begin_body()
        elif token in (";", "=", "}"):
            self._abort(token, MSG_UNREADABLE_LAMBDA)

    def _begin_body(self) -> None:
        ctx = self.context
        outer = ctx.last_function
        if outer is None:
            # Not inside a function body (namespace/class-scope initialiser): the structure is
            # recognised, but extraction there would disturb the surrounding parse. Say so.
            self._warn(self._cap_line, MSG_LAMBDA_OUTSIDE_FUNCTION)
        else:
            label = f"(lambda at line {self._cap_line})"
            ctx.push_new_function(label)
            fn = ctx.current_function
            fn.name = fn.long_name = f"{outer.name}::{label}"
            fn.start_line = self._cap_line
            for t in self._params:
                ctx.parameter(t)
            self.extracted += 1
        self._state = self._idle
        self._prev = "{"


MSG_UNREADABLE_LAMBDA = ("Lambda-like construct could not be read completely: its decisions stay in the "
                         "enclosing function and may be mis-counted")
MSG_LAMBDA_OUTSIDE_FUNCTION = ("Lambda outside any function body (namespace/class scope): not extracted; "
                               "its decisions are not attributed to a function")
MSG_PP_UNBALANCED = "Unbalanced preprocessor conditionals (#else/#elif/#endif without #if): the file may be incomplete"
MSG_PP_DEAD = "Constant-false preprocessor region (#if 0 / #else of #if 1) was excluded from the analysis"


# --------------------------------------------------------------------------- the reader
_COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
_INT_RE = re.compile(r"^\(?\s*(\d+)\s*\)?$")


def _literal_condition(expression: str) -> Optional[bool]:
    """True/False for a plain decimal literal condition (``0``, ``1``, ``(0)``), else None."""
    text = _COMMENT_RE.sub(" ", expression).replace("\\\n", " ").strip()
    m = _INT_RE.match(text)
    return (int(m.group(1)) != 0) if m else None


class _PPFrame:
    __slots__ = ("parent_skip", "taken", "skip", "had_dead")

    def __init__(self, parent_skip: bool, taken: bool, skip: bool):
        self.parent_skip, self.taken, self.skip, self.had_dead = parent_skip, taken, skip, skip and not parent_skip


class AppCLikeReader(CLikeReader):
    """Upstream C/C++ reader with the three corrections described in the module docstring."""

    def __init__(self, context, cpp: bool = True, preprocessor: str = PREPROCESSOR_IGNORE) -> None:
        super().__init__(context)
        if preprocessor not in (PREPROCESSOR_IGNORE, PREPROCESSOR_LEGACY):
            raise ValueError(f"unknown preprocessor mode {preprocessor!r}")
        self.cpp = cpp
        self.preprocessor = preprocessor
        self.parser_warnings: List[Tuple[int, str]] = []
        self.lambda_states = LambdaStates(context, self._warn) if cpp else None
        # '&&' is counted by AmpAmpStates (only where it is a logical AND), not by the generic counter.
        self.conditions.discard("&&")
        states: List[CodeStateMachine] = [CLikeStates(context)]
        if self.lambda_states is not None:
            states.append(self.lambda_states)       # must run before the nesting stack sees '{'
        states.append(CLikeNestingStackStates(context))
        init_list = _InitListShared() if cpp else None
        states.append(AmpAmpStates(context, cpp=cpp, init_list=init_list))
        if init_list is not None:
            states.append(InitListStates(context, init_list, self.conditions))
        self.parallel_states = tuple(states)
        self._pp_stack: List[_PPFrame] = []
        self._pp_skip = False
        self._dead_reported = False

    def _warn(self, line: int, message: str) -> None:
        item = (line, message)
        if item not in self.parser_warnings:
            self.parser_warnings.append(item)

    # ---- preprocessor policy
    def _directive(self, name: str, rest: str) -> None:
        if name in ("if", "ifdef", "ifndef"):
            literal = _literal_condition(rest) if name == "if" else None
            parent = self._pp_skip
            skip = parent or literal is False
            frame = _PPFrame(parent, taken=bool(literal) and not parent, skip=skip)
            self._pp_stack.append(frame)
            self._pp_skip = skip
            if frame.had_dead:
                self._dead_reported = True
        elif name == "elif":
            if not self._pp_stack:
                self._warn(self.context.current_line, MSG_PP_UNBALANCED)
                return
            f = self._pp_stack[-1]
            literal = _literal_condition(rest)
            if f.parent_skip or f.taken:
                f.skip = True
                f.had_dead = f.had_dead or not f.parent_skip
            elif literal is False:
                f.skip = True
                f.had_dead = True
            else:
                f.skip = False
                f.taken = literal is True
            self._pp_skip = f.skip
            self._dead_reported = self._dead_reported or f.had_dead
        elif name == "else":
            if not self._pp_stack:
                self._warn(self.context.current_line, MSG_PP_UNBALANCED)
                return
            f = self._pp_stack[-1]
            f.skip = f.parent_skip or f.taken
            if f.taken and not f.parent_skip:
                f.had_dead = True
                self._dead_reported = True
            self._pp_skip = f.skip
        elif name == "endif":
            if not self._pp_stack:
                self._warn(self.context.current_line, MSG_PP_UNBALANCED)
                return
            self._pp_stack.pop()
            self._pp_skip = self._pp_stack[-1].skip if self._pp_stack else False

    def preprocess(self, tokens):
        tilde = False
        for token in tokens:
            if token == "~":
                tilde = True
                continue
            if tilde:
                tilde = False
                if not self._pp_skip:
                    yield "~" + token
                continue
            if token.isspace() and token != "\n":
                continue
            macro = self.macro_pattern.match(token)
            if macro:
                name, rest = macro.group(1), macro.group(2)
                self._directive(name, rest)
                if (self.preprocessor == PREPROCESSOR_LEGACY and name in ("if", "ifdef", "elif")
                        and not self._pp_skip):
                    self.context.add_condition()
                elif name == "include" and not self._pp_skip:
                    yield "#include"
                    yield rest or "\"\""
                for _ in rest.split("\n")[1:]:
                    yield "\n"
            elif self._pp_skip:
                for _ in range(token.count("\n")):   # keep line numbers; the code itself is excluded
                    yield "\n"
            else:
                yield token

    def eof(self):
        if self._dead_reported:
            self._warn(0, MSG_PP_DEAD)
        if self._pp_stack:
            self._warn(0, MSG_PP_UNBALANCED)
