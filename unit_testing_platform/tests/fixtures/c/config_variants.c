/* Fixture for docs/PREPROCESSOR_LIMITATIONS.md: where the analysis of ALL conditional branches together
 * differs from the code of one compiled configuration. Each function is one category. The numbers
 * (union vs. each configuration) are hand-derived in tests/test_preprocessor_configurations.py.
 * Validity: gcc -std=gnu11 -fsyntax-only -DMODE_FAST -DFEATURE_X -DSAFE -DUSE_A tests/fixtures/c/config_variants.c  (and without the -D flags) */
extern void log_msg(int);

/* A: alternative branches with different decisions */
int mode_select(int x) {
#ifdef MODE_FAST
    if (x > 10) return 1;
    if (x > 20) return 2;
#else
    if (x > 5) return 3;
#endif
    return 0;
}

/* B: an optional feature adds a decision to otherwise shared code */
int feature(int a) {
    int r = 0;
#ifdef FEATURE_X
    if (a) r++;
#endif
    return r;
}

/* C: decisions hidden in a macro BODY (macros are not expanded by the analysis) */
#define CLAMP(v) ((v) < 0 ? 0 : ((v) > 9 ? 9 : (v)))
int use_clamp(int v) {
    return CLAMP(v);
}

/* D: a macro whose body depends on the configuration */
#ifdef SAFE
#define CHK(x) if (!(x)) return -1;
#else
#define CHK(x)
#endif
int checked(int a) {
    CHK(a)
    return a;
}

/* E: the same function defined differently per configuration */
#ifdef USE_A
int pick(int x) { if (x) return 1; return 0; }
#else
int pick(int x) { return x ? 2 : 3; }
#endif

/* F: constant-false code is excluded by the analysis (equals every configuration) */
int dead_code(int x) {
#if 0
    if (x) log_msg(1);
#endif
    return x;
}
