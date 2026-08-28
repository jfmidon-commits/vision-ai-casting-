# Visagism identity anchor

Haircut simulation is an edit of the analysis source photo, not a regeneration of the person.

The safety gate therefore uses the original analysis photo as the mandatory identity anchor. Three to five real source/reference images are still required, but publication needs at least one score at or above the identity threshold (0.80). In the production simulation flow the first reference is always the original analysis photo, so the candidate must match the immutable source identity. Additional references remain useful as diagnostics and resilience against pose, lighting, age, beard and camera differences, but they no longer veto an otherwise valid pixel-locked edit merely because unrelated angles score lower.

This keeps fail-closed behavior for missing scores, invalid reference counts, mask failures, protected-region changes, body changes, provider errors and candidate/original identity mismatch.
