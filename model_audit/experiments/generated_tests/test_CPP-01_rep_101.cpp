#include "banking_transactions.hpp"
#include <cassert>

int main() {
    // Test constructor
    bank::Account acc(1000, 500);
    assert(acc.get_balance() == 1000);
    assert(acc.get_daily_withdrawn() == 0);
    assert(acc.get_daily_limit() == 500);

    // Test valid withdrawal
    assert(acc.withdraw(200) == bank::WithdrawResult::SUCCESS);
    assert(acc.get_balance() == 800);
    assert(acc.get_daily_withdrawn() == 200);

    // Test invalid amount
    assert(acc.withdraw(0) == bank::WithdrawResult::INVALID_AMOUNT);
    assert(acc.get_balance() == 800);
    assert(acc.get_daily_withdrawn() == 200);

    // Test insufficient funds
    assert(acc.withdraw(1000) == bank::WithdrawResult::INSUFFICIENT_FUNDS);
    assert(acc.get_balance() == 800);
    assert(acc.get_daily_withdrawn() == 200);

    // Test daily limit exceeded
    assert(acc.withdraw(300) == bank::WithdrawResult::DAILY_LIMIT_EXCEEDED);
    assert(acc.get_balance() == 800);
    assert(acc.get_daily_withdrawn() == 200);

    // Test reset daily limit
    acc.reset_daily_limit();
    assert(acc.get_daily_withdrawn() == 0);
    assert(acc.withdraw(300) == bank::WithdrawResult::SUCCESS);
    assert(acc.get_balance() == 500);
    assert(acc.get_daily_withdrawn() == 300);

    // Test another valid withdrawal after reset
    assert(acc.withdraw(200) == bank::WithdrawResult::SUCCESS);
    assert(acc.get_balance() == 300);
    assert(acc.get_daily_withdrawn() == 500);

    return 0;
}