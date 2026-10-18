# FIELDWORK — DESIGN SYSTEM & FRONTEND VISUAL CONTRACT
Version: 1.0
Status: Authoritative
Audience: frontend engineers, product designers
Product: Fieldwork — evidence layer for second-hand commerce

> IMPORTANT
> This file is the visual and interaction source of truth for Fieldwork.
> Do not invent a new visual language, color, radius, typography treatment, animation style, card style, AI treatment, or evidence state when implementing a screen.
> Reuse the tokens, components, patterns, and rules in this document.
> When the product brief and this file conflict on visual decisions, use this file for visual execution and the product brief for product behavior.

---

# 0. PRODUCT CONTEXT

Fieldwork is not a marketplace and not a generic AI assistant. It is an embedded trust/evidence layer for second-hand transactions.

Core promise:
"Show what the evidence says, what it does not establish, and what to do next."

Core product moments:
1. List in seconds
2. Capture evidence as you go
3. Ask the item
4. Agree a price
5. 20-second handover check
6. Problem → human-reviewed case

Primary emotional target:
CALM PROOF

The interface should feel:
- precise
- calm
- human
- premium
- practical
- globally credible
- quick
- transparent

The interface must NOT feel:
- cyber-security software
- insurance portal
- bank dashboard
- generic AI startup
- futuristic "AI magic"
- childish marketplace
- legal/compliance software
- template-generated SaaS

---

# 1. VISUAL THESIS

## 1.1 Direction

LOCKED DIRECTION:
MINERAL + EDITORIAL + INSTRUMENT

The visual metaphor is:

premium editorial information design
+
precision inspection instrument
+
modern mobile commerce

Think:
- field notes
- annotated evidence
- camera framing
- measurement marks
- photographic proof
- transaction records
- quiet confidence

Do NOT make the visual metaphor literal or decorative.

Use:
- crop corners
- small registration marks
- fine dividers
- evidence labels
- restrained metadata
- photo annotations
- timelines
- precise numeric treatment
- subtle geometry

Do NOT use:
- giant shields
- lock graphics
- generic checkmarks as the primary brand idea
- AI sparkles
- glowing orbs
- neon gradients
- blue/purple "AI" gradients
- excessive glassmorphism
- excessive 3D
- decorative dashboard charts

## 1.2 Design principle

SHOW, DON'T TELL.

Whenever possible:
photo > paragraph
specific fact > adjective
source > claim
observable result > confidence score
next action > vague warning

Example:
BAD:
"Excellent condition"

GOOD:
"Screen: no crack visible in 5 angles"

BAD:
"Verified"

GOOD:
"4 of 5 claims shown in photos"

BAD:
"AI decided"

GOOD:
"Recommended by AI · rule 4.2 · person confirms"

---

# 2. SYSTEM ARCHITECTURE

Use four token layers:

Primitive tokens
    ↓
Semantic tokens
    ↓
Component tokens
    ↓
Host-theme overrides

Never style components directly with random values if a token exists.

Never introduce:
- arbitrary hex colors
- arbitrary spacing
- arbitrary border radii
- arbitrary shadows
- arbitrary font sizes

If a new value genuinely needs to exist:
1. determine whether an existing token can be reused;
2. if not, add a named token at the correct layer;
3. document why.

---

# 3. TECHNOLOGY / COMPONENT STRATEGY

## 3.1 Preferred implementation model

Prefer:
- React / Next.js
- TypeScript
- CSS variables for tokens
- Tailwind utilities backed by CSS variables OR CSS modules
- shadcn/ui-style open-code components where useful
- Radix primitives for complex accessible interaction behavior
- Lucide or an equivalent consistent SVG icon set

The important rule:

SHADCN/RADIX ARE IMPLEMENTATION PRIMITIVES, NOT THE FIELDWORK VISUAL IDENTITY.

Do not retain default shadcn colors, radii, shadows, typography, or visual density when they conflict with this system.

Use the actual component source, customize it, and keep Fieldwork's tokens as the visual source of truth.

## 3.2 Component philosophy

Components should be:
- composable
- deterministic
- accessible
- state-complete
- responsive
- easy for an LLM to reason about

A component should expose variants through named props or data attributes, not through one-off class combinations.

Example:
<Button variant="primary" size="lg" state="default" />

NOT:
<Button className="bg-[#245a53] rounded-[13px] ..." />

---

# 4. BRAND COLORS

## 4.1 Brand palette

The brand palette is deliberately restrained.

### Core

Deep Forest
#123A34
Role:
- primary dark
- brand depth
- hero surfaces
- selected navigation
- large emphasis areas

Mineral
#2F6C63
Role:
- primary brand action
- links
- focused interactions
- brand accent

Mineral Dark
#24574F
Role:
- hover
- pressed
- dark variants

Sage Mist
#82978F
Role:
- secondary visual accent
- subtle illustration
- disabled-adjacent visual support
- photography overlay

Oxide Copper
#B6784D
Role:
- editorial accent
- tiny visual markers
- selected metadata accents
- special emphasis
NEVER use this as the "Differs" semantic state.

Warm Stone
#C9C1B4
Role:
- dividers
- borders
- inactive geometry

Parchment
#F3EFE6
Role:
- page background
- warm canvas

Paper
#FAF8F3
Role:
- cards
- sheets
- content surfaces

