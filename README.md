# photos

Wallpaper / screensaver photos for the [Google TV launcher](https://github.com/rahinroy/GoogleTV),
served straight off `raw.githubusercontent.com` so the TV picks up new pictures
without rebuilding or reinstalling the APK.

## Layout

```
photos/                       the image files themselves
screensaver.json              generated manifest the launcher fetches
scripts/build_manifest.py     regenerates the manifest from photos/
.github/workflows/build-manifest.yml   runs that script on every photo change
```

## Adding or removing photos

Drop `.jpg` / `.jpeg` / `.png` / `.webp` files into `photos/` and push (or upload
them through the GitHub web UI). The **Build screensaver manifest** workflow runs
on any change under `photos/`, rewrites `screensaver.json`, and commits it back.
Nothing else to do — the TV re-fetches the manifest on its own.

Deleting a photo works the same way; the workflow drops it from the manifest.

## Manifest format

```json
{
  "count": 48,
  "images": [
    {
      "url": "https://raw.githubusercontent.com/rahinroy/photos/main/photos/PXL_20230723_013604267.jpg",
      "lat": 36.623869,
      "lon": -121.940319,
      "taken": "2023-07-22T18:36:04"
    }
  ]
}
```

`lat` / `lon` / `taken` come from each photo's EXIF and are **omitted** when the
photo has none. The file is deterministic for a given photo set — there is no build
timestamp — so the workflow only commits when the photos actually changed. The launcher uses them for the place/date overlay in the
top-right of the home screen: it reverse-geocodes the coordinates on-device
(nothing is looked up here) and formats `taken` as "July 22, 2023".

The launcher also accepts a bare `["url", ...]` array, so this object shape is a
superset — hand-editing the file down to a plain list still works.

## Running the generator locally

```bash
pip install pillow
python scripts/build_manifest.py
```

It writes `screensaver.json` in place. The URL base defaults to
`rahinroy/photos@main`; in CI it is taken from `GITHUB_REPOSITORY` and
`GITHUB_REF_NAME`, so a fork or a renamed branch generates correct URLs
automatically.

## Notes

- **`raw.githubusercontent.com` caches for about 5 minutes.** After the workflow commits
  a new `screensaver.json`, the TV can still see the previous one for a few minutes.
  Nothing is wrong — wait it out. (The launcher fetches the manifest once at start, so
  a new photo shows up on its next restart anyway.)
- Keep individual files under GitHub's 100 MB hard limit. `raw.githubusercontent.com`
  has no published rate limit but is not a CDN contract — it is fine for one TV.
- Photos are downloaded once and disk-cached by Coil on the device, so a large
  file costs bandwidth only on first display.
