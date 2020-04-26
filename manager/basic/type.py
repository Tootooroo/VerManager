from typing import Callable, Any

"""
State type represent state of function
"""
State = int
Ok = 0
Error = 2

"""
Predicate is a function to test something with
some conditions.
"""
Predicate = Callable[[Any], bool]
