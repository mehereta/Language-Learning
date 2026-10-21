# Daily language practice

Two small installable web apps for learning everyday phrases.

| Folder | App | Language |
|---|---|---|
| `amharic/` | Tinish Tinish | Amharic |
| `polish/` | Krok po kroku | Polish |

The top-level `index.html` is the home page that links to both apps.

## Releasing an update to one app
1. Change files inside that app's folder only.
2. If you changed anything besides `index.html` (icons, manifest, audio), bump `VERSION` in that folder's `sw.js`.

## Adding another language
Copy one app folder, give it a new name, and change the storage key (`KEY`), backup id, and cache prefix in its `sw.js` so it doesn't share data with the others. Then add a card to the top-level `index.html`.
