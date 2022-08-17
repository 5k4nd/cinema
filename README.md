[![GitHub last commit](https://img.shields.io/github/last-commit/baptabl/cinema?style=flat-square)](https://github.com/baptabl/cinema/commits)  [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Fetch theaters shows from http://www.allocine.fr in order to put them on a lightweight web page.

Credits for the idea and initial code goes to my friend JC. And design credits goes to Hamlet.

This code is licensed under GNU AGPL 3.0: **a modified version used to provide a service, commercial or not, must distribute its complete source code.**
Illegal uses will be prosecuted under French law.

### Quickstart
Clone this repo then run:
```sh
python3 cinema.py
```

Your freshly generated `index.html` pages will be located in `html/`.


### Settings
Edit settings in `settings.py`.

Edit your theaters preference list in `theaters.csv`. Get theaters codes from the allocine URL,
ex. http://allocine.fr/seance/salle_gen_csalle=C0076.html where `C0076` is the code.


### Contributing
Contributions are welcome! Feel free to open [issues](https://github.com/baptabl/cinema/issues) or [pull requests](https://github.com/baptabl/cinema/pulls).

Development on the latest version of Python is preferred. As of this writing it's 3.10.

Install pre-commit hooks:
```sh
pip install pre-commit
pre-commit install
```

Then, any new commit will run linting tools. You're ready to contribute!
