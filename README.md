[![GitHub last commit](https://img.shields.io/github/last-commit/baptabl/cinema?style=flat-square)](https://github.com/baptabl/cinema/commits)  [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Fetch theaters shows from http://www.allocine.fr in order to put them on a lightweight web page.

Credits for the idea and initial code goes to my friend JC. And design credits goes to Hamlet.

This code is licensed under GNU AGPL 3.0: **a modified version used to provide a service, commercial or not, must distribute its complete source code.**
Illegal uses will be prosecuted under French law.


### Quickstart
Install `imagemagick` (for compressing images, disable this with `COMPRESS_PIC=False` in settings), e.g. on Debian:
```sh
sudo apt install imagemagick
```

then clone this repo and run the script with:
```sh
python3 main.py
```

Your freshly generated `index.html` pages will be located in `html/`.

That's it!


### (optional) systemd service
Do not forget to use absolute paths in settings.py if using a systemd service.

Move:
- `templates/systemd/cinema.unit`   # adapt the script path to your own location
- `templates/systemd/cinema.timer`  # cron to run the service everyday

into a systemd subdir of your choice, e.g.:
- `/etc/systemd/system/`

Then enable and optionally start the unit (as you would do for any systemd unit):
```sh
systemctl enable cinema.timer
# restart your system or run the following:
systemctl start cinema.timer
```

You should see your timer here:
```sh
systemctl list-timers
```


### Settings
Edit settings in `settings.py`.

Edit your theaters preference list in `theaters.csv`. Get theaters codes from the allocine URL,
ex. http://allocine.fr/seance/salle_gen_csalle=C0076.html where `C0076` is the code.


### Translation
By default, everything is generated as french. You can change this by changing "fr_FR.UTF-8" to your locale in the settings.
Before doing so, you need to ensure your locale is available in your current Linux system:
```sh
locale -a
```

If not, uncomment the desired locale from `/etc/locale.gen` (if multiple entries, use the UTF-8 one) then run:
```sh
sudo locale-gen
```


### Contributing
Contributions are welcome! Feel free to open [issues](https://github.com/baptabl/cinema/issues) or [pull requests](https://github.com/baptabl/cinema/pulls).

Development on the latest version of Python is preferred. As of this writing it's 3.11.

Install pre-commit hooks:
```sh
pip install pre-commit
pre-commit install
```

Then, any new commit will run linting tools. You're ready to contribute!
