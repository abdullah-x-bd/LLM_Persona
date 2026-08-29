# Data

Raw NSO CAMS microdata should be stored locally under `data/raw/` and must not be committed to this repository.

Recommended local layout:

```text
data/
├── raw/                 # Original downloaded NSO files, ignored by git
├── interim/             # Local merged and respondent-level working files
└── processed/           # Reproducible derived data safe for version control, if permitted
```

Before committing any derived file, verify that it contains no restricted or respondent-level information and that redistribution is permitted under the source terms.
