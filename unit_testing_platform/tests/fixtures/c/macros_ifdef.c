/* Fixture: constructs Lizard cannot see through (no preprocessing).
 * Tests expect VISIBLE WARNINGS here, not a guaranteed complexity value. */
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define SQUARE(x) ((x) * (x))

int uses_macro(int a, int b) { /* START uses_macro */
    return MAX(a, b) + SQUARE(a);
} /* END uses_macro */

int with_ifdef(int x) { /* START with_ifdef */
#ifdef FEATURE_A
    if (x > 0) {
        return 1;
    }
#else
    if (x < 0) {
        return -1;
    }
#endif
    return 0;
} /* END with_ifdef */
