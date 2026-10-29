"""Generates the sample receipt photos used by the simulator and tests. Run once: python fixtures/make_receipts.py"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "receipts"
OUT.mkdir(exist_ok=True)

RECEIPTS = {
    "harbor_table.jpg": {
        "merchant": "Harbor Table", "city": "Chicago", "total": 412.00, "guest_count": 4,
        "occurred_at": "2026-10-27T21:52:00-05:00",
        "lines": ["HARBOR TABLE", "312 N Clark St, Chicago IL", "Tue Oct 27 2026  9:52 PM", "Table 14   Guests: 4", "",
                  "Branzino            48.00", "Ribeye              64.00", "Short rib           42.00", "Risotto             34.00",
                  "Wine, Barolo       118.00", "Dessert x2          26.00", "Sparkling water     24.00", "",
                  "Subtotal           356.00", "Tax                 36.00", "Tip                 20.00", "TOTAL              412.00",
                  "", "VISA ****4471", "Thank you"],
        "items": [{"name": "Branzino", "amount": 48}, {"name": "Ribeye", "amount": 64}, {"name": "Short rib", "amount": 42},
                  {"name": "Risotto", "amount": 34}, {"name": "Wine, Barolo", "amount": 118}, {"name": "Dessert x2", "amount": 26},
                  {"name": "Sparkling water", "amount": 24}],
        "rep_id": "rep_maya", "order": 1,
        "label": "Client dinner, Chicago. Calendar + CRM both match (auto-tag path).",
    },
    "blue_door.jpg": {
        "merchant": "Blue Door Coffee", "city": "Oakland", "total": 18.40, "guest_count": None,
        "occurred_at": "2026-10-29T13:12:00-07:00",
        "lines": ["BLUE DOOR COFFEE", "Oakland, CA", "Thu Oct 29 2026  1:12 PM", "", "Latte               6.50", "Latte               6.50",
                  "Almond croissant    5.40", "", "TOTAL              18.40", "", "VISA ****4471"],
        "items": [{"name": "Latte", "amount": 6.5}, {"name": "Latte", "amount": 6.5}, {"name": "Almond croissant", "amount": 5.4}],
        "rep_id": "rep_maya", "order": 2,
        "label": "Coffee with no attendees on the calendar. Agent asks which account (clarify path).",
    },
    "osteria_nove.jpg": {
        "merchant": "Osteria Nove", "city": "San Francisco", "total": 1240.00, "guest_count": 6,
        "occurred_at": "2026-10-14T21:52:00-07:00",
        "lines": ["OSTERIA NOVE", "San Francisco, CA", "Wed Oct 14 2026  9:52 PM", "Guests: 6", "", "Tasting menu x6    840.00",
                  "Wine pairing x4    280.00", "", "Subtotal          1120.00", "Tax                 97.00", "Tip                 23.00",
                  "TOTAL             1240.00", "", "AMEX ****1002"],
        "items": [{"name": "Tasting menu x6", "amount": 840}, {"name": "Wine pairing x4", "amount": 280}],
        "rep_id": "rep_tom", "order": 3,
        "label": "Tom's Pinecrest team dinner. Already seeded; re-sending shows the over-limit routing.",
    },
}


def main():
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for name, r in RECEIPTS.items():
        h = 60 + 30 * len(r["lines"]) + 40
        img = Image.new("RGB", (520, h), (250, 249, 245))
        d = ImageDraw.Draw(img)
        y = 30
        for line in r["lines"]:
            d.text((40, y), line, fill=(30, 30, 30), font=font)
            y += 30
        img.save(OUT / name, quality=88)
        side = {k: v for k, v in r.items() if k != "lines"}
        (OUT / name).with_suffix(".json").write_text(json.dumps(side, indent=2))
        print("wrote", name)


if __name__ == "__main__":
    main()
