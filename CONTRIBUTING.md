# Contributing to ResQVision

This guide describes the proposed workflow for the four-member academic project team. Follow any repository-specific instructions added by a module before changing that module.

## Development Workflow

1. Read the relevant requirements, architecture notes, and open decisions before implementation.
2. Select a focused task and coordinate ownership with the team.
3. Create a branch from the agreed integration point; do not commit directly to main.
4. Work feature-first and use test-driven development: define expected behavior, add or update tests, implement, then run the relevant checks.
5. Update documentation when behavior, interfaces, configuration, or decisions change.
6. Open a pull request for review and merge only after agreed checks and review are complete.

The intended stable branch is `main`. `develop` is a planned integration branch that the team may create when ready. Repository setup does not create or switch branches automatically.

## Branch Naming

Use short, descriptive lowercase names with a category prefix:

- feature branches: feature/backend-foundation, feature/flutter-foundation, feature/ai-detection, feature/database-design
- fixes: fix/incident-validation
- documentation: docs/system-architecture

Keep each branch focused on one reviewable change.

## Commit Message Convention

Use the format type: description. Keep the description concise and action-oriented. Approved types are feat, fix, docs, refactor, test, chore, build, and ci.

Examples:

- docs: add incident response workflow template
- feat: add incident status validation

## Pull Request Requirements

Each pull request should explain its purpose, summarize the change, link the relevant issue or task when available, and list validation performed. Include screenshots for material UI changes. Call out API, data, configuration, security, and documentation impacts. Keep the change small enough for another team member to review.

## Code Review

At least one teammate should review each pull request before merge. Review correctness, readability, tests, security, and whether documentation matches behavior. Resolve or discuss review comments before merging.

## Testing Before Merge

Run checks relevant to the changed module and report exact outcomes in the pull request. Add or update tests for behavior changes. Do not report checks that were not run. The repository currently has no runnable module test suites.

## Documentation Requirements

Use Markdown with clear headings. Document assumptions and decisions. Keep diagrams, API contracts, setup instructions, and module READMEs aligned with the implementation. Mark planned work as planned; do not describe unimplemented behavior as complete.

## Repository Naming Policy

Use functional capability names in files, documentation, configuration, and commit messages. See the [repository naming policy](docs/repository_naming_policy.md). Enable the version-controlled hooks with `git config core.hooksPath .githooks`; the repository policy workflow enforces the same check on pushes and pull requests.

## Coding Standards

### Python

- Follow PEP 8 and use clear module, function, and variable names.
- Add type hints where they improve clarity.
- Keep business rules separate from API views and transport concerns.
- Read configuration from environment variables; never hardcode credentials.
- Add unit tests for important logic and use structured, meaningful logging.

### Flutter and Dart

- Follow the official Dart and Flutter style conventions.
- Build reusable widgets and separate presentation from business logic.
- Keep API communication out of UI widgets and use secure storage for sensitive authentication tokens.
- Handle loading, error, empty, and success states.
- Add unit and widget tests for relevant behavior.

### APIs and Documentation

- Use consistent REST resource naming, appropriate HTTP methods and status codes, input validation, authentication, and authorization.
- Keep error response shapes consistent and version APIs deliberately.
- Document decisions and assumptions, and keep documentation synchronized with implementation.

## Secret Management

Never commit passwords, tokens, signing keys, service-account files, private CCTV footage, or production data. Use local environment files excluded by .gitignore and update .env.example with placeholder variable names only. If a secret is exposed, notify the team promptly, revoke or rotate it, and follow SECURITY.md.

## Team Responsibilities

The team has four members. Assign primary and secondary ownership together and record it in [the team responsibility template](docs/project_documentation/team_responsibilities.md). Each module owner should seek cross-review from a teammate; shared API and data contracts require review by affected module owners.
