# Mobile Application Architecture

## Status

This is the planned architecture for the Flutter client. No application code, state-management package, routing package, or API client has been selected in Phase 0.

## Responsibilities

- Render role-aware screens for Admin, Police, and Hospital users.
- Communicate with the backend through versioned HTTPS API contracts.
- Represent loading, empty, error, and success states.
- Request only actions permitted for the authenticated user; the backend remains authoritative for authorization.
- Protect authentication tokens with platform-appropriate secure storage.

## Boundaries

The mobile app must not connect directly to PostgreSQL, access object storage without backend-authorized access, or make emergency dispatch decisions. It should not call the AI service directly in the initial architecture. Maps and push delivery are pending provider decisions and must be introduced through reviewed interfaces.

## Suggested Organization

When implementation begins, organize code around features and keep presentation, application logic, data access, and shared UI concerns understandable for the team. Avoid selecting extra layers or libraries until requirements justify them.

## Integration Decisions

Before implementation, agree on authentication flows, API version and error conventions, pagination, role permissions, evidence access, and provider selection. Record material architecture choices as [architecture decision records](../../docs/decisions/README.md).
