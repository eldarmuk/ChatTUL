# IMPORTANT
# pytest discovers unit tests by searching 'test_' prefix
# on test files (like this one) then searching the same prefix on
# functions inside a file with 'test_' prefix

import pytest


def add(left: int, right: int) -> int:
    return left + right


def test_example():
    assert add(1, 1) == 2
    assert add(2**8, 2**8) == 2**9


# uncomment to checkout pytest pretty output
# def test_failing():
#     assert add(1, 1) == 3


class Connection:
    def __init__(self, path):
        # .. imagine some network code here
        self.path = path

    def query(self) -> bool:
        print("querying on a connection")
        return True


@pytest.fixture
def db_connection():
    return Connection("localhost:786")


def test_fixture(db_connection: Connection):
    assert db_connection.query()
