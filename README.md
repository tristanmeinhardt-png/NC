# NC (NeuroConsole)

## What is NC?

NC (NeuroConsole) is a scripting language that runs on top of Python and is designed to make console programs easier to write, easier to read, and faster to prototype.

NC uses `.nc` files as source files. These files are executed by the NC interpreter (`nc.py`) and the command-line launcher (`nc_console.py`). The project also includes an NC HTTP server (`nc_server.py`) and a GUI/TWIN host (`nc_twin_run.py`).

NC is focused on:

- simple syntax
- readable commands
- quick scripting
- reusable functions
- repeat blocks
- console UI elements
- optional GUI/TWIN output
- optional EXE export
- Windows-oriented workflows
- AI programming

---

# Why should I use NC?

## NC is a simple scripting language built on Python that makes console apps easier to write, read, and share.

### Think of NC as:

- simpler Python for CLI apps
- scripting language with built-in UI elements
- fast prototyping language
- beginner-friendly syntax

---

## Windows only

NC is currently intended for Windows only.

Typical directory example:

```text
C:\Users\(Your name)\NC\
```

Why:

- the interpreter is configured around a Windows default imports path
- the CLI workflow is built around Windows usage
- EXE export is Windows-focused
- surrounding tools use Windows-style paths and environments

Other operating systems may work partially, but they are not the target platform.

---

## Main project files

- `nc.py` → main interpreter
- `nc_console.py` → command-line launcher and EXE export
- `nc_server.py` → HTTP server that runs NC files
- `nc_twin_run.py` → GUI/TWIN host for windows, tables, plots, and HTML output
- `t_windows.py` → TWIN / window message helper

---

## Python requirements

### Minimum

For the basic interpreter, NC mainly relies on Python's standard library.

Recommended Python version:

- Python 3.10 or newer

### Optional but recommended modules

Install these for the full NC experience:

```bash
pip install pyinstaller PySide6 PySide6-QtWebEngine
```

### What they are used for

- `pyinstaller` → export `.nc` files as Windows `.exe` files
- `PySide6` → GUI window support in `nc_twin_run.py`
- `PySide6-QtWebEngine` → HTML/JS rendering support in GUI windows

If you only want the basic console language and do not need GUI output or EXE export, Python alone may already be enough for large parts of NC.

---

## Running NC

Run a local NC file:

```bash
python nc_console.py my_program.nc
```

If you have a wrapper or alias installed, this may also work:

```bash
nc my_program.nc
```

Run an NC file from a URL:

```bash
nc https://example.com/test.nc
```

### CLI options

NC also supports additional CLI options:

```bash
nc my_program.nc --base C:\Users\meinh\NC
nc my_program.nc --libs C:\Users\meinh\NC\libs
nc my_program.nc --allow-http
nc my_program.nc --allow-private
```

What they do:

- `--base` → sets the base folder or URL directory for imports
- `--libs` → adds additional search paths for imports
- `--allow-http` → allows insecure HTTP imports and URLs
- `--allow-private` → allows private or localhost hosts

### Important for buttons and checkmarks

Buttons are shown best in a real interactive terminal such as normal Windows CMD or PowerShell.

If NC is started in a non-interactive environment, button rendering may not be shown properly.

---

## EXE export

You can build a Windows executable from a local `.nc` file:

```bash
python nc_console.py my_program.nc --exe
```

For GUI/TWIN programs you can also use:

```bash
python nc_twin_run.py my_program.nc --exe
```

This feature requires `pyinstaller`.

---

# New in this version

This version adds several quality-of-life features for console apps, menus, reusable code, and GUI output.

## 1. Input without parentheses

Both styles work:

```nc
let name = input("What is your name?")
```

```nc
let name = input "What is your name?"
```

## 2. Better `+` string concatenation

This works well even with mixed values:

```nc
let name = input "What is your name?"
print "Hello, " + name + "!"
```

## 3. `end` keyword

`end` closes the current NC run immediately.

```nc
print "Hello"
end
print "This will not run"
```

