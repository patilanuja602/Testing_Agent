// Fixture: C++ classes, constructors, overloads, switch, loops.
// START <id> marks the signature line, END <id> the closing line.
#include <vector>

class Calculator {
public:
    Calculator(int base) : base_(base) { // START ctor
        if (base_ < 0) {
            base_ = 0;
        }
    } // END ctor

    int add(int a, int b) { // START add_int
        return a + b + base_;
    } // END add_int

    double add(double a, double b) { // START add_double
        return a + b;
    } // END add_double

    int add(int a, int b, int c) { // START add_three
        if (c > 0) {
            return a + b + c;
        }
        return a + b;
    } // END add_three

    int classify(int x) { // START classify
        if (x > 0) {
            if (x > 100) {
                return 2;
            }
            return 1;
        }
        return 0;
    } // END classify

    int scale(int x);

private:
    int base_;
};

int Calculator::scale(int x) { // START scale
    int total = 0;
    for (int i = 0; i < x; i++) {
        if (i % 2 == 0) {
            total += i;
        }
    }
    return total;
} // END scale

int day_type(int d) { // START day_type
    switch (d) {
        case 0:
        case 6:
            return 0;
        default:
            return 1;
    }
} // END day_type

int sum_positive(const std::vector<int>& values) { // START sum_positive
    int total = 0;
    for (int v : values) {
        if (v > 0) {
            total += v;
        }
    }
    return total;
} // END sum_positive
