/* Fixture: macros. The analyzer does NOT expand macros, so a decision hidden in a macro BODY is not
 * counted at the use site, while a decision written in a macro ARGUMENT is. Expected values are
 * hand-derived for that documented convention (they differ from the expanded code's complexity).
 * Validity: gcc -std=gnu11 -fsyntax-only tests/fixtures/c/macros_expansion.c */
extern void free(void *);
extern void log_msg(int);
#define IS_OK(x) ((x) && (x) < 5)
#define CHECK(c) do { if (!(c)) log_msg(1); } while (0)
#define SAFE_FREE(p) do { if (p) { free(p); (p) = 0; } } while (0)
#define MAX(a, b) ((a) > (b) ? (a) : (b))

int macro_body_hidden(int a) { /* START macro_body_hidden */
    return IS_OK(a) ? 1 : 0;
} /* END macro_body_hidden */

void macro_arg_counted(int a, int b) { /* START macro_arg_counted */
    CHECK(a && b);
} /* END macro_arg_counted */

void macro_with_if_inside(char *p) { /* START macro_with_if_inside */
    SAFE_FREE(p);
} /* END macro_with_if_inside */

int macro_ternary_hidden(int a, int b) { /* START macro_ternary_hidden */
    return MAX(a, b);
} /* END macro_ternary_hidden */