## 4. `end` can be aliased

```nc
end = ending

button "Exit":
  action:
    ending
```

## 5. Button keyword variants

NC accepts all of these button keywords:

```nc
button "Play":
  action:
    print "Starting"
```

```nc
botton "Play":
  action:
    print "Starting"
```

```nc
knopf "Play":
  action:
    print "Starting"
```

For documentation and examples, `button` is recommended as the standard spelling.

## 6. `repeat (function) N times`

NC supports directly repeating a callable action:

```nc
fn ping():
  print "hi"

repeat (ping) 5 times
```

This also works without parentheses for simple names:

```nc
repeat ping 3 times
```

## 7. `repeat --all N times`

NC can repeat the whole top-level program:

```nc
repeat --all 3 times
```

You can also write:

```nc
repeat --all (3) times
```

## 8. `export --all`

Inside modules you can export everything at once:

```nc
export --all
```

## 9. `from "...“ import ... as ...`

NC supports path-based imports with optional aliasing:

```nc
from "libs" import tools
from "libs" import tools as helper
```

## 10. `return` and `ret`

Both forms are accepted inside functions:

```nc
fn add():
  ret 5
```

```nc
fn add():
  return 5
```

## 11. `break` and `continue`

Loop control keywords are supported:

```nc
break
continue
```

## 12. More color keyword variants

NC supports additional text color names:

- `textcolor`
- `textcollor`
- `textcolour`
- `fontcolor`
- `printcolor`

Example:

```nc
fontcolor red
print "Hello"
```

Global text color:

```nc
printcolor --all blue
print "Everything is blue"
```

---

# Complete NC learning guide

## 1. Print text

```nc
print "Hello world"
print "NC is simple"
print "NC is readable"
```

NC can also print multiple values:

```nc
print "Score:", 10, "Lives:", 3
```

## 2. Variables

Use `let` for a new variable and `set` for an existing variable.

```nc
let x = 5
let name = "Alex"
let enabled = True

print x
print name
print enabled
```

Change an existing variable:

```nc
let score = 0
set score = score + 1
print score
```

## 3. Functions

```nc
fn hello():
  print "Hello"

hello()
```

Multi-line example:

```nc
fn greet():
  print "Hello user"
  print "Welcome to NC"

greet()
```

Returning values:

```nc
fn get_name():
  return "Alex"
```

or:

```nc
fn get_name():
  ret "Alex"
```

## 4. Repeat blocks

```nc
repeat 3:
  print "Hello"
```

## 5. Repeating functions directly

```nc
fn ping():
  print "hi"

repeat (ping) 3 times
```

## 6. Repeat the whole program

```nc
print "This whole file repeats"
repeat --all 2 times
```

## 7. Aliases

```nc
repeat = again

again 3:
  print "Hi"
```

You can also alias `times` and similar words if your NC setup defines them:

```nc
repeat = wiederhole
times = mal

wiederhole (ping) 2 mal
```

## 8. Conditions

```nc
let x = 5
let enabled = True

if x == 5:
  print "x is 5"
else:
  print "x is not 5"

if enabled:
  print "enabled"
else:
  print "disabled"
```

## 9. `when` as a simpler alias

```nc
when x == 10:
  print "ten"
else:
  print "not ten"
```

## 10. Buttons

Inside a button block, action code must be placed inside `action:`.

Correct example:

```nc
button "Start":
  action:
    print "Starting"

button "Exit":
  action:
    end
```

Buttons can be selected with arrow keys and activated with Enter.

Menu example:

```nc
print "Main menu"

button "Play":
  action:
    print "Game starting..."

button "Settings":
  action:
    print "Opening settings..."

button "Exit":
  action:
    end
```

### Button colors

```nc
button "Play":
  color "green"
  action:
    print "Starting"
```

### Global button color

```nc
color --all "cyan"
```

## 11. Checkmarks

Basic example:

