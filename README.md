# Chatbot2k

Chatbot2k is a multi-platform chatbot application with an integrated web dashboard for managing commands, clips, and bot settings. It connects to Discord and Twitch simultaneously, providing a unified interface for chat moderation and interaction.

## Features

### Core Functionality
🔌 **Multi-Platform Support** – Connects to Discord and Twitch simultaneously  
🗣️ **Command System** – Static responses, parameterized commands, and custom script commands  
📖 **Dictionary** – Auto-responds with definitions when keywords/acronyms are mentioned  
📹 **Soundboard** – Trigger audio/video clips via commands  
⌨️ **Custom Scripting Language** – Create complex commands with persistent state and logic  
🌐 **Web Dashboard** – Manage bot features and settings through a web interface  
🔐 **OAuth Authentication** – Secure login with Twitch OAuth for the broadcaster and viewers  
🔔 **Live Notifications** – Discord notifications when streams go live

### Web Dashboard
- **General Settings** – Configure basic application settings
- **Commands Management** – View all available commands
- **Soundboard** – Upload, play, and delete audio/video clips
- **Live Notifications** – Configure Twitch channels for stream-live notifications
- **Overlay** – Embedded media player for OBS/streaming software

### Command Types
- **Static Commands** – Simple text responses (e.g., `!discord` → "Join my Discord: discord.gg/...")
- **Parameterized Commands** – Response templates with placeholders (e.g., `!hello @user`)
- **Script Commands** – Custom logic using the built-in scripting language
- **Soundboard Commands** – Trigger media clips (managed exclusively via web UI)

## Development