Ink
#171C19
Role:
- primary text
- strongest headings

Graphite
#4E5853
Role:
- secondary text
- metadata
- supporting labels

Muted
#737B76
Role:
- quiet supporting text

White
#FFFFFF
Role:
- only for contrast-heavy areas and controls when genuinely required

## 4.2 Color usage ratio

Default visual balance:
- 65–75% warm neutrals
- 15–20% dark ink / graphite
- 5–10% mineral brand color
- <3% oxide/editorial accent
- semantic colors only where semantic state exists

The interface must NOT become a sea of green.

Most screens should feel neutral first, branded second.

## 4.3 Semantic colors — FIXED ACROSS HOST PLATFORMS

These colors are never replaced by the host marketplace theme.

MATCHES / SHOWN
Foreground: #28644F
Background: #E4EEE8
Border: #BFD7CA
Icon fill: #28644F

NOT SHOWN
Foreground: #646863
Background: #ECEBE6
Border: #D6D4CD
Icon fill: #646863

DIFFERS
Foreground: #A65342
Background: #F4E4DE
Border: #E2BEB4
Icon fill: #A65342

CAN'T TELL
Foreground: #8A6A2E
Background: #F1E9D5
Border: #DCC990
Icon fill: #8A6A2E

SYSTEM ERROR
Foreground: #5E5A96
Background: #ECEAF7
Border: #CDC9E7
Icon fill: #5E5A96

MONEY
Foreground: #2D5B88
Background: #E7EEF6
Border: #C5D5E7
Icon fill: #2D5B88

Rules:
- Never communicate semantic meaning with color alone.
- Always pair semantic color with text and/or icon.
- Never use red panic treatment for ordinary differences.
- Never use brand green to mean "truth" in general.
- Semantic colors must remain muted and editorial, not neon.
- Never use semantic colors as large decorative gradients.

---

# 5. TYPOGRAPHY

## 5.1 Typeface strategy

PRIMARY UI FAMILY:
IBM Plex Sans

DISPLAY / EDITORIAL FAMILY:
IBM Plex Serif

TECHNICAL / EVIDENCE METADATA:
IBM Plex Mono

DEVANAGARI:
IBM Plex Sans Devanagari

JAPANESE:
IBM Plex Sans JP

KOREAN:
IBM Plex Sans KR

This combination gives the system a more editorial character without sacrificing UI clarity.

Display rule:
Use IBM Plex Serif for short Latin headlines and high-value statements.
Use IBM Plex Sans for controls, navigation, body text, data, and operational UI.
For Devanagari, Japanese, and Korean, use the corresponding IBM Plex Sans script face rather than forcing a serif.

Never use:
- Inter as a default fallback if a Plex face is available
- Poppins
- Montserrat
- generic geometric sans
- decorative display fonts
- handwritten fonts

Fallback stack:
"IBM Plex Sans", "IBM Plex Sans Devanagari", system-ui, -apple-system, "Segoe UI", sans-serif

## 5.2 Type scale

Display XL
56 / 64
Plex Serif 500
Use only for brand/hero moments on large surfaces.

Display L
44 / 52
Plex Serif 500

Display M
36 / 44
Plex Serif 500

Heading XL
32 / 40
Plex Sans 600

Heading L
28 / 36
Plex Sans 600

Heading M
24 / 32
Plex Sans 600

Heading S
20 / 28
Plex Sans 600

Body L
18 / 28
Plex Sans 400

Body
16 / 24
Plex Sans 400

Body S
14 / 20
Plex Sans 400

Label
13 / 18
Plex Sans 500

Meta
12 / 16
Plex Mono 400

Caption
12 / 16
Plex Sans 400

Button
15 / 20
Plex Sans 600

Numeric XL
40 / 44
Plex Sans 600

Numeric L
32 / 36
Plex Sans 600

Numeric M
24 / 28
Plex Sans 600

## 5.3 Typography behavior

Headings should generally be shorter than conventional SaaS headings.

Prefer:
"Check your item."

Not:
"Let's make sure your item is in good condition before completing the transaction."

Use sentence case.

Avoid all-caps except:
- tiny overlines
- section markers
- technical labels
- evidence metadata

Overlines:
11–12px
500
letter-spacing: 0.08em
uppercase

Do not use:
font-weight 800/900
unless specifically justified for a massive display lockup.

## 5.4 Numbers

Numbers are part of the trust system.

Use tabular numerals for:
- price
- battery
- counts
- timestamps
- evidence coverage

Examples:
₹13,200
87%
4 / 5
20 sec

Money values should always be visually stable and easy to compare.

---

# 6. SPACING

Base grid: 4px
Primary rhythm: 8px

Allowed scale:
4
8
12
16
20
24
32
40
48
64
80
96

Default mobile side inset:
16px

Large mobile section gap:
32px

Default desktop content inset:
24–32px

Never use arbitrary values such as:
13px, 17px, 21px, 27px unless required by a measured asset or typography constraint.

---

# 7. RADIUS / SHAPE LANGUAGE

Fieldwork should feel engineered, not bubbly.

4px
micro geometry

8px
controls, fields, compact elements

12px
standard cards, list items, containers

16px
feature cards, media, prominent surfaces

20px
bottom sheets / major overlays

24px
rare hero/feature surfaces only

32px+
NEVER by default.

