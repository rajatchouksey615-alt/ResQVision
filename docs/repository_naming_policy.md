# Repository Naming Policy

Use functional capability names in paths, documentation, configuration, source files, tests, and commit messages. Suitable names describe work such as authentication, database foundations, incident management, candidate review, or a user workflow. Avoid numbered project-status labels and their inflections.

The automated checker scans first-party filenames, directory names, and text files across the repository, including untracked files. It skips Git internals, virtual environments, generated build output, caches, third-party dependencies, and the ignored local PostgreSQL data directory. The same checker validates staged paths and contents before a commit, and validates the proposed commit message.

Enable the version-controlled hooks for this checkout with:

```sh
git config core.hooksPath .githooks
```

The repository policy workflow also scans repository files and commit messages for pushes and pull requests. A change that fails the check cannot pass that workflow.
