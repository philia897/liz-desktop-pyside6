<div align="center">
  <img src="assets/icon_1024.png" width="100"/>
  <h2>Remember and Execute shortcuts for you</h2>
</div>

# liz-desktop

[English](./README.md) [中文](./README_zh.md) 

A Rust-based shortcut helper to remember, customize and autorun shortcuts or commands. Developed via Rust + Pyside6.

- Windows ☑️
- Linux ☑️
- Mac ✘

![demo](./assets/demo.gif)

## Features

- **Fuzzy search:** Search by description, application name or shortcut keys.
- **Auto-execution:** Use [enigo](https://github.com/enigo-rs/enigo) to auto-execute the selected shortcut.
- **Shortcut/Typing:** Liz supports:
    - Shortcut: `ctrl+c` 
    - Typing a string: `Liz and the Blue Bird` 
    - Hybrid: `esc [STR]+ Liz and the Blue Bird`
- **Dark/Light mode:** Following the system
- **Dynamic rank:** Rank the shortcuts according to the frequency. The most frequently used shortcuts will be on the top.
- **Shortcut manager:** Has a builtin pretty config panel for managing shortcuts
- **Import/Export:** Support importing/exporting the shortcuts via json/txt files.
- **Smaller Memory usage:** Only consumes less than 100M memory.

> You can see an example of **sheet** [here](./data/sheets/examples.json), which denotes the json file that defines a bunch of shortcuts. In the example it shows how to add different types of shortcut commands. In the `data/sheets` you can find other sheets I created and feel free to have a try.

> This [Python script](./scripts/parse_shortcuts.py) can parse Keyboard Shortcuts in [cheatsheets.zip](https://cheatsheets.zip/), extract the shortcuts in the markdown file (click the github icon in the topbar to download the original markdown file), and generate the json file to be imported into Liz.

## Usage

### Installation

Please check the [release](https://github.com/philia897/liz-desktop-pyside6/releases) and download the runnable.

> Arch [AUR](https://aur.archlinux.org/packages/liz-desktop-bin): `paru -S liz-desktop-bin`

### Quick Start

 - Download shortcut sheet examples [here](./data/sheets/).
 - Open the config panel via tray menu `Manage`. Right click the table to `Import` the downloaded json sheets.
 - Click tray menu `Show` to activate Liz and enjoy.

> You can use a `trigger_shortcut` to `Show` liz as well, the shortcut is `<ctrl>+<alt>+L` by default.

### Configuration

You can control the Liz configuration via any of the following ways:

- (Recommand) Use the builtin Config panel via tray menu `Config`.

- write a `rhythm.toml` file following this [example](./data/rhythm.toml) and put it under default `<liz_path>/rhythm.toml`. Liz will automatically use it.

> According to the [doc of enigo](https://github.com/enigo-rs/enigo#), For Linux users you'd better to install these tools for X11 support:
> 
> Debian-based: `apt install libxdo-dev`
>
> Arch: `pacman -S xdotool`
>
> Fedora: `dnf install libX11-devel libxdo-devel`
>
> Gentoo: `emerge -a xdotool`


## TroubleShooting

> Please create an issue if encounter any bug or error

In the first run, Liz will create its data dir `liz_path` automatically with the default config path, which will be:

- **Windows:** `%APPDATA%\liz`, such as: `C:\Users\<YourUsername>\AppData\Roaming\liz`
- **Linux:** `$HOME/.config/liz`, such as: `/home/<YourUsername>/.config/liz`

> It can also be customized by setting the environment variable `LIZ_DATA_DIR`.

To reset settings to default, simply delete the file `<liz_path>/rhythm.toml`, or clear the values in the config panel.

## Future plan

- Add Mac support (It theoretically works, but I have not tested it yet. No Mac equipment)
- Using tauri plugins to remember window position and size.
- Using tauri plugin for logging.
- Try SQLite instead of the json lock file for data persistence.
- Find way to reduce the memory cost, (maybe provide a solution to use external tools like [Rofi](https://github.com/davatorium/rofi/))
- ...

## Credits & License

- Thanks to the wonderful projects [Pyside6](https://doc.qt.io/qtforpython-6/gettingstarted.html#getting-started), [Enigo](https://github.com/enigo-rs/enigo) and [Reference](https://github.com/Fechin/reference/tree/main).
- License: [GPL-3](./LICENSE)

