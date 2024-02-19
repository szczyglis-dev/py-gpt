# Contributing to PyGPT

Interested in contributing to PyGPT? Here's how to get started!

We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Proposing new code to codebase

## We Develop with GitHub

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## Report bugs using GitHub's [issues](https://github.com/szczyglis-dev/py-gpt/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/szczyglis-dev/py-gpt/issues/new); it's that easy!

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Environment details (OS, Python version, installed packages versions from `pip list`)
- Version of the application (e.g. 0.1.0), type (compiled version, Snap, Python)
- Steps to reproduce
  - Be specific!
  - Give step-by-step instructions on how to reproduce the issue.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)
- If possible, change the log level to `DEBUG` in the `Settings / Developer / Log level` option and attach the full debug log (**without OpenAI API requests details!**) produced by the app in the terminal or in the `%workdir%/app.log` file.

## Proposing code changes

Pull requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1. Fork the repo and create your branch from `dev`.
2. If you've added code that should be tested, add tests.
3. If it is needed, update the documentation.
4. Ensure the test suite passes.
5. Issue that pull request targeting the `dev` branch.

## Use a Consistent Coding Style

* You can use any editor you like, but make sure your code conforms to our coding conventions.
* We use [PEP8](https://peps.python.org/pep-0008/) for Python code.

## Testing

Our tests are in the tests folder. We use pytest for unit testing. 
To run all unit tests, run the following in the root dir of the project:

`pytest tests`

## Creating a pull request

See these [instructions](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork) to open a pull request against the PyGPT repo.

## Note
Please remember that the project is still in the early stages of development, many things require refactoring and will undergo changes.