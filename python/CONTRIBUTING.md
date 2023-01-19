# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

## Types of Contributions

### Report Bugs

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

### Write Documentation

You can never have enough documentation! Please feel free to contribute to any
part of the documentation, such as the official docs, docstrings, or even
on the web in blog posts, articles, and such.

### Submit Feedback

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.

## Get Started!

Ready to contribute? Here's how to set up `bento-meta` for local development.

1. Download a copy of `bento-meta` locally.
2. Install `bento-meta` using `poetry`:

    ```console
    $ poetry install
    ```

3. Use `git` (or similar) to create a branch for local development and make your changes:

    ```console
    $ git checkout -b name-of-your-bugfix-or-feature
    ```

4. When you're done making changes, check that your changes conform to any code formatting requirements and pass any tests.

5. Commit your changes and open a pull request.

## Commit Guidelines

Python Semantic Release (PSR) is used to automatically bump version numbers based on keywords in commit messages.

The default commit message format used by PSR is the [Angular commit style](https://github.com/angular/angular.js/blob/master/DEVELOPERS.md#commit-message-format):

```console
<type>(optional scope): short summary in present tense

(optional body: explains motivation for the change)

(optional footer: note BREAKING CHANGES here, and issues to be closed)
```

**Type** should be one of the following:

* **feat**: A new feature (used by PSR to trigger a minor version bump)
* **fix**: A bug fix (used by PSR to trigger a patch version bump)
* **docs**: Documentation only changes
* **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
* **refactor**: A code change that neither fixes a bug nor adds a feature
* **perf**: A code change that improves performance
* **test**: Adding missing or correcting existing tests
* **chore**: Changes to the build process or auxiliary tools and libraries such as documentation generation

**Scope** can be anything specifying place of the commit change (e.g. `$location`) or `*` when the change affects multiple scopes.

**Subject** contains a succinct description of the change in imperative, present tense (e.g. "change"), without a capitalized first letter or a "." at the end.

**Body** also uses imperative, present tense and includes the motivartion for the change and contrasts to previous behavior.

**Footer** should contain any information about breaking changes and references to GitHub issues that this commit closes.

Breaking changes should start with the word `BREAKING CHANGE:` and are used by PSR to trigger a major release.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include additional tests if appropriate.
2. If the pull request adds functionality, the docs should be updated.
3. The pull request should work for all currently supported operating systems and versions of Python.

## Code of Conduct

Please note that the `bento-meta` project is released with a
Code of Conduct. By contributing to this project you agree to abide by its terms.
