from abc import ABC
from abc import abstractmethod
from datetime import UTC
from datetime import datetime
from math import ceil as math_ceil
from math import floor as math_floor
from math import sqrt as math_sqrt
from random import Random
from typing import TYPE_CHECKING
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import Self
from typing import cast
from typing import final
from typing import override

from chatbot2k.scripting_engine.types.data_types import ListType
from chatbot2k.scripting_engine.types.data_types import NumberType
from chatbot2k.scripting_engine.types.execution_error import ExecutionError
from chatbot2k.scripting_engine.types.value import BoolValue
from chatbot2k.scripting_engine.types.value import ListValue
from chatbot2k.scripting_engine.types.value import NumberValue
from chatbot2k.scripting_engine.types.value import StringValue
from chatbot2k.scripting_engine.types.value import Value

if TYPE_CHECKING:
    from chatbot2k.scripting_engine.types.execution_context import ExecutionContext
    from chatbot2k.scripting_engine.types.expressions import Expression

_random: Final = Random()  # noqa: S311


def _format_number(value: float) -> str:
    """Format a number as an integer if it's a whole number, otherwise as a float."""
    return str(int(value)) if value.is_integer() else str(value)


@final
class _Variadic(NamedTuple):
    """Object to mark a function as variadic (accepting any number of arguments)."""

    min_num_arguments: Optional[int]

    @classmethod
    def with_min_num_arguments(cls, min_num_arguments: int) -> Self:
        """Create a Variadic instance with a minimum number of arguments."""
        return cls(min_num_arguments=min_num_arguments)


