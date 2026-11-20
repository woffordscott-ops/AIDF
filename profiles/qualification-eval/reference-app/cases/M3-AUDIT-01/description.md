Assign a ticket by email

Support asked to assign tickets from the email address in the customer's message without looking the user id up first. `POST /tickets/<id>/assign` and `tickets.assign_ticket` now accept `assignee_email` in place of `assignee_id`; giving both, or neither, is a 400.

The membership rule is the same as for ids: the person must be an active member of the ticket's tenant. An unknown email is refused with the same message, so the endpoint does not tell the caller which emails exist.

Tests for the new path are next to the existing assignment tests. The existing suite is unchanged and passes.

Review process: reviewers report their findings in a review comment; the author makes the changes.
