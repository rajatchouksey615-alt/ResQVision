# System Architecture

**Status:** Initial architecture template. Component integration and deployment choices remain to be confirmed.

## Context and Components

- Mobile app: Flutter and Dart UI for the three planned roles.
- Backend: Django REST API and PostgreSQL for authentication, authorization, incident business logic, structured records, evidence metadata, and notification coordination.
- AI service: Python video analysis for detection, tracking, candidate identification, temporal verification, and evidence generation.
- Object storage: provider pending; planned for media files.
- Push notifications: Firebase Cloud Messaging planned; no live configuration or delivery.
- Maps: provider pending.

## Intended Information Flow

1. An approved video source is supplied to the AI service under a reviewed data policy.
2. The service identifies a candidate and applies verification logic. A candidate is not automatically a confirmed accident.
3. The backend receives an authorized result through a documented contract, manages an incident record, and stores evidence metadata.
4. The mobile app reads and updates data through authenticated, role-authorized backend API operations.
5. Any notification behavior in the prototype is simulated. Real emergency service integrations remain disabled unless explicitly authorized.

## Trust and Data Boundaries

The backend is authoritative for authentication and access control. The AI service must not be treated as an authority to dispatch responders. Structured records belong in PostgreSQL; media files are intended for separately governed object storage. All video, location, incident, and evidence data must be treated as sensitive.

## Pending Decisions

Define service-to-service authentication, video input, deployment topology, media access, provider choices, observability, and operational ownership before integration or deployment.
