# DESIGN.md — AgencyDesk

## Tenant isolation (schema-level, not just query-level)

Every business table (`clients`, `projects`, `tasks`, `comments`, `time_entries`,
`files`, `invites`, `project_memberships`) carries an `agency_id` column. That
alone is the usual approach and is only as safe as every app-layer query
remembering to filter by it.

I went one step further: every child table has a **composite foreign key**
`(parent_id, agency_id) -> parent(id, agency_id)`, enforced by a
`UniqueConstraint(id, agency_id)` on the parent. Concretely: `tasks.project_id`
is constrained together with `tasks.agency_id` against `projects(id, agency_id)`.
This means the database itself rejects an insert/update that tries to attach a
task from Agency A to a project owned by Agency B — even if a bug in the app
layer computed the wrong `agency_id`, Postgres refuses the row. Same pattern
for comments→tasks, time_entries→tasks, files→tasks, and
project_memberships→projects/memberships.

On top of that, every route derives `agency_id` from the authenticated
`AuthContext` (never from the request body/URL) and every query is filtered by
it — see `_visible_project_ids()` / `_task_query()` in the routers, which are
the single choke points every list/detail/search path reuses, so the rule
can't drift between the board view and, say, comments.

## Blocking internal content from clients

`tasks`, `comments`, and `files` all carry a `visibility` enum
(`internal` / `client_visible`). Every read path for a `client_user` role adds
`.filter(visibility == client_visible)` at the query level (`_task_query`,
`_file_query`, the comments list). This is applied identically on list views,
single-item lookups (a client hitting a known internal task ID gets a 404, not
a 403 — so an ID guess can't even confirm existence), search, and the
dashboard's task counts. Write paths are equally locked down: `require_agency_staff`
blocks `client_user` from the task-create/update and time-entry routes at the
dependency layer, and comment creation force-overwrites `visibility` to
`client_visible` server-side regardless of what a client's request body claims.

## One identity, two agencies

`User` is a single global table keyed by email — there is no per-agency user
table. A separate `Membership` table (`user_id`, `agency_id`, `role`,
optional `client_id`) is what actually carries role/tenant context, with a
`unique(user_id, agency_id)` constraint: one row per agency, as many rows as
there are agencies. Login is two steps: `/auth/login` verifies the password
once and returns every membership tied to that email; `/auth/select-agency`
takes a short-lived identity token plus a chosen `membership_id` and issues an
access token scoped to exactly that membership. The access token's role/
tenant claims never mix across agencies within one session — switching agencies
means logging in again and picking the other membership.

## Edge case I'm proud of: invite races + double-accept

A **partial unique index** — `CREATE UNIQUE INDEX ... ON invites (agency_id, email)
WHERE status = 'pending'` — makes it impossible for two pending invites to
exist for the same email in the same agency, at the database level, no matter
how many times "resend" is clicked concurrently. The create-invite endpoint
does a find-or-return instead of blind-inserting, so it never even races the
constraint. Accepting is idempotent from the caller's point of view: a second
`accept-invite` call with the same token doesn't error if it's the same
account re-submitting — it just returns a fresh token — but a *different*
account trying to reuse an already-consumed token is rejected. Both paths are
covered by `test_invite_resend_does_not_duplicate` and
`test_accept_invite_twice_is_idempotent`.
