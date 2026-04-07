# BOQ AUTO Taxonomy Strategy

## Why this matters

The current BOQ AUTO knowledge model is still too flat for the types of projects and work packages already visible in the repo.

Today, the normalized schema in `src/cost_schema.py` stores:

- `category`
- `subcategory`
- `material`
- `keywords`

That is useful, but it is not yet a real construction taxonomy.

The result is that matching still depends too heavily on text similarity against a sparse rate library, instead of first understanding what kind of work item the row belongs to.

## What the repo evidence shows

### Existing BOQ structure is already domain-rich

From `boq/demo_boq.xlsx`:

- `Preliminaries`
- `Dayworks Plant`
- `Earthworks`
- `Concrete Works`
- `Finishes`

The dayworks and earthworks sheets already contain specialist plant/equipment such as:

- tipper lorry
- dewatering pump
- compressor with drill
- concrete vibrator
- sheep foot roller
- excavator with loader attachment
- water tanker
- crawler dozer

From `workspace/jobs/parsing_test_eb1f8522/inputs/boq__kaa_boq_filled_v2.xlsx`:

- `BoQ 1; Preliminaries`
- `BoQ 4; Site Clearance`
- `BoQ 5; Earthworks`
- `BoQ 7; Excavation`
- `BoQ 10&20; Gravel & RDfurniture`
- `BoQ 23; Elevated Approach Light`
- `BoQ 22; Dayworks`
- `Engineers office`
- `Engineers lab equipment`
- `Survey Equipment`
- `Equipment for Engineers Staff H`

This is strong evidence that the platform should understand distinct project and work families such as:

- preliminaries
- site clearance
- earthworks
- excavation
- roads / road furniture
- electrical / airfield lighting
- plant and dayworks
- office / accommodation
- laboratory equipment
- survey equipment

### Existing rate library is much narrower

Sampling `database/qs_database.xlsx` shows the top sections are currently:

- `Earthworks`
- `Dayworks`
- `Concrete`
- `Preliminaries`
- `Finishes`

The top subsections are mostly:

- `Plant`
- `Transport`
- `General`
- `Excavation`
- `In-situ`
- `Wall Finishes`

And targeted searches found examples for:

- `roller`
- `grader`
- `excavator`
- `tipper`

But found no examples for:

- `pipe`
- `manhole`
- `laboratory`
- `survey`
- `furniture`

This is the strongest current argument for a taxonomy-first improvement path: the project inputs already span more domains than the current priced library.

## External reference points

This direction is consistent with established construction classification systems:

- CSI MasterFormat separates procurement/general requirements, concrete, plumbing, electrical, earthwork, utilities, transportation, water/wastewater equipment, and more.
- NBS Uniclass is explicitly designed as a unified classification structure across disciplines and scales, including infrastructure and products, to support interoperability.
- WBDG notes that UniFormat/elemental classification is often more useful earlier in design, while CSI-format breakdowns are often used at final bid/document stage.

Useful references:

- CSI MasterFormat Numbers and Titles: https://crmservice.csinet.org/widgets/masterformat/numbersandtitles.aspx?id=cbd8f49d-bed5-ea11-80f3-000d3a04ff75
- NBS Uniclass overview / launch note: https://www.thenbs.com/about-nbs/press-releases/nbs-launches-new-uniclass-tool-to-support-adoption
- WBDG note on UniFormat vs CSI in WBS/cost structure: https://www.wbdg.org/resources/earned-value-analysis

## Recommended design direction

## Principle

BOQ AUTO should separate:

- canonical construction knowledge
- aliases and synonyms
- price observations
- reviewer decisions

Prices should not be the only thing defining the structure.

## Suggested knowledge layers

### 1. Domain

Top-level project/work domains such as:

- preliminaries
- structures
- roads
- drainage and utilities
- water and fluid systems
- electrical and lighting
- finishes
- external works
- plant and transport
- survey and setting out
- laboratory and testing
- accommodation / furnishings / temporary facilities

