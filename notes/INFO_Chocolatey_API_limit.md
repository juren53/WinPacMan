# Chocolatey API 10,000 Package Limitation

**Date:** 2025-12-30
**Status:** Known Limitation
**Impact:** Missing ~1,000 packages (~10% of repository)

## Summary

The Chocolatey Community Repository OData v2 API has a hard-coded pagination limit of 10,000 packages. This prevents WinPacMan from fetching the complete package catalog, which currently contains approximately 11,000 unique packages.

## Investigation Results

### Current Database State

Query of local metadata cache revealed:

```
Package counts by provider (available packages):
  chocolatey: 10,000
  scoop: 1,412
  winget: 10,777
  unknown: 4

Total available packages: 22,193
Total installed packages: 134
```

The exactly 10,000 Chocolatey packages raised suspicion of an artificial limit.

### API Testing

#### 1. Count Endpoint Test
```bash
GET https://community.chocolatey.org/api/v2/Packages/$count?$filter=IsLatestVersion eq true
Response: 10000
```
**Result:** API returns exactly 10,000 (capped, not actual count)

#### 2. Pagination Beyond 10,000 Test
```bash
GET https://community.chocolatey.org/api/v2/Packages?$skip=10000&$top=100&$filter=IsLatestVersion eq true
Response: 406 Client Error: Not Acceptable
```
**Result:** API explicitly rejects requests beyond skip=10,000

### Actual Package Count

According to official Chocolatey sources (August 2025):
- **Unique packages:** ~11,000 packages
- **Total packages (all versions):** 264,000 packages
- **Growth:** Up from 10,400 packages in May 2024

**Sources:**
- [Chocolatey Community Repository](https://community.chocolatey.org/)
- [API Querying Documentation](https://docs.chocolatey.org/en-us/community-repository/api/)
- [Repository Optimizations Blog (Sept 2025)](https://blog.chocolatey.org/2025/09/chocolatey-repository-optimizations/)

### Code Implementation

The limit is documented in our code at:
**File:** `metadata/sync/chocolatey_odata_fetcher.py`

```python
# Line 30
MAX_PACKAGES = 10000  # Chocolatey API limit

# Line 76
while total_fetched < self.MAX_PACKAGES:
    # Fetching loop stops at 10,000
```

This is a **legitimate API limitation**, not an arbitrary code limit.

## Impact Assessment

### What We're Missing
- **Missing packages:** ~1,000 packages (approximately 10%)
- **Affected users:** Users searching for packages not in the first 10,000
- **Ordering:** Packages are fetched ordered by `Id` (alphabetical), so later alphabetically-ordered packages are missing

### User Experience Impact
- Cache Summary shows "10,000" for Chocolatey (accurate for what we can fetch)
- Some Chocolatey packages won't appear in search results
- Users may not find less popular packages in WinPacMan

## Potential Workarounds

### Option 1: Accept the Limitation (Recommended for now)
- **Effort:** Low
- **Action:** Document limitation in UI and user documentation
- **Pros:** No code changes needed, honest about API limits
- **Cons:** Users miss 10% of packages

### Option 2: Multiple Filter Strategies
- **Effort:** Medium
- **Action:** Use different `$filter` criteria to fetch different package sets
- **Example approaches:**
  - Filter by download count ranges
  - Filter by creation date ranges
  - Filter by tags
  - Fetch in multiple passes with different sorting
- **Pros:** Could potentially get more packages
- **Cons:** Complex, may still miss packages, slower refresh

### Option 3: Alternative Data Sources
- **Effort:** High
- **Action:** Scrape Chocolatey website HTML or use unofficial APIs
- **Pros:** Could get complete package list
- **Cons:** Fragile, slower, may violate ToS, maintenance burden

### Option 4: Hybrid Approach
- **Effort:** Medium-High
- **Action:** Use OData API for bulk fetch, supplement with targeted queries for specific packages
- **Pros:** Best of both worlds
- **Cons:** Complex implementation

### Option 5: Request API Enhancement from Chocolatey
- **Effort:** Low (one-time)
- **Action:** File feature request with Chocolatey for higher pagination limits or alternative endpoints
- **Pros:** Official solution, benefits all consumers
- **Cons:** No guarantee of implementation, may take time

## Recommendation

**Short Term (Immediate):**
1. Document the limitation in Cache Summary dialog
2. Add tooltip explaining "Chocolatey: 10,000 (API limit - ~1,000 additional packages exist)"
3. Update help documentation

**Long Term (Future Enhancement):**
1. Investigate Option 2 (Multiple Filter Strategies) for v0.6.x
2. Consider Option 5 (Request API Enhancement) - file issue with Chocolatey team

## Technical Notes

### API Endpoint Details
```
Base URL: https://community.chocolatey.org/api/v2
Packages Endpoint: /Packages
Protocol: NuGet v2 OData

Current Query:
  $filter: IsLatestVersion eq true
  $orderby: Id
  $skip: 0-9999 (works), 10000+ (fails with 406)
  $top: 100 (ignored by API, returns ~40 per page)
```

### Error Response
```
Status: 406 Not Acceptable
Body: (empty)
```

### Related Files
- `metadata/sync/chocolatey_odata_fetcher.py` - Fetcher implementation
- `metadata/providers/chocolatey_provider.py` - Provider wrapper
- `metadata/metadata_cache.py` - Cache management

## Action Items

- [ ] Add limitation note to Cache Summary dialog
- [ ] Update user documentation with known limitations section
- [ ] Consider filing feature request with Chocolatey
- [ ] Investigate multi-filter approach for v0.6.x

## References

### Official Documentation
- [Chocolatey API Documentation](https://docs.chocolatey.org/en-us/community-repository/api/)
- [NuGet v2 OData Protocol](https://www.nuget.org/api/v2/)

### Blog Posts
- [Four Billion Installs (Aug 2025)](https://blog.chocolatey.org/2025/08/four-billion-installs/)
- [Repository Optimizations (Sept 2025)](https://blog.chocolatey.org/2025/09/chocolatey-repository-optimizations/)
- [Three Billion Installs (May 2024)](https://blog.chocolatey.org/2024/05/three-billion-installs/)

### Community
- [Chocolatey Community Repository Homepage](https://community.chocolatey.org/)
- [Chocolatey Software Docs](https://docs.chocolatey.org/)

---

**Last Updated:** 2025-12-30
**Verified Against:** Chocolatey API v2 (community.chocolatey.org)
**Next Review:** After Chocolatey API updates or when implementing workaround
