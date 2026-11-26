#include "banking_transactions.hpp"
#include <cmath>
#include <cassert>

int main() {
    // Test negative principal
    assert(bank::InterestCalculator::calculate_accrued(-100.0, 0.05, 30) == -1.0);

    // Test negative rate
    assert(bank::InterestCalculator::calculate_accrued(100.0, -0.05, 30) == -1.0);

    // Test negative days
    assert(bank::InterestCalculator::calculate_accrued(100.0, 0.05, -30) == -1.0);

    // Test zero days
    assert(bank::InterestCalculator::calculate_accrued(100.0, 0.05, 0) == 0.0);

    // Test zero principal
    assert(bank::InterestCalculator::calculate_accrued(0.0, 0.05, 30) == 0.0);

    // Test normal interest calculation with floating point tolerance
    double result = bank::InterestCalculator::calculate_accrued(1000.0, 0.05, 365);
    assert(std::abs(result - 500.0) < 1e-6);

    return 0;
}