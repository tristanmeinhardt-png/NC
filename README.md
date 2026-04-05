# NC (NeuroConsole)

## What is NC?

NC (NeuroConsole) is a scripting language that runs on top of Python and is designed to make console programs easier to write and easier to read.

NC uses `.nc` files as source files. These files are executed by the NC interpreter (`nc.py`) and the command-line launcher (`nc_console.py`). The project also includes an NC HTTP server (`nc_server.py`) and a GUI/TWIN host (`nc_twin_run.py`).

NC is focused on:

* simple syntax
* readable commands
* quick scripting
* reusable functions
* repeat blocks
* console UI elements
* optional GUI/TWIN output
* optional EXE export
* Windows-oriented workflows

---

## Windows only

NC is currently intended for Windows only.

Typical directory example:

```text
C:\Users\(Your name)\NC\standart_imports
```

Why:

* the interpreter is configured around a Windows default imports path
* the CLI workflow is built around Windows usage
* EXE export is Windows-focused
* surrounding tools use Windows-style paths and environments

Other operating systems may work partially, but they are not the target platform.

---

## Main project files

* `nc.py` → main interpreter
* `nc_console.py` → command-line launcher and EXE export
* `nc_server.py` → HTTP server that runs NC files
* `nc_twin_run.py` → GUI/TWIN host for windows, tables, plots, and HTML output
* `t_windows.py` → TWIN / window message helper

---

## Python requirements

### Minimum

For the basic interpreter, NC mainly relies on Python's standard library.

Recommended Python version:

* Python 3.10 or newer

### Optional but recommended modules

Install these for the full NC experience:

```bash
pip install pyinstaller PySide6 PySide6-QtWebEngine
```

### What they are used for

* `pyinstaller` → export `.nc` files as Windows `.exe` files
* `PySide6` → GUI window support in `nc_twin_run.py`
* `PySide6-QtWebEngine` → HTML/JS rendering support in GUI windows

If you only want the basic console language and do not need GUI output or EXE export, Python alone may already be enough for large parts of NC.

---

## Running NC

Run a local NC file:

```bash
python nc_console.py my_program.nc
```

NC can also support URL targets and EXE export through the CLI.

---

## EXE export

You can build a Windows executable from a local `.nc` file:

```bash
python nc_console.py my_program.nc --exe
```

This feature requires `pyinstaller`.

---

# Complete NC learning guide

## 1. Print text

```nc
print "Hello world"
print "NC is simple"
print "NC is readable"
```

## 2. Variables

```nc
x = 5
name = "Alex"
enabled = true

print x
print name
print enabled
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
repeat 3 times:
  print "Hello"
```

Repeat a function:

```nc
fn hi():
  print "Hi"

repeat (hi) 5 times
```

## 5. Aliases

```nc
repeat = again
times = x

fn hi():
  print "Hi"

again (hi) 3 x
```

## 6. Conditions

```nc
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

**Important:** inside a button block, action code must be placed inside `action:`.

Correct example:

```nc
button "Start":
  action:
    print "Starting"

button "Exit":
  action:
    print "Goodbye"
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
    print "Closing program"
```

## 9. Checkmarks

```nc
(sound) = checkmark "Sound"
(music) = checkmark "Music"

if sound is on:
  print "Sound is enabled"
else:
  print "Sound is disabled"

if music is off:
  print "Music is disabled"
else:
  print "Music is enabled"
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

## 10. Colors

```nc
textcolor red
print "Red text"
```

```nc
textcolor --all blue
print "Everything is blue"
```

## 11. Imports

NC contains built-in placeholder modules such as `ui`, `math`, and `json`.

```nc
import math
print math.pi

import json
```

## 12. Save / load ideas

Because NC already has JSON-related built-in module support, save/load features fit naturally into the language design.

```nc
save settings
load settings

save checkmarks "my_settings"
load checkmarks "my_settings"
```