Rules:
- Pills are reserved for statuses, tags, and compact categorical metadata.
- Primary buttons should NOT be pill-shaped.
- Cards should not all have the same radius.
- No "everything is rounded" aesthetic.
- Corners should feel precise.

---

# 8. BORDERS

Default:
1px solid rgba(23, 28, 25, 0.10)

Strong:
1px solid rgba(23, 28, 25, 0.16)

Subtle:
1px solid rgba(23, 28, 25, 0.06)

Semantic borders come from the semantic token layer.

Avoid:
- thick black outlines
- double borders
- decorative borders everywhere
- gradient borders

---

# 9. ELEVATION

Do not use large floating shadows.

Level 0:
none

Level 1:
0 1px 2px rgba(20, 32, 28, 0.06),
0 4px 14px rgba(20, 32, 28, 0.05)

Level 2:
0 6px 20px rgba(20, 32, 28, 0.08)

Level 3:
0 14px 40px rgba(20, 32, 28, 0.10)

Use elevation mainly for:
- sheets
- menus
- dialogs
- important floating controls

Cards should usually rely on:
surface contrast + border
rather than heavy shadow.

---

# 10. SURFACE SYSTEM

Canvas:
Parchment #F3EFE6

Base surface:
Paper #FAF8F3

Inset surface:
#ECE9E0

Strong dark surface:
Deep Forest #123A34

Ghost surface:
rgba(255,255,255,0.55)

Rules:
- Avoid pure white everywhere.
- Do not make every section a card.
- Use whitespace as a structural tool.
- Prefer one strong surface hierarchy over many floating containers.

Surface vocabulary:
1. Canvas
2. Surface
3. Raised
4. Inset
5. Overlay
6. Dark feature surface

---

# 11. ICONOGRAPHY

Preferred:
Lucide-style outline icons or a similarly consistent custom SVG set.

Geometry:
- 2px apparent stroke
- round caps
- round joins
- simple silhouette
- no gradients
- no filled emoji
- no mixed icon families

Default:
20px

Compact:
16px

Large:
24px

Marketing/hero:
32px maximum unless the icon is specifically a visual illustration.

Important:
Do not use icon + text where text alone is clearer.

Evidence icons:
Use symbolic shapes:
- circle-check
- circle-minus / neutral marker
- directional difference marker
- question / uncertainty
- warning triangle only for true system warnings
- human-review icon

Do not use a shield for evidence.

---

# 12. FIELDWORK GRAPHIC LANGUAGE

The visual system uses subtle "inspection geometry."

Approved motifs:
- corner crop marks
- registration ticks
- small locator dots
- thin measurement lines
- evidence brackets
- timestamp rails
- annotation leaders
- evidence index numbers
- small monospaced labels

Example:
[01] BACK EDGE
Shown in photo 4

Graphic motifs must support content.

Never use them as decoration with no informational role.

Accent geometry should usually be:
1px
low contrast
warm graphite / stone / mineral

---

# 13. PHOTOGRAPHY

Photography is one of Fieldwork's primary brand assets.

Use:
- real item photography
- genuine device surfaces
- close inspection details
- natural environments
- slightly imperfect but controlled framing
- real wear and texture
- warm natural light

Avoid:
- stock-photo hands
- staged "happy buyer/seller" scenes
- glossy fake device renders
- overprocessed HDR
- generic AI-generated product photography
- artificial holographic overlays

Evidence photos must never be replaced by illustrations.

AI-generated images may appear only as explicitly labelled illustration or conceptual marketing art.

---

# 14. LOGO / MARK

Brand concept:
A simple modular "F" derived from:
- field marker
- folded evidence sheet
- inspection frame

Logo requirements:
- recognizable at 16px
- works on Paper and Deep Forest
- works monochrome
- can become a small evidence badge
- no shield
- no magnifying glass
- no camera lens as the literal mark
- no generic AI sparkle

Wordmark:
Fieldwork

Wordmark should use IBM Plex Sans Semibold or approved custom lockup.

App icon:
symbol only

Evidence badge:
symbol + "Evidence" or compact mark depending on host constraints.

The badge communicates:
"guided evidence captured"
NOT:
"seller is trustworthy"
NOT:
"item is certified"
NOT:
"item is guaranteed"

---

# 15. WHITE-LABEL / HOST BRANDING

Fieldwork can be embedded inside other marketplaces.

Separate:
A. Fieldwork structural design language
B. Host brand accent

Host may replace:
- primary action color
- host-selected navigation
- host-brand accents

Host may NOT replace:
- semantic evidence states
- typography hierarchy rules
- accessibility requirements
- evidence vocabulary
- AI/human distinction
- interaction rules

Fieldwork should still be recognizable through:
- evidence geometry
- claim rows
- evidence badge
- evidence timeline
- inspection capture behavior
- state vocabulary
- calm editorial treatment

---

# 16. BUTTON SYSTEM

## Primary

Purpose:
main next action

Style:
- solid Deep Forest / Mineral
- 48px minimum height on mobile
- 8px radius
- clear text
- optional trailing arrow

Example:
Continue →
Complete handover
Make offer

Do not use:
pill radius
gradient
glow
large icon before every label

## Secondary

Purpose:
supporting action

Style:
- transparent / Paper surface
- 1px border
- Ink text

## Tertiary

Purpose:
low emphasis