The project is written in **Python 3.13+** and uses [Astral's uv](https://docs.astral.sh/uv/) as the package manager.

### Setup

Install dependencies:

```bash
uv sync
```

Run the bot locally with hot-reloading:

```bash
uv run uvicorn chatbot2k.main:app --host 0.0.0.0 --port 8080 --reload
```

### Development Tools

Run linting, formatting, and type-checking:

```bash
uv run fix
```

Run tests with coverage:

```bash
uv run test
```

Check code quality without making changes:

```bash
uv run check
```

### Database Migrations

The project uses Alembic for database migrations:

```bash
# Create a new migration
uv run alembic revision -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

---

## Scripting Language

The bot includes a custom scripting language for creating complex, stateful commands. Moderators can add script commands via chat using:

```
!command add-script !<command_name> "<script_code>"
```

**⚠️ Note**: Soundboard clips cannot be added/removed via chat commands – they must be managed by the broadcaster through the web dashboard.

### Script Structure

Each script can contain:

1. **STORE declarations** (optional) – Persistent variables saved in the database
2. **PARAMS declarations** (optional) – Parameters users provide when invoking the command
3. **Statements** – The actual code (variable definitions, assignments, prints, etc.)

### Data Types

The language supports the following data types:

- **Boolean** – Literals `true` and `false`
- **Number** – Integers and floating-point numbers (maps to Python's `float`)
  - Examples: `42`, `3.14`, `-7`, `0`
- **String** – UTF-8 text enclosed in single quotes
  - Escape sequences: `\'` (quote), `\n` (newline), `\\` (backslash)
  - Example: `'Hello, world!'`
- **List** – Ordered collections of same-typed elements
  - Syntax: `[1, 2, 3]`, `['a', 'b']`, `[[1, 2], [3, 4]]`
  - Type notation: `list<number>`, `list<string>`, `list<list<number>>`

### Reserved Keywords

```
and     as      bool    false   fold    for     if      join
LET     list    not     number  or      PARAMS  PRINT   sort
split   string  STORE   true    with    yeet
```

### Identifiers

- Must start with an ASCII letter
- May contain letters, digits, and underscores
- Case-sensitive
- Cannot be a reserved keyword

### STORE Declarations

Persistent variables saved to the database:

```
STORE <store_name> = <initial_value>;
```

- Created once when the script is first added
- Scoped to the individual script
- Can reference other stores defined earlier
- Changes persist between invocations

**Examples:**

```
STORE counter = 0;
STORE greeting = 'Hello, world!';
STORE total = counter + 10;
```

### PARAMS Declarations

Define parameters that users provide when invoking the command:

```
PARAMS <param1>, <param2>, ...;
```

- All parameters are strings
- Must be unique within the script
- Cannot shadow store names

**Example:**

```
PARAMS name, message;
PRINT 'Hello, ' + name + '! You said: ' + message;
```

Invocation: `!greet Alice "How are you?"`

### Statements

#### Variable Definitions

Define local (non-persistent) variables:

```
LET <var_name> = <expression>;
LET <var_name>: <type> = <expression>;
```

- Type annotations required for empty lists
- Cannot shadow existing names
- Scoped to single execution

**Examples:**

```
LET x = 42;
LET message = 'Hello, ' + 'world!';
LET numbers = [1, 2, 3];
LET empty_list: list<string> = [];
```

#### Assignments

Update stores, parameters, or variables:

```
<name> = <expression>;
```

- Store changes persist to database
- Must respect type compatibility
- Failed executions don't update stores

**Examples:**

```
STORE counter = 0;
counter = counter + 1;  // Updates database

PARAMS name;
name = 'upper'(name);   // Modifies parameter value

LET x = 10;
x = x * 2;             // Updates local variable
```

#### PRINT Statement

Output to chat:

```
PRINT <expression>;
```

- Converts result to string
- Multiple PRINTs are concatenated
- Sent as single message after execution

**Example:**

```
STORE counter = 0;
counter = counter + 1;
PRINT 'This command has been used ';
PRINT counter;
PRINT ' times!';
```

Output: `This command has been used 1 times!`

### Expressions

#### Literals
- Numbers: `42`, `3.14`, `-7`
- Strings: `'Hello'`, `'Line 1\nLine 2'`
- Booleans: `true`, `false`
- Lists: `[1, 2, 3]`, `['a', 'b']`, `[[1], [2]]`

#### Operators

**Arithmetic**: `+`, `-`, `*`, `/`, `%` (numbers only)
```
PRINT 2 + 3 * 4;  // 14 (precedence: * before +)
PRINT 10 % 3;     // 1 (modulo)
```

**Comparison**: `==`, `!=`, `<`, `<=`, `>`, `>=`
```
PRINT 5 > 3;              // true
PRINT 'apple' < 'banana'; // true (lexicographic)
```

**Logical**: `and`, `or`, `not` (booleans only)
```
PRINT true and false;     // false
PRINT not (5 > 10);       // true
```

**Ternary**: `condition ? value_if_true : value_if_false`
```
LET age = 18;
PRINT age >= 18 ? 'Adult' : 'Minor';  // Adult
```

**Concatenation**: `+` for strings and lists
```
PRINT 'Hello' + ' ' + 'world';  // Hello world
PRINT [1, 2] + [3, 4];          // [1, 2, 3, 4]
```

**Subscript**: `string[index]` or `list[index]` (0-based)
```
PRINT 'Hello'[1];      // e
PRINT [10, 20, 30][2]; // 30
```

#### Conversion Operators

**To Number**: `$expression`
```
PRINT $'42';     // 42
PRINT $true;     // 1
PRINT $false;    // 0
```

**To String**: `#expression`
```
PRINT #42;       // 42
PRINT #true;     // true
PRINT #3.14;     // 3.14
```

**To Boolean**: `?expression`
```
PRINT ?1;        // true
PRINT ?0;        // false
PRINT ?'true';   // true
PRINT ?'false';  // false
```

**Code Evaluation**: `!string_expression`
```
LET code = 'PRINT 2 + 3;';
PRINT !code;  // 5
```

#### Ranges

**Inclusive**: `start ..= end`
```
PRINT 1..=5;   // [1, 2, 3, 4, 5]
PRINT 5..=1;   // [5, 4, 3, 2, 1]
```

**Exclusive**: `start ..< end`
```
PRINT 1..<5;   // [1, 2, 3, 4]
PRINT 0..<0;   // []
```

#### Collection Operations

**split** – Split string into list
```
split(string)              // Split by spaces
split(string, delimiter)   // Split by custom delimiter

PRINT split('a,b,c', ',');        // [a, b, c]
PRINT split('hello world');       // [hello, world]
```

**join** – Join list of strings
```
join(list)                 // No separator
join(list, delimiter)      // Custom separator

PRINT join(['a', 'b'], ',');      // a,b,c
PRINT join(['Hello', 'world']);   // Helloworld
```

**sort** – Sort a list
```
sort(list)                        // Ascending (numbers only)
sort(list; lhs, rhs yeet expr)    // Custom comparison

PRINT sort([3, 1, 4, 1, 5]);                      // [1, 1, 3, 4, 5]
LET words = ['banana', 'apple'];
PRINT sort(words; a, b yeet a < b);               // [apple, banana]
```

#### List Comprehensions

Transform elements from an iterable:

```
for <iterable> as <element> [if <condition>] yeet <expression>
```

**Examples:**

```
// Square numbers
PRINT for [1, 2, 3] as n yeet n * n;  // [1, 4, 9]

// Filter and transform
LET nums = [1, 2, 3, 4, 5];
PRINT for nums as n if n > 2 yeet n * 10;  // [30, 40, 50]

// String to numbers
LET words = ['10', '20', '30'];
PRINT for words as w yeet $w;  // [10, 20, 30]

// Nested (use parentheses)
LET nested = [[1, 2], [3, 4]];
PRINT for nested as sub yeet (for sub as n yeet n * 2);
// [[2, 4], [6, 8]]
```

#### Fold Expressions

Reduce iterable to single value:

```
fold <iterable> as <start>, <acc>, <elem> with <expression>
```

**Examples:**

```
// Sum
LET nums = [1, 2, 3, 4, 5];
PRINT fold nums as 0, acc, n with acc + n;  // 15

// Product
PRINT fold nums as 1, acc, n with acc * n;  // 120

// Concatenate
LET words = ['Hello', ' ', 'World'];
PRINT fold words as '', acc, w with acc + w;  // Hello World

// Count
LET items = ['a', 'b', 'c'];
PRINT fold items as 0, acc, _ with acc + 1;  // 3

// Empty list
LET empty: list<number> = [];
PRINT fold empty as 100, acc, n with acc + n;  // 100
```

### Built-in Functions

Call functions using `'function_name'(args...)`. All function names must be string literals.

#### Type & Inspection

- **`'type'(value)`** – Returns type as string (`'string'`, `'number'`, `'bool'`, `'list<type>'`)
- **`'length'(value)`** – Returns length of string or list

#### String Functions

- **`'upper'(str)`** – Convert to uppercase
- **`'lower'(str)`** – Convert to lowercase  
- **`'trim'(str)`** – Remove leading/trailing whitespace
- **`'replace'(str, old, new)`** – Replace all occurrences
- **`'contains'(haystack, needle)`** – Check if string/list contains value
- **`'starts_with'(str, prefix)`** – Check if string starts with prefix
- **`'ends_with'(str, suffix)`** – Check if string ends with suffix

#### Math Functions

- **`'abs'(num)`** – Absolute value
- **`'min'(num1, num2, ...)`** – Minimum value (accepts list or varargs)
- **`'max'(num1, num2, ...)`** – Maximum value (accepts list or varargs)
- **`'round'(num)`** – Round to nearest integer
- **`'floor'(num)`** – Round down
- **`'ceil'(num)`** – Round up
- **`'sqrt'(num)`** – Square root
- **`'pow'(base, exponent)`** – Exponentiation

#### Utility Functions

- **`'random'(min, max)`** – Random float between min and max
- **`'timestamp'()`** – Current Unix timestamp (seconds since epoch)
- **`'date'(format)`** – Current UTC date/time (Python `strftime` format)

**Examples:**

```
PRINT 'type'([1, 2, 3]);              // list<number>
PRINT 'length'('hello');              // 5
PRINT 'upper'('hello');               // HELLO
PRINT 'replace'('hi hi', 'hi', 'bye'); // bye bye
PRINT 'min'(5, 3, 8);                 // 3
PRINT 'sqrt'(16);                     // 4
PRINT 'date'('%Y-%m-%d');             // 2026-01-02
```

---

### Complete Example Scripts

#### Counter Command

```
STORE count = 0;
count = count + 1;
PRINT 'This command has been used ';
PRINT count;
PRINT ' times!';
```

#### Greeter with Parameters

```
PARAMS name;
PRINT 'Hello, ';
PRINT 'upper'(name);
PRINT '! Welcome to the stream!';
```

#### List Processing

```
PARAMS numbers;
LET num_list = for split(numbers, ',') as n yeet $'trim'(n);
LET sum = fold num_list as 0, acc, n with acc + n;
LET avg = sum / $'length'(num_list);
PRINT 'Sum: ';
PRINT sum;
PRINT ' | Average: ';
PRINT 'round'(avg);
```

Invocation: `!average 10, 20, 30, 40`  
Output: `Sum: 100 | Average: 25`

---

## Architecture

### Technology Stack

- **Backend**: FastAPI (Python 3.13+)
- **Database**: SQLite with SQLModel ORM
- **Migrations**: Alembic
- **Chat APIs**: 
  - Discord.py for Discord integration
  - TwitchAPI for Twitch integration
- **Authentication**: Twitch OAuth with JWT session tokens
- **Frontend**: Jinja2 templates with server-side rendering
- **Package Management**: uv

### Project Structure

```
chatbot2k/
├── src/chatbot2k/
│   ├── chats/              # Chat platform integrations
│   ├── command_handlers/   # Command execution logic
│   ├── database/           # Database engine and models
│   ├── models/             # SQLModel data models
│   ├── routes/             # FastAPI route handlers
│   ├── scripting_engine/   # Custom language parser/interpreter
│   ├── types/              # Type definitions
│   └── utils/              # Helper utilities
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS, JS, images
├── migrations/             # Alembic database migrations
├── data/                   # Runtime data (soundboard files, etc.)
└── tests/                  # Test suite
```

### Key Components

- **AppState** – Singleton managing database, chat connections, and command handlers
- **Database** – SQLite with models for commands, translations, settings, clips, etc.
- **Command Handlers** – Pluggable handlers for different command types
- **Scripting Engine** – Full lexer/parser/interpreter for custom language
- **Broadcaster** – System for posting messages repeatedly at a specified interval

---

## License

MIT license. See [LICENSE.txt](LICENSE.txt) for details.

