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
command_name> "<script_code>"

Each script consists of multiple sections:

1. **Stores (optional)**: Each store defines a variable that is persisted in the bot's database. This allows persisting
   state across multiple invocations of the script.
2. **Statements**: The actual code that is executed when the script command is invoked.

See below for details on each section.

### Data Types

Currently, the language supports the following data types:

- **Numbers**: Integral or floating-point numbers, possibly negative. They are mapped to Python's `float` type.
- **Strings**: Sequences of characters enclosed in single quotes (`'`). They are mapped to Python's `str` type and
  support UTF-8. The only allowed escape sequences are `\'` for single quote and `\n` for newline.

## Keywords

The following keywords are reserved in the scripting language:

- `LET`
- `PRINT`
- `STORE`

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

## Statements

The following statements are supported:

### Variable Definitions

Define a new variable like this:

```
LET <var_name> = <expression>;
```

Each variable is scoped to the script execution, so it will not persist across multiple invocations of the script.  
`<var_name>` can be any valid identifier that has not been used as a variable name in this script execution before.  
`<expression>` can be any valid expression, including references to stores and previously defined variables.

*Note: Referencing a store will yield its current value from the database, not necessarily its initial value.*

**Example:**

```
LET x = 42;
LET y = x + 10;
LET a = 'Hello, ';
LET b = a + 'world!';
```

### Assignments

You can assign new values to both stores and variables like this:

```
<name> = <expression>;
```

`<name>` can be either a store name or a variable name that has been defined earlier in the script.  
`<expression>` can be any valid expression, including references to stores and variables.

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

- **Literals**: Numbers (e.g., `42`, `3.14`, `-7`) and strings (e.g., `'Hello, world!'`)
- **Variable and Store References**: Using the name of a variable or store to get its current value.
- **Arithmetic Operations**: Addition (`+`), subtraction (`-`), multiplication (`*`), and division (`/`) for numbers.
- **String Concatenation**: Using the `+` operator to concatenate strings.
- **Parentheses**: To group expressions and control the order of evaluation.
