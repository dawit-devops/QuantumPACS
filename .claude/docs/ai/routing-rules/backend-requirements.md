# Routing Rules — Backend Requirements

## Context

Routing Rules page at `/routing`. Used by PACS Admins and Technologists to configure DICOM auto-routing. Rules have conditions (JSONB with eq/ne/contains/gt/gte/lt/lte/$or operators), priority, destination, enabled flag. Rules evaluated synchronously on C-STORE/STOW-RS receipt. All matching rules applied (not first-match-only).

## API Endpoints Required

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/routing/rules` | List all rules with priority ordering |
| GET | `/api/routing/rules/{id}` | Get single rule with full condition tree |
| POST | `/api/routing/rules` | Create new rule |
| PUT | `/api/routing/rules/{id}` | Update rule |
| DELETE | `/api/routing/rules/{id}` | Delete rule |
| POST | `/api/routing/rules/reorder` | Batch-update rule priorities |
| POST | `/api/routing/rules/{id}/test` | Test rule against a given study UID or mock DICOM tags |

## Data Model

```
RoutingRule {
  id: uuid
  name: string (unique, max 128 chars)
  description: string (max 512)
  priority: integer (lower = higher priority, unique enforced)
  destination: DestinationConfig
  conditions: ConditionNode  // JSONB — recursive tree structure
  enabled: boolean
  match_count: number        // how many times this rule has matched
  last_matched_at: datetime
  created_at: datetime
  updated_at: datetime
}

DestinationConfig {
  type: "dicom" | "s3" | "local"
  // for type: "dicom"
  ae_title: string
  host: string
  port: integer
  // for type: "s3"
  bucket: string
  prefix: string
  region: string
  // for type: "local"
  path: string
}

ConditionNode {
  type: "group" | "condition"
  // if type: "group"
  operator: "$and" | "$or"
  conditions: ConditionNode[]
  // if type: "condition"
  field: string    // DICOM tag path, e.g. "Modality", "PatientID", "StudyDescription"
  operator: "eq" | "ne" | "contains" | "gt" | "gte" | "lt" | "lte"
  value: string | number
}
```

### Available DICOM Fields for Condition Matching

| Field | Tag | Type | Example Values |
|-------|-----|------|----------------|
| Modality | (0008,0060) | string | CT, MR, XA, US, NM |
| PatientID | (0010,0020) | string | P12345 |
| PatientName | (0010,0010) | string | SMITH* |
| StudyDescription | (0008,1030) | string | "Chest PA" |
| StudyDate | (0008,0020) | date | 2024-01-15 |
| StudyTime | (0008,0030) | time | 143000 |
| AccessionNumber | (0008,0050) | string | ACC-12345 |
| ReferringPhysician | (0008,0090) | string | Dr. House |
| StationName | (0008,1010) | string | CT1 |
| InstitutionName | (0008,0080) | string | General Hospital |
| BodyPartExamined | (0018,0015) | string | CHEST, ABDOMEN |
| SeriesDescription | (0008,103E) | string | "Axial T2" |
| NumberOfSeries | (0020,1206) | integer | 3 |
| StudyInstanceUID | (0020,000D) | string | 1.2.3.4.5.6 |
| SeriesInstanceUID | (0020,000E) | string | 1.2.3.4.5.7 |

## UI Behavior Notes

### Rule List
- Table columns: name, description, destination (type + host/path), priority, enabled toggle, match count, last matched
- Sortable by priority (default ascending), enabled status
- "Enabled" column is a toggle switch that calls PUT to update the flag
- Priority shown as a number badge, click to edit inline

### Visual Condition Builder

**Condition Row** (atomic condition):
- Field dropdown: DICOM field selector (searchable)
- Operator dropdown: eq, ne, contains, gt, gte, lt, lte
- Value input: text input (type=number for numeric fields)
- Remove button (trash icon)

**Group Row** (AND/OR group):
- Contains nested condition rows or nested groups
- Group type toggle: AND / OR
- Collapsible — shows abbreviated preview "(2 conditions)"
- Add condition button
- Add group button

**Root level**: top-level AND group (can be changed to OR)

### Priority Ordering

- Priority is an integer; lower number = higher priority
- New rules get `max_priority + 10` by default
- Manual priority edit: click priority badge → inline number input
- Drag-to-reorder: drag handle on each row → batch POST on drop
- Priority uniqueness enforced by backend; insert shifts existing priorities up

### Testing Rules

- "Test Rule" button on each rule row opens a modal
- Option A: Enter StudyInstanceUID to fetch actual DICOM tags and evaluate
- Option B: Manually enter test tag values (all fields shown as input)
- Result: highlights whether rule matches + shows which conditions passed/failed
- Also available: "Test All Rules" to see which rules would match a given study

### Rule Evaluation Behavior

- All matching rules are applied (not first-match-only)
- Rules evaluated in priority order
- Each rule that matches queues a routing job for its destination
- If destination is unreachable, the job is retried (configurable, default 3 retries) and logged; rule remains enabled
- No cascade stop — failed destinations don't block other rules

### Visibility by Role

- **Admin**: full CRUD
- **Technologist**: read-only visibility (cannot create/edit/delete)
- **Other roles**: no access (route hidden, 403 on API)

## Uncertainties

- [ ] What happens if two rules have the same priority?
- [ ] Can a rule destination be a local path, S3 bucket, or both?
- [ ] What happens when a rule matches but the destination is unreachable?
- [ ] Is there a limit on number of conditions per rule?

## Questions for Backend

- What DICOM fields are available for condition matching?
- Is the condition logic AND-only or does it support OR groups?
- Should I expect the test-rule endpoint to return which rules matched or just yes/no?
- What visibility do non-admin users have into routing rules (read-only, no access)?
- Can I reorder rules or is priority purely numeric?
