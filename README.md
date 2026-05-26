# PrintThreadWizard
**PrintThread Wizard** is a Fusion 360 add-in for creating 3D-printable threads directly on selected cylindrical faces.  The goal of this project is not to generate standard-compliant engineering threads, but to create practical, robust and easy-to-print thread geometry for FDM/FFF 3D printing.

The add-in is designed to help makers, engineers, students and 3D-printing enthusiasts quickly add functional threads to bolts, holes and cylindrical features inside Autodesk Fusion 360.

---

## Project Goal

PrintThread Wizard creates thread geometry that is optimized for 3D printing.

Instead of focusing on strict ISO, metric or industrial thread standards, the add-in focuses on:

- Reliable printability
- Support-free geometry
- Adjustable thread clearance
- Robust thread profiles
- Easy parameter selection
- Usable results for printed prototypes, fixtures and maker projects

The add-in should make it simple to select a cylindrical face, choose a thread preset from a list, adjust a few print-related parameters and generate the thread directly in the Fusion 360 model.

---

## Planned Features

- Select cylindrical faces in Fusion 360
  - External thread on a bolt
  - Internal thread inside a hole

- Thread selection using a list-based wizard interface

- 3D-print-friendly thread profiles
  - Non-standard but practical geometry
  - Reduced overhangs
  - Support-free printing where possible

- Adjustable parameters
  - Thread diameter
  - Pitch
  - Thread depth
  - Clearance
  - Thread length
  - Direction
  - Internal / external thread mode

- Presets for common 3D-printing use cases

- Geometry generation using the Fusion 360 Python API

- Workflow and interface inspired by the Insert Wizard add-in

---

## Why Not Standard Threads?

Standard thread profiles are often designed for machining, injection molding or metal parts.

For FDM 3D printing, these profiles are not always ideal because they may require:

- Very fine details
- Sharp peaks and valleys
- Tight tolerances
- Unsupported overhangs
- Post-processing or thread tapping

PrintThread Wizard focuses on printable and functional threads instead. The generated threads may not follow official standards, but they should be easier to print and more reliable for typical 3D-printed parts.

---

## Target Use Cases

PrintThread Wizard is intended for:

- 3D-printed enclosures
- Screw caps and lids
- Prototype parts
- RC model components
- Workshop fixtures
- Educational models
- Maker projects
- Functional printed assemblies

---

## Development Status

This project is currently in the planning and concept phase.

The implementation will be developed later using:

- Python
- Autodesk Fusion 360 API
- Visual Studio Code
- OpenAI Codex-assisted development

At this stage, the focus is on:

- Project structure
- User workflow
- Add-in architecture
- Thread profile concept
- Parameter model
- GitHub documentation

---

## Repository Structure

The final structure may look similar to this:

```text
PrintThreadWizard/
├── PrintThreadWizard.py
├── PrintThreadWizard.manifest
├── commands/
│   └── print_thread_command.py
├── lib/
│   ├── thread_profiles.py
│   ├── thread_presets.py
│   ├── geometry_builder.py
│   └── fusion_helpers.py
├── resources/
│   ├── icons/
│   └── logo/
├── docs/
│   ├── concept.md
│   ├── development_notes.md
│   └── thread_design.md
├── README.md
└── LICENSE
