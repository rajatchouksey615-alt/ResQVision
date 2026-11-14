# Component Architecture

**Status:** Component boundaries are planned; code modules do not yet exist.

## Mobile App

Presentation and role-specific workflows; backend API client; secure token handling; loading, error, empty, and success states. The backend enforces permissions.

## Backend

API and serializers; domain logic; authentication and authorization; incident and evidence metadata; notification coordination; PostgreSQL persistence. Keep business logic separate from API views.

## AI Service

Input preprocessing; detection; tracking; candidate identification; temporal verification; evidence generation; and an API boundary only if required by the reviewed architecture. Keep detection and verification distinguishable.

## Infrastructure

Future local development and deployment configuration. No Docker services, cloud resources, or monitoring systems are configured in Phase 0.

## Cross-Component Contracts

Agree on versioned API schemas, identity and role semantics, candidate and verification states, evidence references, errors, retries, and data retention before implementation. Document approved contracts under docs/api_documentation/ and related workflows.