class BuiltinFunction(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this builtin function."""

    @property
    @abstractmethod
    def arity(self) -> int | _Variadic:
        """Return the number of arguments this builtin function expects, or Variadic for variadic functions."""

    @abstractmethod
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        """Execute the builtin function with the given arguments."""

    @final
    async def __call__(self, *args: "Expression", context: "ExecutionContext") -> str:
        match self.arity:
            case int() as arity:
                if len(args) != arity:
                    msg = (
                        f"Expected {arity} argument(s), got {len(args)} argument(s) for built-in function {self.name}."
                    )
                    raise ExecutionError(msg)
            case _Variadic() as variadic:
                if variadic.min_num_arguments is not None and len(args) < variadic.min_num_arguments:
                    msg = (
                        f"Expected at least {variadic.min_num_arguments} argument(s), "
                        + f"got {len(args)} for built-in function {self.name}."
                    )
                    raise ExecutionError(msg)
        return await self.execute(*args, context=context)


@final
class _TypeFunction(BuiltinFunction):
    """Builtin function that returns the data type of its argument as a string."""

    @property
    @override
    def name(self) -> str:
        return "type"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 1:
            raise AssertionError
        return str(args[0].get_data_type())


@final
class _LengthFunction(BuiltinFunction):
    """Builtin function that returns the length of a string argument."""

    @property
    @override
    def name(self) -> str:
        return "length"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 1:
            raise AssertionError
        value: Final = await args[0].evaluate(context)
        match value:
            case StringValue():
                return str(len(value.value))
            case ListValue():
                return str(len(value.elements))
            case _:
                msg: Final = f"'length' requires a string or list argument, got '{value.get_data_type()}'"
                raise ExecutionError(msg)


@final
class _UpperFunction(BuiltinFunction):
    """Builtin function that converts a string argument to uppercase."""

    @property
    @override
    def name(self) -> str:
        return "upper"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 1:
            raise AssertionError
        value: Final = await args[0].evaluate(context)
        if not isinstance(value, StringValue):
            msg: Final = f"'upper' requires a string argument, got '{value.get_data_type()}'"
            raise ExecutionError(msg)
        return value.value.upper()


@final
class _LowerFunction(BuiltinFunction):
    """Builtin function that converts a string argument to lowercase."""

    @property
    @override
    def name(self) -> str:
        return "lower"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 1:
            raise AssertionError
        value: Final = await args[0].evaluate(context)
        if not isinstance(value, StringValue):
            msg: Final = f"'lower' requires a string argument, got '{value.get_data_type()}'"
            raise ExecutionError(msg)
        return value.value.lower()


@final
class _TrimFunction(BuiltinFunction):
    """Builtin function that trims whitespace from both ends of a string argument."""

    @property
    @override
    def name(self) -> str:
        return "trim"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 1:
            raise AssertionError
        value: Final = await args[0].evaluate(context)
        if not isinstance(value, StringValue):
            msg: Final = f"'trim' requires a string argument, got '{value.get_data_type()}'"
            raise ExecutionError(msg)
        return value.value.strip()


@final
class _ReplaceFunction(BuiltinFunction):
    """Builtin function that replaces occurrences of a substring in a string argument."""

    @property
    @override
    def name(self) -> str:
        return "replace"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 3

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 3:
            raise AssertionError
        text_value: Final = await args[0].evaluate(context)
        if not isinstance(text_value, StringValue):
            msg = (
                "'replace' can only replace substrings in string arguments, "
                + f"got '{text_value.get_data_type()}' instead"
            )
            raise ExecutionError(msg)
        old_value: Final = await args[1].evaluate(context)
        if not isinstance(old_value, StringValue):
            msg = (
                "'replace' requires a string as the second argument for the substring to be replaced, "
                + f"got '{old_value.get_data_type()}' instead"
            )
            raise ExecutionError(msg)
        new_value: Final = await args[2].evaluate(context)
        if not isinstance(new_value, StringValue):
            msg = (
                "'replace' requires a string as the third argument for the replacement substring, "
                + f"got '{new_value.get_data_type()}' instead"
            )
            raise ExecutionError(msg)

        return text_value.value.replace(old_value.value, new_value.value)


@final
class _ContainsFunction(BuiltinFunction):
    """Builtin function that checks if a string contains a substring."""

    @property
    @override
    def name(self) -> str:
        return "contains"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 2

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 2:
            raise AssertionError
        haystack: Final = await args[0].evaluate(context)
        needle: Final = await args[1].evaluate(context)
        match needle, haystack:
            case StringValue(), StringValue():
                return "true" if needle.value in haystack.value else "false"
            case _, ListValue() as list_:
                if needle.get_data_type() != cast(ListType, list_.get_data_type()).of_type:
                    msg = (
                        "'contains' requires the needle to be of the same type as the elements of the haystack list, "
                        + f"got '{needle.get_data_type()}' and '{list_.get_data_type()}'"
                    )
                    raise ExecutionError(msg)
                return (
                    "true" if any(_ContainsFunction.equals(needle, element) for element in list_.elements) else "false"
                )
            case _:
                msg = (
                    "'contains' requires either both arguments to be strings, "
                    + "or the first argument to be a value and the second argument to be a list"
                )
                raise ExecutionError(msg)

    @staticmethod
    def equals(lhs: Value, rhs: Value) -> bool:
        match lhs, rhs:
            case StringValue(), StringValue():
                return lhs.value == rhs.value
            case NumberValue(), NumberValue():
                return lhs.value == rhs.value
            case BoolValue(), BoolValue():
                return lhs.value == rhs.value
            case ListValue(), ListValue():
                if lhs.get_data_type() != rhs.get_data_type():
                    return False
                if len(lhs.elements) != len(rhs.elements):
                    return False
                return all(
                    _ContainsFunction.equals(left, right)
                    for left, right in zip(lhs.elements, rhs.elements, strict=True)
                )
            case _:
                raise AssertionError("Unreachable")


@final
class _StartsWithFunction(BuiltinFunction):
    """Builtin function that checks if a string starts with a given prefix."""

    @property
    @override
    def name(self) -> str:
        return "starts_with"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 2

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 2:
            raise AssertionError
        text_value: Final = await args[0].evaluate(context)
        prefix_value: Final = await args[1].evaluate(context)
        if not isinstance(text_value, StringValue) or not isinstance(prefix_value, StringValue):
            msg: Final = (
                "'starts_with' requires string arguments, "
                + f"got '{text_value.get_data_type()}' and '{prefix_value.get_data_type()}'"
            )
            raise ExecutionError(msg)
        result: Final = text_value.value.startswith(prefix_value.value)
        return "true" if result else "false"


@final
class _EndsWithFunction(BuiltinFunction):
    """Builtin function that checks if a string ends with a given suffix."""

    @property
    @override
    def name(self) -> str:
        return "ends_with"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 2

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 2:
            raise AssertionError
        text_value: Final = await args[0].evaluate(context)
        suffix_value: Final = await args[1].evaluate(context)
        if not isinstance(text_value, StringValue) or not isinstance(suffix_value, StringValue):
            msg: Final = (
                "'ends_with' requires string arguments, "
                + f"got '{text_value.get_data_type()}' and '{suffix_value.get_data_type()}'"
            )
            raise ExecutionError(msg)
        result: Final = text_value.value.endswith(suffix_value.value)
        return "true" if result else "false"


@final
class _AbsFunction(BuiltinFunction):
    """Builtin function that returns the absolute value of a number."""

    @property
    @override
    def name(self) -> str:
        return "abs"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 1:
            raise AssertionError
        value: Final = await args[0].evaluate(context)
        if not isinstance(value, NumberValue):
            msg: Final = f"'abs' requires a number argument, got {value.get_data_type()}"
            raise ExecutionError(msg)
        return _format_number(abs(value.value))


@final
class _MinFunction(BuiltinFunction):
    """Builtin function that returns the minimum value among its number arguments."""

    @property
    @override
    def name(self) -> str:
        return "min"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return _Variadic.with_min_num_arguments(1)

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) < 1:
            raise AssertionError
        values: Final = [await arg.evaluate(context) for arg in args]

        first_element: Final = values[0]
        if len(values) == 1 and isinstance(first_element, ListValue):
            element_type: Final = first_element.get_data_type()
            if not isinstance(element_type, ListType):
                raise AssertionError
            if not isinstance(element_type.of_type, NumberType):
                msg = f"'min' requires number arguments, got list of {element_type.of_type}"
                raise ExecutionError(msg)
            return _format_number(min(cast(NumberValue, v).value for v in first_element.elements))

        # Check all are numbers.
        for i, val in enumerate(values):
            if not isinstance(val, NumberValue):
                msg = f"'min' requires number arguments, got {val.get_data_type()} at position {i + 1}"
                raise ExecutionError(msg)

        number_values: Final = [cast(NumberValue, v).value for v in values]
        result: Final = min(number_values)
        return _format_number(result)


@final
class _MaxFunction(BuiltinFunction):
    """Builtin function that returns the maximum value among its number arguments."""

    @property
    @override
    def name(self) -> str:
        return "max"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return _Variadic.with_min_num_arguments(1)

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) < 1:
            raise AssertionError
        values: Final = [await arg.evaluate(context) for arg in args]

        first_element: Final = values[0]
        if len(values) == 1 and isinstance(first_element, ListValue):
            element_type: Final = first_element.get_data_type()
            if not isinstance(element_type, ListType):
                raise AssertionError
            if not isinstance(element_type.of_type, NumberType):
                msg = f"'max' requires number arguments, got list of {element_type.of_type}"
                raise ExecutionError(msg)
            return _format_number(max(cast(NumberValue, v).value for v in first_element.elements))

        # Check all are numbers.
        for i, val in enumerate(values):
            if not isinstance(val, NumberValue):
                error_msg = f"'max' requires number arguments, got {val.get_data_type()} at position {i + 1}"
                raise ExecutionError(error_msg)

        number_values: Final = [cast(NumberValue, v).value for v in values]
        result: Final = max(number_values)
        return _format_number(result)


@final
class _RoundFunction(BuiltinFunction):
    """Builtin function that rounds a number to the nearest integer."""

    @property
    @override
    def name(self) -> str:
        return "round"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 1:
            raise AssertionError
        value: Final = await args[0].evaluate(context)
        if not isinstance(value, NumberValue):
            msg: Final = f"'round' requires a number argument, got {value.get_data_type()}"
            raise ExecutionError(msg)
        return _format_number(round(value.value))


@final
class _FloorFunction(BuiltinFunction):
    """Builtin function that returns the largest integer less than or equal to a number."""

    @property
    @override
    def name(self) -> str:
        return "floor"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 1:
            raise AssertionError
        value: Final = await args[0].evaluate(context)
        if not isinstance(value, NumberValue):
            msg: Final = f"'floor' requires a number argument, got {value.get_data_type()}"
            raise ExecutionError(msg)
        return _format_number(float(math_floor(value.value)))


@final
class _CeilFunction(BuiltinFunction):
    """Builtin function that returns the smallest integer greater than or equal to a number."""

    @property
    @override
    def name(self) -> str:
        return "ceil"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 1:
            raise AssertionError
        value: Final = await args[0].evaluate(context)
        if not isinstance(value, NumberValue):
            msg: Final = f"'ceil' requires a number argument, got {value.get_data_type()}"
            raise ExecutionError(msg)
        return _format_number(float(math_ceil(value.value)))


@final
class _SqrtFunction(BuiltinFunction):
    """Builtin function that returns the square root of a number."""

    @property
    @override
    def name(self) -> str:
        return "sqrt"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 1:
            raise AssertionError
        value: Final = await args[0].evaluate(context)
        if not isinstance(value, NumberValue):
            msg: Final = f"'sqrt' requires a number argument, got {value.get_data_type()}"
            raise ExecutionError(msg)
        if value.value < 0:
            negative_msg: Final = f"'sqrt' requires a non-negative argument, got {value.value}"
            raise ExecutionError(negative_msg)
        return _format_number(math_sqrt(value.value))


@final
class _PowFunction(BuiltinFunction):
    """Builtin function that raises a number to the power of another number."""

    @property
    @override
    def name(self) -> str:
        return "pow"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 2

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if len(args) != 2:
            raise AssertionError
        values: Final = [await arg.evaluate(context) for arg in args]
        for i, val in enumerate(values):
            if not isinstance(val, NumberValue):
                error_msg = f"'pow' requires number arguments, got {val.get_data_type()} at position {i + 1}"
                raise ExecutionError(error_msg)
        base: Final = values[0]
        exponent: Final = values[1]
        if not isinstance(base, NumberValue) or not isinstance(exponent, NumberValue):
            raise AssertionError
        return _format_number(base.value**exponent.value)


@final
class _RandomFunction(BuiltinFunction):
    """Builtin function that returns a random number between two given numbers."""

    @property
    @override
    def name(self) -> str:
        return "random"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 2

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if not len(args) == 2:
            raise AssertionError
        values: Final = [await arg.evaluate(context) for arg in args]
        for i, val in enumerate(values):
            if not isinstance(val, NumberValue):
                error_msg = f"'random' requires number arguments, got {val.get_data_type()} at position {i + 1}"
                raise ExecutionError(error_msg)
        min_val: Final = values[0]
        max_val: Final = values[1]
        if not isinstance(min_val, NumberValue) or not isinstance(max_val, NumberValue):
            raise AssertionError
        result: Final = _random.uniform(min_val.value, max_val.value)
        return _format_number(result)


@final
class _TimestampFunction(BuiltinFunction):
    """Builtin function that returns the current timestamp."""

    @property
    @override
    def name(self) -> str:
        return "timestamp"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 0

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if not len(args) == 0:
            raise AssertionError
        timestamp: Final = datetime.now(UTC).timestamp()
        return _format_number(timestamp)


@final
class _DateFunction(BuiltinFunction):
    """Builtin function that returns the current date formatted according to a given format string."""

    @property
    @override
    def name(self) -> str:
        return "date"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if not len(args) == 1:
            raise AssertionError
        format_value: Final = await args[0].evaluate(context)
        if not isinstance(format_value, StringValue):
            msg = f"'date' requires a string argument, got {format_value.get_data_type()}"
            raise ExecutionError(msg)
        now: Final = datetime.now(UTC)
        return now.strftime(format_value.value)


@final
class _ReadFileFunction(BuiltinFunction):
    """Builtin function that reads the content of a file given its path relative
    to the root data path (see `Config` class)."""

    @property
    @override
    def name(self) -> str:
        return "read_file"

    @property
    @override
    def arity(self) -> int | _Variadic:
        return 1

    @override
    async def execute(self, *args: "Expression", context: "ExecutionContext") -> str:
        if not len(args) == 1:
            raise AssertionError
        path_value: Final = await args[0].evaluate(context)
        if not isinstance(path_value, StringValue):
            msg = f"'read_file' requires a string argument for the file path, got {path_value.get_data_type()}"
            raise ExecutionError(msg)
        path: Final = (context.app_state.config.data_root_path / path_value.value).resolve()

        # Make sure that the path is within the data root path to prevent directory traversal attacks.
        resolved_root: Final = context.app_state.config.data_root_path.resolve()
        if resolved_root not in path.parents:
            msg = f"Access to file '{path_value.value}' is outside of the data root path"
            raise ExecutionError(msg)
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise ExecutionError(f"File not found: '{path_value.value}'") from e
        except Exception as e:
            raise ExecutionError(f"Error reading file '{path_value.value}': {e}") from e


_BUILTIN_FUNCTION_LIST: list[BuiltinFunction] = [
    _TypeFunction(),
    _LengthFunction(),
    _UpperFunction(),
    _LowerFunction(),
    _TrimFunction(),
    _ReplaceFunction(),
    _ContainsFunction(),
    _StartsWithFunction(),
    _EndsWithFunction(),
    _AbsFunction(),
    _MinFunction(),
    _MaxFunction(),
    _RoundFunction(),
    _FloorFunction(),
    _CeilFunction(),
    _SqrtFunction(),
    _PowFunction(),
    _RandomFunction(),
    _TimestampFunction(),
    _DateFunction(),
    _ReadFileFunction(),
]

BUILTIN_FUNCTIONS: dict[str, BuiltinFunction] = {func.name: func for func in _BUILTIN_FUNCTION_LIST}
