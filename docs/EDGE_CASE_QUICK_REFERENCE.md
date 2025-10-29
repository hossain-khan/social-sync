# Edge Case Quick Reference Guide

> For detailed analysis, see [EDGE_CASE_ANALYSIS.md](EDGE_CASE_ANALYSIS.md)

## At a Glance

This quick reference provides a summary of identified edge cases for the Social Sync project.

---

## Critical Priority (Fix Immediately)

| # | Issue | Impact | Files Affected |
|---|-------|--------|----------------|
| 1 | **Multi-byte Character Handling** | URL expansion fails with emoji/CJK | `content_processor.py` |
| 2 | **Instance Character Limits** | Unnecessary truncation on high-limit instances | `mastodon_client.py`, `content_processor.py` |
| 3 | **Content Warnings Missing** | NSFW posts sync without warnings | `bluesky_client.py`, `mastodon_client.py`, `sync_orchestrator.py` |

---

## High Priority (Fix Soon)

| # | Issue | Impact | Files Affected |
|---|-------|--------|----------------|
| 4 | **Media Upload Failures** | Posts with missing/partial images | `sync_orchestrator.py` |
| 5 | **Language Tags** | Missing i18n metadata | `bluesky_client.py`, `mastodon_client.py` |

---

## Medium Priority (Enhancements)

| # | Issue | Impact | Files Affected |
|---|-------|--------|----------------|
| 6 | **Video Support** | Videos sync as text placeholders | `bluesky_client.py`, `content_processor.py` |
| 7 | **Quote Depth Limits** | Deep quote chains may break | `content_processor.py` |
| 8 | **Repost Configuration** | No user control over quote posts | `config.py`, `bluesky_client.py` |
| 9 | **Orphaned Media Blobs** | Deleted media not handled | `bluesky_client.py` |
| 10 | **Future: Polls** | Future-proofing for AT Protocol polls | `bluesky_client.py` |

---

## Low Priority (Nice to Have)

| # | Issue | Impact | Files Affected |
|---|-------|--------|----------------|
| 11 | **Rate Limit Tracking** | Basic delays only, no sophisticated backoff | `mastodon_client.py`, `sync_orchestrator.py` |
| 12 | **Idempotency Keys** | Network retries may duplicate posts | `mastodon_client.py` |
| 13 | **Facet Validation** | Malformed facets not validated | `content_processor.py` |
| 14 | **Thread Depth Limits** | No warning for very deep threads | `sync_orchestrator.py` |
| 15 | **Character Counting** | Simple len() vs Mastodon's URL counting | `content_processor.py` |

---

## Recent Bugs Fixed (Context)

These issues were already addressed in recent releases:

- **v0.6.0**: recordWithMedia image sync (quoted posts with images)
- **v0.5.0**: Nested reply detection in other users' threads
- **v0.3.0**: Image blob reference extraction
- **v0.2.0**: Duplicate link handling

---

## Implementation Phases

### Phase 1: Critical Fixes (Week 1-2)
- [ ] Fix multi-byte character handling in `_expand_urls_from_facets()`
- [ ] Add Mastodon instance character limit detection
- [ ] Implement content warning support for self-labels

### Phase 2: Important Enhancements (Week 3-4)
- [ ] Improve media upload failure handling
- [ ] Add language tag support
- [ ] Implement video embed detection

### Phase 3: Feature Completeness (Month 2)
- [ ] Add quote post depth limiting
- [ ] Handle orphaned media blobs
- [ ] Add repost/quote configuration options

### Phase 4: Polish & Future-Proofing (Month 3)
- [ ] Implement rate limit tracking
- [ ] Add idempotency keys
- [ ] Improve facet validation
- [ ] Refine character counting

---

## Testing Requirements

### Must Test Before Release

1. **Multi-byte characters**: Posts with emoji before/after URLs
2. **Content warnings**: Posts with porn/nudity/graphic-media labels  
3. **Instance limits**: Test on instances with >500 character limits
4. **Media failures**: Simulate blob download failures

### Recommended Integration Tests

1. Full sync with emoji-heavy Japanese/Chinese posts
2. NSFW content with proper CW tags
3. Complex quote chains (3+ levels deep)
4. Large batch sync (100+ posts)

---

## Quick Code Snippets

### Check for Multi-byte Issues
```python
# Test string with multi-byte chars
text = "🎉 Check out https://example.com..."
text_bytes = text.encode('utf-8')
print(f"Characters: {len(text)}, Bytes: {len(text_bytes)}")
# Output: Characters: 34, Bytes: 37 (emoji is 4 bytes!)
```

### Detect Self-Labels
```python
# In Bluesky post record:
if hasattr(post.record, 'labels') and post.record.labels:
    labels = [label.val for label in post.record.labels.values]
    print(f"Self-labels: {labels}")
    # Example: ['porn', 'nudity']
```

### Get Instance Character Limit
```python
# Query Mastodon instance info:
instance_info = mastodon_client.instance()
char_limit = instance_info['configuration']['statuses']['max_characters']
print(f"This instance allows {char_limit} characters")
```

---

## Monitoring Recommendations

### Key Metrics to Track

```python
{
    "sync_run_id": "2025-10-29T01:43:23",
    "posts_retrieved": 25,
    "posts_synced": 23,
    "posts_failed": 2,
    "failures": {
        "image_download": 1,
        "image_upload": 1,
        "content_too_long": 0,
        "rate_limit": 0
    },
    "content_warnings_applied": 3,
    "multi_byte_posts": 5,
    "truncated_posts": 1
}
```

### Alert Conditions

- Image failure rate > 10%
- Sync failure rate > 5%
- Rate limit hits per run > 0
- Content warnings missing for self-labeled posts

---

## Common Pitfall Scenarios

### Scenario 1: Emoji URL Misalignment
**Symptom**: Links appear broken or in wrong position  
**Cause**: Facet byte positions don't account for multi-byte chars  
**Fix**: Use byte-level string slicing, not character indexing

### Scenario 2: NSFW Content Without Warning
**Symptom**: Sensitive posts appear without CW on Mastodon  
**Cause**: Self-labels not extracted from AT Protocol  
**Fix**: Extract `post.record.labels.values` and map to Mastodon CW

### Scenario 3: Truncated Long Posts
**Symptom**: Posts truncated at 500 chars on 5000-char instances  
**Cause**: Hardcoded character limit  
**Fix**: Query instance config for actual limit

### Scenario 4: Missing Images After Deletion
**Symptom**: Posts sync without images, no error  
**Cause**: Blob 404s silently logged  
**Fix**: Pre-check blob availability, add retry logic

---

## Related Documentation

- [Full Edge Case Analysis](EDGE_CASE_ANALYSIS.md) - Comprehensive details and code examples
- [API Documentation](API.md) - Current API integration details
- [CHANGELOG](CHANGELOG.md) - History of bug fixes
- [Testing Guide](TESTING.md) - Test suite documentation

---

## Questions or Found New Edge Cases?

1. Check [EDGE_CASE_ANALYSIS.md](EDGE_CASE_ANALYSIS.md) for detailed coverage
2. Review [GitHub Issues](https://github.com/hossain-khan/social-sync/issues)
3. Check recent PRs for similar problems
4. Open a new issue with:
   - Description of the edge case
   - Impact assessment
   - Example scenario
   - Suggested fix (if known)

---

**Last Updated**: 2025-10-29  
**Document Version**: 1.0  
**Analysis Coverage**: 15 edge cases identified
