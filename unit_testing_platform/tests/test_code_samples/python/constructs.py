"""Fixture: Python constructs.  START <id> marks the def line, END <id> the last
line of the function body.  Expected CCN is in ../expected.json (Lizard
convention: 1 + if + elif + for + while + except + and + or)."""


def simple(a, b):  # START simple
    return a + b  # END simple


def if_else(x):  # START if_else
    if x > 0:
        return 1
    else:
        return -1  # END if_else


def nested_if(a, b):  # START nested_if
    if a > 0:
        if b > 0:
            return 1
    return 0  # END nested_if


def elif_chain(x):  # START elif_chain
    if x < 0:
        return -1
    elif x == 0:
        return 0
    elif x < 10:
        return 1
    else:
        return 2  # END elif_chain


def for_loop(items):  # START for_loop
    total = 0
    for i in items:
        total += i
    return total  # END for_loop


def while_loop(n):  # START while_loop
    while n > 0:
        n -= 1
    return n  # END while_loop


def boolean_expr(a, b, c):  # START boolean_expr
    if a and b or c:
        return 1
    return 0  # END boolean_expr


def nested_loops(n, m):  # START nested_loops
    s = 0
    for i in range(n):
        for j in range(m):
            if (i + j) % 2 == 0:
                s += 1
    return s  # END nested_loops


def safe_div(a, b):  # START safe_div
    try:
        return a / b
    except ZeroDivisionError:
        return 0
    except TypeError:
        return None  # END safe_div


def conditional_expr(a, b):  # START conditional_expr
    return a if a > b else b  # END conditional_expr


def try_finally(a):  # START try_finally
    try:
        return 1 / a
    except ZeroDivisionError:
        return 0
    finally:
        print("done")  # END try_finally


def comprehension(xs):  # START comprehension
    return [x for x in xs if x > 0]  # END comprehension
