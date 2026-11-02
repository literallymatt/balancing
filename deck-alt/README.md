# deck-alt

A restyled copy of the deck in [`../deck/`](../deck/), with the same slides, order,
sections, hidden slides and speaker notes. Only the look differs. The original deck
is unchanged.

The style aims for a conventional corporate analyst deck:

- White slides, Arial throughout, navy (`#1F3864`) and mid blue (`#2E75B6`) with greys.
- Left-aligned action titles over a navy rule, with the section name small and
  grey in the top right instead of an uppercase kicker.
- Square-cornered boxes with no coloured accent bars, gradients or icons.
- Charts in navy and grey, with forecasts as pale dashed bars.

Same file layout as `deck/`: `project/deck.json` is the index and
`project/slides/<id>.html` holds one slide each, with speaker notes in `<aside>`.
It is published as its own Slides artifact, separate from the original:
https://claude.ai/artifact/3hwpN79THXMAGQsEicz87S
