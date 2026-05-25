# Product Search

## Search Inputs

Use the canonical food plus relevant note:

- food `beer`, note `Leinenkugel's` -> query `Leinenkugel beer`
- food `bell pepper`, note `orange` -> query `orange bell pepper`
- food `whole bean coffee` -> query `whole bean coffee`
- recipe ingredient `fresh ginger, chopped` -> query `fresh ginger`

Always pass `location_id="03500445"` unless the user changed stores.

## Candidate Judgment

Prefer:

- in-store availability,
- ordinary household package sizes,
- recognizable grocery products,
- mid-range or store-brand options,
- clean package-size data.

Avoid:

- restaurant/prepared-food products unless requested,
- giant bulk products,
- tiny novelty packages,
- unrelated flavor variants,
- organic-only matches when a normal product exists,
- sale-only logic for persistent recipe pricing.

## Package Sizes

Capture the unit basis before using a product:

- ounces or pounds for meats, cheese, produce, dry goods,
- fluid ounces for liquids,
- count for discrete items,
- bunch/package for herbs when Kroger lacks a better quantity.

If the package size cannot be translated to the recipe unit, record the assumption instead of pretending the number is exact.
