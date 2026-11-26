#include "banking_transactions.hpp"
#include <cassert>

int main() {
    // Test constructor
    bank::Account account(1000, 500);
    assert(account.get_balance() == 1000);
    assert(account.get_daily_withdrawn() == 0);
    assert(account.get_daily_limit() == 500);

    // Test withdraw with invalid amount
    assert(account.withdraw(0) == bank::WithdrawResult::INVALID_AMOUNT);
    assert(account.withdraw(-10) == bank::WithdrawResult::INVALID_AMOUNT);

    // Test withdraw with insufficient funds
    assert(account.withdraw(1500) == bank::WithdrawResult::INSUFFICIENT_FUNDS);

    // Test withdraw with daily limit exceeded
    assert(account.withdraw(400) == bank::WithdrawResult::SUCCESS);
    assert(account.withdraw(200) == bank::WithdrawResult::DAILY_LIMIT_EXCEEDED);

    // Test reset daily limit
    account.reset_daily_limit();
    assert(account.withdraw(200) == bank::WithdrawResult::SUCCESS);

    // Test multiple withdrawals within daily limit
    assert(account.withdraw(100) == bank::WithdrawResult::SUCCESS);
    assert(account.withdraw(200) == bank::WithdrawResult::SUCCESS);
    assert(account.withdraw(200) == bank::WithdrawResult::DAILY_LIMIT_EXCEEDED);

    // Test negative balance after withdrawal
    account.reset_daily_limit();
    assert(account.withdraw(1000) == bank::WithdrawResult::SUCCESS);
    assert(account.withdraw(1) == bank::WithdrawResult::INSUFFICIENT_FUNDS);

    // Test balance and daily withdrawn after successful withdrawals
    account.reset_daily_limit();
    assert(account.withdraw(100) == bank::WithdrawResult::SUCCESS);
    assert(account.get_balance() == 900);
    assert(account.get_daily_withdrawn() == 100);

    // Test balance and daily withdrawn after failed withdrawal
    account.reset_daily_limit();
    assert(account.withdraw(1500) == bank::WithdrawResult::INSUFFICIENT_FUNDS);
    assert(account.get_balance() == 1000);
    assert(account.get_daily_withdrawn() == 0);

    return 0;
}