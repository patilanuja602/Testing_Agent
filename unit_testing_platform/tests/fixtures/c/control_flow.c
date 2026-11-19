/* Fixture: control-flow constructs in C. Expected CCN values are hand-derived (1 + decisions):
 * if / else if / for / while / do-while / case / ?: / && / ||. 'else' and 'default' add nothing.
 * Validity: gcc -std=gnu11 -fsyntax-only tests/fixtures/c/control_flow.c */
int for_and_or(int *a, int n, int ok, int b) { /* START for_and_or */
    int c = 0;
    for (int i = 0; i < n && ok; i++)
        if (a[i] || b)
            c++;
    return c;
} /* END for_and_or */

int nested_ternary(int a, int b) { /* START nested_ternary */
    return a ? (b ? 1 : 2) : 3;
} /* END nested_ternary */

int switch_cases(int x) { /* START switch_cases */
    int y;
    switch (x) {
    case 1:
    case 2:
        y = 1;
        break;
    case 3:
        y = 2;
        break;
    default:
        y = 0;
    }
    return y;
} /* END switch_cases */

int do_while_and(int x, int y) { /* START do_while_and */
    do {
        x--;
    } while (x > 0 && y);
    return x;
} /* END do_while_and */

int else_if_chain(int a, int b, int c) { /* START else_if_chain */
    if (a) {
        return 1;
    } else if (b) {
        return 2;
    } else if (c) {
        return 3;
    } else {
        return 4;
    }
} /* END else_if_chain */

int elvis(int a, int b) { /* START elvis */
    return a ?: b;
} /* END elvis */

int goto_loop(int n) { /* START goto_loop */
    int i = 0;
again:
    if (i < n) {
        i++;
        goto again;
    }
    return i;
} /* END goto_loop */

int negations(int a, int b) { /* START negations */
    return !a && !b || (a && !b);
} /* END negations */
