/* Fixture: '&&' in C is always a logical AND (or the GNU label-address operator).
 * Expected values (tests/fixtures/expected.json) are hand-derived: CCN = 1 + decisions.
 * Validity: gcc -std=gnu11 -fsyntax-only tests/fixtures/c/amp_amp_c.c */
extern int next(int);
extern void use(int);

int and_basic(int a, int b) { /* START and_basic */
    return a && b;
} /* END and_basic */

int and_assign_in_cond(int p) { /* START and_assign_in_cond */
    int n;
    while (p && (n = next(p))) {
        use(n);
    }
    return p;
} /* END and_assign_in_cond */

int and_or_mix(int a, int b, int c) { /* START and_or_mix */
    return a && b || c;
} /* END and_or_mix */

int and_chain(int a, int b, int c) { /* START and_chain */
    int x;
    x = a && b && c;
    return x;
} /* END and_chain */

int and_stmt(int c) { /* START and_stmt */
    c && next(c);
    return c;
} /* END and_stmt */

int label_table(int i) { /* START label_table */
    static void *t[] = { &&l0, &&l1 };
    goto *t[i];
l0: return 1;
l1: return 2;
} /* END label_table */

int and_fd(int a) { /* START and_fd */
    int fd;
    if (a && (fd = next(a)) > 0) {
        return fd;
    }
    return -1;
} /* END and_fd */
