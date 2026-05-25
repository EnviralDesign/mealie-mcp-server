# Shopping List Examples

## Add Request

User:

```text
Cucumber
Bell pepper orange
Bread
Sliced Turkey or chicken
Mozzarella cheese sticks
Fresh fruits
Box of salad
2 frozen pizzas
Almond milk
2% milk
Cereal that is not 100% garbage (contains fiber and/or protein)
Coffee
Leinenkugels for today
```

Better normalized list:

- `1 cucumber` linked to food `cucumber`.
- `1 bell pepper orange` linked to food `bell pepper`, note `orange`.
- `Bread` note-only, label `bakery`.
- `Sliced turkey or chicken` note-only, label `meat & seafood`.
- `mozzarella cheese sticks` linked to food `mozzarella cheese sticks`.
- `Fresh fruits` note-only, label `produce`.
- `Box of salad` note-only, label `produce`.
- `2 frozen pizzas` linked to food `frozen pizza`.
- `almond milk` linked to food `almond milk`.
- `2% milk` linked to food `2% milk`.
- `cereal` linked to food `cereal`, note `not 100% garbage (contains fiber and/or protein)`.
- `whole bean coffee` linked to food `whole bean coffee`.
- `beer` linked to food `beer`, note `Leinenkugel's for today`.

## Avoid

Do not create canonical foods like:

- `cereal that is not 100% garbage`
- `Leinenkugel's beer`
- `fresh fruits`
- `sliced turkey or chicken`
- `box of salad`
