# How to contribute

## Working with git and pull requests
Use feature branches - whenever working on a feature/change, don't do it on `main`.
Create a new branch with `git switch -c <branch name>` and implement your changes there.
Once done push your changes upstream (`git push -u origin <branch name>`) and create a pull request using GitHub's UI.

The repository has Jira integration enabled.
If you wish to automatically mark a ticket as done, reference a Jira ticket by its ID in the title of commit or a pull request.
You can also reference a ticket in the body of a commit/PR by prefixing a ticket ID with word 'fixes' or 'closes'

## Maintenance
This project uses `uv` package manager. It is stable and heaps faster than `pip`.
You can install `uv` globally (either with `pip` or your system package manager) or bootstrap it inside a virtual environment.

| pip command     | uv command                      | Comment                                                                                    |
| --------------- | ------------------------------- | ---------------------------                                                                |
| `pip install`   | `uv add`                        | Add a package. Add `--dev` flag if the package is meant to be used only during development |
| `pip uninstall` | `uv remove`                     | Remove a package. Also use `--dev` to remove from development packages.                    |
| `pip freeze`    | `uv pip compile pyproject.toml` | Create `requirements.txt`. Add `--group dev` to include development packages.              |

When adding a package make sure to add **both** `pyproject.toml` and `uv.lock` to your commit.

It is advised to use `pre-commit` although not required.
It installs a git hook that does code format and linter checks before a commit is made.
This help to keep the code style consistent and reduce the number of "fix formatting" commits.
To use `pre-commit` run `pre-commit install` while inside virtual environment.


## Testing
We use `pytest` as our unit testing framework.
Place unit tests inside `test/` directory in order for them to be picked up.


## Setting up development environment
If you have `uv` installed globally just run `uv sync` on the terminal in the root directory of the repository.
`uv` will take care to create a virtual environment with compatible Python version and install **all** packages.

### Bootstrapping
If you don't want to have `uv` globally or can't, you can install it into a virtual environment.
You need to do the following only once since the project lists `uv` as development dependency.

Linux/Mac:
```
python -m venv .venv
source .venv/bin/activate
python -m pip install uv
uv sync
```

Windows (cmd.exe):
```
python -m venv .venv
.\.venv\bin\activate.bat
python -m pip install uv
uv sync
```

## The workflow summarized

  1. Clone the repository
  2. Setup virtual environment
  3. Create a new branch
  4. Make your changes on that branch
  5. Once done push the changes upstream
  6. Make a pull request to merge into main
