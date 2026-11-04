/* Fixture: C constructs.  START <id> marks the signature line, END <id> the
 * closing line.  Expected CCN is in ../expected.json (Lizard convention:
 * 1 + if + for + while + case + && + || + ?). */
#include <stdio.h>

int simple_add(int a, int b) { /* START simple_add */
    return a + b;
} /* END simple_add */

int if_else(int x) { /* START if_else */
    if (x > 0) {
        return 1;
    } else {
        return -1;
    }
} /* END if_else */

int nested_if(int a, int b) { /* START nested_if */
    if (a > 0) {
        if (b > 0) {
            return 1;
        }
    }
    return 0;
} /* END nested_if */

int else_if_chain(int x) { /* START else_if_chain */
    if (x < 0) {
        return -1;
    } else if (x == 0) {
        return 0;
    } else if (x < 10) {
        return 1;
    } else if (x < 100) {
        return 2;
    } else {
        return 3;
    }
} /* END else_if_chain */

int for_loop(int n) { /* START for_loop */
    int s = 0;
    for (int i = 0; i < n; i++) {
        s += i;
    }
    return s;
} /* END for_loop */

int while_loop(int n) { /* START while_loop */
    while (n > 0) {
        n--;
    }
    return n;
} /* END while_loop */

int do_while_loop(int n) { /* START do_while_loop */
    do {
        n--;
    } while (n > 0);
    return n;
} /* END do_while_loop */

int switch_stmt(int c) { /* START switch_stmt */
    switch (c) {
        case 1:
            return 10;
        case 2:
            return 20;
        case 3:
            return 30;
        default:
            return 0;
    }
} /* END switch_stmt */

int logical_ops(int a, int b, int c) { /* START logical_ops */
    if (a && b || c) {
        return 1;
    }
    return 0;
} /* END logical_ops */

int nested_loops(int n, int m) { /* START nested_loops */
    int s = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if ((i + j) % 2 == 0) {
                s++;
            }
        }
    }
    return s;
} /* END nested_loops */

int ternary_max(int a, int b) { /* START ternary_max */
    return a > b ? a : b;
} /* END ternary_max */