```nc
(sound) = checkmark "Sound"
(music) = checkmark "Music"

if sound:
  print "Sound is enabled"
else:
  print "Sound is disabled"

if music:
  print "Music is enabled"
else:
  print "Music is disabled"
```

Color example:

```nc
(sound) = checkmark "Sound" color "green"
```

Alias example:

```nc
tick = checkmark
(music) = tick "Music"
```

Alternative accepted names include:

- `checkmark`
- `checkbox`
- `check`
- `haken`
- `haekchen`
- `häckchen`

### `is on` / `is off`

```nc
if sound is on:
  print "Sound is enabled"
else:
  print "Sound is disabled"
```

If you want the most stable and simple form, prefer this:

```nc
if sound:
  print "Sound is enabled"
else:
  print "Sound is disabled"
```

## 12. Colors

```nc
textcolor red
print "Red text"
```

```nc
textcolor --all blue
print "Everything is blue"
```

Alternative text color spellings also work:

```nc
fontcolor green
print "Green text"

printcolor --all yellow
```

## 13. Input

Classic call style:

```nc
let name = input("What is your name?")
print name
```

Short style:

```nc
let name = input "What is your name?"
print "Hello, " + name + "!"
```

## 14. Imports

NC contains built-in placeholder modules such as `ui`, `math`, and `json`.

```nc
import math
print math.pi

import json
```

NC also supports importing from a specific base path:

```nc
from "libs" import tools
from "libs" import tools as helper
```

## 15. Exporting from modules

Single export:

```nc
export hello
export run
```

Export everything:

```nc
export --all
```

## 16. Saving and loading data

Use the `json` module.

### Save example

```nc
import json

json.save("my_settings", {
  "sound": sound,
  "music": music,
  "hardmode": hardmode
})
```

### Load example

```nc
import json

let data = json.load("my_settings", {})

if data["sound"]:
  print "Saved sound was ON"
else:
  print "Saved sound was OFF"
```

## 17. Flow control

NC supports `break`, `continue`, and `end`.

```nc
break
continue
end
```

## 18. GUI / TWIN output

NC can also produce structured GUI-style output through `__TWIN__` messages.

The GUI host can render:

- windows
- tables
- plots
- HTML content
- CSS and JavaScript in GUI windows
- TWIN / `t_windows` style messages

### JavaScript bridge

In HTML-based GUI windows, JavaScript can send messages back to the log output:

```js
ncSend("hello")
```

### HTML eval support

The GUI host also supports commands such as:

- `html.eval`
- `js.eval`

This allows dynamic JavaScript execution in the loaded HTML window.

## 19. `t_windows.py` helper API

NC projects can also use the TWIN helper module for structured window creation.

Concepts include:

- `Tk`
- `Toplevel`
- window geometry
- fullscreen windows
- custom window style
- direct HTML content

## 20. NC server mode

`nc_server.py` can run NC files as lightweight web handlers.

It can:

- map HTTP requests to NC files
- inject request data into NC code
- capture NC output
- return HTTP metadata and body content
- answer CORS preflight requests
- serve dynamic responses based on request data

Inside the executed NC file, a request object is injected automatically:

```nc
print request["method"]
print request["path"]
```

NC server handlers can also return HTTP metadata through a special first output line using `__HTTP__`.

---

# Step-by-step tutorial

## Step 1: Your first NC file

Create a file called:

```text
hello.nc
```

Content:

```nc
print "Hello world"
```

Run it:

```bash
python nc_console.py hello.nc
```

## Step 2: Use variables

```nc
let name = "Chris"
print name
```

## Step 3: Use functions

```nc
fn greet():
  print "Hello user"

greet()
```

## Step 4: Repeat actions

```nc
repeat 3:
  print "Repeat works"
```

## Step 5: Repeat a function directly

```nc
fn ping():
  print "hi"

repeat (ping) 3 times
```

## Step 6: Use conditions

```nc
let x = 5

if x == 5:
  print "Correct"
else:
  print "Wrong"
```

## Step 7: Create your first menu