## 13. GUI / TWIN output

NC can also produce structured GUI-style output through `__TWIN__` messages.

The GUI host can render:

* windows
* tables
* plots
* HTML content
* TWIN / t_windows style messages

## 14. NC server mode

`nc_server.py` can run NC files as lightweight web handlers.

It can:

* map HTTP requests to NC files
* inject request data into NC code
* capture NC output
* return HTTP metadata and body content

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
name = "Chris"
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
repeat 3 times:
  print "Repeat works"
```

## Step 5: Repeat a function

```nc
fn beep():
  print "Beep"

repeat (beep) 4 times
```

## Step 6: Use conditions

```nc
x = 5

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
    print "Exiting"
```

## Step 8: Add checkmarks

```nc
(sound) = checkmark "Sound" color "green"
(music) = checkmark "Music" color "cyan"

button "Continue":
  action:
    if sound is on:
      print "Sound is on"
    else:
      print "Sound is off"
```

## Step 9: Save settings

```nc
load checkmarks "game_settings"

button "Save":
  action:
    save checkmarks "game_settings"
```

## Step 10: Export your program

```bash
python nc_console.py my_game.nc --exe
```

# Example games in NC

## 1. Number guessing game

```nc
print "Guess the number"

target = 7

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
    print "Game over"
```

## 2. Simple adventure menu

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
```

## 3. Settings menu game

```nc
load checkmarks "settings"

(sound) = checkmark "Sound" color "green"
(music) = checkmark "Music" color "yellow"
(hardmode) = checkmark "Hard Mode" color "red"

button "Start Game":
  action:
    if hardmode is on:
      print "Hard mode enabled"
    else:
      print "Normal mode enabled"

button "Save Settings":
  action:
    save checkmarks "settings"
    print "Saved"

button "Exit":
  action:
    print "Bye"
```

## 4. Quiz game

```nc
score = 0

button "2 + 2 = 4":
  action:
    score = score + 1
    print "Correct"

button "2 + 2 = 5":
  action:
    print "Wrong"

button "Show Score":
  action:
    print score
```

# Big demo file

```nc
print "Welcome to NC Demo"

load checkmarks "demo_settings"

(sound) = checkmark "Sound" color "green"
(music) = checkmark "Music" color "cyan"
(hardmode) = checkmark "Hard Mode" color "red"

fn show_settings():
  if sound is on:
    print "Sound: ON"
  else:
    print "Sound: OFF"

  if music is on:
    print "Music: ON"
  else:
    print "Music: OFF"

  if hardmode is on:
    print "Hard Mode: ON"
  else:
    print "Hard Mode: OFF"

fn intro():
  print "This is a large NC demo"
  print "Use buttons and checkmarks"
  print "Settings can be saved"

fn play_game():
  print "Game started"
  if hardmode is on:
    print "Enemies are stronger"
  else:
    print "Normal difficulty"

fn repeat_demo():
  repeat 3 times:
    print "Repeat block running"

intro()

button "Show Settings":
  action:
    show_settings()

button "Play":
  action:
    play_game()

button "Repeat Demo":
  action:
    repeat_demo()

button "Save Settings":
  action:
    save checkmarks "demo_settings"
    print "Settings saved"

button "Exit":
  action:
    print "Program ended"
```

# Structure explanation

* `nc.py` → main interpreter
* `nc_console.py` → CLI runner and EXE export
* `nc_server.py` → server-based NC execution
* `nc_twin_run.py` → GUI/TWIN host
* `examples/` → learning examples
* `docs/` → beginner-friendly documentation
* `standart_imports/` → standard import modules as named in the interpreter configuration

## Suggested requirements.txt

```text
pyinstaller
PySide6
PySide6-QtWebEngine
```

## Good next files to add

* `README.md`
* `requirements.txt`
* `LICENSE`
* `examples/`
* `docs/syntax.md`
* `docs/tutorial.md`