Style:
- text only
- no container

## Destructive

Only actual destructive actions:
- delete
- cancel transaction where money is at stake
- revoke

Do not make "Differs" actions visually destructive by default.

---

# 17. INPUTS

Height:
48px mobile
44px compact

Radius:
8px

Border:
1px

Focus:
2px visible outer focus ring using Mineral with sufficient contrast.

Placeholder:
Muted
Never use placeholder as the label.

Error:
Use text + icon + border + recovery instruction.

Avoid:
giant rounded fields
floating-label gimmicks
heavy shadows
neumorphism

---

# 18. CHIPS / TAGS

Chips are for:
- categories
- item attributes
- quick answers
- compact filters

Quick-answer chips:
"Used 1 year"
"Never repaired"
"Box + bill"
"Not sure"

Selected:
Mineral tinted surface + strong text

Unselected:
Paper/Inset surface

Status tags:
Use semantic colors.

Do not use chips for primary CTA.

---

# 19. EVIDENCE COMPONENT SYSTEM

This is the most important Fieldwork-specific component family.

## 19.1 Claim row

Anatomy:
[status icon] Claim text ........ [state]
                         [see evidence]

Example:
✓ Screen condition
  No crack visible in these photos
  SHOWN

Secondary:
[See photo]

Rules:
- claim first
- evidence second
- state is explicit
- photo is one tap away
- never hide evidence source

## 19.2 Evidence badge

Compact:
[Fieldwork mark] Evidence

Expanded:
Evidence captured
5 guided angles
1 unit identity marker

Never:
Verified
Certified
Guaranteed

## 19.3 Coverage summary

Example:
4 of 5 claims shown

Visual:
thin horizontal progress
+
numerical summary

Never:
92% trustworthy

## 19.4 Photo with annotation

Structure:
image
+
small evidence marker
+
highlight region
+
caption

Example:
[01] SCREEN
Crack visible in arrival photo

Avoid thick bounding boxes unless necessary.

Highlight box:
1.5–2px
rounded 4px
semantic state color.

---

# 20. EVIDENCE STATES

## SHOWN / MATCHES

Emotional message:
clear confirmation

Copy:
"Matches the listing."
"Shown in the listing photos."

Visual:
muted green
small check
no confetti
no celebration animation

## NOT SHOWN

Emotional message:
neutral absence

Copy:
"Not shown yet."
"No evidence captured for this claim."

Visual:
graphite / neutral grey

Never:
unproven
suspicious
questionable

## DIFFERS

Emotional message:
factual discrepancy

Copy:
"Differs: screen crack"
"Arrival photo shows a crack not visible in the listing evidence."

Visual:
oxide/rust-like semantic accent
amber-red family but muted
never bright warning red

Never:
fraud detected
seller lied
scam

## CAN'T TELL

Emotional message:
uncertainty + action

Copy:
"Can't tell from these photos."
"Take one more photo of the top edge."

Visual:
muted ochre
question/uncertainty icon

Never:
error
failed
insufficient data

## SYSTEM ERROR

Reserved for technical problems:
- upload failure
- authentication failure
- unexpected app issue

Do not confuse product uncertainty with technical error.

---

# 21. AI VISUAL LANGUAGE

AI IS A BEHAVIOR, NOT A COLOR.

Do not use:
- purple glow
- sparkle icon
- rainbow gradient
- orb
- constantly animated "AI brain"

AI should look like a quiet operator.

Preferred signals:
- subtle activity ring
- small status marker
- contextual source line
- progressive checklist
- photo highlight
- "AI" label
- compact reasoning card

## AI states

OBSERVING
"Looking at your photos…"

EXTRACTING
"Reading battery and storage…"

CHECKING
"Comparing this phone with the listing…"

NEEDS YOU
"One thing is still unclear."

SUGGESTING
"Suggested next step"

CAN'T ESTABLISH
"The photos don't establish this."

HUMAN REVIEW
"A person will confirm this."

DONE
"Evidence captured."

## AI agent card

Anatomy:
AI label
+
short current task
+
optional source/evidence
+
progress if meaningful

Do not expose chain-of-thought.

Do expose:
- relevant evidence
- source
- decision basis
- next action

---

# 22. AI + HUMAN AUTHORITY SYSTEM

Three distinct actors must be visually distinguishable:

AI:
small "AI" label
neutral visual treatment

System:
rule / workflow label
e.g. "Rule 4.2"

Human:
name + role
e.g. "Priya · Trust & Safety"

Example:

AI analysis
Crack visible in arrival photo 2.

Rule
Condition discrepancy under rule 4.2.

Human review
Priya · Trust & Safety
[Uphold buyer claim]

Never:
"AI decided"

The user should always understand:
what was observed
what was inferred
what rule applies
who has final authority

---

# 23. AI CHAT / ASK-THE-ITEM

The interface should feel like an object-specific inspection assistant, not a general chatbot.

User:
"Back mein dent hai?"

Fieldwork:
"Not shown clearly in the photos."

Evidence:
[photo crop]

CTA:
"Ask seller"

Rules:
- Answer only from public evidence.
- Cite the relevant photo.
- Do not invent.
- Do not infer hidden facts.
- Do not reveal serial/location/private fields.
- If evidence is missing, say so.
- Prefer short answers.

Bad:
"I think the phone probably doesn't have a dent."

