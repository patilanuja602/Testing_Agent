// Fixture: '&&' as logical AND versus reference declarator (C++17, self-contained, no #include).
// Expected values (tests/fixtures/expected.json) are hand-derived: CCN = 1 + decisions.
// Validity: g++ -std=c++17 -fsyntax-only tests/fixtures/cpp/amp_amp.cpp
extern void execute();
extern bool next_flag(bool);
extern void use(int);
struct Vec { int* begin(); int* end(); };

template <typename T>
void process(T&& value) // START fwd_ref_user_example
{
    if (value > 10)
    {
        execute();
    }
} // END fwd_ref_user_example
template void process<int>(int&&);

void range_for_fwd(Vec& v) { // START range_for_fwd
    for (auto&& e : v) use(e);
} // END range_for_fwd

template <typename T>
void cast_forward(T& t) { // START cast_forward
    use(static_cast<T&&>(t));
} // END cast_forward
template void cast_forward<int>(int&);

int local_rref() { // START local_rref
    int&& r = 5;
    int&& q{6};
    return r + q;
} // END local_rref

bool both(bool a, bool b) { // START both
    return a && b;
} // END both

bool drain(bool a, bool b) { // START drain
    while (a && (b = next_flag(b))) {
        use(1);
    }
    return b;
} // END drain

template <typename T>
bool both_t(T&& v, bool b) { // START both_t
    return v && b;
} // END both_t
template bool both_t<bool>(bool&&, bool);

int pick(bool a, bool b) { // START pick
    return (a && b) ? 1 : 0;
} // END pick

void fn_ptr() { // START fn_ptr
    void (*cb)(int&&) = nullptr;
    if (cb) cb(1);
} // END fn_ptr

struct Buf {
    int v;
    Buf(Buf&& o) noexcept : v(o.v) {} // START move_ctor END move_ctor
    Buf& operator=(Buf&& o) { // START move_assign
        if (this != &o) v = o.v;
        return *this;
    } // END move_assign
    int get() && { return v; } // START ref_qualified END ref_qualified
    int peek() const& { return v; } // START peek_lvalue END peek_lvalue
};

int use_lambdas(int n) { // START lambda_outer
    auto even = [](int x) { return x % 2 == 0; };
    auto both_ok = [](auto&& a, auto&& b) { return a && b; };
    if (even(n) && n > 3)
        return 1;
    return both_ok(n, n) ? 1 : 0;
} // END lambda_outer
