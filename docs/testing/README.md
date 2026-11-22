# Testing Documentation

**Status:** REVISED_DRAFT — pending team approval.

This directory describes the proposed testing approach for requirements and system design. The backend has PostgreSQL-backed model and domain-service tests for accounts, audit, organizations, video sources, detection, candidates/incidents, locations, evidence, responses, and notifications. The current full backend suite passes 67 tests, including transaction rollback and a real concurrent candidate verification test. API authorization, object-storage fault, Flutter, AI-evaluation, and end-to-end tests remain future work.