Good:
"Not shown clearly. Take a closer photo of the back edge."

---

# 24. LISTING CREATION

The listing experience should feel like:
camera → extraction → confirmation
not:
form → form → form → form

Visual priority:
1. photo
2. streaming extraction
3. missing facts
4. coverage
5. price
6. publish

Use progressive disclosure.

Do not show a giant multi-field form upfront.

---

# 25. GUIDED CAMERA

Camera overlay:
- clean
- sparse
- no excessive HUD
- one instruction
- one progress signal

Capture geometry:
thin corner brackets

Progress:
5-step ring / segmented progress

Quality notices:
"Too dark"
"Move closer"
"Hold steady"

Do not use:
red flashing borders
military/cyber HUD style
dense technical readouts

Code-in-frame:
quiet and temporary
monospaced
small
expires without drama

---

# 26. PRICE SYSTEM

Money deserves its own visual hierarchy.

Price confirmation:
Large amount:
₹13,200

Supporting:
Your floor ₹12,800

Counterparty:
Arjun's agent

Action:
Confirm

Rules:
- amount always visible
- explicit confirmation
- clear counterparty
- no ambiguous swipe
- no auto-accept visual trickery
- undo window clearly stated

Price timeline:
Offer → Counter → Agreed

Latest amount gets strong emphasis.

Use Money semantic blue, not brand green.

---

# 27. HANDOVER — HERO EXPERIENCE

The hero screen should feel:
fast
quiet
confident

Header:
"Handover check"

Subheader:
"Verify the same phone in the same condition."

Three phases:
1. Photos
2. Match
3. Review

During analysis:
small AI activity
clear progress

At result:

MATCHES
"This phone matches the listing and is in the same condition."

DIFFERS
"Differs: screen crack"

CAN'T TELL
"Can't tell. Take one more photo of the top edge."

Result should be visually dominant but not theatrical.

No:
confetti
fireworks
green check explosion
giant "SUCCESS!!!"

---

# 28. CASE / DISPUTE UI

Case UI is evidence-first.

Reviewer console anatomy:

CASE #FW-XXXX
Status
Summary

Item
Buyer
Seller

Evidence
Listing
Handover
Arrival

AI analysis
Observation
Confidence only when meaningful
Source

Rule
Rule 4.2

Human decision
radio/select controls

Actions:
Uphold buyer
Uphold seller
Request more evidence

The decision surface must never look like a chatbot.

---

# 29. OUTCOME CARD

User-facing outcome should use four sections:

WHAT WE SAW
THE RULE
DECISION
APPEAL

Example:
What we saw
"Crack visible in arrival photo 2."

The rule
"Condition differences reported at handover may qualify for a repair credit."

Decision
"Repair credit recommended."

Appeal
"Appeal this decision"

Avoid legalistic language.

---

# 30. NAVIGATION

Mobile:
4–5 destinations maximum

Preferred:
Home
Buy
Sell
Help

Center floating Scan action is acceptable only when the product architecture requires it.

Rules:
- selected state uses subtle fill/underline/weight
- no neon indicators
- no excessive navigation chrome
- active item should be obvious without relying on color alone

---

# 31. NEXT-STEP HOME

The home screen should answer one question:

"What should I do next?"

Primary element:
Next-step card

Examples:
"Finish your listing"
"Check Arjun's offer"
"Complete handover"
"Review your open case"

One primary action.

Do not fill Home with analytics dashboards.

---

# 32. COMPONENT INVENTORY

Required components:

FOUNDATION
- Typography
- Icon
- Divider
- Surface
- Stack
- Grid
- Spacer

NAVIGATION
- Top bar
- Bottom navigation
- Tabs
- Breadcrumbs
- Back button

ACTIONS
- Button
- Icon button
- Button group
- Link
- Segmented control

INPUTS
- Text field
- Select
- Search
- Checkbox
- Radio
- Toggle
- OTP
- File/photo input
- Quick-answer chip

FEEDBACK
- Toast
- Banner
- Inline alert
- Progress
- Spinner
- Skeleton
- Empty state

COMMERCE
- Item card
- Price card
- Offer card
- Price timeline
- Protected payment status
- Handover result

EVIDENCE
- Evidence badge
- Claim row
- Coverage summary
- Photo viewer
- Annotated photo
- Evidence timeline
- Capture overlay
- Unit identity marker

AI
- AI activity
- AI message
- AI suggestion
- AI source/evidence citation
- AI uncertainty
- Human handoff

CASE
- Case card
- Evidence comparison
- Rule reference
- Reviewer decision
- Outcome card
- Appeal action

OVERLAYS
- Modal
- Bottom sheet
- Drawer
- Tooltip
- Popover
- Menu

---

# 33. COMPONENT STATE RULE

Every interactive component must define:

default
hover
focus-visible
pressed
disabled
loading
error (if applicable)
selected (if applicable)

For mobile touch:
hover is not a primary interaction state.

Never implement focus by removing the browser focus indication without replacing it.

---

# 34. MOTION

Motion should communicate state, not decorate the UI.

Principles:
- fast
- low amplitude
- reversible
- purposeful
- reduced-motion compatible

Durations:
Instant:
0–80ms

Micro:
100–160ms

Standard:
180–240ms

Emphasis:
260–360ms

Avoid >400ms in routine UI.

