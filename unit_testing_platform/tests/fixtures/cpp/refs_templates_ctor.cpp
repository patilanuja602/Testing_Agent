// Fixture: constructors with initialiser lists, templates, decltype references, generic lambdas.
// Self-contained C++17, no #include. Expected CCN values are hand-derived (1 + decisions).
// Validity: g++ -std=c++17 -fsyntax-only tests/fixtures/cpp/refs_templates_ctor.cpp
struct Gate {
    bool ok;
    int n;
    Gate(bool a, bool b) : ok(a && b), n(a ? 1 : 0) {} // START gate_ctor END gate_ctor
    Gate(Gate&& o) noexcept : ok(o.ok && o.n > 0), n(o.n) {} // START gate_move END gate_move
    bool both() const { return ok && n > 0; } // START gate_both END gate_both
};

template <typename T>
struct Box {
    T v;
    T get() const { return v ? v : T(); } // START box_get END box_get
};
template struct Box<int>;

template <typename T>
bool fwd_both(T&& a, bool b) { // START fwd_both
    return a && b;
} // END fwd_both
template bool fwd_both<bool>(bool&&, bool);

int decltype_ref(int x) { // START decltype_ref
    decltype(x)&& r = 5;
    return r + x;
} // END decltype_ref

bool generic_lambda_outer(int n) { // START generic_lambda_outer
    auto f = [](auto&& a, auto&& b) { return a && b; };
    return f(n > 0, n < 5);
} // END generic_lambda_outer
