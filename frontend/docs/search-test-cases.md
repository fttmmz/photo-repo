# Frontend search test cases

Search is performed against the authenticated photo list in the browser using a literal, case-insensitive substring match. It does not interpret the query as a regular expression, so punctuation and digits remain significant.

| Search query | Expected result with `Image(2).jpg` and `Image(3).jpg` |
|---|---|
| `Image(2)` | Only `Image(2).jpg` |
| `Image(3)` | Only `Image(3).jpg` |
| `Image` | Both files |
| `(3)` | Only `Image(3).jpg` |
| `image(2)` | Only `Image(2).jpg` |

The browser filters the full list returned by `GET /photos`. This avoids relying on backend search implementations that might treat parentheses as regular-expression syntax. The API's `/photos/search` route remains documented in `config.example.js` for future server-side pagination/search integration.
