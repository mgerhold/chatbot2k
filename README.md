# Chatbot2k

Chatbot2k is a chatbot application that is able to connect to multiple chat platforms at the same time (currently
supporting Discord and Twitch).

## Features

🔌 Connects to multiple chat platforms (Discord, Twitch)  
🗣️ Can respond to commands (simple command-response system)  
📖 Provides dictionary functionality: When a user message contains a defined keyword (usually an acronym), the bot
responds with the corresponding definition.  
📹 Can trigger video and audio clips based on user commands (soundboard functionality)  
⌨️ Supports defining and invoking script commands written in a custom scripting language
🌐 Web interface that shows a list of possible commands and clips

The main use-case is to use this bot during my own livestreams and on my Discord sever.

## Development

The project is written in Python and uses [astral's uv](https://docs.astral.sh/uv/) as project and package manager. You
need to have it installed to run the project. Install dependencies like this:

```bash
uv sync
```

Use the following command to run the bot locally using uvicorn. This also supports hot-reloading during development:

```bash
uv run uvicorn chatbot2k.main:app --host 0.0.0.0 --port 8080 --reload
```

## Scripting Language Reference

A new script command can be added by moderators of broadcasters using the command: `!command add-script !<
command_name> "<script_code>"`

Each script consists of multiple sections:

1. **Stores (optional)**: Each store defines a variable that is persisted in the bot's database. This allows persisting
   state across multiple invocations of the script.
2. **Parameters (optional)**: Define parameters that can be passed to the script when invoked.
3. **Statements**: The actual code that is executed when the script command is invoked.

See below for details on each section.

### Data Types

Currently, the language supports the following data types:

- **Booleans**: The literals `true` and `false`.
- **Numbers**: Integral or floating-point numbers, possibly negative. They are mapped to Python's `float` type.
- **Strings**: Sequences of characters enclosed in single quotes (`'`). They are mapped to Python's `str` type and
  support UTF-8. The allowed escape sequences are:
  - `\'` for single quote
  - `\n` for newline
  - `\\` for backslash
- **Lists**: Ordered collections of elements of the same type. Lists are created using square brackets `[]` and can
  contain any data type, including nested lists. All elements in a list must have the same type. The type is written as
  `list<element_type>` (e.g., `list<number>`, `list<string>`, `list<list<number>>`).

## Keywords

The following keywords are reserved in the scripting language:

- `and`
- `as`
- `bool`
- `collect`
- `false`
- `for`
- `if`
- `LET`
- `list`
- `not`
- `number`
- `or`
- `PARAMS`
- `PRINT`
- `sort`
- `split`
- `string`
- `STORE`
- `true`
- `with`
- `yeet`

## Identifiers

Identifiers must start with an ASCII letter. They may continue with ASCII letters, digits, or underscores (`_`).
Identifiers are case-sensitive. Identifiers cannot be the same as reserved keywords.

## Stores

Each store is defined like this:

```
STORE <store_name> = <initial_value>;
```

On script creation, this will create a new database entry for the store with the given initial value. The store is
scoped to the script, so multiple scripts can have stores with the same name without interfering with each other.  
`<store_name>` can be any valid identifier that has not been used as a store name in this script before.  
`<initial_value>` can be any valid expression. It may also reference other stores defined earlier in the same script.

Example:

```
STORE a = 0;
STORE b = 10;
STORE c = a + b;
STORE greeting = 'Hello, world!';
```

## Parameters

Parameters are defined like this:

```
PARAMS <param_name>, <param_name>, ...;
```

`<param_name>` can be any valid identifier that has not been used as a store name or parameter name in this script before. The data type for every parameter is string.  
When invoking the script command, users must provide values for these parameters.

## Statements

The following statements are supported:

### Variable Definitions

Define a new variable like this:

```
LET <var_name> = <expression>;
```

Each variable is scoped to the script execution, so it will not persist across multiple invocations of the script.  
`<var_name>` can be any valid identifier that has not been used before in this script.  
`<expression>` can be any valid expression, including references to stores, parameters, and previously defined variables.

*Note: Referencing a store will yield its current value from the database, not necessarily its initial value.*

Variables can optionally be annotated with a type:

```
LET <var_name>: <type> = <expression>;
```

Where `<type>` is one of `string`, `number`, `bool`, or `list<element_type>` (e.g., `list<number>`, `list<string>`). The
type annotation is required when defining an empty list literal, as the type cannot be inferred. For non-empty lists,
the type is inferred from the elements.

**Example:**

```
LET x = 42;
LET y = x + 10;
LET a = 'Hello, ';
LET b = a + 'world!';
LET numbers = [1, 2, 3, 4, 5];
LET empty_list: list<string> = [];
LET words: list<string> = ['apple', 'banana', 'cherry'];
```

### Assignments

You can assign new values stores, parameters, and variables like this:

```
<name> = <expression>;
```

`<name>` can be either a store name, a parameter name, or a variable name that has been defined earlier in the script.  
`<expression>` can be any valid expression, including references to stores, parameters, and variables.

*Note: Store values are persisted to the database after script execution ends successfully. If it fails at runtime, no
changes are made to the stores.*

### Print Statement

You can output text to the chat using the print statement:

```
PRINT <expression>;
```

`<expression>` can be any valid expression. The result will be converted to a string. All prints inside a script
execution are concatenated and sent as a single message to the chat after the script finishes executing.

**Example:**

```
LET number = 42;
PRINT 'The answer is: ';
PRINT number;
```

This will output: `The answer is: 42`

### Expressions

The following expressions are supported:

- **Literals**: Numbers (e.g., `42`, `3.14`, `-7`), strings (e.g., `'Hello, world!'`), booleans (`true`, `false`), and
  lists (e.g., `[1, 2, 3]`, `['a', 'b', 'c']`, `[[1, 2], [3, 4]]`)
- **Variable, Parameter and Store References**: Using the name of a variable, parameter, or store to get its current value.
- **Arithmetic Operations**: Addition (`+`), subtraction (`-`), multiplication (`*`), division (`/`), and modulo (`%`) for numbers. The language supports both `+` and `-` in their unary and binary forms.
- **Comparison Operations**: Equal (`==`), not equal (`!=`), less than (`<`), less than or equal (`<=`), greater than (`>`), greater than or equal (`>=`) for all data types.
- **Logical Operations**: And (`and`), or (`or`), and not (`not`) for boolean values.
- **Ternary Operator**: The conditional expression `condition ? value_if_true : value_if_false` evaluates the condition and returns `value_if_true` if the condition is true, otherwise returns `value_if_false`. Both branches must have the same type.
- **String Concatenation**: Using the `+` operator to concatenate strings.
- **List Concatenation**: Using the `+` operator to concatenate lists of the same element type (e.g., `[1, 2] + [3, 4]` results in `[1, 2, 3, 4]`).
- **Parentheses**: To group expressions and control the order of evaluation.
- **Subscript Operator**: Access individual characters in a string or elements in a list using the syntax `string[index]`
  or `list[index]`, where `index` is a zero-based integer. The index must be a non-negative integer within the bounds of
  the string or list.
- **Conversion to Number**: The prefix `$` operator converts a value to a number. For strings, the string must represent a number literal, possibly with a leading `+` or `-`. For booleans, `true` is converted to `1` and `false` to `0`. Applying the operator to a number has no effect.
- **Conversion to String**: The prefix `#` operator converts a value to its string representation. For numbers, it formats the number (removing unnecessary decimal points for whole numbers). For booleans, it converts to `'true'` or `'false'`. Applying the operator to a string has no effect.
- **Conversion to Boolean**: The prefix `?` operator converts a value to a boolean. For numbers, `0` is converted to `false`, all other numbers to `true`. For strings, only the literals `'true'` and `'false'` can be converted to their respective boolean values. Applying the operator to a boolean has no effect.
- **Code Evaluation**: The prefix `!` operator evaluates a string as code and returns the result as a string. The evaluated source code must not contain any stores, or parameters. It cannot access any values from the surrounding script context.
- **Function Calls**: Call builtin functions using the syntax `'function_name'(arg1, arg2, ...)`. See the Builtin Functions section below for available functions.
- **Range Operators**: Create integer ranges using the `..=` (inclusive) or `..<` (exclusive) operators. Both operands must be numbers that represent integers (no fractional part). The operators return a `list<number>`. Ranges can be ascending (e.g., `1..=5` produces `[1, 2, 3, 4, 5]`) or descending (e.g., `5..=1` produces `[5, 4, 3, 2, 1]`). The exclusive operator `..<` excludes the end value (e.g., `1..<5` produces `[1, 2, 3, 4]`).
- **Split Expressions**: Split a string into a list of strings using the syntax `split(string)` or `split(string, delimiter)`. If no delimiter is provided, the string is split by spaces. The result is always of type `list<string>`. Both arguments must be strings if a delimiter is provided.
- **Join Expressions**: Join a list of strings into a single string using the syntax `join(list)` or `join(list, delimiter)`. If no delimiter is provided, the strings are joined with no separator. The first argument must be a `list<string>`, and the optional second argument must be a string.
- **Sort Expressions**: Sort a list using the syntax `sort(list)` or `sort(list; lhs, rhs yeet comparison)`. For `list<number>`, the comparison expression is optional and defaults to ascending numeric order. For other list types, you must provide a custom comparison function. The comparison expression should evaluate to `true` if `lhs < rhs`. The identifiers `lhs` and `rhs` can be any names that don't shadow existing identifiers. Returns a sorted list of the same type.
- **List Comprehensions**: Create new lists by transforming elements from an iterable (string or list) using the syntax
  `for <iterable> as <element> [if <condition>] yeet <expression>`. The optional `if <condition>` filters which
  elements are processed. See the List Comprehensions section below for details.
- **Collect Expressions**: Reduce an iterable (string or list) to a single value using the syntax
  `collect <iterable> as <accumulator>, <element> with <expression>`. See the Collect Expressions section below for
  details.

## Builtin Functions

The scripting language provides several builtin functions that can be called using the syntax `'function_name'(arguments...)`. All function names must be specified as string literals. All builtin functions return their result as a string value. This keeps them consistent with calling scripts.

### String Functions

- **`'type'(value)`**: Returns the data type of the value as a string (`'string'`, `'number'`, `'bool'`, or
  `'list<type>'`).
- **`'length'(str)`**: Returns the length of a string or list as a number. Requires a string or list argument.
- **`'upper'(str)`**: Converts a string to uppercase. Requires a string argument.
- **`'lower'(str)`**: Converts a string to lowercase. Requires a string argument.
- **`'trim'(str)`**: Removes whitespace from both ends of a string. Requires a string argument.
- **`'replace'(str, old, new)`**: Replaces all occurrences of `old` with `new` in the string. All arguments must be strings.
- **`'contains'(haystack, needle)`**: Returns `true` if the haystack (string or list) contains the needle, otherwise
  `false`. For lists, the needle must be of the same type as the list elements.
- **`'starts_with'(str, prefix)`**: Returns `true` if the string starts with the prefix, otherwise `false`. Both arguments must be strings.
- **`'ends_with'(str, suffix)`**: Returns `true` if the string ends with the suffix, otherwise `false`. Both arguments must be strings.

### Math Functions

- **`'abs'(num)`**: Returns the absolute value of a number.
- **`'min'(num1, num2, ...)`**: Returns the minimum of one or more numbers. Accepts any number of arguments. Can also
  accept a single list of numbers.
- **`'max'(num1, num2, ...)`**: Returns the maximum of one or more numbers. Accepts any number of arguments. Can also
  accept a single list of numbers.
- **`'round'(num)`**: Rounds a number to the nearest integer.
- **`'floor'(num)`**: Rounds a number down to the nearest integer.
- **`'ceil'(num)`**: Rounds a number up to the nearest integer.
- **`'sqrt'(num)`**: Returns the square root of a non-negative number.
- **`'pow'(base, exponent)`**: Returns base raised to the power of exponent.

### Utility Functions

- **`'random'(min, max)`**: Returns a random floating-point number between min and max.
- **`'timestamp'()`**: Returns the current Unix timestamp (seconds since epoch) as a number.
- **`'date'(format)`**: Returns the current UTC date/time formatted according to the format string (using Python's `strftime()` format codes).

## List Comprehensions

List comprehensions provide a concise way to create new lists by transforming elements from an iterable. The syntax is:

```
for <iterable> as <element> [if <condition>] yeet <expression>
```

- `<iterable>` can be a list or a string
- `<element>` is the name of the loop variable that represents each element during iteration
- `<condition>` (optional) is a boolean expression that filters which elements are included in the result
- `<expression>` is evaluated for each element that passes the condition (if present) and determines what goes into the resulting list
- The keyword `if` introduces an optional filter condition
- The keyword `yeet` separates the condition (or element declaration if no condition) from the transformation expression

The result is a new list containing the transformed elements. When iterating over a string, each character becomes an
element. When iterating over a list, each item in the list becomes an element. If a condition is specified, only
elements for which the condition evaluates to `true` are included in the resulting list.

**Examples:**

```
// Square each number in a list
LET numbers = [1, 2, 3, 4, 5];
LET squared = for numbers as num yeet num * num;
PRINT squared;  // Output: [1, 4, 9, 16, 25]

// Convert strings to numbers
LET words = ['123', '456', '789'];
LET parsed = for words as word yeet $word;
PRINT parsed;  // Output: [123, 456, 789]

// Convert strings to uppercase
LET words = ['apple', 'banana', 'cherry'];
LET upper = for words as word yeet 'upper'(word);
PRINT upper;  // Output: [APPLE, BANANA, CHERRY]

// Iterate over characters in a string
LET result = for 'hello' as char yeet 'upper'(char);
PRINT result;  // Output: [H, E, L, L, O]
```

**Filtering with Conditions:**

You can add an optional `if` condition to filter elements:

```
// Filter numbers greater than 3
LET numbers = [1, 2, 3, 4, 5];
LET filtered = for numbers as num if num > 3 yeet num;
PRINT filtered;  // Output: [4, 5]

// Filter words starting with 'a'
LET words = ['apple', 'acorn', 'banana', 'avocado'];
LET a_words = for words as word if ?'starts_with'(word, 'a') yeet word;
PRINT a_words;  // Output: [apple, acorn, avocado]

// Filter and transform: get squares of numbers greater than 2
LET numbers = [1, 2, 3, 4, 5];
LET large_squares = for numbers as num if num > 2 yeet num * num;
PRINT large_squares;  // Output: [9, 16, 25]
```

**Nested List Comprehensions:**

Nested list comprehensions must be enclosed in parentheses for better readability:

```
LET nested_lists = [[1, 2], [3, 4], [5]];
LET doubled = for nested_lists as sublist yeet (for sublist as num yeet num * 2);
PRINT doubled;  // Output: [[2, 4], [6, 8], [10]]
```

**Important Notes:**

- The loop variable (`<element>`) cannot shadow (have the same name as) any existing variable, parameter, or store
- The optional condition (if provided) must be a boolean expression
- Empty list literals cannot be used in list comprehensions, as the type cannot be inferred
- The type of the resulting list is determined by the type of the `<expression>`

## Range Operators

Range operators provide a convenient way to generate sequences of integers. The scripting language supports two range operators:

- **Inclusive range (`..=`)**: Generates a list that includes both the start and end values
- **Exclusive range (`..<`)**: Generates a list that includes the start value but excludes the end value

### Syntax

```
<start> ..= <end>  // Inclusive range
<start> ..< <end>  // Exclusive range
```

Both `<start>` and `<end>` must be numbers representing integers (no fractional part).

### Behavior

- **Ascending ranges**: When start ≤ end, the range generates values from start to end
- **Descending ranges**: When start > end, the range generates values from start down to end
- **Type**: Both operators return `list<number>`

### Examples

```
// Basic ascending ranges
PRINT 1..=5;    // Output: [1, 2, 3, 4, 5]
PRINT 1..<5;    // Output: [1, 2, 3, 4]

// Descending ranges
PRINT 5..=1;    // Output: [5, 4, 3, 2, 1]
PRINT 5..<1;    // Output: [5, 4, 3, 2]

// Negative ranges
PRINT -2..=2;   // Output: [-2, -1, 0, 1, 2]
PRINT -5..<0;   // Output: [-5, -4, -3, -2, -1]

// Edge cases
PRINT 0..=0;    // Output: [0]
PRINT 0..<0;    // Output: []

// Integration with list comprehensions
LET squares = for (1..=5) as n yeet n * n;
PRINT squares;  // Output: [1, 4, 9, 16, 25]

// Integration with collect
LET sum = collect (1..=10) as acc, n with acc + n;
PRINT sum;      // Output: 55

// Using ranges for iteration
LET data = ['a', 'b', 'c', 'd', 'e'];
LET indices = 0..=4;
LET indexed = for indices as i yeet data[i];
PRINT indexed;  // Output: [a, b, c, d, e]
```

### Important Notes

- Both operands must be numbers without fractional parts (integers)
- Runtime error if operands have fractional parts (e.g., `1.5..=3` raises an error)
- Type error if operands are not numbers (e.g., `'a'..='z'` raises a type error)
- Ranges can be used anywhere a list expression is expected

## Collect Expressions

Collect expressions provide a way to reduce an iterable (string or list) to a single value by repeatedly applying an
operation. This is similar to a fold/reduce operation in functional programming. The syntax is:

```
collect <iterable> as <accumulator>, <element> with <expression>
```

- `<iterable>` can be a list or a string
- `<accumulator>` is the name of the variable that holds the accumulated result
- `<element>` is the name of the variable that represents each element during iteration
- `<expression>` is evaluated for each element and must return a value of the same type as the accumulator
- The keyword `with` introduces the expression that combines the accumulator with each element

For lists, the accumulator is initialized with the first element, and the iteration starts from the second element. For
strings, the accumulator is initialized with an empty string, and all characters are processed.

**Examples:**

```
// Sum all numbers in a list
LET numbers = [1, 2, 3, 4, 5];
LET sum = collect numbers as acc, elem with acc + elem;
PRINT sum;  // Output: 15

// Calculate the product of all numbers
LET numbers = [1, 2, 3, 4];
LET product = collect numbers as acc, elem with acc * elem;
PRINT product;  // Output: 24

// Concatenate strings
LET words = ['Hello', ' ', 'World', '!'];
LET message = collect words as acc, elem with acc + elem;
PRINT message;  // Output: Hello World!

// Concatenate characters from a string
LET result = collect 'hello' as acc, char with acc + 'upper'(char);
PRINT result;  // Output: HELLO
```

**Complex Example - Combining List Comprehension and Collect:**

```
// Calculate the sum of sums of nested lists
LET nested = [[1, 2], [3, 4], [5]];
LET sum = collect (
    for nested as inner_list yeet (
        collect inner_list as acc, num with acc + num
    )
) as outer_acc, inner_sum with outer_acc + inner_sum;
PRINT sum;  // Output: 15
```

**Important Notes:**

- The accumulator and element variables cannot shadow existing variables, parameters, or stores
- The `<expression>` must return a value of the same type as the elements in the iterable
- Empty iterables cannot be used in collect expressions, as the initial accumulator value cannot be determined
- Both the accumulator and element are scoped to the collect expression only

