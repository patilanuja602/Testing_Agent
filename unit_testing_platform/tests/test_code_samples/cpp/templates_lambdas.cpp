// Fixture: templates and lambdas. Lizard support is partial, so the tests
// expect VISIBLE WARNINGS and only loosely check complexity values.
#include <vector>

template <typename T>
T max_of(T a, T b) { // START max_of
    if (a > b) {
        return a;
    }
    return b;
} // END max_of

int count_positive(const std::vector<int>& v) { // START count_positive
    int n = 0;
    auto pred = [](int x) { return x > 0; };
    for (int x : v) {
        if (pred(x)) {
            ++n;
        }
    }
    return n;
} // END count_positive