```nc
print "Main menu"

button "Play":
  action:
    print "Starting game"

button "Settings":
  action:
    print "Opening settings"

button "Exit":
  action:
    end
```

## 8. Add checkmarks

```nc
(sound) = checkmark "Sound" color "green"
(music) = checkmark "Music" color "cyan"

button "Continue":
  action:
    if sound:
      print "Sound is on"
    else:
      print "Sound is off"
```

## Step 9: Ask the user for a name

```nc
button "Say hello":
  action:
    let name = input "What is your name?"
    print "Hello, " + name + "!"
```

## Step 10: Exit cleanly

```nc
button "Exit":
  action:
    end
```

## Step 11: Export your program

```bash
python nc_console.py my_game.nc --exe
```

---

# Example programs in NC

## 1. Hello menu

```nc
print "Hello!"

button "Hello back!":
  action:
    print "Thanks!"
    let name = input "What is your name?"
    print "Nice to meet you, " + name + "!"

button "Exit":
  action:
    end
```

## 2. Number guessing game

```nc
print "Guess the number"

let target = 7

button "Guess 5":
  action:
    if 5 == target:
      print "Correct"
    else:
      print "Wrong"

button "Guess 7":
  action:
    if 7 == target:
      print "Correct"
    else:
      print "Wrong"

button "Exit":
  action:
    end
```

## 3. Simple adventure menu

```nc
print "Adventure"

button "Go left":
  action:
    print "You entered a dark forest"

button "Go right":
  action:
    print "You found a river"

button "Stay":
  action:
    print "Nothing happens"

button "Exit":
  action:
    end
```

## 4. Settings menu game

```nc
import json

(sound) = checkmark "Sound" color "green"
(music) = checkmark "Music" color "yellow"
(hardmode) = checkmark "Hard Mode" color "red"

fn save_settings():
  json.save("settings", {
    "sound": sound,
    "music": music,
    "hardmode": hardmode
  })
  print "Saved"

button "Start Game":
  action:
    if hardmode:
      print "Hard mode enabled"
    else:
      print "Normal mode enabled"

button "Save Settings":
  action:
    save_settings()

button "Exit":
  action:
    end
```

## 5. Module export example

```nc
fn hello():
  print "Hello"

fn bye():
  print "Bye"

export --all
```

## 6. Repeat function example

```nc
fn ping():
  print "hi"

repeat (ping) 5 times
```

---

# Big demo file

```nc
import json

print "Welcome to NC Demo"

let data = json.load("demo_settings", {})
let sound = False
let music = False
let hardmode = False

if "sound" in data:
  set sound = data["sound"]
if "music" in data:
  set music = data["music"]
if "hardmode" in data:
  set hardmode = data["hardmode"]

fn show_settings():
  if sound:
    print "Sound: ON"
  else:
    print "Sound: OFF"

  if music:
    print "Music: ON"
  else:
    print "Music: OFF"

  if hardmode:
    print "Hard Mode: ON"
  else:
    print "Hard Mode: OFF"

fn play_game():
  print "Game started"
  if hardmode:
    print "Enemies are stronger"
  else:
    print "Normal difficulty"

fn save_settings():
  json.save("demo_settings", {"sound": sound, "music": music, "hardmode": hardmode})
  print "Settings saved"

(sound) = checkmark "Sound" color "green"
(music) = checkmark "Music" color "cyan"
(hardmode) = checkmark "Hard Mode" color "red"

button "Show Settings":
  action:
    show_settings()

button "Play":
  action:
    play_game()

button "Save Settings":
  action:
    save_settings()

button "Exit":
  action:
    end
```

---

# Structure explanation

- `nc.py` → main interpreter
- `nc_console.py` → CLI runner and EXE export
- `nc_server.py` → server-based NC execution
- `nc_twin_run.py` → GUI/TWIN host
- `examples/` → learning examples
- `docs/` → beginner-friendly documentation
- `standart_imports/` → standard import modules as named in the interpreter configuration

## Suggested `requirements.txt`

```text
pyinstaller
PySide6
PySide6-QtWebEngine
```