Approved motion:
- listing text progressively appearing
- capture progress
- image-region highlighting
- result transition
- bottom sheet
- toast
- state change

Not approved:
- floating blobs
- perpetual gradients
- pulsing buttons
- rotating AI logos
- confetti
- excessive spring bounce

---

# 35. RESPONSIVE BEHAVIOR

Primary viewport:
360–412dp mobile

Mobile rules:
- 16px page gutters
- 48px touch targets
- bottom sheets preferred to giant modals
- one primary action visible
- avoid horizontal scrolling
- images should remain large enough to inspect
- numbers should not wrap

Tablet:
increase content margins
retain hierarchy

Reviewer desktop:
1280px+

Use a deliberate three-zone structure:
1. case context
2. evidence
3. decision

Do not simply stretch the mobile UI onto desktop.

---

# 36. ACCESSIBILITY

Minimum:
WCAG AA-oriented contrast

Required:
- color-independent state communication
- keyboard navigation
- visible focus
- semantic HTML
- accessible labels
- screen-reader descriptions
- dynamic text support
- reduced motion
- touch target minimum 48px
- logical reading order

Do not:
- encode state only with color
- use tiny metadata as the only explanation
- hide crucial information behind hover
- rely on animation to communicate progress

---

# 37. CONTENT / VOICE

VOICE:
calm, fair, practical, human

Sentence style:
short
specific
direct

Preferred:
"Take one more photo of the top edge."

Avoid:
"Uh-oh! We couldn't verify your item."

Preferred:
"Can't tell from these photos."

Avoid:
"Oops! Our AI isn't sure what happened."

Preferred:
"Shown in 4 of 5 angles."

Avoid:
"Your item has an impressive 80% evidence score!"

Use natural Hinglish where appropriate:
"Back mein dent hai?"

Do not force formal Hindi.

AI messages:
short
task-focused
explicitly labelled

Human support:
role + first name

---

# 38. COPY BANNED LIST

NEVER USE unless legally required and explicitly reviewed:

Verified
Certified
Guaranteed
Fraud detected
Seller lied
Scam
Suspicious seller
Trust score
AI decided
100% safe
Proven genuine
Authentic (unless the specific verification scope justifies it)
No risk
Safe seller

Preferred alternatives:

Shown
Not shown
Differs
Can't tell
Read from screen
Visible in photo
Not checkable from photos
A person will confirm this
Based on rule X
Evidence badge
Evidence captured

---

# 39. EMPTY / LOADING / FAILURE STATES

EMPTY:
helpful and neutral

Example:
"No listings yet."
CTA:
"Sell something"

LOADING:
show what is actually happening

"Reading your photos…"

FAILURE:
state the problem + recovery action

"Upload failed."
"Try again"

OFFLINE:
"Offline — your changes will sync when you're back online."

Do not:
- blame the user
- use technical stack traces
- say "Something went terribly wrong"

---

# 40. 3D / GLASS / VISUAL EFFECTS POLICY

Fieldwork is NOT a glassmorphism brand.

Default:
flat editorial surfaces

Glass can be used only for:
- temporary camera overlays
- image controls
- system chrome over photography

Glass rules:
- low blur
- high legibility
- no floating rainbow effects
- no translucent cards over everything

3D can be used only for:
- marketing hero art
- conceptual illustrations
- item visualization when it adds real utility

The product UI itself should remain mostly 2D and precise.

---

# 41. VISUAL DENSITY

Default density:
comfortable

The product should never look like:
- a trading terminal
- enterprise administration software
- a dashboard from 2018

On evidence-heavy screens:
increase information density through hierarchy, not smaller text.

Use:
large evidence photo
medium claim
small metadata

Not:
small everything.

---

# 42. DESIGN PATTERNS FOR KEY SCREENS

## HOME

Visual structure:
1. compact brand/header
2. hero statement
3. next-step card
4. search
5. recent activity
6. bottom navigation

Tone:
warm editorial

## LISTING CAPTURE

Visual structure:
camera dominates
progress
single instruction
AI extraction sheet

Tone:
instrument-like

## ITEM DETAIL

Visual structure:
photo
price
small attributes
evidence tab
claim rows
ask-the-item

Tone:
editorial marketplace

## PRICE AGREEMENT

Visual structure:
offer amount
floor/ceiling context
price timeline
one primary CTA

Tone:
financially precise

## HANDOVER

Visual structure:
capture
progress
result
evidence

Tone:
quiet confidence

## CASE

Visual structure:
facts
evidence
rule
decision

Tone:
human review, not AI spectacle

---

# 43. DESIGN TOKEN JSON — SOURCE OF TRUTH

Use these values as the semantic baseline.

