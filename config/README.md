# Configuration

`source_registry.json` is the reviewed, allowlisted source registry. It records
publisher, canonical official URL, source class, jurisdiction, dates, scope,
fetch mode, redistribution note, and bounded retrieval configuration for the
official eCFR and TikTok FAQ adapters.

Adding a URL to the registry will not make it trusted by itself. Only reviewed
official sources may be activated, adapter identity/completeness checks must
pass, and a fetch failure must remain visible. Registry sync alone never creates
a snapshot, candidate, review, mapping, finding, or external action.
