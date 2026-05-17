# DevStack UI Rules

This document defines the UI standard for both DevStack interfaces:

- the Python desktop app
- the web dashboard

The target is not a creative dashboard look. The target is a plain, calm, Windows 11 style utility UI.

## Goal

DevStack is a utility app.

It should feel:

- native to Windows
- simple
- quiet
- readable
- predictable
- fast to scan

It should not feel:

- decorative
- playful
- card-heavy
- neon
- gradient-heavy
- like a startup landing page

## Design Basis

These rules follow the same direction as Microsoft Windows / Fluent guidance:

- natural on the platform
- built for focus
- low visual noise
- primary action is clear
- secondary actions have less weight
- use Segoe UI and standard Windows spacing

## Product Layout Rule

Every screen must follow this order:

1. page title
2. one short supporting line if needed
3. main actions
4. status or content list
5. optional logs or details lower on the page

Do not mix all of these at the same visual weight.

## Surface Rule

Do not use floating cards as the default layout pattern.

Use these only:

- window background
- flat sections
- flat rows
- simple dividers

### Background

- App/page background: light neutral gray
- Content sections: white
- Inputs: slightly off-white
- No dark panels unless the whole app is dark mode
- No random black or navy surfaces inside a light app

### Borders

- Use soft gray borders
- Prefer `1px` borders
- Border radius should be restrained
- Standard radius: `8px`
- Section radius can be `0px` if the layout is list-first

### Shadows

- Avoid shadows by default
- Do not use shadows just to make panels look modern
- Only use subtle elevation if there is a true overlay, popup, or dialog

## Color Rule

Use color for meaning, not decoration.

### Base colors

- Background: neutral light gray
- Surfaces: white
- Primary text: near-black
- Secondary text: medium gray
- Muted text: softer gray
- Borders: very light gray

### Accent color

Use one Windows-like blue accent.

Use accent only for:

- selected tab
- primary button
- focus ring
- active link

Do not tint entire layouts blue.

### State colors

Use these states only:

- running: green
- warning / partial: amber
- stopped / error: red

State colors are for:

- badges
- inline status labels
- minimal row border change if truly needed

Do not flood large sections with red, green, or amber.

## Typography Rule

Use `Segoe UI` as the main font.

Use `Cascadia Code` only for logs or code.

### Type scale

- Page title: 24px, semibold or bold
- Section title: 15px to 16px, semibold
- Row title: 14px to 16px, semibold
- Body text: 13px
- Caption/meta text: 11px to 12px

### Text behavior

- Left align text
- Do not center large blocks of copy
- Keep helper text short
- Avoid using bold everywhere
- One strong text element per group is enough

## Button Rule

Buttons must follow Fluent-like hierarchy.

### Primary button

Use for the single most important action in the area.

Examples:

- `Start All`
- `Save`

Rules:

- filled accent background
- white text
- only one primary button in a button group

### Secondary button

Use for non-destructive alternate actions.

Examples:

- `Restart`
- `Open`
- `Refresh`

Rules:

- white or neutral background
- gray border
- accent text only if needed

### Destructive button

Use only for actual destructive or stopping actions.

Examples:

- `Stop`

Rules:

- red fill only when the action is truly destructive or interruptive
- do not put many red buttons everywhere unless necessary

### Button layout

- one primary action per group
- secondary buttons must not visually overpower the main action
- if there are many equal actions, use neutral outline buttons instead of making all of them filled

### Button text

Use short, direct labels:

- `Start`
- `Stop`
- `Restart`
- `Open`
- `Save`
- `Refresh`
- `Close`

Do not use vague labels.

## Spacing Rule

Use a consistent spacing system.

Base scale:

- `4px`
- `8px`
- `12px`
- `16px`
- `20px`
- `24px`

Default usage:

- row gap: `8px` to `12px`
- section padding: `16px` to `20px`
- page padding: `24px`
- large section gap: `20px` to `24px`

Do not use random spacing values unless there is a clear reason.

## Status Rule

Status should be obvious but not loud.

### Good

- one summary line at top
- a compact status badge on each service row
- optional short helper text below summary

### Bad

- giant colored panels
- too many counters
- repeated status messages in every section
- status shown with both border, background, dot, and headline all competing at once

## Row Rule

Service information should use rows, not dashboard tiles.

Each service row should contain:

- service name
- one short role/description
- port/process metadata in a low-emphasis line
- status badge
- actions on the right

The row should be readable in one horizontal scan.

## Logs Rule

Logs are secondary.

- logs should not dominate the main UI
- logs should be manual by default
- logs should sit behind a lower-priority section or separate tab
- logs should not use a dramatically different visual language from the rest of the app

If the app is light, logs should either:

- stay light, or
- move into a clearly intentional code/log surface without affecting the rest of the screen

## Settings Rule

Settings should be plain forms.

- group related settings in flat sections
- labels on the left or above, consistently
- no decorative metric blocks in settings
- save/reset actions at the bottom right or bottom row

## Web Dashboard Rule

The web version must follow the same rules as the desktop app.

- same hierarchy
- same button priority
- same light neutral background
- same restrained color usage
- same service row structure

Do not make the web dashboard more decorative than the desktop app.

## Things We Must Not Do Again

- no random dark panel inside a light UI
- no excessive shadow usage
- no dashboard cards as the default pattern
- no heavy colored borders around every block
- no multiple filled buttons of equal importance in the same group
- no random gradient styling
- no inconsistent radius between controls
- no text that is too low contrast
- no duplicate status logic across tabs

## Standard Component Rules

### Window background

- light neutral gray

### Section background

- white

### Section border

- 1px light gray

### Text

- primary: near-black
- secondary: medium gray
- caption: muted gray

### Primary button

- filled blue
- white text
- one per group

### Secondary button

- white background
- gray border
- dark or blue text

### Danger button

- filled red only for stop/destructive actions

### Badges

- pill shape
- small
- state color only in the badge itself

## Rebuild Order

When rebuilding the UI, do it in this order:

1. fix layout structure
2. fix spacing and alignment
3. fix type hierarchy
4. fix button hierarchy
5. add restrained status color
6. only then add any polish

If polish breaks clarity, remove the polish.

## Definition Of Done

The UI is acceptable only when:

- it looks calm on first glance
- the main action is obvious in under 2 seconds
- service rows are scannable without effort
- no surface looks random or out of place
- desktop app and web dashboard feel like the same product
- it feels closer to Windows Settings / Task Manager utility discipline than a template dashboard
