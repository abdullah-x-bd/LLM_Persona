# CAMS 2022-23 data audit

Source: MoSPI/NSSO Comprehensive Annual Modular Survey (CAMS), NSS 79th Round, 2022-23.

## Files verified

- `NSS79CAMS_Member.csv`: 1,299,988 person records, 57 variables
- `NSS79CAMS_Household.csv`: 302,086 household records, 85 variables
- `NSS79CAMS_Course.csv`: 1,646,813 course records

## Household-person merge

Households are uniquely identified by:

`ST, NSS, DIST, STRM, SSTRM, SR, SRO, FC, FSU, SSS, SSU`

The household key is unique in the household file. The member file contains exactly 302,086 distinct household keys, and all 302,086 match the household file.

## Eligible analysis population

For the initial digital-inclusion experiment, the intended analysis population is persons aged 15 years and above.

- Unweighted member count, age 15+: 970,934

## Sanity check against published CAMS estimates

Using the posted `MULT` survey multiplier and structurally treating skipped digital-skill items as negative outcomes where the questionnaire skip logic implies inability/non-use:

- Used internet at least once during the previous 3 months: 57.54%
- Used copy-and-paste tools / skill indicator: 46.07%

These reproduce the published all-India CAMS figures of approximately 57.5% recent internet use and 46.1% copy-and-paste skill for persons aged 15+.

## Candidate held-out outcomes

- `BL32C6`: ability to use desktop/laptop/tablet/palmtop/notebook
- `BL32C7`: ability to use internet, collapsed to able vs unable for the main binary benchmark
- `BL32C8`: internet use at least once during the previous 3 months
- `BL32C9`: ability to send or receive email
- `BL32C10`: ability to perform banking transactions such as digital payments using a digital device
- `BL33C3`: copy-and-paste ICT skill

All target outcomes must be withheld from persona construction.

## Candidate persona covariates

Person-level candidates:

- age
- gender
- marital status
- formal education/enrolment status
- recent economic activity
- relationship to household head, if useful

Household-level candidates:

- rural/urban sector
- state
- household size
- religion
- social group
- household language, if useful
- monthly household consumer expenditure / per-capita expenditure

Digital ownership, access, and digital-behaviour variables must not be included in the persona because they would leak information about the held-out outcomes.

## Next steps

1. Freeze the thin and rich persona specifications.
2. Freeze the six held-out outcomes and recoding rules.
3. Draw the reproducible matched-person sample.
4. Generate model request files without target leakage.
5. Run the same sample through the selected OpenRouter models.
6. Compare weighted synthetic estimates against held-out NSO outcomes at aggregate and subgroup levels.
