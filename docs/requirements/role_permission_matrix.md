# Role-Permission Matrix

**Status:** Proposed least-privilege baseline for team review; backend enforcement is required. This matrix does not authorize contact with real emergency services.

## Roles

- **ADMIN:** User/role administration and incident oversight. Human verification and assignment permissions are proposed and require explicit team approval.
- **POLICE:** Review and update incidents within an approved assignment or jurisdictional scope.
- **HOSPITAL:** Review the minimum information needed for an approved assignment and update simulated readiness.
- **AI service:** Machine identity for submitting candidate evidence only; it is not one of the human application roles.

## Permissions

Legend: **Yes** = proposed allowed within scope; **No** = not allowed; **Scoped** = only for authorized assignment/scope; **TBD** = policy or authority must be approved.

| Resource/action | ADMIN | POLICE | HOSPITAL | AI service |
|---|---:|---:|---:|---:|
| Authenticate to own account | Yes | Yes | Yes | Service credential |
| Create/disable users and assign supported roles | Yes | No | No | No |
| View user/account administration data | Yes | No | No | No |
| Submit candidate event and evidence metadata | No | No | No | Yes |
| View unverified candidate queue | Yes, proposed | No | No | No |
| Verify or reject candidate | Proposed; authority TBD | No by default; policy TBD | No by default; policy TBD | No |
| View incident summary | Yes, subject to need-to-know | Scoped | Scoped, minimized | No |
| View evidence media | Explicit permission required; scope TBD | Scoped | Scoped and minimized | Write/reference only |
| Assign verified incident | Proposed; assignment policy TBD | No | No | No |
| Acknowledge assignment | No | Scoped | Scoped | No |
| Update police response state | Oversight; exceptional action TBD | Scoped | No | No |
| Update hospital readiness state | Oversight; exceptional action TBD | No | Scoped | No |
| Resolve/close incident | Proposed admin close; operational resolver TBD | Proposed resolve within scope | Readiness update only | No |
| View incident history | Yes | Scoped | Scoped | Own submission outcome only, TBD |
| View aggregate reports | Yes | No by default | No by default | No |
| View audit history | Authorized admin/auditor scope TBD | No | No | No |
| Trigger real emergency notification/dispatch | No | No | No | No |

## Enforcement Rules

1. The backend checks identity, role, resource scope, and action on every protected request. Client-side routing is not an authorization control.
2. Access to incidents and evidence is object-scoped. A role alone does not grant access to every incident or media item.
3. Hospital views should omit fields not required for simulated readiness; final data elements and legal/privacy review are TBD.
4. AI service credentials permit only the agreed event-submission capability. They do not grant user administration, incident assignment, verification, response-state changes, or media browsing.
5. Denied access must not disclose whether an out-of-scope incident or evidence object exists.
6. Role changes, verification, assignment, status changes, and sensitive evidence access require audit events.

## Decisions Required Before Implementation

- Which role or designated human group has final verification/rejection authority?
- Does assignment use a central Admin, rules-based routing, or both?
- What defines Police and Hospital incident scope (explicit assignment, jurisdiction, or another approved rule)?
- Which evidence and incident fields may each responder role see?
- Who may resolve, close, reopen, or correct an incident?
- Which audit actions can be viewed by each role?
