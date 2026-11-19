# Preprocessor conditions: what the reported complexity means

The analyzer reads source text. It does **not** run the C/C++ preprocessor, so it never knows which
`#if` branch a particular build compiles and it does not expand macros. This page states what is
reported, and where that differs from the code of one compiled configuration. Every row below is
reproduced by `tests/test_preprocessor_configurations.py` (reference = the same file run through
`gcc -E -P -D...` and analysed; expected numbers hand-derived) using `tests/fixtures/c/config_variants.c`.

## What is reported

* `#if/#ifdef/#ifndef/#elif/#else/#endif` lines add **nothing** (compile-time, not runtime decisions).
* `#if 0` regions and the `#else` part of `#if 1` are excluded: they are dead in every configuration.
* All other branches are analysed **together** (the "union of all configurations"): the decisions of
  every alternative branch are added up.
* Macros are **not expanded**: a decision written in a macro *argument* is counted, a decision inside
  a macro *body* is not counted at the place the macro is used.

## Where the result differs from one compiled configuration

| # | Situation | Union (reported) | One configuration | Direction |
|---|---|---|---|---|
| A | Alternative branches with different decisions (`#ifdef MODE_FAST` 2 ifs / `#else` 1 if) | 4 | 3 (`MODE_FAST`) or 2 (default) | **over-reports** (sum of branches) |
| B | Optional feature adds one `if` to shared code | 2 | 2 with the feature, 1 without | equals the richest configuration |
| C | Decisions inside a macro body (`CLAMP(v)` = two `?:`) | 1 | 3 | **under-reports** (macro not expanded) |
| D | Macro whose body depends on the configuration (`CHK(x)` is an `if` only when `SAFE`) | 1 | 2 (`SAFE`) or 1 | **under-reports** |
| E | Same function defined in each branch | two entries (2 and 2) | one entry | duplicate entries; only one exists in a build |
| F | `#if 0` code | 1 | 1 | exact |
| G | A branch that opens a block the other branch does not (`#if A  if (x) {  #else  if (y) {  #endif`) | function may be missing or mis-parsed | the compiled code is well-formed | **unreliable**; flagged by a file warning, but functions can still be lost |

So the union figure is **not an upper bound and not a lower bound** of any build: rows A/E push it
up, rows C/D push it down. It is a defined, reproducible *source-level* measure.

Other effects of the same cause (not separately measured):

* `#include` is not followed: complexity in inline functions of other headers is attributed to those headers only.
* Conditions in `#if` expressions (`#if A && B`) are never counted (tested). C++ compile-time constructs are different:
  `static_assert(A && B)` **is** counted like an ordinary expression and so is `if constexpr` (both tested), because the
  core does not treat them as compile-time.

## When a number for one configuration is required

Preprocess outside the application with your real build flags and analyse the output:

```
gcc -E -P -DFLAGS... -Iinclude src/module.c > module.i.c     # use the compiler of your build
```

then upload `module.i.c`. Macros are then expanded and inactive branches are gone (as in the
"One configuration" column above). Two caveats: the preprocessed file also contains the bodies of every
included header, and line numbers refer to the preprocessed text, not to the original file.
Built-in per-configuration analysis (defines supplied in the UI) is not implemented.

## Choosing the counting mode

`core.complexity.backend.AppBackend(preprocessor="legacy")` reproduces upstream Lizard's counting
(+1 for `#if/#ifdef/#elif`, nothing for `#ifndef/#else`) to compare with reports from the original tool.
The UI always uses the default (`ignore`).
