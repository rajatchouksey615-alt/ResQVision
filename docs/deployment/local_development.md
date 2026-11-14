# Local Development Guide

**Status:** Planning guide. No service is runnable from this Phase 0 repository.

## Planned Local Services

The expected development environment may include the mobile app, Django backend, PostgreSQL, and AI service. Docker is planned for supporting local services, but no Compose file or containers are configured. Agree supported tool versions before implementation.

## Setup Conventions

1. Install approved tools for the module being developed using their official instructions.
2. Keep each module's environment isolated and follow its README.
3. Create a private local environment file from .env.example only when the relevant service is implemented. Use local-only placeholder credentials and never commit the private file.
4. Start only services required for the task and use synthetic or approved data.
5. Follow module-specific validation instructions and stop services when finished.

Map, object storage, and Firebase providers are not configured. Do not connect the prototype to real emergency services.
