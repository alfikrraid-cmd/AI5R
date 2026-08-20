import { getPumpKnowledge } from "../../../api/ai5rClient";

// MWO-LTSA-032A-R1 -- KnowledgeWorkspaceController: owns fetch, refresh,
// retry, and cache for the Knowledge Workspace, per the mission's
// architecture (KnowledgeWorkspace -> useKnowledgeWorkspace() ->
// KnowledgeWorkspaceController -> GET /api/ltsa/pumps/{tag}/knowledge).
//
// Scope note: this controller returns the RAW `data` payload from the
// Knowledge API response, not a mapped EquipmentKnowledge object. Field-
// mapping (mapEquipment, mapTimeline, mapRecommendations, etc.) stays in
// useKnowledgeWorkspace.js, unmoved -- repository archaeology for this
// MWO found that file's Recommendation-mapping logic is an actively
// in-progress edit by MWO-LTSA-032B (a different, concurrently-running
// mission this MWO is explicitly required not to touch: "DO NOT change
// Recommendation API... Leave Recommendation integration for the
// follow-up merge"). Keeping all field-mapping together in one place,
// untouched, is the only way to honor that boundary while still
// extracting fetch/cache/refresh/retry into this controller, exactly as
// this mission's architecture diagram requires.

// A tag's entry is only cached after a successful fetch -- a failed
// load() is never cached, so calling load() again after an error
// naturally re-fetches (retry semantics) without needing a separate
// "force" flag. invalidate(tag) drops a tag's cached entry so the next
// load(tag) re-fetches (refresh semantics).
export function createKnowledgeWorkspaceController({ fetchKnowledge = getPumpKnowledge } = {}) {
  const cache = new Map();

  async function load(tag) {
    if (cache.has(tag)) {
      return cache.get(tag);
    }

    const response = await fetchKnowledge(tag);
    cache.set(tag, response.data);
    return response.data;
  }

  function invalidate(tag) {
    cache.delete(tag);
  }

  return { load, invalidate };
}
