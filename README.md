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

If you have a wrapper/alias installed, this may also work:

```bash
nc my_program.nc
```

### Important for buttons and checkmarks

Buttons are shown best in a real interactive terminal such as normal Windows CMD or PowerShell.

If NC is started in a non-interactive environment, button rendering may not be shown properly.

---

## EXE export

You can build a Windows executable from a local `.nc` file:

```bash
python nc_console.py my_program.nc --exe
```

This feature requires `pyinstaller`.

---

# New in this version

This version adds several quality-of-life features for console apps and menus.

## 1. Input without parentheses

Both styles now work:

```nc
let name = input("What is your name?")
```

```nc
let name = input "What is your name?"
```

## 2. Better `+` string concatenation

This now works much better:

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

This is especially useful in buttons:

```nc
button "Exit":
  action:
    end
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

---

# Complete NC learning guide

## 1. Print text

```nc
print "Hello world"
print "NC is simple"
print "NC is readable"
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

## 4. Repeat blocks

```nc
repeat 3:
  print "Hello"
```

## 5. Aliases

```nc
repeat = again

again 3:
  print "Hi"
```

## 6. Conditions

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

## 7. `when` as a simpler alias

```nc
when x == 10:
  print "ten"
else:
  print "not ten"
```

## 8. Buttons

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

## 9. Checkmarks

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

## 10. Colors

```nc
textcolor red
print "Red text"
```

```nc
textcolor --all blue
print "Everything is blue"
```

## 11. Input

Classic call style:

```nc
let name = input("What is your name?")
print name
```

New short style:

```nc
let name = input "What is your name?"
print "Hello, " + name + "!"
```

## 12. Imports

NC contains built-in placeholder modules such as `ui`, `math`, and `json`.

```nc
import math
print math.pi

import json
```

## 13. Saving and loading data

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

## 14. GUI / TWIN output

NC can also produce structured GUI-style output through `__TWIN__` messages.

The GUI host can render:

- windows
- tables
- plots
- HTML content
- TWIN / `t_windows` style messages

## 15. NC server mode

`nc_server.py` can run NC files as lightweight web handlers.

It can:

- map HTTP requests to NC files
- inject request data into NC code
- capture NC output
- return HTTP metadata and body content

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

## Step 5: Use conditions

```nc
let x = 5

if x == 5:
  print "Correct"
else:
  print "Wrong"
```

## Step 6: Create your first menu

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

## Step 7: Add checkmarks

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

## Step 8: Ask the user for a name

```nc
button "Say hello":
  action:
    let name = input "What is your name?"
    print "Hello, " + name + "!"
```

## Step 9: Exit cleanly

```nc
button "Exit":
  action:
    end
```

## Step 10: Export your program

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

---

# Big demo file

```nc
import json

print "Welcome to NC Demo"

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
  json.save("demo_settings", {
    "sound": sound,
    "music": music,
    "hardmode": hardmode
  })
  print "Settings saved"

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
