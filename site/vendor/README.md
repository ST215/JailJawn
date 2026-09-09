# Vendored libraries

## pretext 0.0.9

`layout.js` and the modules it imports are the unmodified `dist/` build of
[@chenglou/pretext](https://github.com/chenglou/pretext) by Cheng Lou, MIT
licensed. It measures and lays out text without touching the DOM, and it is
what places every glyph in the crowd on the front page.

Vendored so the site has no build step and no runtime dependency on a CDN.
To update: fetch the new `dist/` files from the npm package and replace these.