### 2. Work family

Mid-level families inside a domain, for example:

- earthworks
- excavation
- fill and compaction
- concrete
- reinforcement
- formwork
- pavements
- bituminous works
- road furniture
- pipework
- manholes and chambers
- drainage structures
- airfield lighting
- testing services
- site offices
- temporary utilities

### 3. Category / equipment class

A tighter operational grouping such as:

- excavators
- tippers
- graders
- rollers
- compactors
- pumps
- mixers
- lighting poles
- survey instruments
- lab benches
- office furniture

For non-equipment items, this would be a comparable grouping such as:

- strip footings
- blinding concrete
- kerbs
- culverts
- HDPE pipes
- manholes

### 4. Canonical item

This is the actual BOQ AUTO "truth" object that aliases and prices point to.

Examples:

- `Excavator with loader attachment 1.7 m3`
- `Pneumatic tyre roller`
- `HDPE pipe 110 mm`
- `Precast concrete kerb`
- `Total station`
- `Engineer's office container`

### 5. Observations and commercial data

Separate, attachable observations:

- region
- project type
- source
- date/effective period
- unit
- observed rate
- approval state
- reviewer confidence

This lets BOQ AUTO know what an item is even before it has many prices.

## Fit with the current architecture

This should extend the current architecture, not replace it.

### Keep

- `RateLibrary`
- `Aliases`
- candidate review / promotion flow
- `match_feedback`
- matcher and workbook output patterns

### Add underneath

- a canonical taxonomy table set
- canonical items that current rate rows map into
- richer category compatibility based on taxonomy instead of only string hints

### Keep Excel compatibility

The existing Excel export/import path should still work.

`section` and `subsection` can remain as compatibility columns, but should eventually be derived from richer canonical fields such as:

- `domain`
- `work_family`
- `category`
- `subcategory`

## Proposed schema evolution

### New conceptual entities

- `taxonomy_domains`
- `taxonomy_families`
- `taxonomy_categories`
- `canonical_items`
- `canonical_item_aliases`
- `rate_observations`
- `context_tags`

### Practical field additions to current item structure

If BOQ AUTO wants a lighter migration path first, add these fields before introducing many new tables:

- `domain`
- `work_family`
- `category`
- `subcategory`
- `item_kind`
  - values such as `work_item`, `equipment`, `material`, `service`, `fixture`, `temporary_facility`
- `project_context`
  - values such as `roads`, `structures`, `water`, `airfield`, `building`, `utilities`
- `unit_family`
- `is_priced`
- `canonical_group_id`

This can coexist with the current `section`, `subsection`, `material`, and `keywords` fields.

## Immediate high-value taxonomy groups to design first

These are the best initial groups because they are already visible in BOQs or already known weak spots:

- preliminaries and temporary facilities
- plant and transport
- earthworks and excavation
- compaction and pavement support plant
- structures / concrete / reinforcement / formwork
- roads / bituminous works / road furniture
- drainage / pipes / manholes / utilities
- survey equipment and setting-out services
- laboratory and testing equipment/services
- electrical support / lighting / poles / control equipment
- engineer accommodation / office / furniture

## Recommendation

Yes, BOQ AUTO should move toward a taxonomy-first database design.

The best path is not:

- wait until all prices are available

The best path is:

1. design the canonical taxonomy now
2. map current database rows into it
3. route matching and review through it
4. attach prices progressively over time

That will improve:

- matching precision
- reviewer clarity
- learning-loop quality
- ingestion consistency
- long-term maintainability

## Suggested next implementation step

The next architecture step should be:

1. define the first canonical taxonomy for BOQ AUTO
2. add compatible schema fields or tables in `src/cost_schema.py`
3. backfill the current small rate library into the new structure
4. update matcher hints to use taxonomy values
5. let reviewer-approved tasks eventually promote into canonical items or aliases, not only flat rate rows