```json
{
  "color": {
    "brand": {
      "forest": "#123A34",
      "mineral": "#2F6C63",
      "mineralDark": "#24574F",
      "sage": "#82978F",
      "oxide": "#B6784D"
    },
    "neutral": {
      "parchment": "#F3EFE6",
      "paper": "#FAF8F3",
      "inset": "#ECE9E0",
      "stone": "#C9C1B4",
      "ink": "#171C19",
      "graphite": "#4E5853",
      "muted": "#737B76",
      "white": "#FFFFFF"
    },
    "semantic": {
      "matches": {
        "fg": "#28644F",
        "bg": "#E4EEE8",
        "border": "#BFD7CA"
      },
      "notShown": {
        "fg": "#646863",
        "bg": "#ECEBE6",
        "border": "#D6D4CD"
      },
      "differs": {
        "fg": "#A65342",
        "bg": "#F4E4DE",
        "border": "#E2BEB4"
      },
      "cantTell": {
        "fg": "#8A6A2E",
        "bg": "#F1E9D5",
        "border": "#DCC990"
      },
      "system": {
        "fg": "#5E5A96",
        "bg": "#ECEAF7",
        "border": "#CDC9E7"
      },
      "money": {
        "fg": "#2D5B88",
        "bg": "#E7EEF6",
        "border": "#C5D5E7"
      }
    }
  },
  "radius": {
    "sm": "4px",
    "control": "8px",
    "card": "12px",
    "feature": "16px",
    "sheet": "20px",
    "hero": "24px"
  },
  "space": {
    "1": "4px",
    "2": "8px",
    "3": "12px",
    "4": "16px",
    "5": "20px",
    "6": "24px",
    "8": "32px",
    "10": "40px",
    "12": "48px",
    "16": "64px",
    "20": "80px",
    "24": "96px"
  },
  "type": {
    "displayXL": ["56px", "64px"],
    "displayL": ["44px", "52px"],
    "displayM": ["36px", "44px"],
    "headingXL": ["32px", "40px"],
    "headingL": ["28px", "36px"],
    "headingM": ["24px", "32px"],
    "headingS": ["20px", "28px"],
    "bodyL": ["18px", "28px"],
    "body": ["16px", "24px"],
    "bodyS": ["14px", "20px"],
    "label": ["13px", "18px"],
    "meta": ["12px", "16px"],
    "button": ["15px", "20px"],
    "numericXL": ["40px", "44px"],
    "numericL": ["32px", "36px"],
    "numericM": ["24px", "28px"]
  }
}
```

---

# 44. CSS VARIABLES

Recommended root variables:

```css
:root {
  --fw-brand-forest: #123A34;
  --fw-brand-mineral: #2F6C63;
  --fw-brand-mineral-dark: #24574F;
  --fw-brand-sage: #82978F;
  --fw-brand-oxide: #B6784D;

  --fw-neutral-parchment: #F3EFE6;
  --fw-neutral-paper: #FAF8F3;
  --fw-neutral-inset: #ECE9E0;
  --fw-neutral-stone: #C9C1B4;
  --fw-neutral-ink: #171C19;
  --fw-neutral-graphite: #4E5853;
  --fw-neutral-muted: #737B76;

  --fw-match-fg: #28644F;
  --fw-match-bg: #E4EEE8;
  --fw-match-border: #BFD7CA;

  --fw-not-shown-fg: #646863;
  --fw-not-shown-bg: #ECEBE6;
  --fw-not-shown-border: #D6D4CD;

  --fw-differs-fg: #A65342;
  --fw-differs-bg: #F4E4DE;
  --fw-differs-border: #E2BEB4;

  --fw-cant-tell-fg: #8A6A2E;
  --fw-cant-tell-bg: #F1E9D5;
  --fw-cant-tell-border: #DCC990;

  --fw-system-fg: #5E5A96;
  --fw-system-bg: #ECEAF7;
  --fw-system-border: #CDC9E7;

  --fw-money-fg: #2D5B88;
  --fw-money-bg: #E7EEF6;
  --fw-money-border: #C5D5E7;

  --fw-radius-control: 8px;
  --fw-radius-card: 12px;
  --fw-radius-feature: 16px;
  --fw-radius-sheet: 20px;

  --fw-page-gutter-mobile: 16px;
  --fw-page-gutter-desktop: 32px;
}
```

---

# 45. HOST THEME CONTRACT

Host theme variables:

```css
[data-host-theme] {
  --fw-host-primary: var(--fw-brand-mineral);
  --fw-host-primary-strong: var(--fw-brand-mineral-dark);
  --fw-host-on-primary: #FFFFFF;
}
```

Use host colors only for:
- primary actions
- host-selected navigation
- links
- host-brand accents

Never overwrite:
--fw-match-*
--fw-not-shown-*
--fw-differs-*
--fw-cant-tell-*
--fw-system-*
--fw-money-*

---

# 46. FONT LOADING

Preferred packages:
@ibm/plex-sans
@ibm/plex-sans-devanagari
@ibm/plex-serif
@ibm/plex-mono
@ibm/plex-sans-jp
@ibm/plex-sans-kr

Use local/self-hosted or project-managed fonts when possible.

Do not depend on a single third-party web font request for critical rendering.

---

# 47. DO NOT IMPROVISE RULES

1. Never add a new color casually.
2. Never introduce purple/blue AI gradients.
3. Never use a shield as the primary trust metaphor.
4. Never use sparkles to represent AI.
5. Never make every component a rounded card.
6. Never use giant pill buttons.
7. Never use pure white as the default page background.
8. Never use bright red for an ordinary evidence discrepancy.
9. Never call an item "verified" unless a separately approved product rule defines exactly what was verified.
10. Never show a fabricated confidence number.
11. Never represent "can't tell" as an error.
12. Never use color as the only state indicator.
13. Never create a second primary CTA on a screen without a product reason.
14. Never hide critical evidence behind a tooltip.
15. Never use animation without a semantic purpose.
16. Never make AI look more authoritative than a human reviewer.
17. Never expose private item evidence to public item views.
18. Never mix icon families.
19. Never use arbitrary spacing.
20. Never use emoji as product UI icons.
21. Never let host branding alter evidence semantics.
22. Never replace evidence with decorative illustration.
23. Never style the reviewer console like a chatbot.
24. Never create a dashboard when a focused workflow is required.
25. Never sacrifice readability to make the UI look "minimal."

