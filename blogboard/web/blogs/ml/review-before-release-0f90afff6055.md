## A deliberate release

This is an authored synthetic fixture, not a live model result. A dependable publishing pipeline treats generation and publication as separate decisions.

## Review the exact artifact

Reviewers should inspect the complete draft before promoting it. A content digest binds approval to the inspected artifact: editing the draft invalidates an earlier approval.

```python
import hashlib
digest = hashlib.sha256(b'reviewed content').hexdigest()
```

## Preserve the previous release

A failed upload must not replace an existing index with an empty collection. Promote a validated site snapshot only after every referenced article is available.

| Condition | Outcome |
| --- | --- |
| Invalid review | Keep the draft private |
| Stale approval | Reject publication |
| Missing article | Preserve the prior index |
| Validated release | Promote the complete snapshot |

## Operational boundaries

Local write tests demonstrate failure handling, not cloud availability or factual accuracy. Model-generated claims and external sources still require human review.
