# Arch Linux Disk Analyzer

[English](#english) | [Українська](#українська)

## English

A command-line utility for Python 3.10+ with no third-party dependencies.
Reports the pacman cache, yay cache and build files, the user's trash,
`/var/log` (including the persistent systemd journal), the temporary journal
in `/run/log/journal`, and the largest top-level directories in the home
directory, including hidden ones.

```bash
cd /home/user/First
python disk_analyzer.py
python disk_analyzer.py --top 20
python disk_analyzer.py --home /home/another_user
python disk_analyzer.py --yay-cache /path/to/yay --pacman-cache /path/to/pkg
```

The program only reads files. Run it as your own user: running it with `sudo`
changes the home directory and may report root's cache and trash instead.
Inaccessible files are marked as an incomplete result, with warnings sent
to stderr. Missing directories are marked separately. Exit codes: `0` — scan
completed, `1` — incomplete scan, `2` — invalid arguments, `130` — Ctrl+C.

Pacman cache paths are read using `pacman-conf CacheDir`; the yay build path
is read from `buildDir` in the yay configuration. If the configuration is
unavailable, default paths are used. Absolute `XDG_CACHE_HOME`, `XDG_CONFIG_HOME`,
and `XDG_DATA_HOME` paths are supported. When `--home` is explicitly provided,
the standard subdirectories of that directory are used, ignoring the current
user's XDG environment variables.

Sizes are calculated from allocated blocks (`st_blocks × 512`), including
the directories themselves. Symbolic links are not followed; hard links
are counted once within each measured directory. Filesystems mounted inside
directories are also scanned. Scanning large disks can take a while. Files
that change during the scan may affect the results.

Trash refers to `$XDG_DATA_HOME/Trash` (by default `~/.local/share/Trash`),
including metadata. Trash directories on other disks are not scanned. Regular
files directly in the home directory are excluded from the directory ranking.
Categories overlap with the ranking and should not be added together. On Btrfs
and other filesystems with shared blocks, these figures do not guarantee how
much space deleting files would free.

Run the tests:

```bash
python -m unittest discover -s tests -v
```

## Українська

### Аналізатор диска для Arch Linux

Консольна утиліта на Python 3.10+ без сторонніх залежностей. Показує кеш
pacman, кеш і збірки yay, кошик користувача, `/var/log` (разом із постійним
systemd journal), тимчасовий journal у `/run/log/journal` та найбільші папки
першого рівня в домашній директорії, включно з прихованими.

```bash
cd /home/user/First
python disk_analyzer.py
python disk_analyzer.py --top 20
python disk_analyzer.py --home /home/інший_користувач
python disk_analyzer.py --yay-cache /шлях/до/yay --pacman-cache /шлях/до/pkg
```

Програма лише читає файли. Запускайте від свого користувача: запуск через
`sudo` змінює домашній каталог і може показати кеш та кошик root.
Недоступні файли позначаються як неповний результат; попередження надходять
у stderr. Відсутній каталог позначається окремо. Коди завершення: `0` — обхід
завершено, `1` — неповний обхід, `2` — помилка аргументів, `130` — Ctrl+C.

Шляхи кешу pacman читаються через `pacman-conf CacheDir`, шлях збірок yay —
з `buildDir` у конфігурації yay. Якщо конфігурація недоступна, використовуються
стандартні шляхи. Підтримуються абсолютні `XDG_CACHE_HOME`, `XDG_CONFIG_HOME`
і `XDG_DATA_HOME`. З явним `--home` використовуються стандартні підкаталоги
вказаної директорії, без XDG-змінних поточного користувача.

Розміри рахуються за виділеними блоками (`st_blocks × 512`), з урахуванням
самих каталогів. Символічні посилання не обходяться; жорсткі посилання
враховуються один раз у межах кожної вимірюваної папки. Змонтовані всередині
папок файлові системи також обходяться. На великих дисках аналіз може тривати
довго. Файли, що змінюються під час обходу, можуть впливати на результат.

Кошик — це `$XDG_DATA_HOME/Trash` (типово `~/.local/share/Trash`), включно
з метаданими. Кошики на інших дисках не скануються. Звичайні файли безпосередньо
в домашньому каталозі не входять до рейтингу папок. Категорії перетинаються
з рейтингом: їх не слід додавати. На Btrfs та інших файлових системах зі
спільними блоками ці числа не дорівнюють гарантованому обсягу звільнення
після видалення.

Перевірка:

```bash
python -m unittest discover -s tests -v
```
