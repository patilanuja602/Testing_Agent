#include "banking_transactions.hpp"
#include <climits>
#include <cassert>

int main() {
    // Test invalid amounts
    bank::Account acc(100, 1000);
    assert(acc.deposit(0) == bank::DepositResult::INVALID_AMOUNT);
    assert(acc.deposit(-1) == bank::DepositResult::INVALID_AMOUNT);

    // Test normal positive deposit
    assert(acc.deposit(50) == bank::DepositResult::SUCCESS);
    assert(acc.get_balance() == 150);

    // Test balance update
    assert(acc.deposit(200) == bank::DepositResult::SUCCESS);
    assert(acc.get_balance() == 350);

    // Test overflow condition near LONG_MAX
    bank::Account acc2(LONG_MAX - 100, 1000);
    assert(acc2.deposit(100) == bank::DepositResult::SUCCESS);
    assert(acc2.get_balance() == LONG_MAX);
    assert(acc2.deposit(1) == bank::DepositResult::OVERFLOW_ERROR);

    return 0;
}