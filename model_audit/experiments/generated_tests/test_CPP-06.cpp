#include "banking_transactions.hpp"
#include <cassert>
#include <string>

int main() {
    // Test empty username
    assert(bank::SecurityManager::authenticate("", "hash", "stored_hash", 0) == bank::AuthStatus::INVALID_INPUT);

    // Test empty provided hash
    assert(bank::SecurityManager::authenticate("username", "", "stored_hash", 0) == bank::AuthStatus::INVALID_INPUT);

    // Test locked account (attempts >= 3)
    assert(bank::SecurityManager::authenticate("username", "hash", "stored_hash", 3) == bank::AuthStatus::ACCOUNT_LOCKED);

    // Test successful authentication
    assert(bank::SecurityManager::authenticate("username", "stored_hash", "stored_hash", 0) == bank::AuthStatus::AUTHENTICATED);

    // Test invalid credentials
    assert(bank::SecurityManager::authenticate("username", "wrong_hash", "stored_hash", 0) == bank::AuthStatus::INVALID_CREDENTIALS);

    return 0;
}