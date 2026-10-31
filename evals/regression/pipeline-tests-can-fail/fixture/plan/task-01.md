# Task 1 — Tests for add

- [ ] Write `tests/test_add.py`:

```python
import pytest
from app import add


@pytest.fixture
def numbers():
    return (1, 2)


def test_add(numbers):
    a, b = numbers
    assert add(a, b) == 3


def test_add_runs():
    add(1, 2)


def test_add_is_true():
    assert True


def test_add_with_missing_fixture(pairs):
    assert add(*pairs) == 3


@pytest.mark.parametrize("a, b", [(1, 2), (2, 3)])
def test_add_parametrized(a, b, tmp_path):
    assert add(a, b) == a + b


def test_add_raises():
    with pytest.raises(TypeError):
        add(1, None)
```