---

# 48. VIBE-CODING / AI IMPLEMENTATION RULES

Before coding:
1. Inspect the existing component system.
2. Identify whether shadcn/Radix or another primitive system already exists.
3. Reuse existing primitives where behavior is correct.
4. Replace their styling through Fieldwork tokens.
5. Build missing Fieldwork components as local, open code.
6. Do not introduce a second component framework solely for one screen.

For every new screen:
1. identify its primary task;
2. select an existing pattern;
3. use existing tokens;
4. use existing components;
5. implement all relevant states;
6. check responsive behavior;
7. perform a visual consistency pass.

For every new component:
- define anatomy
- define props/variants
- define state behavior
- define accessibility
- define responsive behavior
- define semantic color usage

---

# 49. VISUAL QA CHECKLIST

Before considering a screen complete, ask:

BRAND
- Does this look like Fieldwork rather than generic SaaS?
- Does it feel calm and precise?
- Is the brand color restrained?

TYPOGRAPHY
- Is the hierarchy immediately clear?
- Are numbers visually important when money/evidence is involved?
- Is body text readable at 16px?
- Does Devanagari retain the same hierarchy?

COLOR
- Is the page mostly neutral?
- Is semantic color used only where it carries meaning?
- Could the state still be understood in grayscale?

LAYOUT
- Is there one primary action?
- Is there enough whitespace?
- Are cards being used only when they create real grouping?

AI
- Is AI visible enough to be accountable?
- Is it visually subordinate to evidence and human decisions?
- Does uncertainty have a next action?

EVIDENCE
- Can the user see what supports the claim?
- Is source/context visible?
- Is "can't tell" treated neutrally?

MOTION
- Does every animation communicate something?

WHITE LABEL
- Would the system still work if the host color changed?

---

# 50. KEY SCREEN VISUAL RECIPES

## Recipe A — Item card

Layout:
Image
↓
Title + price
↓
compact attributes
↓
Evidence coverage
↓
primary action

Visual:
large photography
little chrome
one evidence strip

Example:
iPhone 13
₹24,999

128 GB · Battery 87%

4 of 5 claims shown

[Make offer]

## Recipe B — Evidence claim

Title
"Screen condition"

Support
"No crack visible in these photos"

State
SHOWN

Source
"Photo 4 · back angle"

## Recipe C — AI extraction

Top:
AI

Main:
"Reading battery and storage…"

Checklist:
✓ Model
✓ Storage
○ Battery

No chatbot bubbles.

## Recipe D — Handover result

Headline:
"Matches"

Supporting:
"This phone matches the listing and is in the same condition."

Evidence:
5/5 checks
20 sec

Primary:
"Complete handover"

Secondary:
"View full report"

## Recipe E — Dispute outcome

Headline:
"Case reviewed"

What we saw:
"Crack visible in arrival photo 2."

The rule:
"Condition differences reported at handover are covered."

Decision:
"Repair credit recommended."

Action:
"Appeal"

---

# 51. IMPLEMENTATION PRIORITY

Build in this order:

PHASE 1
- tokens
- typography
- surfaces
- button
- field
- icon button
- badge/tag
- navigation

PHASE 2
- item card
- claim row
- evidence badge
- coverage
- photo viewer
- AI activity
- AI message

PHASE 3
- guided camera
- price agreement
- handover result
- case card
- outcome card

PHASE 4
- reviewer console
- white-label theming
- motion polish
- accessibility audit
- visual regression

Do not begin by creating dozens of custom components.

---

# 52. SOURCE / RESEARCH BASIS FOR THE IMPLEMENTATION APPROACH

This system intentionally uses established open design-system practices while creating a distinct Fieldwork visual language.

Reference principles:
- GitHub Primer separates foundations, patterns, components, responsive rules and accessibility.
- Radix provides unstyled, composable, accessibility-focused primitives suitable as a base layer.
- shadcn/ui uses open component code and composable interfaces.

Fieldwork-specific decisions above are product/design decisions, not claims that any one reference system mandates them.

---

# 53. FINAL AGENT INSTRUCTION

Treat this document as a DESIGN CONTRACT.

When asked to build or modify Fieldwork UI:
- read this file first;
- inspect existing components;
- reuse and extend;
- use the tokens;
- do not invent a new aesthetic;
- do not default to generic AI UI;
- do not default to generic shadcn UI;
- visually inspect the implemented screen;
- fix deviations from this contract before declaring the work complete.

The desired result is:

PREMIUM
+
MINIMAL
+
EDITORIAL
+
PRECISE
+
HUMAN
+
EVIDENCE-FIRST

Not:

AI DASHBOARD
Not:
GENERIC MARKETPLACE
Not:
CYBERSECURITY PRODUCT
Not:
FINTECH TEMPLATE

FIELDWORK SHOULD FEEL LIKE A PRECISION INSTRUMENT THAT HAPPENS TO BE EASY TO USE.
