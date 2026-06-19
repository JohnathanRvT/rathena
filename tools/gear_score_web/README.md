# Gear Score Simulator

This is a standalone web application for simulating rAthena equipment setups and calculating their Gear Score.

## Prerequisites

- Python 3.x
- Flask
- PyYAML

You can install the dependencies using pip:

```bash
pip install Flask PyYAML
```

## How to Run

1.  Navigate to the repository root.
2.  Run the application:

    ```bash
    python3 tools/gear_score_web/app.py
    ```

3.  Open your web browser and go to `http://localhost:5000`.

## How to Use

- **Search Item**: Click on the "Search item..." box in any equipment slot and type the name or ID of the item you want to equip. Select the item from the dropdown list.
- **Refine**: Enter the refinement level (0-20) in the "Refine" box. The score increases exponentially with the refine level (`refine * refine * 10`).
- **Cards**: Enter the IDs of the cards you wish to slot (up to 4 per item). Each card adds a flat 50 points to the score.
- **Dynamic Score**: The "Total Gear Score" and the slot-by-slot breakdown on the right update automatically as you make changes.

## Scoring Formula

The score for each item is calculated as:
`Score = (ItemLevel * 100) + ATK + MATK + (DEF * 5) + (Refine^2 * 10) + (Cards * 50)`
