Fetch theaters shows from http://www.allocine.fr in order to put them on a lightweight web page.

Credits for the idea and initial code goes to my friend JC. And design credits goes to Hamlet.

### Quickstart
Clone this repo then run:
```sh
python3 cinema.py
```

And go to `html/` to see your freshly generated `index.html` page.


### Settings
Edit settings in `settings.py`.

Edit your theaters preference list in `theaters.csv`. Get theaters codes from the allocine URL,
ex. http://allocine.fr/seance/salle_gen_csalle=C0076.html where `C0076` is the code.


### Contributing
You'll need Python3, and only Python3 standard lib.

This repo tries to follow [Python PEPs](https://peps.python.org/pep-0000/). Please run [Black](https://github.com/psf/black) after any change:
```sh
black --config pyproject.toml .
```

Contributors are welcome, feel free to open issues or pull requests.

Todo:
- locally fetch pictures in order to dispense users from having to request allocine.fr
